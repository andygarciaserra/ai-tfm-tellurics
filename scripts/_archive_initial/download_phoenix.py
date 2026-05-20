from pathlib import Path
from urllib.request import urlretrieve

import numpy as np
import matplotlib.pyplot as plt
from astropy.io import fits

# ============================================================
# CONFIG
# ============================================================

BASE_DIR = Path("/home/andy/Documentos/TFM")
BASE_OUTDIR = BASE_DIR / "data/synthetic/phoenix"
DOWNLOAD_DIR = BASE_OUTDIR / "downloads"
RAW_DIR = BASE_OUTDIR / "raw"
RESAMPLED_DIR = BASE_OUTDIR / "resampled"

for d in [DOWNLOAD_DIR, RAW_DIR, RESAMPLED_DIR]:
    d.mkdir(parents=True, exist_ok=True)

PLOTDIR = BASE_DIR / "outputs/phoenix"
PLOTDIR.mkdir(parents=True, exist_ok=True)

BASE_URL = "https://phoenix.astro.physik.uni-goettingen.de/data/HiResFITS"

TEFF = 9600
LOGG = 4.0

Z_FOLDER = "Z-0.0"
Z_FILE = "-0.0"
FEH_VALUE = 0.0

WMIN_MICRON = 0.38
WMAX_MICRON = 0.79

N_RESAMPLED = 10000

MODEL_LABEL = f"A0V_T{TEFF}_logg{str(LOGG).replace('.', 'p')}"

# ============================================================
# FUNCIONES
# ============================================================

def running_percentile(y, window=5001, percentile=95):
    if window % 2 == 0:
        window += 1

    half = window // 2
    continuum = np.full_like(y, np.nan, dtype=float)

    for i in range(len(y)):
        lo = max(0, i - half)
        hi = min(len(y), i + half + 1)
        continuum[i] = np.nanpercentile(y[lo:hi], percentile)

    return continuum


def save_spectrum_fits(path, wave, flux, continuum=None, flux_norm=None, comment=""):
    cols = [
        fits.Column(name="WAVE_MICRON", array=wave.astype("float32"), format="E"),
        fits.Column(name="FLUX", array=flux.astype("float32"), format="E"),
    ]

    if continuum is not None:
        cols.append(
            fits.Column(name="CONTINUUM", array=continuum.astype("float32"), format="E")
        )

    if flux_norm is not None:
        cols.append(
            fits.Column(name="FLUX_CONT_NORM", array=flux_norm.astype("float32"), format="E")
        )

    hdu = fits.BinTableHDU.from_columns(cols)
    hdu.header["TEFF"] = TEFF
    hdu.header["LOGG"] = LOGG
    hdu.header["FEH"] = FEH_VALUE
    hdu.header["WMIN"] = WMIN_MICRON
    hdu.header["WMAX"] = WMAX_MICRON
    hdu.header["NPOINTS"] = len(wave)
    hdu.header["COMMENT"] = comment
    hdu.writeto(path, overwrite=True)


def plot_spectrum(path, wave, flux, title, ylabel="Flujo PHOENIX"):
    plt.figure(figsize=(14, 5))
    plt.plot(wave, flux, color="black", linewidth=0.35)
    plt.xlabel("Longitud de onda [micras]")
    plt.ylabel(ylabel)
    plt.title(title)
    plt.tight_layout()
    plt.savefig(path, dpi=300)
    plt.close()


# ============================================================
# URLS Y FICHEROS DESCARGADOS
# ============================================================

wave_name = "WAVE_PHOENIX-ACES-AGSS-COND-2011.fits"
wave_url = f"{BASE_URL}/{wave_name}"
wave_file = DOWNLOAD_DIR / wave_name

spectrum_name = (
    f"lte{TEFF:05d}-{LOGG:.2f}{Z_FILE}."
    "PHOENIX-ACES-AGSS-COND-2011-HiRes.fits"
)

spectrum_url = (
    f"{BASE_URL}/PHOENIX-ACES-AGSS-COND-2011/"
    f"{Z_FOLDER}/{spectrum_name}"
)

