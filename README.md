# ai-tfm-tellurics

Synthetic spectral dataset generation for telluric correction using **PHOENIX** stellar models and **Molecfit** atmospheric transmission models.

This repository is part of a Master's Thesis project focused on building physically controlled synthetic datasets for machine learning applications in astronomical spectroscopy.

---

## Project overview

The goal of this project is to generate synthetic observed spectra by combining clean stellar spectra with telluric atmospheric transmission models.

Conceptually, the pipeline is:

```text
clean stellar spectrum
× atmospheric transmission
× instrumental effects
+ noise
= synthetic observed spectrum
```

The first development stage focuses on:

```text
PHOENIX stellar spectrum × Molecfit mtrans = synthetic telluric-contaminated spectrum
```

The final objective is to train machine learning models either to:

* recover telluric-corrected spectra, or
* infer physical atmospheric parameters such as precipitable water vapour, airmass, or molecular abundances.

The second approach is especially interesting because it keeps the model output physically interpretable.

---

## Scientific motivation

Ground-based astronomical spectra are affected by absorption features produced by Earth's atmosphere. These telluric features depend on atmospheric conditions, observing geometry, and molecular species such as H2O, O2, O3, and CO2.

Traditional telluric correction methods rely on physical modelling or standard-star observations. This project explores a complementary approach: generating large synthetic datasets with known ground-truth atmospheric parameters and using them to train data-driven models.

The key idea is to keep the synthetic generation process modular and physically interpretable.

---

## Pipeline architecture

The project is designed around four independent components:

```text
stellar spectrum
atmosphere
instrument
noise
```

This separation allows controlled experiments, reproducible datasets, and scalable dataset generation.

### Current minimal pipeline

```text
PHOENIX clean spectrum
        |
        v
wavelength cut + resampling
        |
        v
Molecfit atmospheric transmission
        |
        v
clean_flux × transmission
        |
        v
synthetic observed spectrum
```

### Planned full pipeline

```text
PHOENIX clean spectrum
        |
        v
stellar preprocessing
        |
        v
Molecfit transmission grid
        |
        v
stellar × atmosphere combination
        |
        v
instrumental convolution
        |
        v
noise injection
        |
        v
final ML-ready dataset
```

---

## Repository layout

The repository contains code, configuration files, documentation, and lightweight examples. Large datasets and generated outputs should live outside the Git repository.

Recommended local structure:

```text
~/TFM/
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

  docs/
    notes, references, development notes
```

Recommended external data structure:

```text
~/TFM_DATA/
  phoenix/
    downloads/
    raw/
    resampled/

  molecfit/
    inputs/
    outputs/
    mtrans/

  synthetic/
    spectra/
    metadata/
    plots/
```

### Why keep `TFM_DATA` outside the repository?

Generated spectra, PHOENIX files, Molecfit outputs, FITS products, plots, and ML datasets can become very large. They should not be tracked by Git.

The repository should contain:

* source code,
* configuration files,
* documentation,
* small examples,
* reproducibility instructions.

The repository should not contain:

* large FITS files,
* full PHOENIX downloads,
* generated datasets,
* heavy plots,
* trained models unless explicitly required.

---

## Scripts

Scripts are numbered according to their position in the pipeline. Each script should have a clear responsibility and should be documented here when added.

General rule:

```text
every new script must have:
1. a numbered filename,
2. a short docstring at the top of the file,
3. an entry in this README,
4. clear inputs and outputs.
```

---

### `scripts/01_download_prepare_phoenix.py`

Download and prepare PHOENIX stellar spectra.

#### Purpose

This script downloads a PHOENIX wavelength grid and one or more stellar spectra, cuts them to the desired wavelength range, optionally estimates a continuum, resamples the spectra to a lighter grid, and saves the results as FITS files.

#### Current functionality

* Downloads the PHOENIX wavelength file.
* Downloads a selected PHOENIX stellar model.
* Converts wavelength from Angstrom to micron.
* Cuts the spectrum to the selected wavelength interval.
* Estimates an approximate continuum using a running percentile.
* Creates a continuum-normalized version.
* Resamples the spectrum to a fixed number of wavelength points.
* Saves full-resolution and resampled FITS files.
* Generates diagnostic plots.

#### Inputs

Currently configured inside the script:

