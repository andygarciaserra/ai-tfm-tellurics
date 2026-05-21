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
  README.md
  requirements.txt
  setup.sh
  .gitignore

  scripts/
    01_download_prepare_phoenix.py
    02_generate_phoenix_pool.sh
    03_validate_phoenix_pool.py
    04_generate_mtrans_single.sh
    05_generate_mtrans_grid.sh *
    06_validate_mtrans_grid.py *
    07_build_synthetic_dataset.py *

    utils/
      inspect_fits.py
      create_flat_spectrum.py

    examples/
      demo_blackbody_tellurics.py

    _archive_initial/
      (old exploratory scripts)

  configs/
    phoenix_initial_pool.csv


* To be done
```

Large generated files should be stored outside the repository, for example:

```text
TFM_DATA/
  phoenix/
  molecfit/
  synthetic/
  plots/
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

Initial script for generating one Molecfit/mtrans atmospheric transmission model.

This script is the starting point for the atmospheric part of the pipeline. The goal is to first generate one local `mtrans` product in a controlled and reproducible way before scaling to a grid of atmospheric models.

**Planned role:**

* generate one atmospheric transmission model,
* store the output in `TFM_DATA/molecfit/`,
* keep logs and metadata for the run,
* serve as the basic unit for future grid generation and parallelization.

**Example:**

```bash
bash scripts/04_generate_mtrans_single.sh
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

* [x] Molecfit installed and running.
* [x] PHOENIX download tested.
* [x] First PHOENIX spectrum downloaded and resampled.
* [x] Initial Molecfit output plots created.
* [x] Scripts reorganized into final structure.
* [x] Initial PHOENIX stellar pool generated and validated.
* [x] PHOENIX pool configuration file added.
* [x] PHOENIX pool validation script added.
* [ ] Molecfit/mtrans atmospheric grid automated.

---

## Roadmap

1. Automate Molecfit/mtrans single-run generation.
2. Generate a small local mtrans test grid.
3. Test the same workflow on Dicha/IAC.
4. Add parallel mtrans generation.
5. Build the first synthetic dataset.
6. Add instrumental resolution and noise.


## Notes

This repository is under active development. Early scripts may be exploratory, but the goal is to progressively convert them into a clean, documented, reproducible pipeline.

