from astropy.io import fits
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# ==========================================
# CONFIG
# ==========================================

FITS_FILE = Path("/home/andy/Documentos/TFM/data/demo/share/esopipes/datademo/molecfit/raw/ESPRESSO/espectro.fits")

OUTPUT_DIR = Path("/home/andy/Documentos/TFM/outputs/fits_preview")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ==========================================
# ABRIR FITS
# ==========================================

with fits.open(FITS_FILE) as hdul:
    print("\n=== FITS INFO ===")
    hdul.info()

    for i, hdu in enumerate(hdul):
        print(f"\n--- EXTENSION {i} ---")
        print("Name:", hdu.name)
        print("Type:", type(hdu.data))

        if hdu.data is None:
            continue

        data = hdu.data

        # Caso tabla FITS
        if hasattr(data, "columns"):
            print("Columns:", data.columns.names)

            cols = data.columns.names
            lower_cols = [c.lower() for c in cols]

            wave_candidates = ["lambda", "wavelength", "wave", "wl", "wavelength_air", "wavelength_vac"]
            flux_candidates = ["flux", "flx", "science", "spec", "spectrum"]

            wave_col = None
            flux_col = None

            for candidate in wave_candidates:
                if candidate in lower_cols:
                    wave_col = cols[lower_cols.index(candidate)]
                    break

            for candidate in flux_candidates:
                if candidate in lower_cols:
                    flux_col = cols[lower_cols.index(candidate)]
                    break

            if wave_col is not None and flux_col is not None:
                wave = np.array(data[wave_col], dtype=float)
                flux = np.array(data[flux_col], dtype=float)

                good = np.isfinite(wave) & np.isfinite(flux)
                wave = wave[good]
                flux = flux[good]

                plt.figure(figsize=(12, 5))
                plt.plot(wave, flux)
                plt.xlabel(f"Wavelength [{wave_col}]")
                plt.ylabel(f"Flux [{flux_col}]")
                plt.title(f"{FITS_FILE.name} - ext {i}")
                plt.tight_layout()

                out = OUTPUT_DIR / f"{FITS_FILE.stem}_ext{i}_table.png"
                plt.savefig(out, dpi=300)
                plt.close()

                print("Saved:", out)

        # Caso imagen 1D
        elif isinstance(data, np.ndarray):
            print("Shape:", data.shape)

            if data.ndim == 1:
                flux = np.array(data, dtype=float)
                wave = np.arange(len(flux))

                good = np.isfinite(flux)
                wave = wave[good]
                flux = flux[good]

                plt.figure(figsize=(12, 5))
                plt.plot(wave, flux)
                plt.xlabel("Pixel")
                plt.ylabel("Flux")
                plt.title(f"{FITS_FILE.name} - ext {i} - 1D image")
                plt.tight_layout()

                out = OUTPUT_DIR / f"{FITS_FILE.stem}_ext{i}_1d.png"
                plt.savefig(out, dpi=300)
                plt.close()

                print("Saved:", out)

            elif data.ndim == 2:
                plt.figure(figsize=(10, 6))
                plt.imshow(data, origin="lower", aspect="auto")
                plt.colorbar(label="Value")
                plt.title(f"{FITS_FILE.name} - ext {i} - 2D image")
                plt.tight_layout()

                out = OUTPUT_DIR / f"{FITS_FILE.stem}_ext{i}_2d.png"
                plt.savefig(out, dpi=300)
                plt.close()

                print("Saved:", out)

print("\nDone.")
