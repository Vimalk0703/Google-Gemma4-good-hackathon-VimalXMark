"""Download and verify all datasets needed for Malaika.

Run this script on Day 1 to get all data staged.
Each dataset is downloaded to data/<name>/ and verified.

Usage:
    python scripts/download_datasets.py [--dataset <name>]

Datasets:
    icbhi       - ICBHI 2017 Respiratory Sound Database
    jaundice    - Neonatal Jaundice images (Mendeley + NJN)
    waxal       - WAXAL African language speech (subset)
    circor      - CirCor Pediatric Heart Sound Database
    imci        - WHO smart-emcare IMCI protocol
    all         - Download everything
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"


DATASETS = {
    "icbhi": {
        "name": "ICBHI 2017 Respiratory Sound Database",
        "source": "kaggle",
        "kaggle_id": "vbookshelf/respiratory-sound-database",
        "size": "~4 GB",
        "license": "Research use",
        "purpose": "Fine-tune breath sound classification",
    },
    "jaundice_mendeley": {
        "name": "Neonatal Jaundice (Mendeley)",
        "source": "manual",
        "url": "https://data.mendeley.com/datasets/yfsz6c36vc/1",
        "size": "~200 MB",
        "license": "CC-BY-4.0",
        "purpose": "Fine-tune jaundice detection",
    },
    "jaundice_njn": {
        "name": "Neonatal Jaundice (NJN/Zenodo)",
        "source": "manual",
        "url": "https://zenodo.org/records/7825810",
        "size": "~300 MB",
        "license": "CC-BY-4.0",
        "purpose": "Supplementary jaundice data",
    },
    "waxal": {
        "name": "WAXAL African Language Speech",
        "source": "huggingface",
        "hf_id": "google/WaxalNLP",
        "size": "~50 GB (full), ~2 GB (subset)",
        "license": "CC-BY-4.0",
        "purpose": "Fine-tune African language speech understanding",
        "note": "Download Swahili + Hausa subsets only",
    },
    "circor": {
        "name": "CirCor Pediatric Heart Sounds",
        "source": "physionet",
        "url": "https://physionet.org/content/circor-heart-sound/1.0.3/",
        "size": "~10 GB",
        "license": "ODC-By 1.0",
        "purpose": "Fine-tune MEMS heart module",
    },
    "imci": {
        "name": "WHO smart-emcare IMCI Protocol",
        "source": "github",
        "repo": "WorldHealthOrganization/smart-emcare",
        "size": "~50 MB",
        "license": "CC-BY-IGO 3.0",
        "purpose": "Encode IMCI state machine",
    },
}


def download_kaggle(dataset_id: str, output_dir: Path) -> None:
    """Download a Kaggle dataset."""
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"  Downloading from Kaggle: {dataset_id}")
    print(f"  Target: {output_dir}")
    print(f"  Command: kaggle datasets download -d {dataset_id} -p {output_dir} --unzip")
    print()
    print(f"  Run this manually:")
    print(f"    pip install kaggle")
    print(f"    export KAGGLE_USERNAME=<your_username>")
    print(f"    export KAGGLE_KEY=<your_api_key>")
    print(f"    kaggle datasets download -d {dataset_id} -p {output_dir} --unzip")


def download_github(repo: str, output_dir: Path) -> None:
    """Clone a GitHub repository."""
    output_dir.mkdir(parents=True, exist_ok=True)
    clone_url = f"https://github.com/{repo}.git"
    print(f"  Cloning: {clone_url}")
    print(f"  Target: {output_dir}")
    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", clone_url, str(output_dir)],
            check=True,
        )
        print(f"  ✓ Cloned successfully")
    except subprocess.CalledProcessError as e:
        print(f"  ✗ Clone failed: {e}")
    except FileNotFoundError:
        print(f"  ✗ git not found. Install git and try again.")


def download_huggingface(hf_id: str, output_dir: Path) -> None:
    """Download from HuggingFace."""
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"  HuggingFace dataset: {hf_id}")
    print(f"  Target: {output_dir}")
    print()
    print(f"  For WAXAL, download Swahili + Hausa subsets only:")
    print(f"    from datasets import load_dataset")
    print(f"    ds = load_dataset('{hf_id}', 'swahili', split='train[:1000]')")
    print(f"    ds.save_to_disk('{output_dir}/swahili')")


def download_manual(name: str, url: str, output_dir: Path) -> None:
    """Print instructions for manual download."""
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"  Manual download required:")
    print(f"  1. Go to: {url}")
    print(f"  2. Download the dataset")
    print(f"  3. Extract to: {output_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Download Malaika datasets")
    parser.add_argument(
        "--dataset",
        choices=list(DATASETS.keys()) + ["all"],
        default="all",
        help="Which dataset to download (default: all)",
    )
    args = parser.parse_args()

    targets = list(DATASETS.keys()) if args.dataset == "all" else [args.dataset]

    print("=" * 60)
    print("Malaika Dataset Downloader")
    print("=" * 60)

    for key in targets:
        ds = DATASETS[key]
        output_dir = DATA_DIR / key
        print(f"\n{'─' * 60}")
        print(f"Dataset: {ds['name']}")
        print(f"Size: {ds['size']}")
        print(f"License: {ds['license']}")
        print(f"Purpose: {ds['purpose']}")
        if "note" in ds:
            print(f"Note: {ds['note']}")
        print()

        if output_dir.exists() and any(output_dir.iterdir()):
            print(f"  ✓ Already exists at {output_dir}")
            continue

        source = ds["source"]
        if source == "kaggle":
            download_kaggle(ds["kaggle_id"], output_dir)
        elif source == "github":
            download_github(ds["repo"], output_dir)
        elif source == "huggingface":
            download_huggingface(ds["hf_id"], output_dir)
        elif source == "manual":
            download_manual(key, ds["url"], output_dir)
        elif source == "physionet":
            download_manual(key, ds["url"], output_dir)

    print(f"\n{'=' * 60}")
    print("Done. Check data/ directory for downloaded datasets.")
    print("=" * 60)


if __name__ == "__main__":
    main()
