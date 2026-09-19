"""Figures for the lane-change externality analysis.

  fig1_speed_profile.png   mean follower speed trace: control vs car vs truck
  fig2_cost_by_regime.png  attributable speed drop, by regime and vehicle class
  fig3_truck_penalty.png   truck-minus-car penalty with bootstrap CIs

Palette: categorical slots 1-3 of the reference palette (blue / orange / aqua),
validated all-pairs for normal and CVD vision at 3 series. Every series is
direct-labelled as well as coloured, so identity is never carried by colour
alone; the same numbers appear as a table in outputs/tables/03_results.md.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import ngsim  # noqa: E402

# Reference palette, light mode.
C_CAR = "#2a78d6"  # slot 1, blue
C_TRUCK = "#eb6834"  # slot 2, orange
C_CONTROL = "#1baf7a"  # slot 3, aqua
INK = "#0b0b0b"
INK_2 = "#52514e"
GRID = "#e6e5e1"
SURFACE = "#fcfcfb"

PRE_START = -40  # must match scripts/02_detect_events.py
# Regime labels must match scripts/02_detect_events.py::attach_regime.
REGIME_LABEL = {
    "light": "Lighter traffic\n(>= 25 km/h)",
    "heavy": "Heavy congestion\n(< 25 km/h)",
}
FRAME_S = ngsim.FRAME_SECONDS


def style() -> None:
    plt.rcParams.update({
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "axes.edgecolor": GRID,
        "axes.labelcolor": INK_2,
        "axes.titlecolor": INK,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "text.color": INK,
        "xtick.color": INK_2,
        "ytick.color": INK_2,
        "grid.color": GRID,
        "grid.linewidth": 0.8,
        "font.size": 10,
        "figure.dpi": 150,
        "savefig.bbox": "tight",
    })


def boot_ci(x: np.ndarray, n: int = 2000, seed: int = 20260919) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if len(x) < 2:
        return (np.nan, np.nan)
    draws = rng.choice(x, size=(n, len(x)), replace=True).mean(axis=1)
    return tuple(np.percentile(draws, [2.5, 97.5]))


# --------------------------------------------------------------------------- #
def fig_speed_profile(events, controls, ev_prof, ctl_prof, out: Path) -> None:
    """The money chart: how the follower's speed dips and recovers."""
    t = (np.arange(ev_prof.shape[1]) + PRE_START) * FRAME_S

    series = [
        ("No lane change (matched control)", ctl_prof, C_CONTROL),
        ("Car changes in front", ev_prof[events["v_class"].to_numpy() == ngsim.CLASS_AUTO], C_CAR),
        ("Truck changes in front", ev_prof[events["v_class"].to_numpy() == ngsim.CLASS_TRUCK], C_TRUCK),
    ]

    fig, ax = plt.subplots(figsize=(9.6, 4.6))
    ax.grid(axis="y", zorder=0)
    ax.axvline(0, color=INK_2, lw=1, ls=(0, (4, 3)), zorder=1)

    for label, arr, color in series:
        if arr is None or len(arr) == 0:
            continue
        m = np.nanmean(arr, axis=0) * 100
        ax.plot(t, m, color=color, lw=2, zorder=3, solid_capstyle="round")
        # Direct label at the right edge; no legend box needed.
        ax.annotate(
            f"{label}  (n={len(arr):,})",
            xy=(t[-1], m[-1]),
            xytext=(6, 0),
            textcoords="offset points",
            color=color,
            fontsize=9,
            va="center",
            fontweight="medium",
        )

    ax.set_xlabel("Seconds relative to the lane change")
    ax.set_ylabel("Follower speed\n(% of its own pre-event baseline)")
    ax.set_title(
        "Matched until the manoeuvre, different after it — "
        "and a truck cutting in is not what hurts",
        fontsize=12, pad=12, loc="left",
    )
    # Reserve the right of the x-range for direct labels, so no legend box is
    # needed and nothing collides with the traces.
    ax.set_xlim(t[0], t[-1] + 0.62 * (t[-1] - t[0]))
    # Ticks only where there is data; the right margin exists for the labels.
    ax.set_xticks(np.arange(np.ceil(t[0] / 2) * 2, t[-1] + 0.01, 2))
    ax.margins(y=0.18)
    # Placed after plotting, in axes-fraction y, so it tracks the final ylim.
    ax.annotate("lane change", xy=(0.15, 0.97), xycoords=("data", "axes fraction"),
                color=INK_2, fontsize=9, va="top", ha="left")
    fig.savefig(out, facecolor=SURFACE)
    plt.close(fig)
    print(f"wrote {out}")


