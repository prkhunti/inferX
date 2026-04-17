#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../apps/dashboard"
exec npm run dev
