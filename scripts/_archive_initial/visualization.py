from astropy.io import fits
import matplotlib.pyplot as plt

data = fits.open("outputs/BEST_FIT_MODEL.fits")

print(data.info())