def fig_cost_by_regime(events, controls, out: Path) -> None:
    """Grouped bars: mean follower speed drop by regime and who changed lanes."""
    regimes = ["light", "heavy"]
    groups = [
        ("No lane change", C_CONTROL, lambda r: controls[controls["regime"] == r]),
        ("Car", C_CAR, lambda r: events[(events["regime"] == r) & (events["v_class"] == ngsim.CLASS_AUTO)]),
        ("Truck", C_TRUCK, lambda r: events[(events["regime"] == r) & (events["v_class"] == ngsim.CLASS_TRUCK)]),
    ]

    fig, ax = plt.subplots(figsize=(7.4, 4.4))
    ax.grid(axis="y", zorder=0)
    width = 0.24
    x = np.arange(len(regimes))

    for i, (label, color, sel) in enumerate(groups):
        means, los, his, ns = [], [], [], []
        for r in regimes:
            v = sel(r)["drop_kmh"].to_numpy()
            v = v[np.isfinite(v)]
            means.append(v.mean() if len(v) else np.nan)
            lo, hi = boot_ci(v)
            los.append(lo)
            his.append(hi)
            ns.append(len(v))
        pos = x + (i - 1) * (width + 0.02)
        # 2px surface gap between adjacent bars comes from the +0.02 offset.
        bars = ax.bar(pos, means, width, color=color, zorder=3,
                      label=label, linewidth=0)
        ax.errorbar(pos, means, yerr=[np.array(means) - np.array(los),
                                      np.array(his) - np.array(means)],
                    fmt="none", ecolor=INK_2, elinewidth=1.2, capsize=3, zorder=4)
        for b, m, hi, n in zip(bars, means, his, ns):
            if not np.isfinite(m):
                continue
            # Above the CI whisker, not the bar top, so the two never collide.
            top = hi if np.isfinite(hi) else m
            ax.annotate(f"{m:.1f}", (b.get_x() + b.get_width() / 2, top),
                        xytext=(0, 7), textcoords="offset points",
                        ha="center", fontsize=9, color=INK)
            ax.annotate(f"n={n:,}", (b.get_x() + b.get_width() / 2, 0),
                        xytext=(0, 4), textcoords="offset points",
                        ha="center", fontsize=7.5, color=INK_2)

    ax.set_xticks(x, [REGIME_LABEL[r] for r in regimes])
    ax.set_ylabel("Follower speed drop (km/h)")
    ax.set_title("Cost imposed on the following vehicle, by traffic state",
                 fontsize=12, pad=52, loc="left")
    # Legend sits in its own band between the title and the plot, so a tall
    # confidence interval can never collide with it.
    leg = ax.legend(frameon=False, ncol=3, loc="lower left",
                    bbox_to_anchor=(0, 1.0))
    for txt in leg.get_texts():
        txt.set_color(INK_2)
    ax.set_ylim(bottom=0)
    ax.margins(y=0.22)
    fig.savefig(out, facecolor=SURFACE)
    plt.close(fig)
    print(f"wrote {out}")


