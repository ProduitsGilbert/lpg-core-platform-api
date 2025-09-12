#!/usr/bin/env bash
set -euo pipefail
SHA=$(git rev-parse --short HEAD)
DATE=$(date -u +%Y%m%d%H%M%S)
echo "${DATE}-${SHA}"