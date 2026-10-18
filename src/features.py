"""Generic match-level summary features from StatsBomb events."""
from __future__ import annotations

import pandas as pd

ON_TARGET = ["Goal", "Saved", "Saved to Post"]


def get_teams(events: pd.DataFrame) -> list[str]:
    """The two team names of a match."""
    return list(events["team"].dropna().unique())


def regular_play(events: pd.DataFrame) -> pd.DataFrame:
    """Drop period 5 (penalty shootout) so it doesn't pollute shot stats."""
    return events[events["period"] <= 4]


def shot_summary(events: pd.DataFrame) -> pd.DataFrame:
    """Shots, shots on target, goals and total xG per team."""
    shots = regular_play(events)
    shots = shots[shots["type"] == "Shot"]
    grouped = shots.groupby("team")
    return pd.DataFrame({
        "shots": grouped.size(),
        "on_target": grouped["shot_outcome"].apply(lambda s: s.isin(ON_TARGET).sum()),
        "goals": grouped["shot_outcome"].apply(lambda s: (s == "Goal").sum()),
        "xg": grouped["shot_statsbomb_xg"].sum().round(2),
        "shot_accuracy_%": (100 * grouped["shot_outcome"].apply(lambda s: s.isin(ON_TARGET).sum()) / grouped.size()).round(1),
        "shot_share_%": (100 * grouped.size() / grouped.size().sum()).round(1)
    })


def pass_summary(events: pd.DataFrame) -> pd.DataFrame:
    """Passes, completed passes, accuracy and share of all passes per team.

    In StatsBomb, a pass with no `pass_outcome` is a completed pass.
    The pass share is a common possession proxy.
    """
    passes = regular_play(events)
    passes = passes[passes["type"] == "Pass"]
    grouped = passes.groupby("team")
    out = pd.DataFrame({
        "passes": grouped.size(),
        "completed": grouped["pass_outcome"].apply(lambda s: s.isna().sum()),
    })
    out["pass_accuracy_%"] = (100 * out["completed"] / out["passes"]).round(1)
    out["pass_share_%"] = (100 * out["passes"] / out["passes"].sum()).round(1)
    return out


def match_summary(events: pd.DataFrame) -> pd.DataFrame:
    """One table with shots + passes per team."""
    return shot_summary(events).join(pass_summary(events))


def xg_timeline(events: pd.DataFrame) -> pd.DataFrame:
    """Cumulative xG per team by minute (rows = minutes, columns = teams)."""
    shots = regular_play(events)
    shots = shots[shots["type"] == "Shot"]
    per_minute = shots.pivot_table(
        index="minute", columns="team", values="shot_statsbomb_xg", aggfunc="sum"
    ).fillna(0)
    full_range = range(0, int(regular_play(events)["minute"].max()) + 1)
    return per_minute.reindex(full_range, fill_value=0).cumsum()

import numpy as np


def passing_network(events: pd.DataFrame, team: str, min_passes: int = 3):
    """Nodes and edges of a team's pass network (starting XI, before first substitution).

    Needs x, y columns: run add_xy(events) first.
    Returns:
        nodes: one row per player (x, y = average pass location, passes = completed passes)
        edges: one row per player pair with at least `min_passes` passes between them
    """
    team_ev = regular_play(events)
    team_ev = team_ev[team_ev["team"] == team]

    subs = team_ev[team_ev["type"] == "Substitution"]
    cutoff = subs["index"].min() if len(subs) else float("inf")

    passes = team_ev[
        (team_ev["type"] == "Pass")
        & (team_ev["pass_outcome"].isna())        # no outcome = completed
        & (team_ev["index"] < cutoff)             # before the first substitution
    ].dropna(subset=["pass_recipient", "x", "y"])

    nodes = passes.groupby("player").agg(
        x=("x", "mean"), y=("y", "mean"), passes=("player", "size")
    )

    # sort each (passer, recipient) pair so A->B and B->A count as the same link
    pairs = pd.DataFrame(
        np.sort(passes[["player", "pass_recipient"]].to_numpy(), axis=1),
        columns=["player_a", "player_b"],
    )
    edges = pairs.value_counts().rename("passes").reset_index()
    edges = edges[
        (edges["passes"] >= min_passes)
        & edges["player_a"].isin(nodes.index)
        & edges["player_b"].isin(nodes.index)
    ].reset_index(drop=True)

    for side in ("a", "b"):
        edges[f"x_{side}"] = edges[f"player_{side}"].map(nodes["x"])
        edges[f"y_{side}"] = edges[f"player_{side}"].map(nodes["y"])
    return nodes, edges

def event_locations(events, event_types, team=None):
    """Located events of the given types (list), optionally for one team. Needs x, y."""
    ev = regular_play(events)
    ev = ev[ev["type"].isin(event_types)]
    if team:
        ev = ev[ev["team"] == team]
    return ev.dropna(subset=["x", "y"])


def pressing_summary(events):
    """Pressures per team and where they happen (x >= 60 opp. half, x >= 80 final third)."""
    p = event_locations(events, ["Pressure"])
    grouped = p.groupby("team")["x"]
    return pd.DataFrame({
        "pressures": grouped.size(),
        "opp_half_%": grouped.apply(lambda s: 100 * (s >= 60).mean()).round(1),
        "final_third_%": grouped.apply(lambda s: 100 * (s >= 80).mean()).round(1),
    })