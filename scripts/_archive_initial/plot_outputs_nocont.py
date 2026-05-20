from astropy.io import fits
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

OUTPUTS = Path("outputs")
INPUT_FILE = OUTPUTS / "BEST_FIT_MODEL.fits"

WMIN = 0.68
WMAX = 0.72

with fits.open(INPUT_FILE) as hdul:
    data = hdul[1].data

    wave = np.array(data["lambda"], dtype=float)
    flux = np.array(data["flux"], dtype=float)
    mflux = np.array(data["mflux"], dtype=float)
    mtrans = np.array(data["mtrans"], dtype=float)

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

zoom = (wave >= WMIN) & (wave <= WMAX)

print("wave min:", np.nanmin(wave))
print("wave max:", np.nanmax(wave))
print(f"Puntos en zoom {WMIN}-{WMAX}:", np.sum(zoom))

if np.sum(zoom) == 0:
    zoom = np.ones_like(wave, dtype=bool)

# Corrección aproximada SIN normalizar
flux_corrected = flux / mtrans

# ============================================================
# 1) Flujo observado y modelo SIN normalizar
# ============================================================

plt.figure(figsize=(12, 6))

plt.plot(wave[zoom], flux[zoom], label="Observado sin normalizar")
plt.plot(wave[zoom], mflux[zoom], label="Modelo ajustado sin normalizar")

plt.xlabel("Longitud de onda [micras]")
plt.ylabel("Flujo")
plt.title(f"Espectro sin normalizar ({WMIN}-{WMAX} micras)")
plt.legend()
plt.tight_layout()
plt.savefig(OUTPUTS / "04_sin_normalizar_observado_modelo.png", dpi=300)
plt.close()

# ============================================================
# 2) Observado, corregido y transmisión
# ============================================================

fig, ax1 = plt.subplots(figsize=(12, 6))

ax1.plot(wave[zoom], flux[zoom], label="Observado sin normalizar")
ax1.plot(wave[zoom], flux_corrected[zoom], label="Corregido aprox. sin normalizar")

ax1.set_xlabel("Longitud de onda [micras]")
ax1.set_ylabel("Flujo")

ax2 = ax1.twinx()
ax2.plot(wave[zoom], mtrans[zoom], linestyle="--", label="Transmisión telúrica")
ax2.set_ylabel("Transmisión")
ax2.set_ylim(0, 1.05)

lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2)

plt.title(f"Corrección telúrica sin normalizar ({WMIN}-{WMAX} micras)")
plt.tight_layout()
plt.savefig(OUTPUTS / "05_sin_normalizar_correccion.png", dpi=300)
plt.close()

print("Figuras guardadas:")
print(OUTPUTS / "04_sin_normalizar_observado_modelo.png")
print(OUTPUTS / "05_sin_normalizar_correccion.png")
