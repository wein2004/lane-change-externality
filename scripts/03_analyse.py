"""Quantify the lane-change externality and test whether trucks impose more of it.

Three questions, in order:
  Q-A  Does a lane change cost the follower anything at all, once you compare
       against matched moments with no lane change?
  Q-B  Is the cost larger when the lane-changer is a truck than a car?
  Q-C  Does congestion amplify the gap?

Outputs
  outputs/tables/03_results.md   human-readable results
  outputs/results.json           machine-readable, consumed by 04_figures.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import ngsim  # noqa: E402

RNG_SEED = 20260919
N_BOOT = 5000

# Labels must match scripts/02_detect_events.py::attach_regime.
REGIMES = ["heavy", "light"]
REGIME_LABEL = {"heavy": "Heavy congestion (<25 km/h)",
                "light": "Lighter traffic (>=25 km/h)"}


def boot_mean_diff(
    a: np.ndarray, b: np.ndarray, n_boot: int = N_BOOT, seed: int = RNG_SEED
) -> dict[str, float]:
    """Bootstrap the difference in means, mean(a) - mean(b)."""
    rng = np.random.default_rng(seed)
    a, b = np.asarray(a, float), np.asarray(b, float)
    a, b = a[np.isfinite(a)], b[np.isfinite(b)]
    base = {
        "mean_a": float(a.mean()) if len(a) else np.nan,
        "mean_b": float(b.mean()) if len(b) else np.nan,
        "n_a": int(len(a)),
        "n_b": int(len(b)),
    }
    if len(a) < 2 or len(b) < 2:
        # Too few observations to resample. Report the counts and say so rather
        # than emitting a point estimate that looks like a finding.
        return {**base, "diff": np.nan, "lo": np.nan, "hi": np.nan}
    draws = np.empty(n_boot)
    for i in range(n_boot):
        draws[i] = rng.choice(a, len(a), replace=True).mean() - rng.choice(
            b, len(b), replace=True
        ).mean()
    lo, hi = np.percentile(draws, [2.5, 97.5])
    return {**base, "diff": float(a.mean() - b.mean()),
            "lo": float(lo), "hi": float(hi)}


def describe(s: pd.Series) -> dict[str, float]:
    s = s.dropna()
    return {
        "n": int(len(s)),
        "mean": float(s.mean()) if len(s) else np.nan,
        "median": float(s.median()) if len(s) else np.nan,
        "p90": float(s.quantile(0.9)) if len(s) else np.nan,
    }


def num(x: float, nd: int = 2) -> str:
    """Format a number, or say "n/a" instead of printing nan."""
    return f"{x:.{nd}f}" if np.isfinite(x) else "n/a"


def fmt_ci(d: dict, unit: str = "km/h") -> str:
    if not np.isfinite(d.get("diff", np.nan)):
        return f"insufficient sample (n={d.get('n_a', 0)} vs {d.get('n_b', 0)})"
    return f"{d['diff']:+.2f} {unit}  (95% CI {d['lo']:+.2f} .. {d['hi']:+.2f}), n={d['n_a']} vs {d['n_b']}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--processed", default="data/processed")
    args = parser.parse_args()

    p = Path(args.processed)
    events = pd.read_parquet(p / "events.parquet")
    controls = pd.read_parquet(p / "controls.parquet")

    # Motorcycles are a negligible and behaviourally distinct class; drop them
    # so "car vs truck" means what it says.
    events = events[events["v_class"].isin([ngsim.CLASS_AUTO, ngsim.CLASS_TRUCK])]

    out: dict = {"n_events": int(len(events)), "n_controls": int(len(controls))}
    md: list[str] = [
        "# Results: the cost of one lane change, and who imposes more of it",
        "",
        f"Events analysed: **{len(events):,}**  ·  matched controls: **{len(controls):,}**",
        "",
    ]

    # ---------------------------------------------------------------- Q-A --
    md += ["## Q-A — Is there a cost at all?", ""]
    qa = boot_mean_diff(events["drop_kmh"].to_numpy(), controls["drop_kmh"].to_numpy())
    out["qa_drop_vs_control"] = qa
    md += [
        f"- Follower speed drop after a lane change: **{num(qa['mean_a'])} km/h**",
        f"- Same statistic at matched no-lane-change moments: **{num(qa['mean_b'])} km/h**",
        f"- Attributable excess: **{fmt_ci(qa)}**",
        "",
    ]
    qa_rec = boot_mean_diff(
        events["recovery_s"].to_numpy(), controls["recovery_s"].to_numpy()
    )
    out["qa_recovery_vs_control"] = qa_rec
    md += [f"- Excess recovery time: **{fmt_ci(qa_rec, 's')}**", ""]

    # ---------------------------------------------------------------- Q-B --
    md += ["## Q-B — Do trucks cost more than cars?", ""]
    truck = events[events["v_class"] == ngsim.CLASS_TRUCK]
    car = events[events["v_class"] == ngsim.CLASS_AUTO]
    out["n_truck_events"] = int(len(truck))
    out["n_car_events"] = int(len(car))

    qb = boot_mean_diff(truck["drop_kmh"].to_numpy(), car["drop_kmh"].to_numpy())
    qb_rec = boot_mean_diff(truck["recovery_s"].to_numpy(), car["recovery_s"].to_numpy())
    out["qb_truck_vs_car_drop"] = qb
    out["qb_truck_vs_car_recovery"] = qb_rec
    md += [
        f"- Truck-initiated lane change: **{num(qb['mean_a'])} km/h** drop (n={qb['n_a']})",
        f"- Car-initiated lane change:   **{num(qb['mean_b'])} km/h** drop (n={qb['n_b']})",
        f"- Truck penalty: **{fmt_ci(qb)}**",
        f"- Truck penalty in recovery time: **{fmt_ci(qb_rec, 's')}**",
        "",
    ]

    # ---------------------------------------------------------------- Q-C --
    md += ["## Q-C — Does congestion amplify it?", ""]
    out["qc"] = {}
    for regime in REGIMES:
        t = truck[truck["regime"] == regime]["drop_kmh"].to_numpy()
        c = car[car["regime"] == regime]["drop_kmh"].to_numpy()
        d = boot_mean_diff(t, c)
        out["qc"][regime] = d
        md.append(f"- **{REGIME_LABEL[regime]}**: truck penalty {fmt_ci(d)}")
    md.append("")

    # Absolute cost by regime, for the business framing.
    out["cost_by_regime"] = {}
    md += ["### Absolute follower cost by regime and class", "",
           "| regime | class | n | mean drop (km/h) | median recovery (s) |",
           "|---|---|---:|---:|---:|"]
    for regime in REGIMES:
        for label, sub in [("car", car), ("truck", truck)]:
            s = sub[sub["regime"] == regime]
            d = describe(s["drop_kmh"])
            r = describe(s["recovery_s"])
            out["cost_by_regime"][f"{regime}|{label}"] = {"drop": d, "recovery": r}
            md.append(
                f"| {REGIME_LABEL[regime]} | {label} | {d['n']} | "
                f"{num(d['mean'])} | {num(r['median'])} |"
            )
    md.append("")

    # --------------------------------------------------------- exposure ----
    exposure_path = p / "exposure.parquet"
    if exposure_path.exists():
        exp = pd.read_parquet(exposure_path)
        agg = exp.groupby("class_label", as_index=False)[
            ["vehicles", "vehicle_hours", "lane_changes"]
        ].sum()
        agg["changes_per_vehicle_hour"] = (
            agg["lane_changes"] / agg["vehicle_hours"]
        )
        out["exposure"] = agg.to_dict(orient="records")
        md += [
            "## How often does each class change lanes?",
            "",
            "The per-event penalty has a small truck sample. This does not — it",
            "uses every observed truck-second, not only the trucks that changed",
            "lanes.",
            "",
            "| class | vehicles | vehicle-hours | lane changes | changes / vehicle-hour |",
            "|---|---:|---:|---:|---:|",
        ]
        for _, r in agg.iterrows():
            md.append(
                f"| {r['class_label']} | {int(r['vehicles']):,} | "
                f"{r['vehicle_hours']:.1f} | {int(r['lane_changes']):,} | "
                f"{r['changes_per_vehicle_hour']:.2f} |"
            )
        md.append("")
        car_rate = agg.loc[agg["class_label"] == "car", "changes_per_vehicle_hour"]
        truck_rate = agg.loc[agg["class_label"] == "truck", "changes_per_vehicle_hour"]
        if len(car_rate) and len(truck_rate) and truck_rate.iloc[0] > 0:
            ratio = car_rate.iloc[0] / truck_rate.iloc[0]
            out["car_to_truck_rate_ratio"] = float(ratio)
            md += [f"Cars change lanes **{ratio:.1f}x** as often per hour as trucks.",
                   ""]
        elif len(truck_rate) and truck_rate.iloc[0] == 0:
            md += ["No truck lane changes survived the filters in this sample.", ""]

    # ------------------------------------------------------- regression ----
    md += ["## Controlling for confounders", "",
           "A truck penalty could just reflect *where* and *when* trucks change",
           "lanes. This regression holds those constant.", ""]
    reg = run_regression(events)
    out["regression"] = reg["coefs"]
    md += ["```", reg["summary"], "```", ""]

    Path("outputs/tables").mkdir(parents=True, exist_ok=True)
    Path("outputs/tables/03_results.md").write_text("\n".join(md), encoding="utf-8")
    Path("outputs/results.json").write_text(
        json.dumps(out, indent=2, default=float), encoding="utf-8"
    )
    print("\n".join(md))
    return 0


def run_regression(events: pd.DataFrame) -> dict:
    """OLS: follower speed drop ~ truck + traffic state + site."""
    import statsmodels.formula.api as smf

    d = events.copy()
    d["site_c"] = (d["site"] == "us-101").astype(int)
    d = d.replace([np.inf, -np.inf], np.nan).dropna(
        subset=["drop_kmh", "is_truck", "baseline_kmh", "space_headway",
                "local_mean_kmh"]
    )
    if d["is_truck"].nunique() < 2 or d["is_truck"].sum() < 10:
        msg = (
            f"Regression skipped: only {int(d['is_truck'].sum())} truck events "
            "in the estimation sample. With a truck indicator this sparse the "
            "coefficient would be driven by a handful of observations and would "
            "imply a precision the data does not support. The bootstrap "
            "confidence intervals above remain the honest summary."
        )
        return {"summary": msg, "coefs": {}, "skipped": True}
    # Congestion enters continuously (local mean speed) rather than as a
    # threshold dummy: the question is whether the truck penalty grows as
    # traffic slows, and a dummy throws away most of that variation.
    model = smf.ols(
        "drop_kmh ~ is_truck + local_mean_kmh + is_truck:local_mean_kmh"
        " + baseline_kmh + space_headway + site_c",
        data=d,
    ).fit(cov_type="HC3")
    return {
        "skipped": False,
        "summary": str(model.summary().tables[1]),
        "coefs": {
            k: {"coef": float(v), "p": float(model.pvalues[k])}
            for k, v in model.params.items()
        },
    }


if __name__ == "__main__":
    sys.exit(main())
