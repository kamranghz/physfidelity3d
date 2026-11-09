"""Benchmark constants shared by every module."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RECORDS_DIR = REPO_ROOT / "data" / "records"
RECORDED_DIR = REPO_ROOT / "data" / "recorded"
CHECKSUMS_FILE = REPO_ROOT / "data" / "checksums.sha256"

# Methods in the order used by every table and figure.
METHODS = ["dust3r", "mast3r", "vggt", "vggt_omega", "vgg_t3"]
METHOD_LABELS = {
    "dust3r": "DUSt3R",
    "mast3r": "MASt3R",
    "vggt": "VGGT",
    "vggt_omega": "VGGT-Ω",
    "vgg_t3": "VGG-T³",
}

DATASETS = ["ycbv", "tless", "picasso"]
DATASET_LABELS = {"ycbv": "YCB-V", "tless": "T-LESS", "picasso": "Picasso"}
SCENES_PER_DATASET = {"ycbv": 12, "tless": 20, "picasso": 10}

NPS_CAP_MM = 10.0

# Scene bootstrap settings (Section 3.3 of the paper).
N_BOOT = 10_000
SEED = 2026
