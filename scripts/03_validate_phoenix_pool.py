#!/usr/bin/env python3
"""
Validate a PHOENIX stellar pool generated from a CSV configuration.

Checks:
- Expected FITS and metadata files exist.
- FITS contains WAVE_MICRON and FLUX columns.
- Wavelength and flux arrays have the expected length.
- Wavelength grid is finite, increasing, and matches requested range.
- Flux is finite and not identically zero.
- Metadata broadly matches the CSV configuration.
- Writes a validation summary CSV.

Default config:
  configs/phoenix_initial_pool.csv

Default data root:
  ~/TFM_DATA
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from astropy.io import fits


def resolve_repo_root() -> Path:
    """Return repository root assuming this script lives in repo/scripts."""
    return Path(__file__).resolve().parents[1]


def normalize_bool(value: Any) -> bool:
    """Convert common string/bool representations to bool."""
    if isinstance(value, bool):
        return value

    value_str = str(value).strip().lower()
    return value_str in {"true", "1", "yes", "y"}


def get_metadata_value(metadata: dict[str, Any], possible_keys: list[str]) -> Any:
    """
    Retrieve a metadata value using a list of possible key names.

    This makes the validator robust against small metadata naming differences.
    """
    for key in possible_keys:
        if key in metadata:
            return metadata[key]

    lower_map = {str(k).lower(): v for k, v in metadata.items()}
    for key in possible_keys:
        if key.lower() in lower_map:
            return lower_map[key.lower()]

    return None


def find_single_file(directory: Path, label: str, suffix: str) -> Path | None:
    """
    Find one file containing the model label.

    This avoids depending too strongly on the exact filename convention.
    """
    if not directory.exists():
        return None

    candidates = sorted(directory.glob(f"*{label}*{suffix}"))

    if len(candidates) == 1:
        return candidates[0]

    if len(candidates) > 1:
        # Prefer files that look resampled / metadata-like if several exist.
        preferred = [
            path for path in candidates
            if "resampled" in path.name.lower() or "metadata" in path.name.lower()
        ]
        if len(preferred) == 1:
            return preferred[0]

        # Fall back to first sorted candidate, but this will be reported.
        return candidates[0]

    return None


def read_fits_table(fits_path: Path):
    """
    Return the first FITS table HDU containing named columns.
    """
    with fits.open(fits_path) as hdul:
        for hdu in hdul:
            data = getattr(hdu, "data", None)
            names = getattr(data, "names", None)
            if data is not None and names is not None:
                return data

    raise ValueError("No table HDU with named columns found.")


def add_check(errors: list[str], condition: bool, message: str) -> None:
    """Append message to errors if condition is False."""
    if not condition:
        errors.append(message)


def validate_model(row: dict[str, str], data_root: Path) -> dict[str, Any]:
    label = row["label"].strip()

    expected_teff = float(row["teff"])
    expected_logg = float(row["logg"])
    expected_feh = float(row["feh"])
    expected_wmin = float(row["wmin"])
    expected_wmax = float(row["wmax"])
    expected_n = int(row["n_resampled"])
    expected_normalize = normalize_bool(row.get("normalize", "false"))

    resampled_dir = data_root / "phoenix" / "resampled"
    metadata_dir = data_root / "phoenix" / "metadata"

    fits_path = find_single_file(resampled_dir, label, ".fits")
    metadata_path = find_single_file(metadata_dir, label, ".json")

    errors: list[str] = []

    result: dict[str, Any] = {
        "label": label,
        "expected_teff": expected_teff,
        "expected_logg": expected_logg,
        "expected_feh": expected_feh,
        "expected_wmin": expected_wmin,
        "expected_wmax": expected_wmax,
        "expected_n": expected_n,
        "expected_normalize": expected_normalize,
        "fits_path": str(fits_path) if fits_path else "",
        "metadata_path": str(metadata_path) if metadata_path else "",
        "n_points": np.nan,
        "wave_min": np.nan,
        "wave_max": np.nan,
        "flux_min": np.nan,
        "flux_max": np.nan,
        "flux_median": np.nan,
        "nan_wave": np.nan,
        "nan_flux": np.nan,
        "status": "FAIL",
        "errors": "",
    }

    if fits_path is None:
        errors.append(f"Missing FITS file for label {label} in {resampled_dir}.")
    else:
        try:
            table = read_fits_table(fits_path)
            columns = list(table.names)

            add_check(errors, "WAVE_MICRON" in columns, "Missing FITS column WAVE_MICRON.")
            add_check(errors, "FLUX" in columns, "Missing FITS column FLUX.")

            if "WAVE_MICRON" in columns and "FLUX" in columns:
                wave = np.asarray(table["WAVE_MICRON"], dtype=float)
                flux = np.asarray(table["FLUX"], dtype=float)

                result["n_points"] = len(wave)
                result["wave_min"] = float(np.nanmin(wave))
                result["wave_max"] = float(np.nanmax(wave))
                result["flux_min"] = float(np.nanmin(flux))
                result["flux_max"] = float(np.nanmax(flux))
                result["flux_median"] = float(np.nanmedian(flux))
                result["nan_wave"] = int(np.isnan(wave).sum())
                result["nan_flux"] = int(np.isnan(flux).sum())

                add_check(errors, len(wave) == expected_n, f"Expected {expected_n} wavelength points, got {len(wave)}.")
                add_check(errors, len(flux) == expected_n, f"Expected {expected_n} flux points, got {len(flux)}.")

                add_check(errors, np.all(np.isfinite(wave)), "Wavelength array contains NaN or inf.")
                add_check(errors, np.all(np.isfinite(flux)), "Flux array contains NaN or inf.")

                add_check(errors, np.all(np.diff(wave) > 0), "Wavelength grid is not strictly increasing.")
                add_check(errors, not np.allclose(flux, 0.0), "Flux array appears to be all zero.")

                # Tolerance: allow tiny interpolation/grid edge differences.
                add_check(
                    errors,
                    np.isclose(np.nanmin(wave), expected_wmin, rtol=0.0, atol=5e-4),
                    f"wave_min mismatch: expected ~{expected_wmin}, got {np.nanmin(wave)}.",
                )
                add_check(
                    errors,
                    np.isclose(np.nanmax(wave), expected_wmax, rtol=0.0, atol=5e-4),
                    f"wave_max mismatch: expected ~{expected_wmax}, got {np.nanmax(wave)}.",
                )

        except Exception as exc:
            errors.append(f"Could not read/validate FITS: {exc}")

    if metadata_path is None:
        errors.append(f"Missing metadata JSON for label {label} in {metadata_dir}.")
    else:
        try:
            with metadata_path.open("r", encoding="utf-8") as f:
                metadata = json.load(f)

            meta_label = get_metadata_value(metadata, ["label", "LABEL"])
            meta_teff = get_metadata_value(metadata, ["teff", "TEFF", "T_EFF"])
            meta_logg = get_metadata_value(metadata, ["logg", "LOGG"])
            meta_feh = get_metadata_value(metadata, ["feh", "FEH", "metallicity", "METALLICITY"])
            meta_wmin = get_metadata_value(metadata, ["wmin", "WMIN", "wavelength_min", "WAVELENGTH_MIN"])
            meta_wmax = get_metadata_value(metadata, ["wmax", "WMAX", "wavelength_max", "WAVELENGTH_MAX"])
            meta_n = get_metadata_value(metadata, ["n_resampled", "N_RESAMPLED", "n_points", "N_POINTS"])
            meta_normalize = get_metadata_value(metadata, ["normalize", "NORMALIZE", "normalized", "NORMALIZED"])

            if meta_label is not None:
                add_check(errors, str(meta_label) == label, f"Metadata label mismatch: expected {label}, got {meta_label}.")

            if meta_teff is not None:
                add_check(errors, np.isclose(float(meta_teff), expected_teff), f"Metadata teff mismatch: expected {expected_teff}, got {meta_teff}.")

            if meta_logg is not None:
                add_check(errors, np.isclose(float(meta_logg), expected_logg), f"Metadata logg mismatch: expected {expected_logg}, got {meta_logg}.")

            if meta_feh is not None:
                add_check(errors, np.isclose(float(meta_feh), expected_feh), f"Metadata feh mismatch: expected {expected_feh}, got {meta_feh}.")

            if meta_wmin is not None:
                add_check(errors, np.isclose(float(meta_wmin), expected_wmin, atol=5e-4), f"Metadata wmin mismatch: expected {expected_wmin}, got {meta_wmin}.")

            if meta_wmax is not None:
                add_check(errors, np.isclose(float(meta_wmax), expected_wmax, atol=5e-4), f"Metadata wmax mismatch: expected {expected_wmax}, got {meta_wmax}.")

            if meta_n is not None:
                add_check(errors, int(meta_n) == expected_n, f"Metadata n_resampled mismatch: expected {expected_n}, got {meta_n}.")

            if meta_normalize is not None:
                add_check(
                    errors,
                    normalize_bool(meta_normalize) == expected_normalize,
                    f"Metadata normalize mismatch: expected {expected_normalize}, got {meta_normalize}.",
                )

        except Exception as exc:
            errors.append(f"Could not read/validate metadata JSON: {exc}")

    if errors:
        result["status"] = "FAIL"
        result["errors"] = " | ".join(errors)
    else:
        result["status"] = "OK"
        result["errors"] = ""

    return result


def main() -> int:
    repo_root = resolve_repo_root()

    parser = argparse.ArgumentParser(
        description="Validate a PHOENIX pool generated from a CSV configuration."
    )
    parser.add_argument(
        "config",
        nargs="?",
        default=str(repo_root / "configs" / "phoenix_initial_pool.csv"),
        help="Path to PHOENIX pool CSV config. Relative paths are interpreted from repo root.",
    )
    parser.add_argument(
        "--data-root",
        default=str(Path.home() / "TFM_DATA"),
        help="Root directory containing PHOENIX outputs. Default: ~/TFM_DATA",
    )
    parser.add_argument(
        "--summary-out",
        default=None,
        help="Output CSV summary path. Default: ~/TFM_DATA/phoenix/metadata/phoenix_initial_pool_validation_summary.csv",
    )

    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = repo_root / config_path

    data_root = Path(args.data_root).expanduser().resolve()

    if args.summary_out is None:
        summary_out = data_root / "phoenix" / "metadata" / "phoenix_initial_pool_validation_summary.csv"
    else:
        summary_out = Path(args.summary_out).expanduser()
        if not summary_out.is_absolute():
            summary_out = repo_root / summary_out

    if not config_path.exists():
        print(f"ERROR: Config file not found: {config_path}")
        return 1

    print("Repository root:")
    print(f"  {repo_root}")
    print()
    print("Using PHOENIX config:")
    print(f"  {config_path}")
    print()
    print("Using data root:")
    print(f"  {data_root}")
    print()

    with config_path.open("r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        print("ERROR: Config file contains no data rows.")
        return 1

    results = []

    for i, row in enumerate(rows, start=1):
        label = row["label"].strip()
        print(f"[{i}/{len(rows)}] Validating {label}...")

        result = validate_model(row, data_root)
        results.append(result)

        if result["status"] == "OK":
            print(f"  [OK] {label}")
        else:
            print(f"  [FAIL] {label}")
            for error in result["errors"].split(" | "):
                print(f"    - {error}")

    df = pd.DataFrame(results)

    summary_out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(summary_out, index=False)

    print()
    print("Validation summary written to:")
    print(f"  {summary_out}")
    print()

    n_ok = int((df["status"] == "OK").sum())
    n_fail = int((df["status"] == "FAIL").sum())

    print("Summary:")
    print(f"  OK:   {n_ok}")
    print(f"  FAIL: {n_fail}")
    print(f"  TOTAL:{len(df)}")

    if n_fail > 0:
        print()
        print("Some checks failed.")
        return 1

    print()
    print("All PHOENIX pool checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
