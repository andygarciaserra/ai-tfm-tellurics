#!/usr/bin/env bash
set -euo pipefail

# ------------------------------------------------------------
# Generate one Molecfit/calctrans mtrans run from a CSV config.
#
# Usage:
#   ./scripts/04_generate_mtrans_single.sh atm001 configs/molecfit/mtrans_config.csv
#
# Pipeline:
#   template PHOENIX FITS
#     -> molecfit_model
#     -> mapping FITS files
#     -> molecfit_calctrans
#     -> TELLURIC_DATA / TELLURIC_CORR
# ------------------------------------------------------------

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

DATA_ROOT="${TFM_DATA_ROOT:-$HOME/TFM_DATA}"

RUN_ID="${1:-atm001}"
CONFIG_CSV_ARG="${2:-configs/molecfit/mtrans_config.csv}"

if [[ "$CONFIG_CSV_ARG" = /* ]]; then
  CONFIG_CSV="$CONFIG_CSV_ARG"
else
  CONFIG_CSV="$REPO_ROOT/$CONFIG_CSV_ARG"
fi

if [[ ! -f "$CONFIG_CSV" ]]; then
  echo "ERROR: Missing config CSV:"
  echo "  $CONFIG_CSV"
  exit 1
fi

# ------------------------------------------------------------
# Read selected row from CSV using Python csv module.
# This supports quoted comma-separated fields like:
#   "H2O,O2,O3,CO2"
# ------------------------------------------------------------

eval "$(
python - "$CONFIG_CSV" "$RUN_ID" <<'PY'
import csv
import shlex
import sys
from pathlib import Path

config_path = Path(sys.argv[1])
run_id = sys.argv[2]

with config_path.open(newline="") as f:
    reader = csv.DictReader(f)
    rows = [row for row in reader if row.get("run_id") == run_id]

if not rows:
    raise SystemExit(f"ERROR: run_id '{run_id}' not found in {config_path}")

row = rows[0]

required = [
    "template_spectrum",
    "pwv",
    "telalt",
    "rhum",
    "pres",
    "temp",
    "molecules",
    "fit_molec",
    "rel_col",
    "wave_include",
    "wavelength_frame",
    "latitude",
    "longitude",
    "geoelev",
    "slit_width",
    "pix_scale",
]

missing = [key for key in required if key not in row or row[key] == ""]
if missing:
    raise SystemExit(f"ERROR: missing required columns/values: {missing}")

mapping = {
    "TEMPLATE_SPECTRUM": row["template_spectrum"],
    "PWV": row["pwv"],
    "TELALT": row["telalt"],
    "RHUM": row["rhum"],
    "PRES": row["pres"],
    "TEMP": row["temp"],
    "MOLECULES": row["molecules"],
    "FIT_MOLEC": row["fit_molec"],
    "REL_COL": row["rel_col"],
    "WAVE_INCLUDE": row["wave_include"],
    "WAVELENGTH_FRAME": row["wavelength_frame"],
    "LATITUDE": row["latitude"],
    "LONGITUDE": row["longitude"],
    "GEOELEV": row["geoelev"],
    "SLIT_WIDTH": row["slit_width"],
    "PIX_SCALE": row["pix_scale"],
}

for key, value in mapping.items():
    print(f"{key}={shlex.quote(str(value))}")
PY
)"

MODEL_RC="$REPO_ROOT/configs/molecfit/molecfit_model.rc"
CALCTRANS_RC="$REPO_ROOT/configs/molecfit/molecfit_calctrans.rc"

RUN_ROOT="$DATA_ROOT/molecfit/runs/$RUN_ID"
MODEL_OUT="$RUN_ROOT/molecfit_model"
CALCTRANS_OUT="$RUN_ROOT/molecfit_calctrans"
LOG_DIR="$RUN_ROOT/logs"
METADATA_DIR="$RUN_ROOT/metadata"

MODEL_LOG="$LOG_DIR/molecfit_model.log"
CALCTRANS_LOG="$LOG_DIR/molecfit_calctrans.log"
TIME_LOG="$LOG_DIR/timing.log"

MODEL_SOF="$RUN_ROOT/molecfit_model.sof"
CALCTRANS_SOF="$RUN_ROOT/molecfit_calctrans.sof"

MAPPING_ATM="$RUN_ROOT/MAPPING_ATMOSPHERIC.fits"
MAPPING_CONV="$RUN_ROOT/MAPPING_CONVOLVE.fits"

mkdir -p "$MODEL_OUT" "$CALCTRANS_OUT" "$LOG_DIR" "$METADATA_DIR"

echo "========================================"
echo "Generating Molecfit/calctrans mtrans run"
echo "Run ID:             $RUN_ID"
echo "Config CSV:         $CONFIG_CSV"
echo "Repo root:          $REPO_ROOT"
echo "Data root:          $DATA_ROOT"
echo "Template spectrum:  $TEMPLATE_SPECTRUM"
echo "PWV:                $PWV"
echo "TELALT:             $TELALT"
echo "Molecules:          $MOLECULES"
echo "Fit molecules:      $FIT_MOLEC"
echo "Relative columns:   $REL_COL"
echo "Wave include:       $WAVE_INCLUDE"
echo "Run folder:         $RUN_ROOT"
echo "========================================"
echo

if [[ ! -f "$MODEL_RC" ]]; then
  echo "ERROR: Missing Molecfit model config:"
  echo "  $MODEL_RC"
  exit 1
fi

if [[ ! -f "$CALCTRANS_RC" ]]; then
  echo "ERROR: Missing Molecfit calctrans config:"
  echo "  $CALCTRANS_RC"
  exit 1
fi

if [[ ! -f "$TEMPLATE_SPECTRUM" ]]; then
  echo "ERROR: Template spectrum does not exist:"
  echo "  $TEMPLATE_SPECTRUM"
  exit 1
fi

if ! command -v esorex >/dev/null 2>&1; then
  echo "ERROR: esorex not found in PATH."
  exit 1
fi

cat > "$MODEL_SOF" <<EOF
$TEMPLATE_SPECTRUM SCIENCE
EOF

{
  echo "Run ID: $RUN_ID"
  echo "Date:   $(date -Iseconds)"
  echo "Host:   $(hostname)"
  echo "Config CSV: $CONFIG_CSV"
  echo "Template spectrum: $TEMPLATE_SPECTRUM"
  echo
  echo "Atmospheric/config parameters:"
  echo "PWV=$PWV"
  echo "TELALT=$TELALT"
  echo "RHUM=$RHUM"
  echo "PRES=$PRES"
  echo "TEMP=$TEMP"
  echo "MOLECULES=$MOLECULES"
  echo "FIT_MOLEC=$FIT_MOLEC"
  echo "REL_COL=$REL_COL"
  echo "WAVE_INCLUDE=$WAVE_INCLUDE"
  echo "WAVELENGTH_FRAME=$WAVELENGTH_FRAME"
  echo "LATITUDE=$LATITUDE"
  echo "LONGITUDE=$LONGITUDE"
  echo "GEOELEV=$GEOELEV"
  echo "SLIT_WIDTH=$SLIT_WIDTH"
  echo "PIX_SCALE=$PIX_SCALE"
  echo
} > "$TIME_LOG"

echo "Running molecfit_model..."
echo "Log: $MODEL_LOG"
echo

/usr/bin/time -p \
  esorex \
    --recipe-config="$MODEL_RC" \
    --output-dir="$MODEL_OUT" \
    molecfit_model \
    --LIST_MOLEC="$MOLECULES" \
    --FIT_MOLEC="$FIT_MOLEC" \
    --REL_COL="$REL_COL" \
    --WAVE_INCLUDE="$WAVE_INCLUDE" \
    --COLUMN_LAMBDA="WAVE_MICRON" \
    --COLUMN_FLUX="FLUX" \
    --COLUMN_DFLUX="NULL" \
    --COLUMN_MASK="NULL" \
    --WLG_TO_MICRON="1.0" \
    --WAVELENGTH_FRAME="$WAVELENGTH_FRAME" \
    --PWV="$PWV" \
    --OBSERVING_DATE_KEYWORD="NONE" \
    --OBSERVING_DATE_VALUE="60100.0" \
    --UTC_KEYWORD="NONE" \
    --UTC_VALUE="36000.0" \
    --TELESCOPE_ANGLE_KEYWORD="NONE" \
    --TELESCOPE_ANGLE_VALUE="$TELALT" \
    --RELATIVE_HUMIDITY_KEYWORD="NONE" \
    --RELATIVE_HUMIDITY_VALUE="$RHUM" \
    --PRESSURE_KEYWORD="NONE" \
    --PRESSURE_VALUE="$PRES" \
    --TEMPERATURE_KEYWORD="NONE" \
    --TEMPERATURE_VALUE="$TEMP" \
    --MIRROR_TEMPERATURE_KEYWORD="NONE" \
    --MIRROR_TEMPERATURE_VALUE="$TEMP" \
    --ELEVATION_KEYWORD="NONE" \
    --ELEVATION_VALUE="$GEOELEV" \
    --LONGITUDE_KEYWORD="NONE" \
    --LONGITUDE_VALUE="$LONGITUDE" \
    --LATITUDE_KEYWORD="NONE" \
    --LATITUDE_VALUE="$LATITUDE" \
    --SLIT_WIDTH_KEYWORD="NONE" \
    --SLIT_WIDTH_VALUE="$SLIT_WIDTH" \
    --PIX_SCALE_KEYWORD="NONE" \
    --PIX_SCALE_VALUE="$PIX_SCALE" \
    --FIT_WLC="0" \
    --WLC_N="0" \
    --WLC_CONST="0.0" \
    "$MODEL_SOF" \
  > "$MODEL_LOG" 2>&1

echo "molecfit_model finished."
echo "molecfit_model finished at: $(date -Iseconds)" >> "$TIME_LOG"
echo

echo "Searching molecfit_model products..."

MODEL_MOLECULES="$(find "$MODEL_OUT" -type f -iname "*MODEL_MOLECULES*.fits" | head -n 1)"
ATM_PARAMETERS="$(find "$MODEL_OUT" -type f -iname "*ATM_PARAMETERS*.fits" | head -n 1)"
BEST_FIT_PARAMETERS="$(find "$MODEL_OUT" -type f -iname "*BEST_FIT_PARAMETERS*.fits" | head -n 1)"

if [[ -z "$MODEL_MOLECULES" || -z "$ATM_PARAMETERS" || -z "$BEST_FIT_PARAMETERS" ]]; then
  echo "ERROR: Could not find all required molecfit_model products."
  echo
  echo "MODEL_MOLECULES:      ${MODEL_MOLECULES:-MISSING}"
  echo "ATM_PARAMETERS:       ${ATM_PARAMETERS:-MISSING}"
  echo "BEST_FIT_PARAMETERS:  ${BEST_FIT_PARAMETERS:-MISSING}"
  echo
  echo "Generated files:"
  find "$MODEL_OUT" -maxdepth 2 -type f | sort
  exit 1
fi

echo "Creating Molecfit mapping FITS files..."

python "$REPO_ROOT/scripts/utils/create_molecfit_mappings.py" \
  "$RUN_ROOT" \
  --atm-ext 1 \
  --lblrtm-ext 1

echo "Creating calctrans SOF:"
echo "  $CALCTRANS_SOF"

cat > "$CALCTRANS_SOF" <<EOF
$TEMPLATE_SPECTRUM SCIENCE
$MODEL_MOLECULES MODEL_MOLECULES
$ATM_PARAMETERS ATM_PARAMETERS
$BEST_FIT_PARAMETERS BEST_FIT_PARAMETERS
$MAPPING_ATM MAPPING_ATMOSPHERIC
$MAPPING_CONV MAPPING_CONVOLVE
EOF

cat "$CALCTRANS_SOF"
echo

echo "Running molecfit_calctrans..."
echo "Log: $CALCTRANS_LOG"
echo

/usr/bin/time -p \
  esorex \
    --recipe-config="$CALCTRANS_RC" \
    --output-dir="$CALCTRANS_OUT" \
    molecfit_calctrans \
    --SCALE_PWV="none" \
    "$CALCTRANS_SOF" \
  > "$CALCTRANS_LOG" 2>&1

echo "molecfit_calctrans finished."
echo "molecfit_calctrans finished at: $(date -Iseconds)" >> "$TIME_LOG"
echo

echo "Generated calctrans files:"
find "$CALCTRANS_OUT" -maxdepth 2 -type f | sort

echo
echo "Timing log:"
echo "  $TIME_LOG"
echo

echo "Done."
echo "========================================"
