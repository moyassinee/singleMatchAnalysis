"""Plot helpers."""
import matplotlib.pyplot as plt
from mplsoccer import VerticalPitch,Pitch


def plot_xg_timeline(timeline, goals=None, ax=None):
    """Step plot of cumulative xG. Optionally mark goals: [(minute, team), ...]."""
    if ax is None:
        _, ax = plt.subplots(figsize=(9, 4))
    for team in timeline.columns:
        ax.step(timeline.index, timeline[team], where="post", label=team, linewidth=2)
    if goals:
        for minute, team in goals:
            ax.scatter(minute, timeline.loc[minute, team], s=80, zorder=3, edgecolor="black")
    ax.set_xlabel("Minute")
    ax.set_ylabel("Cumulative xG")
    ax.legend()
    return ax.figure


def plot_shot_map(pitch,shots, team, ax=None):
    """Half-pitch shot map for one team. Marker size = xG, goals in red and labeled."""
    if ax is None:
        _, ax = plt.subplots(figsize=(6, 6))
    pitch.draw(ax=ax)

    df = shots[shots["team"] == team]
    #marker size scales with xG value 900 * stretches xG (a number between 0 and 1) into a visible size,
    # and 80 + makes sure even tiny-xG shots are still visible.
    size = 80 + 900 * df["shot_statsbomb_xg"].fillna(0.05)

    is_goal = df["shot_outcome"] == "Goal"
    pitch.scatter(df.loc[~is_goal, "x"], df.loc[~is_goal, "y"],
                  s=size[~is_goal], c="#999", alpha=0.5, edgecolor="black", ax=ax)
    pitch.scatter(df.loc[is_goal, "x"], df.loc[is_goal, "y"],
                  s=size[is_goal], c="#d62728", alpha=0.95, edgecolor="black", ax=ax)

    for _, row in df[is_goal].iterrows():
        pitch.annotate(row["player"].split()[-1], xy=(row["x"], row["y"]),
                       xytext=(row["x"] - 4, row["y"]), ax=ax, fontsize=9, ha="center")

    ax.set_title(f"{team}: {len(df)} shots, {df['shot_statsbomb_xg'].sum():.2f} xG")
    return ax.figure

def plot_pass_network(pitch,nodes, edges, team, labels=None, ax=None):
    """Pass network on a full pitch. `labels` is an optional {full_name: short_name} dict."""
    labels = labels or {}
    if ax is None:
        _, ax = plt.subplots(figsize=(9, 6))
    pitch.draw(ax=ax)

    pitch.lines(edges["x_a"], edges["y_a"], edges["x_b"], edges["y_b"],
                lw=0.6 * edges["passes"], color="#1f77b4", alpha=0.5, zorder=1, ax=ax)
    pitch.scatter(nodes["x"], nodes["y"], s=60 + 12 * nodes["passes"],
                  c="#d62728", edgecolor="white", linewidth=1.5, zorder=2, ax=ax)
    for player, row in nodes.iterrows():
        name = labels.get(player, player.split()[-1])   # default: last word of the name
        pitch.annotate(name, xy=(row["x"], row["y"] + 4.5), ha="center", va="center",
                       fontsize=9, zorder=3, ax=ax)
    ax.set_title(f"{team}: pass network (starting XI, before first substitution)")
    return ax.figure

def plot_heatmap(df,pitch, title="", bins=(6, 5), cmap="Reds", ax=None):
    """Zone heatmap of event counts. df needs x, y columns (StatsBomb 120x80 pitch)."""
    if ax is None:
        _, ax = plt.subplots(figsize=(9, 6))
    pitch.draw(ax=ax)
    stat = pitch.bin_statistic(df["x"], df["y"], statistic="count", bins=bins)
    pitch.heatmap(stat, ax=ax, cmap=cmap, edgecolors="white", alpha=0.85)
    pitch.label_heatmap(stat, ax=ax, str_format="{:.0f}", fontsize=11, ha="center", va="center")
    ax.set_title(title)
    return ax.figure