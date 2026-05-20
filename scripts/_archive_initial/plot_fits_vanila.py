from astropy.io import fits
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# =========================
# CONFIGURACIÓN BÁSICA
# =========================

FITS_FILE = Path("outputs/BEST_FIT_MODEL.fits")
OUTPUT_FILE = Path("outputs/vanilla_fits_plot.png")

EXTENSION = 1  # normalmente 1 o 2

WMIN = None   # ejemplo: 0.755
WMAX = None   # ejemplo: 0.770

# =========================
# LEER FITS
# =========================

with fits.open(FITS_FILE) as hdul:
    print(hdul.info())

    data = hdul[EXTENSION].data

    print("Columnas disponibles:")
    print(data.columns.names)

    wave = np.array(data["lambda"], dtype=float)
    flux = np.array(data["flux"], dtype=float)
    mtrans = np.array(data["mtrans"], dtype=float)

# =========================
# LIMPIAR DATOS
# =========================

good = (
    np.isfinite(wave)
    & np.isfinite(flux)
    & np.isfinite(mtrans)
)

wave = wave[good]
flux = flux[good]
mtrans = mtrans[good]

# =========================
# ZOOM OPCIONAL
# =========================

if WMIN is not None and WMAX is not None:
    mask = (wave >= WMIN) & (wave <= WMAX)
else:
    mask = np.ones_like(wave, dtype=bool)

wave_plot = wave[mask]
flux_plot = flux[mask]
mtrans_plot = mtrans[mask]

print("Rango usado:")
print("lambda min =", np.min(wave_plot))
print("lambda max =", np.max(wave_plot))
print("N puntos =", len(wave_plot))

# =========================
# PLOT VANILLA
# =========================

fig, ax1 = plt.subplots(figsize=(12, 5))

ax1.plot(wave_plot, flux_plot, label="Flujo observado")
ax1.set_xlabel("Longitud de onda [micras]")
ax1.set_ylabel("Flujo observado")
ax1.grid(True, alpha=0.3)

# Segundo eje para transmisión, porque va de 0 a 1
ax2 = ax1.twinx()
ax2.plot(wave_plot, mtrans_plot, linestyle="--", label="Transmisión telúrica")
ax2.set_ylabel("Transmisión telúrica")
ax2.set_ylim(0, 1.05)

# Leyenda combinada
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc="best")

plt.title("Visualización básica del FITS")
plt.tight_layout()
plt.savefig(OUTPUT_FILE, dpi=300)
plt.close()

print(f"Figura guardada en: {OUTPUT_FILE}")
