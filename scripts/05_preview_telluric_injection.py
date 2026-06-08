#!/usr/bin/env python3

from pathlib import Path
from astropy.io import fits
import numpy as np
import matplotlib.pyplot as plt


RUN_ID = "atm_test002"

TELLURIC_DATA = Path.home() / f"TFM_DATA/molecfit/runs/{RUN_ID}/molecfit_calctrans/TELLURIC_DATA.fits"

OUTPUT_DIR = Path.home() / f"TFM_DATA/molecfit/runs/{RUN_ID}/preview"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


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
        & (mtrans >= 0)
        & (mtrans <= 1)
    )

    return wavelength[good], flux[good], mlambda[good], mtrans[good], qual[good]


def main():
    wavelength, flux, mlambda, mtrans, qual = read_telluric_data(TELLURIC_DATA)

    synthetic_flux = flux * mtrans

    print("Loaded:", TELLURIC_DATA)
    print("N points:", len(wavelength))
    print("lambda range:", wavelength.min(), wavelength.max())
    print("mtrans range:", mtrans.min(), mtrans.max())
    print("flux range:", flux.min(), flux.max())
    print("synthetic flux range:", synthetic_flux.min(), synthetic_flux.max())

    # 1. Transmission preview
    plt.figure(figsize=(12, 4))
    plt.plot(wavelength, mtrans, linewidth=0.8)
    plt.xlabel("Wavelength [micron]")
    plt.ylabel("Transmission")
    plt.title(f"Molecfit mtrans preview - {RUN_ID}")
    plt.tight_layout()
    out = OUTPUT_DIR / f"{RUN_ID}_mtrans.png"
    plt.savefig(out, dpi=300)
    plt.close()
    print("Saved:", out)

    # 2. Original vs telluric-contaminated spectrum
    plt.figure(figsize=(12, 5))
    plt.plot(wavelength, flux, linewidth=0.8, label="PHOENIX clean")
    plt.plot(wavelength, synthetic_flux, linewidth=0.8, label="PHOENIX × mtrans")
    plt.xlabel("Wavelength [micron]")
    plt.ylabel("Flux")
    plt.title(f"Telluric injection preview - {RUN_ID}")
    plt.legend()
    plt.tight_layout()
    out = OUTPUT_DIR / f"{RUN_ID}_phoenix_vs_telluric.png"
    plt.savefig(out, dpi=300)
    plt.close()
    print("Saved:", out)

    # 3. Zoom where tellurics are usually visible in this range
    zoom_min, zoom_max = 0.68, 0.79
    zoom = (wavelength >= zoom_min) & (wavelength <= zoom_max)

    plt.figure(figsize=(12, 5))
    plt.plot(wavelength[zoom], flux[zoom], linewidth=0.8, label="PHOENIX clean")
    plt.plot(wavelength[zoom], synthetic_flux[zoom], linewidth=0.8, label="PHOENIX × mtrans")
    plt.xlabel("Wavelength [micron]")
    plt.ylabel("Flux")
    plt.title(f"Telluric injection zoom {zoom_min}-{zoom_max} micron - {RUN_ID}")
    plt.legend()
    plt.tight_layout()
    out = OUTPUT_DIR / f"{RUN_ID}_phoenix_vs_telluric_zoom.png"
    plt.savefig(out, dpi=300)
    plt.close()
    print("Saved:", out)


if __name__ == "__main__":
    main()
