import os

# ruta a molecfit (ajústala)
MOLECFIT_PATH = "/home/andy/molecfit/bin/"

# crear archivo .par simple
par_content = """
filename: data/flat.fits
output_dir: output/

wrange_include: 1.1 1.8
list_molec: H2O CO2 O2

airmass: 1.2
pwv: 2.0
"""

with open("config.par", "w") as f:
    f.write(par_content)

# ejecutar molecfit
os.system(f"esoreflex molecfit config.par")
os.system(f"esoreflex calctrans config.par")
