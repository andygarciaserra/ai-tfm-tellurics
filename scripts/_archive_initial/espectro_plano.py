from astropy.io import fits
import numpy as np

wave = np.linspace(1.1, 1.8, 2000)
flux = np.ones_like(wave)

col1 = fits.Column(name='WAVE', array=wave, format='D')
col2 = fits.Column(name='FLUX', array=flux, format='D')

hdu = fits.BinTableHDU.from_columns([col1, col2])
hdu.writeto('data/flat.fits', overwrite=True)
