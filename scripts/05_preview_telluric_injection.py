#!/usr/bin/env python3

from pathlib import Path
from astropy.io import fits
import numpy as np
import matplotlib.pyplot as plt
import csv
import re

RUN_ID = "atm_test002"

TELLURIC_DATA = Path.home() / f"TFM_DATA/molecfit/runs/{RUN_ID}/molecfit_calctrans/TELLURIC_DATA.fits"

OUTPUT_DIR = Path.home() / f"TFM_DATA/molecfit/runs/{RUN_ID}/preview"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_CSV = Path("configs/molecfit/mtrans_config_test.csv")

def read_template_from_sof(run_id: str):
    sof_path = Path.home() / f"TFM_DATA/molecfit/runs/{run_id}/molecfit_model.sof"

    with sof_path.open() as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            parts = line.split()
            if len(parts) >= 2 and parts[1] == "SCIENCE":
                return Path(parts[0])

    raise ValueError(f"No SCIENCE file found in {sof_path}")

def read_run_config(config_csv: Path, run_id: str):
    with config_csv.open(newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["run_id"] == run_id:
                return row

    raise ValueError(f"run_id '{run_id}' not found in {config_csv}")

def parse_phoenix_filename(path: Path):
    name = path.name

    meta = {
        "star_type": "unknown",
        "teff": "unknown",
        "logg": "unknown",
        "feh": "unknown",
    }

    m = re.search(r"phoenix_([A-Za-z0-9]+)_", name)
    if m:
        meta["star_type"] = m.group(1)

    m = re.search(r"_T(\d+)_", name)
    if m:
        meta["teff"] = m.group(1)

    m = re.search(r"_logg([mp0-9]+)_", name)
    if m:
        meta["logg"] = m.group(1).replace("p", ".").replace("m", "-")

    m = re.search(r"_feh([mp0-9]+)_", name)
    if m:
        feh = m.group(1).replace("p", ".").replace("m", "-")
        if not feh.startswith("-"):
            feh = "+" + feh
        meta["feh"] = feh

    return meta

def build_metadata_text(run_id: str, config_row: dict, star_meta: dict):
    return "\n".join([
        f"Run: {run_id}",
        f"Star: {star_meta['star_type']}",
        f"Teff: {star_meta['teff']} K",
        f"log g: {star_meta['logg']} [cgs]",
        f"[Fe/H]: {star_meta['feh']} dex",
        "",
        f"PWV: {config_row['pwv']} mm",
        f"Tel. alt.: {config_row['telalt']} deg",
        f"Rel. hum.: {config_row['rhum']} %",
        f"Pressure: {config_row['pres']} hPa",
        f"Temp.: {config_row['temp']} °C",
        f"Molecules: {config_row['molecules']}",
        f"Rel. col.: {config_row['rel_col']} [-]",
        f"Wave inc.: {config_row['wave_include']} µm",
    ])

def add_metadata_box(ax, metadata_text: str):
    ax.text(
        0.01,0.03,
        metadata_text,
        transform=ax.transAxes,
        fontsize=8, 
        horizontalalignment="left",
        verticalalignment="bottom",
        bbox=dict(
            boxstyle="round",
            facecolor="white",
            alpha=0.85,
        ),
    )

def read_telluric_data(path: Path):
    with fits.open(path) as hdul:
        data = hdul[1].data

        wavelength = np.asarray(data["lambda"], dtype=float)
        flux = np.asarray(data["flux"], dtype=float)
        mlambda = np.asarray(data["mlambda"], dtype=float)
        mtrans = np.asarray(data["mtrans"], dtype=float)
        qual = np.asarray(data["qual"], dtype=int)

    good = (
        np.isfinite(wavelength)
        & np.isfinite(flux)
        & np.isfinite(mtrans)
        & np.isfinite(mlambda)
        & np.isfinite(qual)
        & (mtrans >= 0)
        & (mtrans <= 1)
    )

    return wavelength[good], flux[good], mlambda[good], mtrans[good], qual[good]

def interpolate_mtrans_to_lambda(wavelength, flux, mlambda, mtrans, qual):
    print("\n=== Interpolation diagnostics ===")
    print(f"Input points: {len(wavelength)}")
    print(f"lambda range:  {wavelength.min():.6f} - {wavelength.max():.6f}")
    print(f"mlambda range: {mlambda.min():.6f} - {mlambda.max():.6f}")
    print(f"mtrans range:  {mtrans.min():.6f} - {mtrans.max():.6f}")

    # Solapamiento entre grids
    overlap_min = max(wavelength.min(), mlambda.min())
    overlap_max = min(wavelength.max(), mlambda.max())

    print(f"Overlap range: {overlap_min:.6f} - {overlap_max:.6f}")

    if overlap_min >= overlap_max:
        raise ValueError("No overlap between wavelength and mlambda grids.")

    # Interpolación
    mtrans_on_lambda = np.interp(
        wavelength,
        mlambda,
        mtrans,
        left=np.nan,
        right=np.nan
    )

    n_nan_interp = np.isnan(mtrans_on_lambda).sum()
    print(f"NaNs after interpolation: {n_nan_interp}/{len(mtrans_on_lambda)}")

    # Máscara final de validez
    valid = (
        np.isfinite(wavelength)
        & np.isfinite(flux)
        & np.isfinite(mtrans_on_lambda)
        & (mtrans_on_lambda >= 0)
        & (mtrans_on_lambda <= 1)
    )

    n_valid = valid.sum()
    n_rejected = len(valid) - n_valid

    print(f"Valid points after filtering:   {n_valid}/{len(valid)}")
    print(f"Rejected points after filtering: {n_rejected}/{len(valid)}")

    wavelength_out = wavelength[valid]
    flux_out = flux[valid]
    mtrans_on_lambda_out = mtrans_on_lambda[valid]
    qual_out = qual[valid]

    synthetic_flux_out = flux_out * mtrans_on_lambda_out

    print(f"Final wavelength range: {wavelength_out.min():.6f} - {wavelength_out.max():.6f}")
    print(f"Final mtrans range:     {mtrans_on_lambda_out.min():.6f} - {mtrans_on_lambda_out.max():.6f}")
    print(f"Final synthetic flux range: {synthetic_flux_out.min():.6e} - {synthetic_flux_out.max():.6e}")

    if np.isnan(synthetic_flux_out).any():
        print("WARNING: NaNs detected in synthetic_flux after filtering.")
    else:
        print("OK: No NaNs in synthetic_flux.")

    if np.any((mtrans_on_lambda_out < 0) | (mtrans_on_lambda_out > 1)):
        print("WARNING: Interpolated transmission outside [0, 1].")
    else:
        print("OK: Interpolated transmission within [0, 1].")

    print("=== End interpolation diagnostics ===\n")

    return wavelength_out, flux_out, mtrans_on_lambda_out, synthetic_flux_out, qual_out


def main():
    
    template_spectrum = read_template_from_sof(RUN_ID)
    config_row = read_run_config(CONFIG_CSV, RUN_ID)
    star_meta = parse_phoenix_filename(template_spectrum)
    metadata_text = build_metadata_text(RUN_ID, config_row, star_meta)
    wavelength, flux, mlambda, mtrans, qual = read_telluric_data(TELLURIC_DATA)

    wavelength, flux, mtrans_on_lambda, synthetic_flux, qual = interpolate_mtrans_to_lambda(
        wavelength, flux, mlambda, mtrans, qual)

    print("Loaded:", TELLURIC_DATA)
    print("N points:", len(wavelength))
    print("lambda range:", wavelength.min(), wavelength.max())
    print("mtrans original range:", mtrans.min(), mtrans.max())
    print("mtrans interpolated range:", mtrans_on_lambda.min(), mtrans_on_lambda.max())
    print("flux range:", flux.min(), flux.max())
    print("synthetic flux range:", synthetic_flux.min(), synthetic_flux.max())

    # 1. Transmission preview
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(wavelength, mtrans_on_lambda, linewidth=0.8)
    ax.set_xlabel("Wavelength [micron]")
    ax.set_ylabel("Transmission")
    ax.set_title(f"Molecfit mtrans preview - {RUN_ID}")
    add_metadata_box(ax, metadata_text)
    fig.tight_layout()
    out = OUTPUT_DIR / f"{RUN_ID}_mtrans.png"
    fig.savefig(out, dpi=300)
    plt.close()
    print("Saved:", out)

    # 2. Original vs telluric-contaminated spectrum
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(wavelength, flux, linewidth=0.8, label="PHOENIX clean")
    ax.plot(wavelength, synthetic_flux, linewidth=0.8, label="PHOENIX × mtrans")
    ax.set_xlabel("Wavelength [micron]")
    ax.set_ylabel("Flux")
    ax.set_title(f"Telluric injection preview - {RUN_ID}")
    add_metadata_box(ax, metadata_text)
    fig.tight_layout()
    out = OUTPUT_DIR / f"{RUN_ID}_phoenix_vs_telluric.png"
    fig.savefig(out, dpi=300)
    plt.close()
    print("Saved:", out)

    # 3. Zoom where tellurics are usually visible in this range
    zoom_min, zoom_max = 0.68, 0.79
    zoom = (wavelength >= zoom_min) & (wavelength <= zoom_max)

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(wavelength[zoom], flux[zoom], linewidth=0.8, label="PHOENIX clean")
    ax.plot(wavelength[zoom], synthetic_flux[zoom], linewidth=0.8, label="PHOENIX × mtrans")
    ax.set_xlabel("Wavelength [micron]")
    ax.set_ylabel("Flux")
    ax.set_title(f"Telluric injection zoom {zoom_min}-{zoom_max} micron - {RUN_ID}")
    add_metadata_box(ax, metadata_text)
    fig.tight_layout()
    out = OUTPUT_DIR / f"{RUN_ID}_phoenix_vs_telluric_zoom.png"
    fig.savefig(out, dpi=300)
    plt.close()
    print("Saved:", out)

if __name__ == "__main__":
    main()