def fig_truck_penalty(events, out: Path) -> None:
    """Dot plot: truck-minus-car excess, overall and by regime, with 95% CIs."""
    rng = np.random.default_rng(20260919)
    rows = []
    for label, sub in [("All traffic", events),
                       ("Lighter traffic", events[events["regime"] == "light"]),
                       ("Heavy congestion", events[events["regime"] == "heavy"])]:
        t = sub[sub["v_class"] == ngsim.CLASS_TRUCK]["drop_kmh"].to_numpy()
        c = sub[sub["v_class"] == ngsim.CLASS_AUTO]["drop_kmh"].to_numpy()
        t, c = t[np.isfinite(t)], c[np.isfinite(c)]
        if len(t) < 2 or len(c) < 2:
            rows.append((label, np.nan, np.nan, np.nan, len(t), len(c)))
            continue
        draws = np.array([
            rng.choice(t, len(t), True).mean() - rng.choice(c, len(c), True).mean()
            for _ in range(3000)
        ])
        lo, hi = np.percentile(draws, [2.5, 97.5])
        rows.append((label, t.mean() - c.mean(), lo, hi, len(t), len(c)))

    fig, ax = plt.subplots(figsize=(7.8, 3.2))
    ax.grid(axis="x", zorder=0)
    labels: list[tuple[float, str]] = []
    ax.axvline(0, color=INK_2, lw=1, zorder=2)
    y = np.arange(len(rows))[::-1]
    for yi, (label, d, lo, hi, nt, nc) in zip(y, rows):
        if not np.isfinite(d):
            ax.annotate("sample too small", (0, yi), xytext=(8, 0),
                        textcoords="offset points", va="center",
                        color=INK_2, fontsize=9)
            continue
        ax.plot([lo, hi], [yi, yi], color=C_TRUCK, lw=2,
                solid_capstyle="round", zorder=3)
        ax.plot([d], [yi], "o", ms=9, color=C_TRUCK,
                mec=SURFACE, mew=2, zorder=4)
        labels.append((yi, f"{d:+.2f} km/h   (n={nt} trucks vs {nc:,} cars)"))

    # All value labels share one x, so they form a clean column instead of
    # tracking the ragged right end of each interval.
    finite_hi = [r[3] for r in rows if np.isfinite(r[3])]
    label_x = max(finite_hi) if finite_hi else 0.0
    span = ax.get_xlim()[1] - ax.get_xlim()[0]
    for yi, text in labels:
        ax.annotate(text, (label_x + 0.04 * span, yi), xytext=(0, 0),
                    textcoords="offset points", va="center", color=INK,
                    fontsize=9)

    ax.set_yticks(y, [r[0] for r in rows])
    ax.set_xlabel("Extra speed drop imposed by a truck vs a car  (km/h, 95% CI)")
    ax.set_title(
        "There is no truck penalty - the sign points the other way",
        fontsize=12, pad=12, loc="left",
    )
    ax.set_ylim(-0.6, len(rows) - 0.4)
    ax.margins(x=0.45)
    fig.savefig(out, facecolor=SURFACE)
    plt.close(fig)
    print(f"wrote {out}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--processed", default="data/processed")
    parser.add_argument("--out", default="outputs/figures")
    args = parser.parse_args()

    style()
    p = Path(args.processed)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    events = pd.read_parquet(p / "events.parquet")
    controls = pd.read_parquet(p / "controls.parquet")
    ev_prof = np.load(p / "events_profiles.npy")
    ctl_prof = np.load(p / "controls_profiles.npy")

    keep = events["v_class"].isin([ngsim.CLASS_AUTO, ngsim.CLASS_TRUCK]).to_numpy()
    events, ev_prof = events[keep].reset_index(drop=True), ev_prof[keep]

    fig_speed_profile(events, controls, ev_prof, ctl_prof,
                      out / "fig1_speed_profile.png")
    fig_cost_by_regime(events, controls, out / "fig2_cost_by_regime.png")
    fig_truck_penalty(events, out / "fig3_truck_penalty.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
