#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Batch process multiple well LAS files and generate reports.

This script processes multiple LAS files in a directory and generates
summary statistics, individual plots, and a consolidated report.

Usage:
    python batch_process.py [INPUT_DIR] [OUTPUT_DIR] [PATTERN]

Examples:
    python batch_process.py ./data ./results "well_*.las"
    python batch_process.py /data/wells /results/analysis "*.las"
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Dict, List

import pandas as pd

from well_analysis import process_well

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def find_las_files(input_dir: str, pattern: str = "*.las") -> List[Path]:
    """
    Find all LAS files matching pattern in input directory.

    Args:
        input_dir: Directory to search
        pattern: Glob pattern for matching files (default: "*.las")

    Returns:
        List of Path objects for matching LAS files

    Raises:
        FileNotFoundError: If input directory does not exist
    """
    input_path = Path(input_dir)

    if not input_path.exists():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")

    if not input_path.is_dir():
        raise ValueError(f"Not a directory: {input_dir}")

    las_files = sorted(input_path.glob(pattern))

    if not las_files:
        logger.warning(f"No files matching pattern '{pattern}' in {input_dir}")
        return []

    logger.info(f"Found {len(las_files)} LAS files matching pattern '{pattern}'")
    return las_files


def process_well_batch(
    input_dir: str,
    output_dir: str,
    pattern: str = "*.las",
) -> Dict[str, Dict]:
    """
    Process multiple well LAS files in batch mode.

    Args:
        input_dir: Directory containing LAS files
        output_dir: Directory for output files
        pattern: Glob pattern for LAS files (default: "*.las")

    Returns:
        Dictionary with well_id: {results_dict} for each processed well

    Raises:
        FileNotFoundError: If input directory not found
        ValueError: If no LAS files found
    """
    las_files = find_las_files(input_dir, pattern)

    if not las_files:
        raise ValueError(f"No LAS files found matching '{pattern}' in '{input_dir}'")

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    results = {}
    failures = []

    logger.info(f"Processing {len(las_files)} wells...")
    logger.info(f"Output directory: {output_path}")

    for i, las_file in enumerate(las_files, 1):
        well_id = las_file.stem  # Filename without extension

        logger.info(f"\n[{i}/{len(las_files)}] Processing: {las_file.name}")

        try:
            df = process_well(str(las_file), str(output_path), well_number=well_id)

            # Extract statistics
            vsh = df["Vsh"].values
            kn = df["Kn"].values
            kpr = df["Kпр"].values

            results[well_id] = {
                "status": "success",
                "file": las_file.name,
                "depth_range": f"{df['DEPT'].min():.1f} - {df['DEPT'].max():.1f} m",
                "measurements": len(df),
                "vsh_min": float(vsh.min()),
                "vsh_max": float(vsh.max()),
                "vsh_mean": float(vsh.mean()),
                "kn_min": float(kn.min()),
                "kn_max": float(kn.max()),
                "kn_mean": float(kn.mean()),
                "kpr_min": float(kpr[kpr > 0].min() if (kpr > 0).any() else 0.0),
                "kpr_max": float(kpr.max()),
                "kpr_mean": float(kpr[kpr > 0].mean() if (kpr > 0).any() else 0.0),
            }

            logger.info(f"  ✓ Success: {well_id}")

        except Exception as e:
            logger.error(f"  ✗ Failed: {well_id} - {e}")
            failures.append((well_id, str(e)))
            results[well_id] = {
                "status": "failed",
                "file": las_file.name,
                "error": str(e),
            }

    return results


def generate_summary_report(
    results: Dict[str, Dict],
    output_dir: str,
) -> None:
    """
    Generate summary report from batch processing results.

    Args:
        results: Results dictionary from process_well_batch
        output_dir: Directory to save report
    """
    output_path = Path(output_dir)
    report_path = output_path / "batch_summary.csv"

    # Convert results to DataFrame
    rows = []
    for well_id, data in results.items():
        row = {"well_id": well_id}
        row.update(data)
        rows.append(row)

    df_summary = pd.DataFrame(rows)

    # Save to CSV
    df_summary.to_csv(report_path, index=False)
    logger.info(f"Summary report saved: {report_path}")

    # Print summary
    logger.info("\n" + "=" * 70)
    logger.info("BATCH PROCESSING SUMMARY")
    logger.info("=" * 70)

    successful = (df_summary["status"] == "success").sum()
    failed = (df_summary["status"] == "failed").sum()

    logger.info(f"Total wells processed: {len(df_summary)}")
    logger.info(f"Successful: {successful}")
    logger.info(f"Failed: {failed}")

    if successful > 0:
        df_success = df_summary[df_summary["status"] == "success"]

        logger.info("\nStatistics (successful wells):")
        logger.info(f"  Shale Volume (Vsh):")
        logger.info(
            f"    Mean: {df_success['vsh_mean'].mean():.2%} "
            f"(range: {df_success['vsh_min'].min():.2%} - {df_success['vsh_max'].max():.2%})"
        )
        logger.info(f"  Porosity (Kn):")
        logger.info(
            f"    Mean: {df_success['kn_mean'].mean():.2%} "
            f"(range: {df_success['kn_min'].min():.2%} - {df_success['kn_max'].max():.2%})"
        )
        logger.info(f"  Permeability (Kпр):")
        logger.info(
            f"    Mean: {df_success['kpr_mean'].mean():.2f} mD "
            f"(range: {df_success['kpr_min'].min():.2f} - {df_success['kpr_max'].max():.2f} mD)"
        )

    logger.info("=" * 70 + "\n")


def main() -> int:
    """
    Command-line entry point for batch processing.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    parser = argparse.ArgumentParser(
        description="Batch process multiple well LAS files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python batch_process.py ./data ./results
  python batch_process.py /wells /analysis "well_*.las"
  python batch_process.py . . "*.las"
        """,
    )

    parser.add_argument(
        "input_dir",
        help="Directory containing LAS files",
    )
    parser.add_argument(
        "output_dir",
        help="Directory for output files",
    )
    parser.add_argument(
        "-p",
        "--pattern",
        default="*.las",
        help="Glob pattern for LAS files (default: *.las)",
    )

    args = parser.parse_args()

    logger.info("Batch Petrophysical Well Analysis")
    logger.info(f"Python {sys.version}")

    try:
        results = process_well_batch(
            input_dir=args.input_dir,
            output_dir=args.output_dir,
            pattern=args.pattern,
        )

        generate_summary_report(results, args.output_dir)

        # Check for failures
        failures = sum(1 for r in results.values() if r["status"] == "failed")
        if failures > 0:
            logger.warning(f"⚠ {failures} wells failed processing")
            return 1
        else:
            logger.info("✓ All wells processed successfully")
            return 0

    except (FileNotFoundError, ValueError) as e:
        logger.error(f"✗ Error: {e}")
        return 1
    except Exception as e:
        logger.error(f"✗ Unexpected error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
