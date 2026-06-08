#!/usr/bin/env bash
set -euo pipefail

# ------------------------------------------------------------
# Generate one Molecfit/calctrans run.
#
# Pipeline:
#   PHOENIX FITS
#     -> molecfit_model
#     -> molecfit_calctrans
#     -> TELLURIC_DATA / TELLURIC_CORR
# ------------------------------------------------------------

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

DATA_ROOT="${TFM_DATA_ROOT:-$HOME/TFM_DATA}"

RUN_ID="${1:-atm001}"
MODEL_SOF_ARG="${2:-configs/molecfit/molecfit_model.sof}"

MODEL_RC="$REPO_ROOT/configs/molecfit/molecfit_model.rc"
CALCTRANS_RC="$REPO_ROOT/configs/molecfit/molecfit_calctrans.rc"

# Interpret relative SOF paths from the repository root.
if [[ "$MODEL_SOF_ARG" = /* ]]; then
  MODEL_SOF="$MODEL_SOF_ARG"
else
  MODEL_SOF="$REPO_ROOT/$MODEL_SOF_ARG"
fi

RUN_ROOT="$DATA_ROOT/molecfit/runs/$RUN_ID"
MODEL_OUT="$RUN_ROOT/molecfit_model"
CALCTRANS_OUT="$RUN_ROOT/molecfit_calctrans"
LOG_DIR="$RUN_ROOT/logs"
METADATA_DIR="$RUN_ROOT/metadata"

MODEL_LOG="$LOG_DIR/molecfit_model.log"
CALCTRANS_LOG="$LOG_DIR/molecfit_calctrans.log"
TIME_LOG="$LOG_DIR/timing.log"
CALCTRANS_SOF="$RUN_ROOT/molecfit_calctrans.sof"

MAPPING_ATM="$RUN_ROOT/MAPPING_ATMOSPHERIC.fits"
MAPPING_CONV="$RUN_ROOT/MAPPING_CONVOLVE.fits"

mkdir -p "$MODEL_OUT" "$CALCTRANS_OUT" "$LOG_DIR" "$METADATA_DIR"

echo "========================================"
echo "Generating Molecfit/calctrans single run"
echo "Run ID:        $RUN_ID"
echo "Repo root:     $REPO_ROOT"
echo "Data root:     $DATA_ROOT"
echo "Model RC:      $MODEL_RC"
echo "Calctrans RC:  $CALCTRANS_RC"
echo "Model SOF:     $MODEL_SOF"
echo "Run folder:    $RUN_ROOT"
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

if [[ ! -f "$MODEL_SOF" ]]; then
  echo "ERROR: Missing model SOF file:"
  echo "  $MODEL_SOF"
  exit 1
fi

if ! command -v esorex >/dev/null 2>&1; then
  echo "ERROR: esorex not found in PATH."
  exit 1
fi

SCIENCE_FILE="$(awk 'NF && $1 !~ /^#/ {print $1; exit}' "$MODEL_SOF")"

if [[ ! -f "$SCIENCE_FILE" ]]; then
  echo "ERROR: Science file listed in SOF does not exist:"
  echo "  $SCIENCE_FILE"
  exit 1
fi

{
  echo "Run ID: $RUN_ID"
  echo "Date:   $(date -Iseconds)"
  echo "Host:   $(hostname)"
  echo "Science file: $SCIENCE_FILE"
  echo
} > "$TIME_LOG"

echo "Running molecfit_model..."
echo "Log: $MODEL_LOG"
echo

{
  echo "Command:"
  echo "esorex --recipe-config=$MODEL_RC --output-dir=$MODEL_OUT molecfit_model ..."
  echo
} >> "$TIME_LOG"

/usr/bin/time -p \
  esorex \
    --recipe-config="$MODEL_RC" \
    --output-dir="$MODEL_OUT" \
    molecfit_model \
    --LIST_MOLEC="H2O,O2,O3,CO2" \
    --FIT_MOLEC="1,1,0,0" \
    --REL_COL="1.0,1.0,1.0,1.0" \
    --WAVE_INCLUDE="0.68,0.72,0.75,0.79" \
    --COLUMN_LAMBDA="WAVE_MICRON" \
    --COLUMN_FLUX="FLUX" \
    --COLUMN_DFLUX="NULL" \
    --COLUMN_MASK="NULL" \
    --WLG_TO_MICRON="1.0" \
    --WAVELENGTH_FRAME="VAC" \
    --PWV="3.0" \
    --OBSERVING_DATE_KEYWORD="NONE" \
    --OBSERVING_DATE_VALUE="60100.0" \
    --UTC_KEYWORD="NONE" \
    --UTC_VALUE="36000.0" \
    --TELESCOPE_ANGLE_KEYWORD="NONE" \
    --TELESCOPE_ANGLE_VALUE="60.0" \
    --RELATIVE_HUMIDITY_KEYWORD="NONE" \
    --RELATIVE_HUMIDITY_VALUE="15.0" \
    --PRESSURE_KEYWORD="NONE" \
    --PRESSURE_VALUE="750.0" \
    --TEMPERATURE_KEYWORD="NONE" \
    --TEMPERATURE_VALUE="15.0" \
    --MIRROR_TEMPERATURE_KEYWORD="NONE" \
    --MIRROR_TEMPERATURE_VALUE="15.0" \
    --ELEVATION_KEYWORD="NONE" \
    --ELEVATION_VALUE="2635.0" \
    --LONGITUDE_KEYWORD="NONE" \
    --LONGITUDE_VALUE="-70.4051" \
    --LATITUDE_KEYWORD="NONE" \
    --LATITUDE_VALUE="-24.6276" \
    --SLIT_WIDTH_KEYWORD="NONE" \
    --SLIT_WIDTH_VALUE="0.4" \
    --PIX_SCALE_KEYWORD="NONE" \
    --PIX_SCALE_VALUE="0.086" \
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
$SCIENCE_FILE SCIENCE
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

{
  echo
  echo "Command:"
  echo "esorex --recipe-config=$CALCTRANS_RC --output-dir=$CALCTRANS_OUT molecfit_calctrans $CALCTRANS_SOF"
  echo
} >> "$TIME_LOG"

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