* effective temperature, `TEFF`,
* surface gravity, `LOGG`,
* metallicity, `[Fe/H]`,
* wavelength range,
* number of resampled points,
* output directories.

Planned command-line usage:

```bash
python scripts/01_download_prepare_phoenix.py \
  --teff 9600 \
  --logg 4.0 \
  --feh 0.0 \
  --wmin 0.38 \
  --wmax 0.79 \
  --n-resampled 10000
```

#### Outputs

Expected outputs:

```text
~/TFM_DATA/phoenix/downloads/
~/TFM_DATA/phoenix/raw/
~/TFM_DATA/phoenix/resampled/
~/TFM_DATA/synthetic/plots/phoenix/
```

Typical products:

* raw PHOENIX FITS file,
* wavelength-cut PHOENIX FITS file,
* resampled PHOENIX FITS file,
* diagnostic PNG plots.

#### Example

```bash
python scripts/01_download_prepare_phoenix.py
```

---

### `scripts/02_run_molecfit_single.sh`

Run a single Molecfit model execution.

#### Purpose

This script runs Molecfit through `esorex` using a recipe configuration file and a SOF file. It is intended as the first reproducible Molecfit execution script before automating a full atmospheric grid.

#### Inputs

Expected inputs:

* Molecfit recipe configuration file,
* SOF file,
* input spectrum,
* selected output directory.

Typical files:

```text
configs/molecfit.rc
configs/example.sof
```

#### Outputs

Typical Molecfit products:

* best-fit model FITS file,
* atmospheric transmission model,
* Molecfit logs,
* intermediate outputs.

Expected output location:

```text
~/TFM_DATA/molecfit/outputs/
```

or, during early testing:

```text
outputs/
```

#### Example

```bash
bash scripts/02_run_molecfit_single.sh
```

---

### `scripts/03_plot_molecfit_outputs.py`

Visualize Molecfit output products.

#### Purpose

This script inspects and plots Molecfit output FITS files, especially the best-fit model and atmospheric transmission.

It is useful for checking whether Molecfit produced physically reasonable results before using the transmission curves in the synthetic dataset pipeline.

#### Inputs

Expected input:

```text
BEST_FIT_MODEL.fits
```

Expected columns may include:

* wavelength,
* observed flux,
* model flux,
* atmospheric transmission, `mtrans`.

#### Outputs

Diagnostic plots such as:

* observed spectrum vs fitted model,
* telluric transmission,
* absorption depth,
* approximate telluric correction.

Expected output location:

```text
~/TFM_DATA/molecfit/plots/
```

or, during early testing:

```text
outputs/
```

#### Example

```bash
python scripts/03_plot_molecfit_outputs.py
```

---

### `scripts/04_build_synthetic_dataset.py`

Build the first synthetic telluric-contaminated dataset.

#### Purpose

This script will combine prepared PHOENIX spectra with Molecfit atmospheric transmission models.

The basic operation is:

```text
observed_flux = clean_flux × transmission
```

This is the first script that connects the stellar and atmospheric modules into a dataset-generation pipeline.

#### Inputs

Expected inputs:

* prepared PHOENIX spectra,
* Molecfit `mtrans` files,
* common wavelength grid or interpolation strategy,
* stellar metadata,
* atmospheric metadata.

#### Outputs

Expected outputs:

```text
~/TFM_DATA/synthetic/spectra/
~/TFM_DATA/synthetic/metadata/
~/TFM_DATA/synthetic/plots/
```

Typical products:

* synthetic observed FITS files,
* clean spectrum references,
* transmission references,
* metadata table with physical parameters,
* optional diagnostic plots.

#### Example

```bash
python scripts/04_build_synthetic_dataset.py
```

---

## Utility scripts

Utility scripts are not part of the numbered production pipeline, but they are useful for debugging and inspection.

### `scripts/utils/inspect_fits.py`

Inspect a FITS file and generate quick-look plots when possible.

#### Purpose

Useful for checking FITS structure, extensions, available columns, and simple 1D or 2D previews.

#### Example

```bash
python scripts/utils/inspect_fits.py path/to/file.fits
```

---

### `scripts/utils/create_flat_spectrum.py`

Create a simple flat test spectrum.

#### Purpose

Useful for testing Molecfit or FITS I/O without using a real stellar spectrum.

#### Example

```bash
python scripts/utils/create_flat_spectrum.py
```

---

## Example scripts

