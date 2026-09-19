"""Shared constants and loaders for the NGSIM lane-change externality analysis.

Unit note: NGSIM is published in US customary units.
  local_y, space_headway  -> feet
  v_vel                   -> feet / second
  v_acc                   -> feet / second^2
  frame_id                -> 10 Hz, i.e. one frame = 0.1 s
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

# --------------------------------------------------------------------------- #
# Units
# --------------------------------------------------------------------------- #
FT_TO_M = 0.3048
FPS_TO_KMH = 3.6 * FT_TO_M  # 1 ft/s = 1.09728 km/h
FRAME_HZ = 10
FRAME_SECONDS = 1.0 / FRAME_HZ


# --------------------------------------------------------------------------- #
# Vehicle classes (NGSIM codebook)
# --------------------------------------------------------------------------- #
CLASS_MOTORCYCLE = 1
CLASS_AUTO = 2
CLASS_TRUCK = 3

CLASS_LABEL = {
    CLASS_MOTORCYCLE: "motorcycle",
    CLASS_AUTO: "car",
    CLASS_TRUCK: "truck",
}


# --------------------------------------------------------------------------- #
# Sites
# --------------------------------------------------------------------------- #
# Mainline through-lanes only. Higher lane numbers are on-ramps, off-ramps and
# auxiliary merge lanes, where a "lane change" is a forced merge rather than a
# discretionary one and the follower's deceleration has a different cause.
SITE_MAINLINE_LANES = {
    "i-80": (1, 2, 3, 4, 5, 6),
    "us-101": (1, 2, 3, 4, 5),
}

SITE_FILES = {
    "i-80": "ngsim_i80.parquet",
    "us-101": "ngsim_us101.parquet",
}

# Each 15-minute recording restarts `frame_id` at its own origin, so
# `global_time - frame_id * 100` is constant inside a recording and differs
# between recordings. That offset is the period key. See decision log D5.
FRAME_MS = 100


def load_site(
    site: str, raw_dir: str | Path = "data/raw", report: list | None = None
) -> pd.DataFrame:
    """Load one site's raw trajectories, deduplicate, and label recording periods.

    The published NGSIM table contains exact duplicate rows — 1,408,000 of
    US-101's 4,802,933 rows (29%) are byte-for-byte repeats of another row.
    They are dropped here. Because every duplicate is identical in every
    column, dropping them loses no information, but leaving them in would
    double-count those vehicles in every average. See decision log D9.
    """
    path = Path(raw_dir) / SITE_FILES[site]
    df = pd.read_parquet(path)

    before = len(df)
    df = df.drop_duplicates().reset_index(drop=True)
    dropped = before - len(df)
    if report is not None:
        report.append(
            f"- exact duplicate rows dropped: {dropped:,} of {before:,} "
            f"({dropped / before:.1%})"
        )

    df["site"] = site
    df["period"] = assign_periods(df["global_time"], df["frame_id"])
    return df


def assign_periods(global_time: pd.Series, frame_id: pd.Series) -> pd.Series:
    """Label each row with the index of the recording period it belongs to.

    NGSIM concatenates several 15-minute recordings per site and restarts both
    `vehicle_id` and `frame_id` in each one. The recording's clock origin,
    `global_time - frame_id * FRAME_MS`, is therefore constant within a
    recording and different between recordings — an exact key.

    An earlier version cut on gaps in `global_time` instead. That silently
    failed: I-80's 17:00-17:15 and 17:15-17:30 recordings are contiguous in
    wall-clock time, so no gap exists between them, the two merged into one
    period, and 88 vehicle IDs collided. See docs/decision-log.md D5.
    """
    epoch = global_time.astype("int64") - frame_id.astype("int64") * FRAME_MS
    codes = pd.factorize(np.sort(epoch.unique()))[0]
    lookup = pd.Series(codes, index=np.sort(epoch.unique()))
    return epoch.map(lookup).astype("int8")


def trajectory_key(df: pd.DataFrame) -> pd.Series:
    """A key that uniquely identifies one vehicle's trajectory.

    `vehicle_id` alone is NOT unique: it restarts in every recording period and
    repeats across sites.
    """
    return (
        df["site"].astype(str)
        + "|"
        + df["period"].astype(str)
        + "|"
        + df["vehicle_id"].astype(str)
    )


def smooth_speed(df: pd.DataFrame, window_frames: int = 11) -> pd.Series:
    """Centred moving average of speed within each trajectory.

    NGSIM speeds are differentiated from video-extracted positions and carry
    substantial high-frequency noise (Punzo et al., 2011). Every speed statistic
    in this project is computed on the smoothed series. An 11-frame window is
    1.1 s: long enough to suppress differentiation noise, short enough to keep a
    real braking response intact.
    """
    return (
        df.groupby("traj_key", observed=True)["v_vel"]
        .transform(lambda s: s.rolling(window_frames, center=True, min_periods=1).mean())
    )


def prepare(df: pd.DataFrame) -> pd.DataFrame:
    """Add derived columns used throughout the analysis."""
    df = df.sort_values(["site", "period", "vehicle_id", "frame_id"]).reset_index(
        drop=True
    )
    df["traj_key"] = trajectory_key(df)
    df["v_smooth"] = smooth_speed(df)
    df["speed_kmh"] = df["v_smooth"] * FPS_TO_KMH
    df["t_sec"] = df["global_time"] / 1000.0
    return df


def is_mainline(df: pd.DataFrame) -> pd.Series:
    """True where the vehicle is in a through-lane of its site."""
    out = pd.Series(False, index=df.index)
    for site, lanes in SITE_MAINLINE_LANES.items():
        mask = (df["site"] == site) & df["lane_id"].isin(lanes)
        out |= mask
    return out