spectrum_file = DOWNLOAD_DIR / spectrum_name

print("Modelo PHOENIX:")
print("TEFF =", TEFF)
print("LOGG =", LOGG)
print("[Fe/H] =", FEH_VALUE)
print("Spectrum URL:", spectrum_url)

# ============================================================
# DOWNLOAD
# ============================================================

if not wave_file.exists():
    print("Descargando fichero de longitudes de onda...")
    urlretrieve(wave_url, wave_file)
else:
    print("El fichero de longitudes de onda ya existe.")

if not spectrum_file.exists():
    print("Descargando espectro PHOENIX...")
    urlretrieve(spectrum_url, spectrum_file)
else:
    print("El espectro PHOENIX ya existe.")

# ============================================================
# READ + CUT
# ============================================================

wave_angstrom = fits.getdata(wave_file)
flux = fits.getdata(spectrum_file)

wave_micron = wave_angstrom * 1e-4

mask = (wave_micron >= WMIN_MICRON) & (wave_micron <= WMAX_MICRON)

wave_cut = wave_micron[mask]
flux_cut = flux[mask]

print("\nFULLRES recortado:")
print("lambda min [micron]:", np.nanmin(wave_cut))
print("lambda max [micron]:", np.nanmax(wave_cut))
print("N puntos:", len(wave_cut))

# ============================================================
# FULLRES OUTPUT
# ============================================================

continuum_full = running_percentile(flux_cut, window=5001, percentile=95)
flux_norm_full = flux_cut / continuum_full

fullres_fits = RAW_DIR / f"phoenix_{MODEL_LABEL}_fullres.fits"

save_spectrum_fits(
    fullres_fits,
    wave_cut,
    flux_cut,
    continuum_full,
    flux_norm_full,
    comment="PHOENIX full-resolution spectrum cut to ESPRESSO-like range.",
)

# ============================================================
# RESAMPLING
# ============================================================

wave_resampled = np.linspace(
    np.nanmin(wave_cut),
    np.nanmax(wave_cut),
    N_RESAMPLED,
)

flux_resampled = np.interp(
    wave_resampled,
    wave_cut,
    flux_cut,
)

print("\nRESAMPLED:")
print("lambda min [micron]:", np.nanmin(wave_resampled))
print("lambda max [micron]:", np.nanmax(wave_resampled))
print("N puntos:", len(wave_resampled))

continuum_resampled = running_percentile(flux_resampled, window=501, percentile=95)
flux_norm_resampled = flux_resampled / continuum_resampled

resampled_fits = RESAMPLED_DIR / f"phoenix_{MODEL_LABEL}_{N_RESAMPLED}pts.fits"

save_spectrum_fits(
    resampled_fits,
    wave_resampled,
    flux_resampled,
    continuum_resampled,
    flux_norm_resampled,
    comment="PHOENIX resampled spectrum cut to ESPRESSO-like range.",
)

# ============================================================
# PLOTS
# ============================================================

plot_spectrum(
    PLOTDIR / f"phoenix_{MODEL_LABEL}_fullres_raw.png",
    wave_cut,
    flux_cut,
    f"PHOENIX {MODEL_LABEL} fullres sin normalizar",
)

plot_spectrum(
    PLOTDIR / f"phoenix_{MODEL_LABEL}_{N_RESAMPLED}pts_raw.png",
    wave_resampled,
    flux_resampled,
    f"PHOENIX {MODEL_LABEL} resampled {N_RESAMPLED} pts sin normalizar",
)

plot_spectrum(
    PLOTDIR / f"phoenix_{MODEL_LABEL}_{N_RESAMPLED}pts_norm.png",
    wave_resampled,
    flux_norm_resampled,
    f"PHOENIX {MODEL_LABEL} resampled {N_RESAMPLED} pts normalizado",
    ylabel="Flujo normalizado al continuo",
)

print("\nGuardado FITS fullres:")
print(fullres_fits)
print("Guardado FITS resampled:")
print(resampled_fits)
print("\nPlots en:")
print(PLOTDIR)
