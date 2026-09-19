"""Download NGSIM vehicle trajectory data from the US DOT open data portal.

Source : https://data.transportation.gov/Automobiles/Next-Generation-Simulation-NGSIM-Vehicle-Trajector/8ect-6jqj
Access : public Socrata API, no authentication required (verified 2026-09-19).

We keep only the columns the lane-change analysis needs, and only the two
freeway sites (I-80 Emeryville, US-101 Los Angeles). The arterial sites
(Lankershim, Peachtree) are signal-controlled and are excluded: stop-and-go at
traffic lights would contaminate the deceleration measurement.

Pagination note: this pages on `vehicle_id` ranges, not on `$offset`. Socrata's
`$offset` degrades sharply past a few hundred thousand rows on a table this size
(measured: an offset page stalled for minutes, the equivalent keyset page
returned 816k rows in 49s). See docs/decision-log.md D7.

Output: data/raw/ngsim_<site>.parquet
"""

from __future__ import annotations

import argparse
import sys
import time
from io import StringIO
from pathlib import Path

import pandas as pd
import requests

RESOURCE = "https://data.transportation.gov/resource/8ect-6jqj.csv"

# `following` / `preceding` / `space_headway` are supplied by NGSIM itself and
# save us from re-deriving the car-following relationship.
COLUMNS = [
    "vehicle_id",
    "frame_id",
    "global_time",
    "local_y",
    "v_vel",
    "v_acc",
    "v_class",
    "lane_id",
    "preceding",
    "following",
    "space_headway",
    "time_headway",
]

SITES = ["i-80", "us-101"]

VEHICLE_CHUNK = 400  # vehicle_ids per request; ~650k rows, well under the cap
HARD_LIMIT = 2_000_000  # per-request row cap; we assert we never hit it
REQUEST_TIMEOUT = 600
MAX_RETRIES = 4

DTYPES = {
    "vehicle_id": "int32",
    "frame_id": "int32",
    "global_time": "int64",
    "local_y": "float32",
    "v_vel": "float32",
    "v_acc": "float32",
    "v_class": "int8",
    "lane_id": "int8",
    "preceding": "int32",
    "following": "int32",
    "space_headway": "float32",
    "time_headway": "float32",
}


def _get(session: requests.Session, params: dict, timeout: int) -> str:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = session.get(RESOURCE, params=params, timeout=timeout)
            resp.raise_for_status()
            return resp.text
        except Exception as exc:  # noqa: BLE001 - retry any transport-level error
            if attempt == MAX_RETRIES:
                raise
            wait = 5 * attempt
            print(f"    retry {attempt}/{MAX_RETRIES} after {exc!r}; sleeping {wait}s",
                  flush=True)
            time.sleep(wait)
    raise RuntimeError("unreachable")


def site_bounds(site: str, session: requests.Session) -> tuple[int, int, int]:
    """(min vehicle_id, max vehicle_id, total rows) for one site."""
    text = _get(
        session,
        {
            "$select": "min(vehicle_id),max(vehicle_id),count(vehicle_id)",
            "$where": f"location='{site}'",
        },
        timeout=120,
    )
    row = pd.read_csv(StringIO(text)).iloc[0]
    return int(row.iloc[0]), int(row.iloc[1]), int(row.iloc[2])


def fetch_vehicle_range(
    site: str, lo: int, hi: int, session: requests.Session
) -> pd.DataFrame:
    """All rows for vehicle_id in [lo, hi) at `site`."""
    text = _get(
        session,
        {
            "$select": ",".join(COLUMNS),
            "$where": f"location='{site}' AND vehicle_id>={lo} AND vehicle_id<{hi}",
            "$limit": HARD_LIMIT,
        },
        timeout=REQUEST_TIMEOUT,
    )
    df = pd.read_csv(StringIO(text))
    if len(df) >= HARD_LIMIT:
        raise RuntimeError(
            f"{site} vehicles [{lo},{hi}) hit the {HARD_LIMIT:,}-row cap; "
            "results would be silently truncated. Lower VEHICLE_CHUNK."
        )
    return df


def download_site(
    site: str, out_dir: Path, session: requests.Session,
    max_vehicles: int | None = None,
) -> Path:
    lo, hi, total = site_bounds(site, session)
    if max_vehicles is not None:
        hi = min(hi, lo + max_vehicles - 1)
        total = None  # row count no longer known up front
        print(f"[{site}] smoke run: vehicles {lo}..{hi} only", flush=True)
    n_rows = f"{total:,} rows" if total is not None else "row count unknown"
    print(f"[{site}] vehicle_id {lo}..{hi}, {n_rows}", flush=True)

    frames: list[pd.DataFrame] = []
    got = 0
    for start in range(lo, hi + 1, VEHICLE_CHUNK):
        t0 = time.time()
        page = fetch_vehicle_range(site, start, start + VEHICLE_CHUNK, session)
        frames.append(page)
        got += len(page)
        progress = f"{got:,}/{total:,}, {got / total:.0%}" if total else f"{got:,}"
        print(
            f"[{site}] vehicles {start}-{start + VEHICLE_CHUNK - 1}: "
            f"{len(page):,} rows  ({progress})  {time.time() - t0:.1f}s",
            flush=True,
        )

    df = pd.concat(frames, ignore_index=True)
    if total is not None and len(df) != total:
        print(f"[{site}] WARNING: got {len(df):,} rows, API reported {total:,}",
              flush=True)

    for col, dtype in DTYPES.items():
        df[col] = df[col].fillna(0).astype(dtype)
    df = df.sort_values(["vehicle_id", "frame_id"]).reset_index(drop=True)

    out_path = out_dir / f"ngsim_{site.replace('-', '')}.parquet"
    df.to_parquet(out_path, index=False)
    print(
        f"[{site}] wrote {out_path} ({len(df):,} rows, "
        f"{out_path.stat().st_size / 1e6:.0f} MB)",
        flush=True,
    )
    return out_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="data/raw")
    parser.add_argument("--sites", nargs="+", default=SITES, choices=SITES)
    parser.add_argument(
        "--max-vehicles", type=int, default=None,
        help="only fetch the first N vehicle_ids per site (smoke runs)",
    )
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    with requests.Session() as session:
        for site in args.sites:
            download_site(site, out_dir, session, args.max_vehicles)
    return 0


if __name__ == "__main__":
    sys.exit(main())
