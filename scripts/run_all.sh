#!/usr/bin/env bash
# Full pipeline, start to finish. Roughly 15 minutes, most of it the download.
set -euo pipefail
cd "$(dirname "$0")/.."

mkdir -p outputs/figures outputs/tables

python tests/test_detection.py
python -u scripts/01_download_ngsim.py  2>&1 | tee outputs/01_download.log
python -u scripts/02_detect_events.py   2>&1 | tee outputs/02_detect.log
python -u scripts/03_analyse.py         2>&1 | tee outputs/03_analyse.log
python -u scripts/04_figures.py         2>&1 | tee outputs/04_figures.log
python scripts/check_answer_length.py

echo
echo "Done. Results: outputs/tables/03_results.md, figures: outputs/figures/"
