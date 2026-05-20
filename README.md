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
    02_run_molecfit_single.sh
    03_plot_molecfit_outputs.py
    04_build_synthetic_dataset.py

    utils/
      inspect_fits.py
      create_flat_spectrum.py

    examples/
      demo_blackbody_tellurics.py

    _archive_initial/
      old exploratory scripts

  configs/
    molecfit.rc
    example.sof
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

### `scripts/02_run_molecfit_single.sh`

Runs one Molecfit execution using `esorex`.

**Main tasks:**

* run `molecfit_model`,
* use a Molecfit recipe config,
* use a `.sof` input file,
* write Molecfit outputs.

**Main inputs:**

```text
configs/molecfit.rc
configs/example.sof
```

**Outputs:**

```text
TFM_DATA/molecfit/outputs/
```

or, during early testing:

```text
outputs/
```

**Example:**

```bash
bash scripts/02_run_molecfit_single.sh
```

---

### `scripts/03_plot_molecfit_outputs.py`

Plots Molecfit output products.

**Main tasks:**

* read `BEST_FIT_MODEL.fits`,
* plot observed flux,
* plot fitted model,
* plot telluric transmission,
* plot approximate telluric correction.

**Expected FITS columns:**

* `lambda`
* `flux`
* `mflux`
* `mtrans`

**Outputs:**

```text
TFM_DATA/plots/molecfit/
```

or, during early testing:

```text
outputs/
```

**Example:**

```bash
python scripts/03_plot_molecfit_outputs.py
```

---

### `scripts/04_build_synthetic_dataset.py`

Builds the first synthetic dataset by combining PHOENIX spectra with Molecfit transmission models.

**Main operation:**

```text
observed_flux = clean_flux × transmission
```

**Main inputs:**

* prepared PHOENIX spectra,
* Molecfit `mtrans` files,
* stellar metadata,
* atmospheric metadata.

**Outputs:**

```text
TFM_DATA/synthetic/spectra/
TFM_DATA/synthetic/metadata/
TFM_DATA/plots/synthetic/
```

**Example:**

```bash
python scripts/04_build_synthetic_dataset.py
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
* [ ] Scripts reorganized into final structure.
* [ ] PHOENIX stellar pool generated.
* [ ] Molecfit atmospheric grid automated.
* [ ] First synthetic dataset generated.

---

## Roadmap

1. Clean and rename current scripts.
2. Generate a small PHOENIX stellar pool.
3. Automate Molecfit transmission generation.
4. Build the first synthetic dataset.
5. Add instrumental resolution.
6. Add synthetic noise.


## Notes

This repository is under active development. Early scripts may be exploratory, but the goal is to progressively convert them into a clean, documented, reproducible pipeline.

