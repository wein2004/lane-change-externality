"""Smoke tests for the lane-change detection and response measurement.

Run: python tests/test_detection.py

These use hand-built synthetic trajectories where the right answer is known by
construction, so a logic error shows up here rather than as a plausible-looking
but wrong number in the results table.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src import ngsim  # noqa: E402

spec = importlib.util.spec_from_file_location(
    "detect", ROOT / "scripts" / "02_detect_events.py"
)
detect = importlib.util.module_from_spec(spec)
spec.loader.exec_module(detect)

FAILURES: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  PASS  {name}")
    else:
        print(f"  FAIL  {name}  {detail}")
        FAILURES.append(name)


def make_traj(
    vehicle_id: int,
    lanes: list[int],
    speeds: list[float],
    v_class: int = ngsim.CLASS_AUTO,
    following: int = 0,
    start_frame: int = 0,
) -> pd.DataFrame:
    n = len(lanes)
    return pd.DataFrame({
        "vehicle_id": vehicle_id,
        "frame_id": np.arange(start_frame, start_frame + n),
        "global_time": (np.arange(start_frame, start_frame + n) * 100).astype("int64"),
        "local_y": np.cumsum(speeds),
        "v_vel": speeds,
        "v_acc": 0.0,
        "v_class": v_class,
        "lane_id": lanes,
        "preceding": 0,
        "following": following,
        "space_headway": 60.0,
        "time_headway": 2.0,
        "site": "i-80",
        "period": 0,
    })


def finish(df: pd.DataFrame) -> pd.DataFrame:
    """Apply the same preparation the real pipeline does."""
    df = df.sort_values(["site", "period", "vehicle_id", "frame_id"]).reset_index(
        drop=True
    )
    df["traj_key"] = ngsim.trajectory_key(df)
    # No smoothing in tests: it would blur the step changes we are asserting on.
    df["v_smooth"] = df["v_vel"]
    df["speed_kmh"] = df["v_smooth"] * ngsim.FPS_TO_KMH
    df["t_sec"] = df["global_time"] / 1000.0
    return detect.attach_regime(df)


# --------------------------------------------------------------------------- #
def test_single_clean_lane_change() -> None:
    print("\ntest_single_clean_lane_change")
    n = 300
    lanes = [2] * 150 + [3] * 150  # one change at frame 150
    df = finish(make_traj(1, lanes, [30.0] * n, following=2))
    ev = detect.detect_lane_changes(df)

    check("exactly one transition detected", len(ev) == 1, f"got {len(ev)}")
    if len(ev) == 1:
        row = ev.iloc[0]
        check("change is at frame 150", row["frame_id"] == 150, str(row["frame_id"]))
        check("lane 2 -> 3", (row["lane_from"], row["lane_to"]) == (2, 3))
        check("passes the 3s stability filter both sides",
              row["run_before"] >= detect.STABLE_FRAMES
              and row["run_after"] >= detect.STABLE_FRAMES,
              f"before={row['run_before']} after={row['run_after']}")


def test_flicker_is_rejected() -> None:
    print("\ntest_flicker_is_rejected")
    # One-frame lane blip at 150: a tracking artefact, not a manoeuvre.
    lanes = [2] * 150 + [3] * 1 + [2] * 149
    df = finish(make_traj(1, lanes, [30.0] * 300, following=2))
    ev = detect.detect_lane_changes(df)
    kept = ev[(ev["run_before"] >= detect.STABLE_FRAMES)
              & (ev["run_after"] >= detect.STABLE_FRAMES)]
    check("two raw transitions seen", len(ev) == 2, f"got {len(ev)}")
    check("both rejected by the stability filter", len(kept) == 0, f"kept {len(kept)}")


def test_weaving_is_rejected() -> None:
    print("\ntest_weaving_is_rejected")
    # Three changes inside 3 seconds; none has a stable 3s run on both sides.
    lanes = [2] * 100 + [3] * 10 + [4] * 10 + [5] * 180
    df = finish(make_traj(1, lanes, [30.0] * 300, following=2))
    ev = detect.detect_lane_changes(df)
    kept = ev[(ev["run_before"] >= detect.STABLE_FRAMES)
              & (ev["run_after"] >= detect.STABLE_FRAMES)]
    check("the two short-run changes are rejected", len(kept) == 0,
          f"kept {len(kept)} of {len(ev)}")


def test_response_measurement() -> None:
    print("\ntest_response_measurement")
    # Follower cruises at 30 ft/s, drops to 20 ft/s for 2s from t=0, recovers.
    n = 200
    speeds = [30.0] * 100 + [20.0] * 20 + [30.0] * 80
    df = finish(make_traj(2, [3] * n, speeds))
    idx = detect.build_frame_index(df)
    # window starts at frame 100 + PRE_START
    start = 100 + detect.PRE_START
    res = detect.measure_response(
        idx["speed"], start, detect.RECOVERY_END - detect.PRE_START
    )
    check("a response was measured", res is not None)
    if res:
        expect_base = 30.0 * ngsim.FPS_TO_KMH
        expect_drop = 10.0 * ngsim.FPS_TO_KMH
        check("baseline is the pre-event cruise speed",
              abs(res["baseline_kmh"] - expect_base) < 0.01,
              f"{res['baseline_kmh']:.3f} vs {expect_base:.3f}")
        check("drop equals the injected 10 ft/s deceleration",
              abs(res["drop_kmh"] - expect_drop) < 0.01,
              f"{res['drop_kmh']:.3f} vs {expect_drop:.3f}")
        check("recovery is the 2s slow patch (measured from the minimum)",
              abs(res["recovery_s"] - 2.0) < 0.15, f"{res['recovery_s']:.2f}s")
        check("recovery is not censored", res["recovery_censored"] is False)


def test_no_recovery_is_censored() -> None:
    print("\ntest_no_recovery_is_censored")
    speeds = [30.0] * 100 + [20.0] * 100  # never comes back up
    df = finish(make_traj(2, [3] * 200, speeds))
    idx = detect.build_frame_index(df)
    res = detect.measure_response(
        idx["speed"], 100 + detect.PRE_START, detect.RECOVERY_END - detect.PRE_START
    )
    check("a response was measured", res is not None)
    if res:
        check("flagged as censored", res["recovery_censored"] is True)


def test_period_split_prevents_fake_changes() -> None:
    print("\ntest_period_split_prevents_fake_changes")
    # Same vehicle_id in two recording periods, in different lanes. Without the
    # period split these would look like one vehicle changing lanes.
    a = make_traj(1, [2] * 100, [30.0] * 100, start_frame=0)
    b = make_traj(1, [5] * 100, [30.0] * 100, start_frame=0)
    b["global_time"] = b["global_time"] + 900_000  # a later recording
    both = pd.concat([a, b], ignore_index=True)
    both["period"] = ngsim.assign_periods(both["global_time"], both["frame_id"])
    check("two periods detected", both["period"].nunique() == 2,
          f"got {both['period'].nunique()}")

    df = finish(both)
    check("trajectory keys are distinct", df["traj_key"].nunique() == 2,
          f"got {df['traj_key'].nunique()}")
    ev = detect.detect_lane_changes(df)
    check("no phantom lane change across the period boundary", len(ev) == 0,
          f"got {len(ev)}")


def test_contiguous_recordings_are_still_split() -> None:
    """Regression test for the bug in decision log D5.

    Two recordings that butt up against each other in wall-clock time - no gap
    at all - must still be separated, because frame_id restarts in each.
    """
    print("\ntest_contiguous_recordings_are_still_split")
    a = make_traj(1, [2] * 100, [30.0] * 100, start_frame=0)
    b = make_traj(1, [5] * 100, [30.0] * 100, start_frame=0)
    # Second recording starts exactly where the first ended: zero gap.
    b["global_time"] = b["global_time"] + a["global_time"].max() + 100
    both = pd.concat([a, b], ignore_index=True)
    both["period"] = ngsim.assign_periods(both["global_time"], both["frame_id"])
    check("gapless recordings still split into two periods",
          both["period"].nunique() == 2, f"got {both['period'].nunique()}")

    df = finish(both)
    check("trajectory keys stay distinct", df["traj_key"].nunique() == 2,
          f"got {df['traj_key'].nunique()}")
    check("no duplicate (traj_key, frame_id) pairs",
          not df.duplicated(subset=["traj_key", "frame_id"]).any())


def test_mainline_filter() -> None:
    print("\ntest_mainline_filter")
    df = finish(make_traj(1, [1] * 50 + [7] * 50, [30.0] * 100))
    keep = ngsim.is_mainline(df)
    check("I-80 lane 1 kept", bool(keep.iloc[0]))
    check("I-80 lane 7 (on-ramp) dropped", not bool(keep.iloc[-1]))


def main() -> int:
    for fn in [
        test_single_clean_lane_change,
        test_flicker_is_rejected,
        test_weaving_is_rejected,
        test_response_measurement,
        test_no_recovery_is_censored,
        test_period_split_prevents_fake_changes,
        test_contiguous_recordings_are_still_split,
        test_mainline_filter,
    ]:
        fn()

    print()
    if FAILURES:
        print(f"{len(FAILURES)} FAILED: {', '.join(FAILURES)}")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
