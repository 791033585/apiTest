#!/bin/sh
set -eu

if [ ! -f data/api_cases.xlsx ]; then
  python tools/create_sample_xlsx.py
fi

exec "$@"

