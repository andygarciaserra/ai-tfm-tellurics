#!/usr/bin/env bash
set -euo pipefail

# Resolve repository root from this script location.
# This makes the script independent of the directory from which it is executed.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

DEFAULT_CONFIG="$REPO_ROOT/configs/phoenix_initial_pool.csv"

# If no argument is given, use the default config.
# If the argument is absolute, use it as-is.
# If the argument is relative, interpret it relative to the repository root.
if [[ $# -eq 0 ]]; then
  CONFIG_FILE="$DEFAULT_CONFIG"
else
  if [[ "$1" = /* ]]; then
    CONFIG_FILE="$1"
  else
    CONFIG_FILE="$REPO_ROOT/$1"
  fi
fi

if [[ ! -f "$CONFIG_FILE" ]]; then
  echo "ERROR: Config file not found:"
  echo "  $CONFIG_FILE"
  exit 1
fi

# Count non-empty data rows, excluding the header.
TOTAL_MODELS="$(
  tail -n +2 "$CONFIG_FILE" | awk -F',' 'NF && $1 !~ /^[[:space:]]*$/ {count++} END {print count+0}'
)"

if [[ "$TOTAL_MODELS" -eq 0 ]]; then
  echo "ERROR: No models found in config file:"
  echo "  $CONFIG_FILE"
  exit 1
fi

echo "Repository root:"
echo "  $REPO_ROOT"
echo

echo "Using PHOENIX config:"
echo "  $CONFIG_FILE"
echo

CURRENT_MODEL=0

tail -n +2 "$CONFIG_FILE" | while IFS=, read -r label teff logg feh wmin wmax n_resampled normalize; do
  # Skip empty lines.
  if [[ -z "${label// }" ]]; then
    continue
  fi

  CURRENT_MODEL=$((CURRENT_MODEL + 1))

  echo "========================================"
  echo "[$CURRENT_MODEL/$TOTAL_MODELS] Generating PHOENIX model: $label"
  echo "Teff=$teff, logg=$logg, [Fe/H]=$feh"
  echo "Range=${wmin}-${wmax} micron, N=$n_resampled, normalize=$normalize"
  echo "========================================"

  cmd=(
    python "$REPO_ROOT/scripts/01_download_prepare_phoenix.py"
    --label "$label"
    --teff "$teff"
    --logg "$logg"
    --feh "$feh"
    --wmin "$wmin"
    --wmax "$wmax"
    --n-resampled "$n_resampled"
    --overwrite
  )

  if [[ "$normalize" == "true" ]]; then
    cmd+=(--normalize)
  fi

  "${cmd[@]}"
  echo
done

echo "========================================"
echo "Done generating PHOENIX pool."
echo "Processed $TOTAL_MODELS model(s)."
echo "========================================"
