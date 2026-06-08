# ai-tfm-tellurics

Synthetic spectral dataset generation for telluric correction using **PHOENIX** stellar models and **Molecfit** atmospheric transmission models.

This repository is part of a Master's Thesis project focused on building controlled synthetic spectra for machine learning applications in astronomical spectroscopy.

The basic idea is:

```text
clean stellar spectrum × atmospheric transmission = synthetic observed spectrum
```

In later stages, instrumental resolution and noise will be added to make the synthetic spectra more realistic.

---

## Contents

* [Project overview](#project-overview)
* [Repository structure](#repository-structure)
* [Scripts](#scripts)
  * [PHOENIX scripts](#phoenix-scripts)
    * [01 — Download and prepare PHOENIX](#01--download-and-prepare-phoenix)
    * [02 — Generate PHOENIX pool](#02--generate-phoenix-pool)
    * [03 — Validate PHOENIX pool](#03--validate-phoenix-pool)
  * [Molecfit / mtrans scripts](#molecfit--mtrans-scripts)
    * [04 — Generate one mtrans model](#04--generate-one-mtrans-model)
* [Installation](#installation)
* [Current status](#current-status)
* [Roadmap](#roadmap)

---

## Project overview

The pipeline combines:

* clean stellar spectra from **PHOENIX**,
* atmospheric transmission models generated with **Molecfit**,
* metadata describing the stellar and atmospheric parameters.

The first target dataset is:

```text
5 stellar spectra × 20 atmospheric models = 100 synthetic spectra
```

The final goal is to use these datasets to train machine learning models for telluric correction or atmospheric-parameter inference.

---

## Repository structure

```text

ai-tfm-tellurics/
├── README.md
├── requirements.txt
├── configs/
│   ├── phoenix_initial_pool.csv
│   └── molecfit/
│       ├── molecfit_model.rc
│       ├── molecfit_calctrans.rc
│       ├── mtrans_single_config.csv
│       ├── mtrans_grid.csv
│       ├── mtrans_config_test.csv
│       ├── molecfit_model_manual.txt
│       └── molecfit_calctrans_manual.txt
├── docs/
│   └── postit.md
└── scripts/
    ├── 01_download_prepare_phoenix.py
    ├── 02_generate_phoenix_pool.sh
    ├── 03_validate_phoenix_pool.py
    ├── 04_generate_mtrans_single.sh
    ├── 05_preview_telluric_injection.py
    ├── utils/
    │   ├── inspect_fits.py
    │   ├── debug_fits_structure.py
    │   ├── create_flat_spectrum.py
    │   └── create_molecfit_mappings.py
    ├── examples/
    │   └── demo_blackbody_tellurics.py
    └── _archive_initial/
        └── old exploratory scripts
```


Large generated files are stored outside the repository, following this structure:

```text
TFM_DATA/
├── phoenix/
│   ├── downloads/
│   ├── raw/
│   ├── resampled/
│   └── metadata/
├── molecfit/
│   └── runs/
│       └── <run_id>/
│           ├── molecfit_model/
│           ├── molecfit_calctrans/
│           ├── logs/
│           ├── metadata/
│           └── preview/
├── synthetic/
└── plots/
```

---

## Scripts

Scripts are numbered according to their position in the pipeline.

### `scripts/01_download_prepare_phoenix.py`

Downloads and prepares PHOENIX stellar spectra.

**Main tasks:**

* download PHOENIX wavelength grid,
* download selected stellar model,
* cut wavelength range,
* estimate continuum,
* create continuum-normalized flux,
* resample to a lighter wavelength grid,
* save FITS files and diagnostic plots.

**Main inputs:**

* `TEFF`
* `LOGG`
* `[Fe/H]`
* wavelength range
* number of resampled points

**Outputs:**
- download the PHOENIX wavelength grid,
- download a selected stellar model,
- cut the spectrum to a chosen wavelength range,
- resample it to a lighter wavelength grid,
- save FITS files and diagnostic plots.

By default, this script keeps the original PHOENIX flux without continuum normalization. Normalized products are only generated when explicitly requested with `--normalize`.

**Main inputs:**

- stellar label, for example `A0V`, `G2V`, `M2V`,
- effective temperature, `--teff`,
- surface gravity, `--logg`,
- metallicity, `--feh`,
- wavelength range, `--wmin` and `--wmax`,
- number of resampled points, `--n-resampled`.

**Standard outputs:**

```text
TFM_DATA/phoenix/downloads/
TFM_DATA/phoenix/raw/
TFM_DATA/phoenix/resampled/
TFM_DATA/phoenix/metadata/
TFM_DATA/plots/phoenix/
```

The standard FITS products contain:

```text
WAVE_MICRON
FLUX
```

If `--normalize` is used, the FITS files also include:

```text
CONTINUUM
FLUX_CONT_NORM
```

**Standard example:**

```bash
python scripts/01_download_prepare_phoenix.py \
  --label A0V \
  --teff 9600 \
  --logg 4.0 \
  --feh 0.0 \
  --wmin 0.38 \
  --wmax 0.79 \
  --n-resampled 10000
```

**With normalization:**

```bash
python scripts/01_download_prepare_phoenix.py \
  --label A0V \
  --teff 9600 \
  --logg 4.0 \
  --feh 0.0 \
  --wmin 0.38 \
  --wmax 0.79 \
  --n-resampled 10000 \
  --normalize
```

---

### `scripts/02_generate_phoenix_pool.sh`

Generates the initial PHOENIX stellar pool from a CSV configuration file.

This script is a Bash wrapper around `scripts/01_download_prepare_phoenix.py`. It reads one row per stellar model from:

```text
configs/phoenix_initial_pool.csv
```

and runs the PHOENIX preparation script with the corresponding parameters.

**Main tasks:**

* read the PHOENIX pool configuration,
* generate several PHOENIX spectra in batch,
* keep the pool definition version-controlled and reproducible,
* print progress as `[i/N]` for each model.

**Main inputs:**

* `configs/phoenix_initial_pool.csv`

The current initial pool contains:

```text
F5V
G2V
K5V
M0V
M2V
```

**Example:**

```bash
bash scripts/02_generate_phoenix_pool.sh
```

A different config file can also be passed explicitly:

```bash
bash scripts/02_generate_phoenix_pool.sh configs/phoenix_initial_pool.csv
```

---

### `scripts/03_validate_phoenix_pool.py`

Validates the generated PHOENIX stellar pool.

The script reads the same CSV configuration used to generate the pool and checks that the expected FITS and metadata products were created correctly.

**Main checks:**

* expected FITS files exist,
* expected metadata JSON files exist,
* FITS files contain `WAVE_MICRON` and `FLUX`,
* wavelength and flux arrays have the expected length,
* wavelength grid is finite and strictly increasing,
* wavelength range matches the requested range,
* flux values are finite and not identically zero,
* available metadata values are consistent with the CSV configuration.

**Main inputs:**

* `configs/phoenix_initial_pool.csv`
* generated PHOENIX products in `TFM_DATA/phoenix/`

**Outputs:**

```text
TFM_DATA/phoenix/metadata/phoenix_initial_pool_validation_summary.csv
```

**Example:**

```bash
python scripts/03_validate_phoenix_pool.py
```

A different config file can also be passed explicitly:

```bash
python scripts/03_validate_phoenix_pool.py configs/phoenix_initial_pool.csv
```

---

### `scripts/04_generate_mtrans_single.sh`

Generates one Molecfit/calctrans atmospheric transmission run from a CSV configuration file.

This script is the basic unit of the atmospheric part of the pipeline. It uses a PHOENIX spectrum as the wavelength/template input and generates the corresponding Molecfit products and telluric transmission files.

The script reads one row from a Molecfit configuration CSV, selected by `run_id`.

**Main inputs:**

```text
configs/molecfit/mtrans_single_config.csv
configs/molecfit/mtrans_grid.csv
configs/molecfit/mtrans_config_test.csv
```

Each row contains the atmospheric and observational parameters used for a run, for example:

```text
run_id
template_spectrum
pwv
telalt
rhum
pres
temp
molecules
fit_molec
rel_col
wave_include
wavelength_frame
latitude
longitude
geoelev
slit_width
pix_scale
```

**Main tasks:**

* read atmospheric parameters from a CSV configuration file,
* create the `molecfit_model.sof` file for the selected run,
* run `esorex molecfit_model`,
* locate the required Molecfit products:

  * `MODEL_MOLECULES.fits`,
  * `ATM_PARAMETERS.fits`,
  * `BEST_FIT_PARAMETERS.fits`,
* create explicit Molecfit mapping FITS files,
* create the `molecfit_calctrans.sof` file,
* run `esorex molecfit_calctrans`,
* store all outputs in a run-specific folder.

**Example:**

```bash
bash scripts/04_generate_mtrans_single.sh atm_test002 configs/molecfit/mtrans_config_test.csv
```

**Run output structure:**

```text
TFM_DATA/molecfit/runs/<run_id>/
  molecfit_model.sof
  molecfit_calctrans.sof
  MAPPING_ATMOSPHERIC.fits
  MAPPING_CONVOLVE.fits

  molecfit_model/
    MODEL_MOLECULES.fits
    ATM_PARAMETERS.fits
    BEST_FIT_PARAMETERS.fits
    BEST_FIT_MODEL.fits
    MOLECFIT_DATA.fits
    ...

  molecfit_calctrans/
    TELLURIC_DATA.fits
    TELLURIC_CORR.fits
    LBLRTM_RESULTS.fits

  logs/
    molecfit_model.log
    molecfit_calctrans.log
    timing.log
```

The most relevant product for the synthetic dataset is:

```text
TELLURIC_DATA.fits
```

It contains the original input spectrum and the telluric model columns, including:

```text
lambda
flux
mlambda
mtrans
cflux
qual
```

---

### `scripts/05_preview_telluric_injection.py`

Creates diagnostic plots for one Molecfit/calctrans run.

This script is used to visually validate that a generated atmospheric transmission can be applied to a PHOENIX spectrum to create a telluric-contaminated synthetic spectrum.

**Main tasks:**

* read `TELLURIC_DATA.fits` from a selected `run_id`,
* extract:
  * `lambda`,
  * `flux`,
  * `mlambda`,
  * `mtrans`,
  * `qual`,
* interpolate the telluric transmission from the Molecfit model wavelength grid to the PHOENIX wavelength grid,
* compute:

```text
synthetic_flux(lambda) = flux(lambda) × mtrans_interpolated(lambda)
```

* generate diagnostic plots:

  * atmospheric transmission,
  * PHOENIX clean spectrum vs PHOENIX × mtrans,
  * zoomed view of the telluric absorption region,
* print interpolation diagnostics:

  * input wavelength ranges,
  * overlap between `lambda` and `mlambda`,
  * NaNs after interpolation,
  * valid/rejected points,
  * final wavelength range,
  * final transmission range.

**Important note about wavelength grids:**

`TELLURIC_DATA.fits` contains both:

```text
lambda   = wavelength grid of the input PHOENIX spectrum
mlambda  = wavelength grid of the Molecfit telluric model
mtrans   = telluric transmission defined on mlambda
```

Therefore, the transmission should not be applied by array index. It must first be interpolated:

```text
mtrans(mlambda) → mtrans(lambda)
```

and only then multiplied by the PHOENIX flux.

**Example:**

```bash
python scripts/05_preview_telluric_injection.py
```

**Preview outputs:**

```text
TFM_DATA/molecfit/runs/<run_id>/preview/
  <run_id>_mtrans.png
  <run_id>_phoenix_vs_telluric.png
  <run_id>_phoenix_vs_telluric_zoom.png
```


---

## Utility scripts

### `scripts/utils/inspect_fits.py`

Inspects a FITS file and prints its structure, extensions, columns and basic information.

```bash
python scripts/utils/inspect_fits.py path/to/file.fits
```

### `scripts/utils/create_flat_spectrum.py`

Creates a simple flat FITS spectrum for testing.

```bash
python scripts/utils/create_flat_spectrum.py
```

---

## Example scripts

### `scripts/examples/demo_blackbody_tellurics.py`

Conceptual demo showing how telluric transmission affects a simple stellar continuum.

```bash
python scripts/examples/demo_blackbody_tellurics.py
```

---

## Installation

Create and activate a Python environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

Install Python dependencies:

```bash
pip install -r requirements.txt
```

Molecfit must be installed separately. One working option is:

```bash
brew install esopipe-molecfit
```

Check that `esorex` is available:

```bash
which esorex
```

---

## Current status


* [x] Molecfit installed through ESO pipelines / EsoRex.
* [x] PHOENIX download and preparation tested.
* [x] Initial PHOENIX stellar pool generated.
* [x] PHOENIX pool validation script added.
* [x] First Molecfit/calctrans run completed from PHOENIX input.
* [x] Explicit Molecfit mapping FITS files implemented.
* [x] Atmospheric parameters moved to CSV configuration.
* [x] `TELLURIC_DATA.fits` generated and inspected.
* [x] Telluric injection preview implemented.
* [x] `mtrans(mlambda)` interpolation to the PHOENIX `lambda` grid implemented.
* [ ] Automated mtrans grid generation.
* [ ] Synthetic dataset FITS builder.
* [ ] Execution and timing comparison on Dicha/IAC.


---

## Roadmap

1. Clean and consolidate the Molecfit configuration files.
2. Generate a small atmospheric mtrans grid from CSV.
3. Validate changes in `mtrans` with PWV, telescope altitude and molecule columns.
4. Apply each generated mtrans to the PHOENIX stellar pool.
5. Build self-contained synthetic FITS files containing:
   * clean stellar flux,
   * interpolated mtrans,
   * telluric-contaminated flux,
   * atmospheric parameters,
   * stellar parameters.
6. Add noise and instrumental effects.
7. Test the pipeline on Dicha/IAC.
8. Parallelize mtrans generation.

## Notes

This repository is under active development. Early scripts may be exploratory, but the goal is to progressively convert them into a clean, documented, reproducible pipeline.

