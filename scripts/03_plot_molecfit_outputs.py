from astropy.io import fits
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

OUTPUTS = Path("outputs")
OUTPUTS.mkdir(exist_ok=True)

INPUT_FILE = OUTPUTS / "BEST_FIT_MODEL.fits"

# Rango en MICRAS
WMIN = 0.68
WMAX = 0.72

with fits.open(INPUT_FILE) as hdul:
    data = hdul[1].data

    wave = np.array(data["lambda"], dtype=float)
    flux = np.array(data["flux"], dtype=float)
    mflux = np.array(data["mflux"], dtype=float)
    mtrans = np.array(data["mtrans"], dtype=float)

print("Rango de longitud de onda:")
print("wave min:", np.nanmin(wave))
print("wave max:", np.nanmax(wave))

good = (
    np.isfinite(wave)
    & np.isfinite(flux)
    & np.isfinite(mflux)
    & np.isfinite(mtrans)
    & (mtrans > 0.05)
)

wave = wave[good]
flux = flux[good]
mflux = mflux[good]
mtrans = mtrans[good]

flux_norm = flux / np.nanmedian(flux)
mflux_norm = mflux / np.nanmedian(mflux)
flux_corrected = flux_norm / mtrans

zoom = (wave >= WMIN) & (wave <= WMAX)

print(f"Puntos dentro del zoom {WMIN}-{WMAX} micras:", np.sum(zoom))

if np.sum(zoom) == 0:
    print("No hay puntos en ese rango. Usando todo el espectro.")
    zoom = np.ones_like(wave, dtype=bool)

# ============================================================
# 1) Observado, modelo y corregido
# ============================================================

plt.figure(figsize=(12, 6))

plt.plot(wave[zoom], flux_norm[zoom], label="Observado normalizado")
plt.plot(wave[zoom], mflux_norm[zoom], label="Modelo ajustado")
plt.plot(
    wave[zoom],
    flux_corrected[zoom],
    label="Corregido aprox. = observado / transmisión",
)

plt.xlabel("Longitud de onda [micras]")
plt.ylabel("Flujo normalizado")
plt.title(f"Comparación espectral normalizada ({WMIN}-{WMAX} micras)")
plt.legend()
plt.tight_layout()
plt.savefig(OUTPUTS / "01_comparacion_normalizada.png", dpi=300)
plt.close()

# ============================================================
# 2) Transmisión telúrica
# ============================================================

plt.figure(figsize=(12, 4))

plt.plot(wave[zoom], mtrans[zoom], label="Transmisión telúrica")

plt.xlabel("Longitud de onda [micras]")
plt.ylabel("Transmisión")
plt.title(f"Transmisión telúrica modelada ({WMIN}-{WMAX} micras)")
plt.ylim(0, 1.05)
plt.legend()
plt.tight_layout()
plt.savefig(OUTPUTS / "02_transmision_telurica.png", dpi=300)
plt.close()

# ============================================================
# 3) Profundidad de absorción
# ============================================================

plt.figure(figsize=(12, 4))

plt.plot(wave[zoom], 1 - mtrans[zoom], label="Absorción telúrica = 1 - transmisión")

plt.xlabel("Longitud de onda [micras]")
plt.ylabel("Profundidad de absorción")
plt.title(f"Profundidad de líneas telúricas ({WMIN}-{WMAX} micras)")
plt.legend()
plt.tight_layout()
plt.savefig(OUTPUTS / "03_absorcion_telurica.png", dpi=300)
plt.close()

print("Figuras guardadas en:")
print(OUTPUTS / "01_comparacion_normalizada.png")
print(OUTPUTS / "02_transmision_telurica.png")
print(OUTPUTS / "03_absorcion_telurica.png")
