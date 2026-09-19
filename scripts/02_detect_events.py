"""Detect lane-change events and build a matched control group.

For every discretionary lane change on a freeway mainline we record how the
vehicle that ends up directly behind the lane-changer responds, and we record
the same response statistic at matched moments where no lane change happened.
The difference between the two is the externality attributable to the manoeuvre.

Outputs
  data/processed/events.parquet          real lane-change events + response
  data/processed/controls.parquet        matched pseudo-events + response
  outputs/tables/02_detection_summary.md counts at every filter stage
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import ngsim  # noqa: E402

# --------------------------------------------------------------------------- #
# Tunables (all in frames; 1 frame = 0.1 s)
# --------------------------------------------------------------------------- #
STABLE_FRAMES = 30  # 3.0 s of stable lane membership required either side
PRE_START, PRE_END = -40, -10  # baseline window: -4.0 s .. -1.0 s
POST_END = 50  # response window: 0 .. +5.0 s
RECOVERY_END = 100  # recovery searched up to +10.0 s
RECOVERY_FRACTION = 0.95  # "recovered" = back to 95% of baseline speed
SETTLE_FRAMES = 5  # read the new follower 0.5 s after the change

# Congestion regime: mean speed of surrounding traffic, km/h.
# 25 km/h, not the textbook 40: both NGSIM freeway sites were recorded in
# the peak, and local mean speed spans roughly 5-47 km/h with a median near
# 24. A 40 km/h cut would label 99% of the sample "congested" and the
# comparison would be empty. See docs/decision-log.md D6.
CONGESTION_KMH = 25.0
REGIME_BIN_FRAMES = 300  # 30 s aggregation window for local traffic state

CANDIDATES_PER_EVENT = 40  # candidate windows offered to the matcher per control
MIN_POOL = 20_000

RNG_SEED = 20260919

RESPONSE_COLUMNS = [
    "baseline_kmh",
    "vmin_kmh",
    "drop_kmh",
    "drop_pct",
    "recovery_s",
    "recovery_censored",
    "pre_trend_kmh",
    "headway_pre_ft",
    "headway_at_t",
]


# --------------------------------------------------------------------------- #
# Lane-change detection
# --------------------------------------------------------------------------- #
def detect_lane_changes(df: pd.DataFrame) -> pd.DataFrame:
    """Return one row per clean, discretionary mainline lane change."""
    g = df.groupby("traj_key", observed=True)
    prev_lane = g["lane_id"].shift(1)
    changed = prev_lane.notna() & (df["lane_id"] != prev_lane)

    events = df.loc[changed, ["traj_key", "site", "period", "vehicle_id",
                              "frame_id", "lane_id", "v_class", "following",
                              "speed_kmh", "space_headway"]].copy()
    events = events.rename(columns={"lane_id": "lane_to"})
    events["lane_from"] = prev_lane.loc[changed].astype("int8")

    # Stability: the vehicle must have held the origin lane for STABLE_FRAMES
    # before, and hold the target lane for STABLE_FRAMES after. This removes
    # weaving (several changes in quick succession) and detector flicker, both
    # of which would otherwise be counted as separate events.
    lane_run = _lane_run_lengths(df)
    events["run_before"] = lane_run["run_before"].loc[changed].to_numpy()
    events["run_after"] = lane_run["run_after"].loc[changed].to_numpy()

    return events


def _lane_run_lengths(df: pd.DataFrame) -> pd.DataFrame:
    """For every frame: frames held in the current lane before / after it."""
    key = df["traj_key"].to_numpy()
    lane = df["lane_id"].to_numpy()
    new_run = np.empty(len(df), dtype=bool)
    new_run[0] = True
    new_run[1:] = (key[1:] != key[:-1]) | (lane[1:] != lane[:-1])
    run_id = np.cumsum(new_run)

    run_sizes = pd.Series(run_id).groupby(run_id).transform("size").to_numpy()
    pos_in_run = np.arange(len(df)) - np.maximum.accumulate(
        np.where(new_run, np.arange(len(df)), 0)
    )
    return pd.DataFrame(
        {
            # frames already spent in this lane at this frame
            "run_before_here": pos_in_run,
            # frames remaining in this lane from this frame onwards
            "run_after": run_sizes - pos_in_run,
            # frames spent in the *previous* lane, i.e. the run that just ended
            "run_before": _previous_run_length(run_id, run_sizes, new_run),
        },
        index=df.index,
    )


def _previous_run_length(run_id, run_sizes, new_run) -> np.ndarray:
    """Length of the run immediately preceding the current one."""
    starts = np.flatnonzero(new_run)
    sizes_by_run = run_sizes[starts]
    prev_sizes = np.concatenate([[0], sizes_by_run[:-1]])
    out = np.zeros(len(run_id), dtype=np.int32)
    out[starts] = prev_sizes
    return out


# --------------------------------------------------------------------------- #
# Follower response
# --------------------------------------------------------------------------- #
def build_frame_index(df: pd.DataFrame) -> dict:
    """Map (traj_key, frame_id) -> positional row index, for O(1) window lookup."""
    return {
        "speed": df["speed_kmh"].to_numpy(),
        "headway": df["space_headway"].to_numpy(),
        "lookup": pd.Series(
            np.arange(len(df)),
            index=pd.MultiIndex.from_arrays([df["traj_key"], df["frame_id"]]),
        ),
    }


def measure_response(
    speed: np.ndarray, start_idx: int, n_frames: int
) -> dict[str, float] | None:
    """Baseline / drop / recovery statistics for one follower window.

    `start_idx` is the positional index of frame (t + PRE_START) inside a
    contiguous trajectory block of length `n_frames` starting there.
    """
    if n_frames < (RECOVERY_END - PRE_START):
        return None
    w = speed[start_idx : start_idx + (RECOVERY_END - PRE_START)]
    pre = w[0 : (PRE_END - PRE_START)]
    post = w[(-PRE_START) : (-PRE_START) + POST_END]

    baseline = float(np.mean(pre))
    if baseline <= 1.0:  # effectively stopped; a "slowdown" is meaningless
        return None

    v_min = float(np.min(post))
    drop = baseline - v_min
    argmin = int(np.argmin(post))

    tail = w[(-PRE_START) + argmin :]
    recovered = np.flatnonzero(tail >= RECOVERY_FRACTION * baseline)
    if len(recovered):
        recovery_frames = int(recovered[0])
        censored = False
    else:
        recovery_frames = RECOVERY_END - argmin
        censored = True

    return {
        "baseline_kmh": baseline,
        "vmin_kmh": v_min,
        "drop_kmh": drop,
        "drop_pct": 100.0 * drop / baseline,
        "recovery_s": recovery_frames * ngsim.FRAME_SECONDS,
        "recovery_censored": censored,
        # Speed change across the baseline window, i.e. what the vehicle was
        # already doing before the event. Controls must be matched on this:
        # a vehicle accelerating out of a stop-and-go wave cannot slow down
        # much further, so ignoring it builds a control group that is
        # structurally incapable of showing the effect. See decision log D8.
        "pre_trend_kmh": float(pre[-1] - pre[0]),
    }


def attach_responses(
    events: pd.DataFrame,
    df: pd.DataFrame,
    follower_col: str,
    frame_col: str,
    profiles_out: list | None = None,
) -> pd.DataFrame:
    """Compute the follower response for each event row.

    If `profiles_out` is given, the follower's full speed trace over the window
    (normalised to its own baseline) is appended to it for the surviving rows,
    so figure 2 can plot the average dip-and-recovery shape.
    """
    idx = build_frame_index(df)
    speed = idx["speed"]
    lookup = idx["lookup"]

    # Trajectories are contiguous and frame_id is consecutive within one, so a
    # window is valid iff its first and last frames map to indices that differ
    # by exactly the window length.
    span = RECOVERY_END - PRE_START
    first = pd.MultiIndex.from_arrays(
        [events[follower_col], events[frame_col] + PRE_START]
    )
    last = pd.MultiIndex.from_arrays(
        [events[follower_col], events[frame_col] + PRE_START + span - 1]
    )
    i0 = lookup.reindex(first).to_numpy()
    i1 = lookup.reindex(last).to_numpy()
    valid = np.isfinite(i0) & np.isfinite(i1) & ((i1 - i0) == span - 1)

    headway = idx["headway"]
    records: list[dict | None] = []
    traces: list[np.ndarray | None] = []
    for ok, start in zip(valid, i0):
        if not ok:
            records.append(None)
            traces.append(None)
            continue
        s = int(start)
        rec = measure_response(speed, s, span)
        if rec is not None:
            # Pre-treatment gap: mean over the baseline window, entirely before
            # the lane change. This is what controls are matched on.
            rec["headway_pre_ft"] = float(
                np.mean(headway[s : s + (PRE_END - PRE_START)])
            )
            # Gap at the moment of the event. NOT a matching covariate: for a
            # real event this is the gap the lane-changer just took, so it is
            # post-treatment and conditioning on it would match away the very
            # mechanism being measured. Kept only as a diagnostic - the
            # difference between the two columns shows the cut-in happened.
            rec["headway_at_t"] = float(headway[s - PRE_START])
        records.append(rec)
        traces.append(speed[s : s + span] if rec is not None else None)

    resp = pd.DataFrame(
        [r if r is not None else {} for r in records], index=events.index
    )
    if "baseline_kmh" not in resp.columns:
        # No event survived; return an empty frame with the expected schema so
        # downstream concatenation does not silently misalign columns.
        resp = resp.reindex(columns=RESPONSE_COLUMNS)
    out = pd.concat([events, resp], axis=1)
    keep = out["baseline_kmh"].notna().to_numpy()

    if profiles_out is not None:
        kept = [t for t, k in zip(traces, keep) if k and t is not None]
        if kept:
            arr = np.vstack(kept).astype(np.float32)
            base = resp.loc[keep, "baseline_kmh"].to_numpy(dtype=np.float32)[:, None]
            profiles_out.append(arr / base)  # speed relative to own baseline

    return out[keep].copy()


# --------------------------------------------------------------------------- #
# Congestion regime
# --------------------------------------------------------------------------- #
def attach_regime(df: pd.DataFrame) -> pd.DataFrame:
    """Local traffic state: mean speed over all vehicles in a lane x 30 s cell."""
    cell = df["frame_id"] // REGIME_BIN_FRAMES
    key = pd.MultiIndex.from_arrays(
        [df["site"], df["period"], df["lane_id"], cell], names=["site", "period", "lane_id", "cell"]
    )
    mean_speed = df.groupby(key, observed=True)["speed_kmh"].transform("mean")
    df["local_mean_kmh"] = mean_speed
    df["regime"] = np.where(mean_speed < CONGESTION_KMH, "heavy", "light")
    df["_cell"] = cell
    return df


def lane_change_exposure(df: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    """How often does each vehicle class change lanes, per hour of driving?

    The per-event truck penalty has a small sample. This statistic does not: it
    uses every truck-second observed, not just the trucks that changed lanes. It
    also answers a question fleet managers actually ask - not "how bad is one
    manoeuvre" but "how often does my fleet do it".
    """
    seconds = (
        df.groupby("v_class", observed=True).size() * ngsim.FRAME_SECONDS
    )
    vehicles = df.groupby("v_class", observed=True)["traj_key"].nunique()
    changes = events.groupby("v_class", observed=True).size()

    out = pd.DataFrame({
        "vehicles": vehicles,
        "vehicle_hours": seconds / 3600.0,
        "lane_changes": changes,
    }).fillna({"lane_changes": 0})
    out["changes_per_vehicle_hour"] = out["lane_changes"] / out["vehicle_hours"]
    out.index = out.index.map(ngsim.CLASS_LABEL)
    return out.reset_index(names="class_label")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", default="data/raw")
    parser.add_argument("--out", default="data/processed")
    parser.add_argument("--controls-per-event", type=int, default=3)
    parser.add_argument(
        "--sites", nargs="+", default=list(ngsim.SITE_MAINLINE_LANES),
        choices=list(ngsim.SITE_MAINLINE_LANES),
    )
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    Path("outputs/tables").mkdir(parents=True, exist_ok=True)

    log: list[str] = ["# Event detection summary", ""]
    all_events, all_controls = [], []
    ev_profiles: list = []
    ctl_profiles: list = []
    exposures: list = []

    for site in args.sites:
        print(f"[{site}] loading")
        dedup_note: list[str] = []
        df = ngsim.prepare(ngsim.load_site(site, args.raw, dedup_note))
        log.append(f"## {site}")
        log.extend(dedup_note)
        log.append(f"- rows after dedup: {len(df):,}")
        log.append(f"- recording periods: {df['period'].nunique()}")

        df = df[ngsim.is_mainline(df)].reset_index(drop=True)
        log.append(f"- mainline rows: {len(df):,}")
        df = attach_regime(df)

        ev = detect_lane_changes(df)
        log.append(f"- raw lane-change transitions: {len(ev):,}")

        ev = ev[
            (ev["run_before"] >= STABLE_FRAMES) & (ev["run_after"] >= STABLE_FRAMES)
        ]
        log.append(f"- after stability filter (>={STABLE_FRAMES/10:.0f}s each side): {len(ev):,}")

        ev = ev[ev["following"] > 0]
        log.append(f"- with a follower in the target lane: {len(ev):,}")

        ev["follower_key"] = (
            ev["site"].astype(str) + "|" + ev["period"].astype(str) + "|"
            + ev["following"].astype(str)
        )
        ev = attach_responses(ev, df, "follower_key", "frame_id", ev_profiles)
        log.append(f"- with a complete follower response window: {len(ev):,}")

        ev = _attach_event_context(ev, df)
        all_events.append(ev)

        exp = lane_change_exposure(df, ev)
        exp.insert(0, "site", site)
        exposures.append(exp)
        log.append("")
        log.append("| class | vehicles | vehicle-hours | lane changes | per vehicle-hour |")
        log.append("|---|---:|---:|---:|---:|")
        for _, r in exp.iterrows():
            log.append(
                f"| {r['class_label']} | {int(r['vehicles']):,} | "
                f"{r['vehicle_hours']:.1f} | {int(r['lane_changes']):,} | "
                f"{r['changes_per_vehicle_hour']:.2f} |"
            )

        ctrl = build_controls(df, ev, args.controls_per_event, ctl_profiles)
        log.append(f"- matched control observations: {len(ctrl):,}")
        log.append("")
        all_controls.append(ctrl)

        del df

    events = pd.concat(all_events, ignore_index=True)
    controls = pd.concat(all_controls, ignore_index=True)
    events.to_parquet(out_dir / "events.parquet", index=False)
    controls.to_parquet(out_dir / "controls.parquet", index=False)
    pd.concat(exposures, ignore_index=True).to_parquet(
        out_dir / "exposure.parquet", index=False
    )
    if ev_profiles:
        np.save(out_dir / "events_profiles.npy", np.vstack(ev_profiles))
    if ctl_profiles:
        np.save(out_dir / "controls_profiles.npy", np.vstack(ctl_profiles))

    log.append("## totals")
    log.append(f"- events: {len(events):,}")
    log.append(f"- controls: {len(controls):,}")
    by_class = events["v_class"].map(ngsim.CLASS_LABEL).value_counts()
    for label, n in by_class.items():
        log.append(f"- events by {label} lane-changer: {n:,}")

    Path("outputs/tables/02_detection_summary.md").write_text(
        "\n".join(log), encoding="utf-8"
    )
    print("\n".join(log[-8:]))
    return 0


def _attach_event_context(ev: pd.DataFrame, df: pd.DataFrame) -> pd.DataFrame:
    """Copy the local traffic state at the moment of the change onto the event."""
    ctx = df.set_index(["traj_key", "frame_id"])[
        ["regime", "local_mean_kmh", "_cell"]
    ]
    keys = pd.MultiIndex.from_arrays([ev["traj_key"], ev["frame_id"]])
    got = ctx.reindex(keys)
    ev = ev.copy()
    ev["regime"] = got["regime"].to_numpy()
    ev["local_mean_kmh"] = got["local_mean_kmh"].to_numpy()
    ev["is_truck"] = (ev["v_class"] == ngsim.CLASS_TRUCK).astype(int)
    ev["class_label"] = ev["v_class"].map(ngsim.CLASS_LABEL)
    return ev[ev["regime"].notna()]


def build_controls(
    df: pd.DataFrame, events: pd.DataFrame, per_event: int,
    profiles_out: list | None = None,
) -> pd.DataFrame:
    """Build a counterfactual group by nearest-neighbour matching.

    A control is a (vehicle, frame) pair whose lane stayed constant across the
    whole -4 s .. +10 s window, so nothing cut in front of it. Candidates are
    measured exactly like real events, then each event is matched to its
    nearest candidates within the same site and congestion regime on three
    standardised covariates:

      baseline_kmh    how fast the vehicle was going
      pre_trend_kmh   whether it was already speeding up or slowing down
      headway_pre_ft  how much room it had in front, BEFORE the event

    All three are measured strictly before t=0. The gap at the moment of the
    change (`headway_at_t`) is deliberately excluded: a cut-in is *defined* by
    the gap shrinking, so that column is post-treatment and matching on it
    would match away the mechanism under study. See decision log D10.

    `pre_trend_kmh` is the one that matters most. An earlier version matched on
    speed level alone and produced a control group that accelerated 23% over
    the window while real followers stayed flat: conditioning on a low speed in
    stop-and-go traffic selects vehicles emerging from a wave, which cannot
    decelerate much further. That control group was structurally unable to show
    the effect. See docs/decision-log.md D8.

    Matching is without replacement, so no single quiet moment can anchor many
    events at once.
    """
    from scipy.spatial import cKDTree

    rng = np.random.default_rng(RNG_SEED)

    runs = _lane_run_lengths(df)
    stable = (runs["run_before_here"] >= -PRE_START) & (
        runs["run_after"] >= RECOVERY_END
    )
    pool = df.loc[stable, ["traj_key", "frame_id", "site", "regime",
                           "local_mean_kmh", "speed_kmh", "space_headway",
                           "v_class"]].copy()
    if pool.empty or events.empty:
        return pool.reindex(columns=[*pool.columns, *RESPONSE_COLUMNS]).iloc[0:0]

    # Thin: adjacent frames of the same vehicle are near-duplicate windows and
    # would fake precision. One candidate every 0.5 s.
    pool = pool[pool["frame_id"] % 5 == 0]

    # Cap the pool so measuring it stays cheap, while leaving plenty of choice
    # for the matcher.
    max_pool = max(MIN_POOL, per_event * CANDIDATES_PER_EVENT * len(events))
    if len(pool) > max_pool:
        pool = pool.iloc[rng.choice(len(pool), size=max_pool, replace=False)]

    pool = attach_responses(pool, df, "traj_key", "frame_id")
    if pool.empty:
        return pool

    picked_idx: list[int] = []
    for (site, regime), ev_grp in events.groupby(["site", "regime"], observed=True):
        cand = pool[(pool["site"] == site) & (pool["regime"] == regime)]
        if len(cand) == 0:
            continue

        cols = ["baseline_kmh", "pre_trend_kmh", "headway_pre_ft"]
        c_raw = cand[cols].to_numpy(dtype=float)
        e_raw = ev_grp[cols].to_numpy(dtype=float)
        ok_c = np.isfinite(c_raw).all(axis=1)
        ok_e = np.isfinite(e_raw).all(axis=1)
        c_raw, e_raw = c_raw[ok_c], e_raw[ok_e]
        if len(c_raw) == 0 or len(e_raw) == 0:
            continue

        # Standardise on the candidate pool so no covariate dominates by unit.
        mu, sd = c_raw.mean(axis=0), c_raw.std(axis=0)
        sd[sd == 0] = 1.0
        tree = cKDTree((c_raw - mu) / sd)

        k = min(per_event * 4, len(c_raw))
        _, nn = tree.query((e_raw - mu) / sd, k=k)
        nn = np.atleast_2d(nn)

        cand_positions = cand.index.to_numpy()[ok_c]
        used: set[int] = set()
        for row in nn:
            taken = 0
            for j in row:
                pos = int(cand_positions[j])
                if pos in used:
                    continue
                used.add(pos)
                picked_idx.append(pos)
                taken += 1
                if taken >= per_event:
                    break

    controls = pool.loc[sorted(set(picked_idx))].copy()
    controls["is_truck"] = np.nan
    controls["class_label"] = "control"

    if profiles_out is not None and len(controls):
        profiles_out.append(_profiles_for(controls, df))
    return controls


def _profiles_for(rows: pd.DataFrame, df: pd.DataFrame) -> np.ndarray:
    """Baseline-normalised speed traces for already-measured control rows."""
    idx = build_frame_index(df)
    speed, lookup = idx["speed"], idx["lookup"]
    span = RECOVERY_END - PRE_START
    starts = lookup.reindex(
        pd.MultiIndex.from_arrays([rows["traj_key"], rows["frame_id"] + PRE_START])
    ).to_numpy()
    traces = np.vstack([speed[int(s): int(s) + span] for s in starts]).astype(np.float32)
    return traces / rows["baseline_kmh"].to_numpy(dtype=np.float32)[:, None]


if __name__ == "__main__":
    sys.exit(main())
