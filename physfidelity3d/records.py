"""Load the 210 released evaluation records.

Layout: ``data/records/<dataset>/<scene_id>/<method>/{nps,sps,mesh_stats}.json``.
"""

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .config import CHECKSUMS_FILE, DATASETS, METHODS, RECORDS_DIR, REPO_ROOT


@dataclass(frozen=True)
class Records:
    scenes: pd.DataFrame  # one row per method-scene evaluation
    pairs: pd.DataFrame  # one row per object-object penetration term
    planes: pd.DataFrame  # one row per object-plane penetration term


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_records(root: Path = RECORDS_DIR) -> Records:
    scenes, pairs, planes = [], [], []
    for dataset in DATASETS:
        for scene_dir in sorted((root / dataset).iterdir()):
            for method in METHODS:
                folder = scene_dir / method
                nps, sps = _read(folder / "nps.json"), _read(folder / "sps.json")
                meshes = _read(folder / "mesh_stats.json")
                key = {"dataset": dataset, "scene_id": scene_dir.name, "method": method}

                objects = [str(o) for o in nps["object_order"]]
                n = len(objects)
                scene_pairs = []
                for i in range(n):
                    for j in range(i + 1, n):
                        scene_pairs.append(
                            {
                                **key,
                                "object_i": objects[i],
                                "object_j": objects[j],
                                "pen_mm": nps["pen_matrix_mm"][i][j],
                                "pen_raw_mm": nps["pen_matrix_raw_mm"][i][j],
                                "cap_hit": bool(nps["cap_hit_matrix"][i][j]),
                            }
                        )
                pairs += scene_pairs
                for obj, raw in nps["per_object_env_pen_raw_mm"].items():
                    planes.append({**key, "object": obj, "pen_raw_mm": raw})

                scenes.append(
                    {
                        **key,
                        "n_objects": nps["n_objects"],
                        "nps": nps["nps_scene_mm"],
                        "sps": sps["sps_scene"],
                        "cap_hits": sum(p["cap_hit"] for p in scene_pairs),
                        "n_pairs": len(scene_pairs),
                        "watertight_meshes": sum(m["watertight"] for m in meshes.values()),
                    }
                )
    return Records(pd.DataFrame(scenes), pd.DataFrame(pairs), pd.DataFrame(planes))


def verify_checksums(checksums_file: Path = CHECKSUMS_FILE) -> list[str]:
    """Return the paths whose SHA-256 differs from the published checksum list."""
    mismatched = []
    for line in checksums_file.read_text(encoding="utf-8").splitlines():
        digest, rel_path = line.split(maxsplit=1)
        if hashlib.sha256((REPO_ROOT / rel_path).read_bytes()).hexdigest() != digest:
            mismatched.append(rel_path)
    return mismatched
