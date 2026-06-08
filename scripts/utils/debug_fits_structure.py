#!/usr/bin/env python3

from astropy.io import fits
from pathlib import Path
import argparse
import numpy as np


def print_header_subset(header, keys):
    for key in keys:
        if key in header:
            print(f"  {key}: {header[key]}")


def debug_fits_structure(fits_file: Path, show_header: bool = False):
    fits_file = fits_file.expanduser().resolve()

    if not fits_file.exists():
        raise FileNotFoundError(f"FITS file not found: {fits_file}")

    print("\n" + "=" * 80)
    print(f"FITS file: {fits_file}")
    print("=" * 80)

    with fits.open(fits_file) as hdul:
        print("\n=== HDU INFO ===")
        hdul.info()

        for i, hdu in enumerate(hdul):
            print("\n" + "-" * 80)
            print(f"EXTENSION {i}")
            print("-" * 80)

            print(f"Name: {hdu.name}")
            print(f"HDU type: {type(hdu).__name__}")

            header = hdu.header
            data = hdu.data

            print("\nHeader summary:")
            print_header_subset(
                header,
                [
                    "XTENSION", "EXTNAME", "NAXIS", "NAXIS1", "NAXIS2",
                    "TFIELDS", "PRO.CATG", "ESO PRO CATG",
                    "MJD-OBS", "UTC",
                    "ESO TEL AIRM START", "ESO TEL AIRM END",
                ],
            )

            if show_header:
                print("\nFull header:")
                print(repr(header))

            if data is None:
                print("\nData: None")
                continue

            print(f"\nData type: {type(data)}")

            if hasattr(data, "columns"):
                print("Table format: BINTABLE")
                print(f"Rows: {len(data)}")
                print(f"Columns: {len(data.columns)}")

                print("\nColumn details:")
                for col in data.columns:
                    name = col.name
                    arr = np.asarray(data[name])

                    print(f"  {name}")
                    print(f"    FITS format: {col.format}")
                    print(f"    dtype: {arr.dtype}")
                    print(f"    shape: {arr.shape}")

                    if np.issubdtype(arr.dtype, np.number):
                        finite = np.isfinite(arr)
                        print(f"    finite: {finite.sum()}/{arr.size}")
                        if finite.any():
                            print(f"    min: {np.nanmin(arr)}")
                            print(f"    max: {np.nanmax(arr)}")

            elif isinstance(data, np.ndarray):
                print("Image format")
                print(f"Shape: {data.shape}")
                print(f"dtype: {data.dtype}")

                if np.issubdtype(data.dtype, np.number):
                    finite = np.isfinite(data)
                    print(f"finite: {finite.sum()}/{data.size}")
                    if finite.any():
                        print(f"min: {np.nanmin(data)}")
                        print(f"max: {np.nanmax(data)}")


def main():
    parser = argparse.ArgumentParser(description="Debug FITS file structure.")
    parser.add_argument("fits_file", help="Path to FITS file.")
    parser.add_argument(
        "--show-header",
        action="store_true",
        help="Print full FITS headers.",
    )

    args = parser.parse_args()
    debug_fits_structure(Path(args.fits_file), show_header=args.show_header)


if __name__ == "__main__":
    main()
