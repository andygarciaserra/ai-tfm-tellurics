#!/usr/bin/env python3
"""
01_download_prepare_phoenix.py

Download and prepare PHOENIX stellar spectra.

This script:
- downloads the PHOENIX wavelength grid,
- downloads one PHOENIX stellar model,
- cuts it to a selected wavelength range,
- resamples the spectrum to a lighter wavelength grid,
- saves FITS products and diagnostic plots.

By default, the script keeps the physical/raw PHOENIX flux.
Continuum estimation and continuum-normalized outputs are optional and are only
computed when --normalize is used.

Standard example:
    python scripts/01_download_prepare_phoenix.py \
        --label A0V \
        --teff 9600 \
        --logg 4.0 \
        --feh 0.0 \
        --wmin 0.38 \
        --wmax 0.79 \
        --n-resampled 10000

With optional normalization products:
    python scripts/01_download_prepare_phoenix.py \
        --label A0V \
        --teff 9600 \
        --logg 4.0 \
        --feh 0.0 \
        --wmin 0.38 \
        --wmax 0.79 \
        --n-resampled 10000 \
        --normalize
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from urllib.request import urlretrieve

import matplotlib.pyplot as plt
import numpy as np
from astropy.io import fits

try:
    from scipy.ndimage import percentile_filter
except ImportError:  # pragma: no cover
    percentile_filter = None


PHOENIX_BASE_URL = "https://phoenix.astro.physik.uni-goettingen.de/data/HiResFITS"
PHOENIX_MODEL_GRID = "PHOENIX-ACES-AGSS-COND-2011"
PHOENIX_WAVE_FILE = "WAVE_PHOENIX-ACES-AGSS-COND-2011.fits"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download, crop and resample a PHOENIX stellar spectrum."
    )

    parser.add_argument(
        "--label",
        type=str,
        default="A0V",
        help="Human-readable label for the stellar model, e.g. A0V, G2V, M2V.",
    )
    parser.add_argument(
        "--teff",
        type=int,
        default=9600,
        help="Effective temperature of the PHOENIX model.",
    )
    parser.add_argument(
        "--logg",
        type=float,
        default=4.0,
        help="Surface gravity of the PHOENIX model.",
    )
    parser.add_argument(
        "--feh",
        type=float,
        default=0.0,
        help="Metallicity [Fe/H] of the PHOENIX model.",
    )
    parser.add_argument(
        "--wmin",
        type=float,
        default=0.38,
        help="Minimum wavelength in microns.",
    )
    parser.add_argument(
        "--wmax",
        type=float,
        default=0.79,
        help="Maximum wavelength in microns.",
    )
    parser.add_argument(
        "--n-resampled",
        type=int,
        default=10000,
        help="Number of points in the resampled spectrum.",
    )
    parser.add_argument(
        "--normalize",
        action="store_true",
        help=(
            "Compute continuum and continuum-normalized flux products. "
            "Disabled by default to keep physical/raw spectra as the standard output."
        ),
    )
    parser.add_argument(
        "--continuum-window-fullres",
        type=int,
        default=5001,
        help="Window size for the full-resolution running percentile continuum.",
    )
    parser.add_argument(
        "--continuum-window-resampled",
        type=int,
        default=501,
        help="Window size for the resampled running percentile continuum.",
    )
    parser.add_argument(
        "--continuum-percentile",
        type=float,
        default=95.0,
        help="Percentile used to estimate the approximate continuum.",
    )
    parser.add_argument(
        "--data-root",
        type=Path,
        default=Path(os.environ.get("TFM_DATA", "~/TFM_DATA")).expanduser(),
        help="Root directory for generated data. Defaults to $TFM_DATA or ~/TFM_DATA.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing output FITS and plot files.",
    )
    parser.add_argument(
        "--no-plots",
        action="store_true",
        help="Disable diagnostic plot generation.",
    )

    return parser.parse_args()


def metallicity_strings(feh: float) -> tuple[str, str, float]:
    """
    Convert numeric [Fe/H] into PHOENIX folder and filename metallicity strings.

    For solar metallicity, PHOENIX uses the slightly unintuitive string '-0.0'.
    Example:
        feh = 0.0  -> ('Z-0.0', '-0.0', 0.0)
        feh = -0.5 -> ('Z-0.5', '-0.5', -0.5)
        feh = 0.5  -> ('Z+0.5', '+0.5', 0.5)
    """
    feh = round(float(feh), 1)

    if feh == 0.0:
        return "Z-0.0", "-0.0", 0.0

    sign = "+" if feh > 0 else "-"
    value = abs(feh)
    return f"Z{sign}{value:.1f}", f"{sign}{value:.1f}", feh


def model_label(label: str, teff: int, logg: float, feh: float) -> str:
    logg_str = f"{logg:.1f}".replace(".", "p")
    feh_str = f"{feh:+.1f}".replace("+", "p").replace("-", "m").replace(".", "p")
    return f"{label}_T{teff}_logg{logg_str}_feh{feh_str}"


def ensure_directories(data_root: Path) -> dict[str, Path]:
    paths = {
        "download_dir": data_root / "phoenix" / "downloads",
        "raw_dir": data_root / "phoenix" / "raw",
        "resampled_dir": data_root / "phoenix" / "resampled",
        "metadata_dir": data_root / "phoenix" / "metadata",
        "plot_dir": data_root / "plots" / "phoenix",
    }

    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)

    return paths


def download_if_needed(url: str, output_path: Path) -> None:
    if output_path.exists():
        print(f"Already exists: {output_path}")
        return

    print(f"Downloading:\n  {url}\n  -> {output_path}")
    urlretrieve(url, output_path)


def running_percentile(y: np.ndarray, window: int, percentile: float) -> np.ndarray:
    """Estimate a smooth upper-envelope continuum with a running percentile."""
    if window % 2 == 0:
        window += 1

    if percentile_filter is not None:
        return percentile_filter(y, percentile=percentile, size=window, mode="nearest")

    print("WARNING: scipy not found. Falling back to slower NumPy running percentile.")
    half = window // 2
    continuum = np.full_like(y, np.nan, dtype=float)

    for i in range(len(y)):
        lo = max(0, i - half)
        hi = min(len(y), i + half + 1)
        continuum[i] = np.nanpercentile(y[lo:hi], percentile)

    return continuum


def save_spectrum_fits(
    path: Path,
    wave_micron: np.ndarray,
    flux: np.ndarray,
    metadata: dict,
    overwrite: bool,
    continuum: np.ndarray | None = None,
    flux_norm: np.ndarray | None = None,
) -> None:
    columns = [
        fits.Column(name="WAVE_MICRON", array=wave_micron.astype("float32"), format="E"),
        fits.Column(name="FLUX", array=flux.astype("float32"), format="E"),
    ]

    if continuum is not None and flux_norm is not None:
        columns.extend(
            [
                fits.Column(name="CONTINUUM", array=continuum.astype("float32"), format="E"),
                fits.Column(name="FLUX_CONT_NORM", array=flux_norm.astype("float32"), format="E"),
            ]
        )

    hdu = fits.BinTableHDU.from_columns(columns)
    hdu.name = "SPECTRUM"

    hdu.header["LABEL"] = metadata["label"]
    hdu.header["TEFF"] = metadata["teff"]
    hdu.header["LOGG"] = metadata["logg"]
    hdu.header["FEH"] = metadata["feh"]
    hdu.header["WMIN"] = metadata["wmin_micron"]
    hdu.header["WMAX"] = metadata["wmax_micron"]
    hdu.header["NPOINTS"] = len(wave_micron)
    hdu.header["SRC"] = "PHOENIX"
    hdu.header["NORM"] = bool(metadata["normalized_products"])

    primary = fits.PrimaryHDU()
    primary.header["OBJECT"] = metadata["model_label"]
    primary.header["COMMENT"] = metadata["comment"]

    hdul = fits.HDUList([primary, hdu])
    hdul.writeto(path, overwrite=overwrite)


def save_metadata(path: Path, metadata: dict, overwrite: bool) -> None:
    if path.exists() and not overwrite:
        print(f"Metadata already exists: {path}")
        return

    with path.open("w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)


def plot_spectrum(
    path: Path,
    wave: np.ndarray,
    flux: np.ndarray,
    title: str,
    ylabel: str,
    overwrite: bool,
) -> None:
    if path.exists() and not overwrite:
        print(f"Plot already exists: {path}")
        return

    plt.figure(figsize=(14, 5))
    plt.plot(wave, flux, linewidth=0.35)
    plt.xlabel("Wavelength [micron]")
    plt.ylabel(ylabel)
    plt.title(title)
    plt.tight_layout()
    plt.savefig(path, dpi=300)
    plt.close()


def main() -> None:
    args = parse_args()

    if args.wmin >= args.wmax:
        raise ValueError("--wmin must be smaller than --wmax")

    paths = ensure_directories(args.data_root)
    z_folder, z_file, feh_value = metallicity_strings(args.feh)
    label = model_label(args.label, args.teff, args.logg, feh_value)

    wave_url = f"{PHOENIX_BASE_URL}/{PHOENIX_WAVE_FILE}"
    wave_file = paths["download_dir"] / PHOENIX_WAVE_FILE

    spectrum_name = (
        f"lte{args.teff:05d}-{args.logg:.2f}{z_file}."
        f"{PHOENIX_MODEL_GRID}-HiRes.fits"
    )
    spectrum_url = (
        f"{PHOENIX_BASE_URL}/{PHOENIX_MODEL_GRID}/"
        f"{z_folder}/{spectrum_name}"
    )
    spectrum_file = paths["download_dir"] / spectrum_name

    print("\nPHOENIX model")
    print(f"  label : {args.label}")
    print(f"  TEFF  : {args.teff}")
    print(f"  LOGG  : {args.logg}")
    print(f"  [Fe/H]: {feh_value}")
    print(f"  URL   : {spectrum_url}")
    print(f"  normalize products: {args.normalize}")

    download_if_needed(wave_url, wave_file)
    download_if_needed(spectrum_url, spectrum_file)

    wave_angstrom = fits.getdata(wave_file)
    flux = fits.getdata(spectrum_file)
    wave_micron = wave_angstrom * 1e-4

    cut = (wave_micron >= args.wmin) & (wave_micron <= args.wmax)
    wave_cut = np.asarray(wave_micron[cut], dtype=float)
    flux_cut = np.asarray(flux[cut], dtype=float)

    good = np.isfinite(wave_cut) & np.isfinite(flux_cut)
    wave_cut = wave_cut[good]
    flux_cut = flux_cut[good]

    if len(wave_cut) == 0:
        raise RuntimeError("No valid PHOENIX points found in the selected wavelength range.")

    print("\nFull-resolution cut")
    print(f"  wavelength min [micron]: {np.nanmin(wave_cut):.6f}")
    print(f"  wavelength max [micron]: {np.nanmax(wave_cut):.6f}")
    print(f"  points: {len(wave_cut)}")

    wave_resampled = np.linspace(np.nanmin(wave_cut), np.nanmax(wave_cut), args.n_resampled)
    flux_resampled = np.interp(wave_resampled, wave_cut, flux_cut)

    print("\nResampled spectrum")
    print(f"  wavelength min [micron]: {np.nanmin(wave_resampled):.6f}")
    print(f"  wavelength max [micron]: {np.nanmax(wave_resampled):.6f}")
    print(f"  points: {len(wave_resampled)}")

    continuum_full = None
    flux_norm_full = None
    continuum_resampled = None
    flux_norm_resampled = None

    if args.normalize:
        print("\nComputing optional continuum-normalized products")
        continuum_full = running_percentile(
            flux_cut,
            window=args.continuum_window_fullres,
            percentile=args.continuum_percentile,
        )
        flux_norm_full = flux_cut / continuum_full

        continuum_resampled = running_percentile(
            flux_resampled,
            window=args.continuum_window_resampled,
            percentile=args.continuum_percentile,
        )
        flux_norm_resampled = flux_resampled / continuum_resampled

    metadata = {
        "model_label": label,
        "label": args.label,
        "teff": args.teff,
        "logg": args.logg,
        "feh": feh_value,
        "wmin_micron": args.wmin,
        "wmax_micron": args.wmax,
        "n_resampled": args.n_resampled,
        "normalized_products": args.normalize,
        "continuum_percentile": args.continuum_percentile if args.normalize else None,
        "continuum_window_fullres": args.continuum_window_fullres if args.normalize else None,
        "continuum_window_resampled": args.continuum_window_resampled if args.normalize else None,
        "phoenix_base_url": PHOENIX_BASE_URL,
        "phoenix_model_grid": PHOENIX_MODEL_GRID,
        "wave_file": str(wave_file),
        "spectrum_file": str(spectrum_file),
        "comment": "PHOENIX spectrum prepared for synthetic telluric dataset generation.",
    }

    fullres_fits = paths["raw_dir"] / f"phoenix_{label}_fullres.fits"
    resampled_fits = paths["resampled_dir"] / f"phoenix_{label}_{args.n_resampled}pts.fits"
    metadata_file = paths["metadata_dir"] / f"phoenix_{label}.json"

    save_spectrum_fits(
        fullres_fits,
        wave_cut,
        flux_cut,
        metadata,
        overwrite=args.overwrite,
        continuum=continuum_full,
        flux_norm=flux_norm_full,
    )
    save_spectrum_fits(
        resampled_fits,
        wave_resampled,
        flux_resampled,
        metadata,
        overwrite=args.overwrite,
        continuum=continuum_resampled,
        flux_norm=flux_norm_resampled,
    )
    save_metadata(metadata_file, metadata, overwrite=args.overwrite)

    if not args.no_plots:
        plot_spectrum(
            paths["plot_dir"] / f"phoenix_{label}_fullres_raw.png",
            wave_cut,
            flux_cut,
            f"PHOENIX {label} full-resolution raw flux",
            "PHOENIX flux",
            overwrite=args.overwrite,
        )
        plot_spectrum(
            paths["plot_dir"] / f"phoenix_{label}_{args.n_resampled}pts_raw.png",
            wave_resampled,
            flux_resampled,
            f"PHOENIX {label} resampled raw flux",
            "PHOENIX flux",
            overwrite=args.overwrite,
        )

        if args.normalize and flux_norm_resampled is not None:
            plot_spectrum(
                paths["plot_dir"] / f"phoenix_{label}_{args.n_resampled}pts_norm.png",
                wave_resampled,
                flux_norm_resampled,
                f"PHOENIX {label} resampled continuum-normalized flux",
                "Continuum-normalized flux",
                overwrite=args.overwrite,
            )

    print("\nSaved products")
    print(f"  full-resolution FITS: {fullres_fits}")
    print(f"  resampled FITS      : {resampled_fits}")
    print(f"  metadata            : {metadata_file}")
    if not args.no_plots:
        print(f"  plots               : {paths['plot_dir']}")


if __name__ == "__main__":
    main()

