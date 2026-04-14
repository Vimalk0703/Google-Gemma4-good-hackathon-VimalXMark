"""Push and run a notebook on Kaggle GPU from the command line.

Uses the Kaggle API to create/update a kernel and trigger execution.
Results can be checked with `kaggle kernels status`.

Prerequisites:
    1. pip install kaggle
    2. Place API token at ~/.kaggle/kaggle.json
       (Get it from: kaggle.com → Settings → API → Create New Token)
    3. chmod 600 ~/.kaggle/kaggle.json

Usage:
    python scripts/run_on_kaggle.py --notebook notebooks/03_end_to_end_test.py
    python scripts/run_on_kaggle.py --status
    python scripts/run_on_kaggle.py --output
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

# Your Kaggle username — update this
KAGGLE_USERNAME = "vimalkumar0307"

PROJECT_ROOT = Path(__file__).parent.parent
KERNEL_SLUG = "malaika-e2e-test"


def push_notebook(notebook_path: Path) -> None:
    """Push a notebook to Kaggle and trigger execution with GPU."""

    # Read the notebook/script content
    content = notebook_path.read_text()

    # Create kernel metadata
    metadata = {
        "id": f"{KAGGLE_USERNAME}/{KERNEL_SLUG}",
        "title": "Malaika End-to-End Test",
        "code_file": notebook_path.name,
        "language": "python",
        "kernel_type": "script",
        "is_private": True,
        "enable_gpu": True,
        "enable_internet": True,
        "dataset_sources": [],
        "competition_sources": [],
        "kernel_sources": [],
    }

    # Create temp directory with kernel files
    kernel_dir = PROJECT_ROOT / ".kaggle_kernel"
    kernel_dir.mkdir(exist_ok=True)

    # Write metadata
    (kernel_dir / "kernel-metadata.json").write_text(json.dumps(metadata, indent=2))

    # Copy script
    (kernel_dir / notebook_path.name).write_text(content)

    print(f"Pushing kernel to Kaggle...")
    print(f"  Notebook: {notebook_path.name}")
    print(f"  Kernel: {KAGGLE_USERNAME}/{KERNEL_SLUG}")
    print(f"  GPU: enabled")
    print(f"  Internet: enabled")
    print()

    result = subprocess.run(
        ["kaggle", "kernels", "push", "-p", str(kernel_dir)],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        print(f"Pushed successfully!")
        print(result.stdout)
        print(f"\nCheck status: python scripts/run_on_kaggle.py --status")
        print(f"View output:  python scripts/run_on_kaggle.py --output")
        print(f"Or visit:     https://www.kaggle.com/code/{KAGGLE_USERNAME}/{KERNEL_SLUG}")
    else:
        print(f"Push failed:")
        print(result.stderr)


def check_status() -> None:
    """Check the status of the running kernel."""
    result = subprocess.run(
        ["kaggle", "kernels", "status", f"{KAGGLE_USERNAME}/{KERNEL_SLUG}"],
        capture_output=True,
        text=True,
    )
    print(result.stdout or result.stderr)


def get_output() -> None:
    """Download and display the kernel output."""
    output_dir = PROJECT_ROOT / ".kaggle_output"
    output_dir.mkdir(exist_ok=True)

    result = subprocess.run(
        ["kaggle", "kernels", "output", f"{KAGGLE_USERNAME}/{KERNEL_SLUG}",
         "-p", str(output_dir)],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        print(f"Output downloaded to {output_dir}")
        # Try to read the log
        log_file = output_dir / f"{KERNEL_SLUG}.log"
        if log_file.exists():
            print("\n" + "=" * 60)
            print("KERNEL OUTPUT")
            print("=" * 60)
            print(log_file.read_text())
    else:
        print(result.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Malaika notebooks on Kaggle GPU")
    parser.add_argument("--notebook", type=Path, help="Path to notebook to push and run")
    parser.add_argument("--status", action="store_true", help="Check kernel status")
    parser.add_argument("--output", action="store_true", help="Download kernel output")
    args = parser.parse_args()

    if args.status:
        check_status()
    elif args.output:
        get_output()
    elif args.notebook:
        if not args.notebook.exists():
            print(f"File not found: {args.notebook}")
            sys.exit(1)
        push_notebook(args.notebook)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
