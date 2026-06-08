#!/usr/bin/env python3

from pathlib import Path
from astropy.io import fits
import numpy as np
import argparse


def write_mapping(path: Path, column_name: str, value: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    col = fits.Column(
        name=column_name,
        format="1K",
        array=np.array([0,value], dtype=np.int64),
    )

    hdu = fits.BinTableHDU.from_columns([col])
    hdu.name = "MAPPING"

    hdul = fits.HDUList([
        fits.PrimaryHDU(),
        hdu,
    ])

    hdul.writeto(path, overwrite=True)
    print(f"Written: {path}")


def main():
    parser = argparse.ArgumentParser(
        description="Create Molecfit calctrans mapping FITS files."
    )
    parser.add_argument(
        "output_dir",
        help="Directory where mapping FITS files will be written.",
    )
    parser.add_argument(
        "--atm-ext",
        type=int,
        default=1,
        help="ATM_PARAMETERS extension to map to SCIENCE extension. Default: 1.",
    )
    parser.add_argument(
        "--lblrtm-ext",
        type=int,
        default=1,
        help="LBLRTM_RESULTS extension to map to TELLURIC_CORR extension. Default: 1.",
    )

    args = parser.parse_args()
    output_dir = Path(args.output_dir).expanduser().resolve()

    write_mapping(
        output_dir / "MAPPING_ATMOSPHERIC.fits",
        "ATM_PARAMETERS_EXT",
        args.atm_ext,
    )

    write_mapping(
        output_dir / "MAPPING_CONVOLVE.fits",
        "LBLRTM_RESULTS_EXT",
        args.lblrtm_ext,
    )


if __name__ == "__main__":
    main()
