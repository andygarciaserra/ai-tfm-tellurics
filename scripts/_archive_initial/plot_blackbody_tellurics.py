from astropy.io import fits
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

OUTPUTS = Path("outputs")
INPUT_FILE = OUTPUTS / "BEST_FIT_MODEL.fits"

# Temperatura ficticia para visualizar un continuo tipo cuerpo negro
T = 5800  # K, tipo solar

# Rango amplio para ver curvatura
WMIN = 0.53
WMAX = 1.02

def planck_lambda(wave_micron, T):
    """
    Planck simplificado en función de longitud de onda.
    wave_micron en micras.
    Devuelve intensidad normalizada.
    """
    h = 6.62607015e-34
    c = 2.99792458e8
    k = 1.380649e-23

    lam = wave_micron * 1e-6
    B = (2 * h * c**2) / (lam**5) / (np.exp((h * c) / (lam * k * T)) - 1)
    return B / np.nanmax(B)

with fits.open(INPUT_FILE) as hdul:
    data = hdul[1].data

    wave = np.array(data["lambda"], dtype=float)
    mtrans = np.array(data["mtrans"], dtype=float)

good = np.isfinite(wave) & np.isfinite(mtrans) & (mtrans > 0)
wave = wave[good]
mtrans = mtrans[good]

mask = (wave >= WMIN) & (wave <= WMAX)
wave = wave[mask]
mtrans = mtrans[mask]

# Continuo ideal tipo cuerpo negro
continuum = planck_lambda(wave, T)

# Espectro observado simulado: continuo afectado por telúricas
observed_with_tellurics = continuum * mtrans

# Espectro corregido ideal
corrected = observed_with_tellurics / mtrans

# Evitar artefactos donde transmisión es muy baja
safe = mtrans > 0.1

plt.figure(figsize=(13, 7))

plt.plot(wave, continuum, label="Continuo limpio tipo cuerpo negro")
plt.plot(wave, observed_with_tellurics, label="Observado simulado = continuo × telúricas")
plt.plot(wave[safe], corrected[safe], label="Corregido = observado / telúricas")
plt.plot(wave, mtrans, label="Transmisión telúrica", alpha=0.7)

plt.xlabel("Longitud de onda [micras]")
plt.ylabel("Flujo normalizado")
plt.title("Visualización conceptual: continuo + telúricas + corrección")
plt.legend()
plt.tight_layout()
plt.savefig(OUTPUTS / "06_blackbody_tellurics_correction.png", dpi=300)
plt.close()

print("Guardado en:")
print(OUTPUTS / "06_blackbody_tellurics_correction.png")