Example scripts are conceptual demonstrations. They are useful for explanation and sanity checks but are not part of the main production pipeline.

### `scripts/examples/demo_blackbody_tellurics.py`

Demonstrate the effect of telluric absorption on an idealized stellar continuum.

#### Purpose

This example multiplies a simple blackbody-like continuum by a Molecfit transmission curve and shows how telluric correction works conceptually.

#### Example

```bash
python scripts/examples/demo_blackbody_tellurics.py
```

---

## Configuration files

Configuration files should live in:

```text
configs/
```

Expected Molecfit-related files:

```text
configs/molecfit.rc
configs/example.sof
```

Future configuration files may include:

```text
configs/phoenix_grid.yaml
configs/atmosphere_grid.yaml
configs/dataset_generation.yaml
```

The long-term goal is to avoid hard-coded parameters inside scripts and move experiment settings into explicit config files or command-line arguments.

---

## Data products and metadata

Every generated synthetic spectrum should be accompanied by metadata.

Recommended metadata fields:

```text
spectrum_id
star_id
atmosphere_id
teff
logg
feh
wmin_micron
wmax_micron
n_points
pwv
airmass
tel_alt
molecules
fit_molecules
source_phoenix_file
source_mtrans_file
output_file
```

This makes the dataset traceable and suitable for machine learning experiments.

---

## Development principles

### 1. Keep the pipeline modular

Each script should do one clear thing.

Good:

```text
download PHOENIX
prepare spectra
generate mtrans
combine spectra
plot examples
```

Bad:

```text
one giant script that does everything
```

### 2. Keep code and data separate

Code belongs in:

```text
~/TFM
```

Large generated data belongs in:

```text
~/TFM_DATA
```

### 3. Prefer reproducibility over manual steps

Whenever a manual step is repeated more than once, it should become a script.

### 4. Document every new script

Every new script must be added to the `Scripts` section of this README.

### 5. Avoid committing large files

Large FITS files, PHOENIX downloads, Molecfit outputs, generated datasets, plots, and model checkpoints should not be committed to Git.

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

Molecfit should be installed separately. On macOS, one working option is:

```bash
brew install esopipe-molecfit
```

Check that Molecfit commands are available:

```bash
which esorex
```

---

## Suggested `requirements.txt`

Initial Python dependencies:

```text
numpy
matplotlib
astropy
scipy
pandas
```

Additional packages may be added later for machine learning experiments.

---

## Git workflow

Recommended workflow:

```bash
git status
git add README.md scripts/ configs/ requirements.txt setup.sh .gitignore
git commit -m "Update TFM pipeline documentation and scripts"
git push
```

Before starting work on another machine:

```bash
git pull
```

---

## Current status

* [x] Molecfit installed and running.
* [x] PHOENIX download tested.
* [x] First A0-like PHOENIX spectrum downloaded.
* [x] Initial FITS visualization scripts created.
* [x] Initial Molecfit output plotting scripts created.
* [ ] Repository script structure cleaned.
* [ ] PHOENIX stellar pool generated.
* [ ] Molecfit atmospheric grid automated.
* [ ] First synthetic dataset generated.
* [ ] Instrumental convolution implemented.
* [ ] Noise model implemented.
* [ ] ML-ready dataset format defined.

---

## Immediate roadmap

### Step 1: Clean script structure

Reorganize existing scripts into:

```text
scripts/
scripts/utils/
scripts/examples/
scripts/_archive_initial/
```

### Step 2: Stabilize PHOENIX preparation

Turn the current PHOENIX download script into a reusable script with command-line arguments.

### Step 3: Stabilize Molecfit execution

Move from a single Molecfit run to an automated atmospheric grid.

### Step 4: Build first synthetic dataset

Generate a first controlled dataset:

```text
5 stellar spectra × 20 atmospheric models = 100 synthetic spectra
```

### Step 5: Add instrumental and noise effects

Include realistic instrumental resolution and synthetic noise.

---

## Long-term goals

* Generate large synthetic datasets for telluric correction.
* Store physically meaningful metadata for every synthetic spectrum.
* Train ML models on controlled synthetic spectra.
* Compare direct spectral correction against atmospheric-parameter inference.
* Explore probabilistic outputs for physical atmospheric parameters.

---

## Notes

This repository is under active development. Early scripts may be exploratory, but the goal is to progressively convert them into a clean, documented, reproducible pipeline.

