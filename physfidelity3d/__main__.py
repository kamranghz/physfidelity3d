"""Command line entry point.

python -m physfidelity3d validate             check the released records
python -m physfidelity3d reproduce [--out D]  write every table and figure to D
"""

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from . import figures, tables
from .config import DATASETS, METHODS, SCENES_PER_DATASET
from .records import load_records, verify_checksums


def validate() -> bool:
    rec = load_records()
    per_dataset = rec.scenes.groupby("dataset").size().to_dict()
    checks = {
        "checksums match data/checksums.sha256": not verify_checksums(),
        "210 evaluations (5 methods x 42 scenes)": per_dataset
        == {d: n * len(METHODS) for d, n in SCENES_PER_DATASET.items()},
        "1,955 object-pair penetration terms": len(rec.pairs) == 1955,
        "NPS and SPS are finite": bool(np.isfinite(rec.scenes[["nps", "sps"]]).all().all()),
        "min(raw, 10 mm) equals every stored capped term": tables.cap_parity(rec) == 0.0,
    }
    for name, ok in checks.items():
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    return all(checks.values())


def reproduce(out: Path) -> None:
    rec = load_records()
    (out / "tables").mkdir(parents=True, exist_ok=True)
    (out / "figures").mkdir(parents=True, exist_ok=True)

    print("Computing bootstrap statistics (10,000 replicates)...")
    t = {
        "table2_pooled": tables.table2_pooled(rec),
        "table3_geometry": tables.table3_geometry(rec),
        "table4_gt_aligned": tables.table4_gt_aligned(),
        "table5_vggt_family": tables.table5_vggt_family(),
        "table6_coverage": tables.table6_coverage(rec),
        "table7_collision_geometry": tables.table7_collision_geometry(rec),
        "table8_failure_cases": tables.table8_failure_cases(rec),
        "geometry_correlations": tables.geometry_correlations(),
        "nps_sps_correlation": tables.nps_sps_correlation(rec),
        "nps_saturation": tables.nps_saturation(rec),
        "rank_probabilities": tables.rank_probabilities(rec),
        "paired_vs_dust3r": tables.paired_vs_dust3r(rec),
        "dataset_means": tables.dataset_means(rec),
        "cap_hit_by_dataset_method": tables.cap_hit_by_dataset_method(rec),
        "scale_perturbation": tables.scale_perturbation(),
    }
    for name, df in t.items():
        df.to_csv(out / "tables" / f"{name}.csv", index=False)

    figs = {
        "fig2_pooled": figures.fig2_pooled(t["table2_pooled"]),
        "fig3_ranking_uncertainty": figures.fig3_ranking_uncertainty(t["rank_probabilities"], t["paired_vs_dust3r"]),
        "fig4_dataset_specific": figures.fig4_dataset_specific(t["dataset_means"]),
        "fig5_nps_sps": figures.fig5_nps_sps(rec.scenes),
        "fig6_saturation": figures.fig6_saturation(t["cap_hit_by_dataset_method"], rec.pairs),
        "fig7_gt_aligned": figures.fig7_gt_aligned(t["table4_gt_aligned"]),
        "fig8_vggt_family": figures.fig8_vggt_family(t["table5_vggt_family"]),
        "fig9_scale_perturbation": figures.fig9_scale_perturbation(t["scale_perturbation"]),
    }
    for name, fig in figs.items():
        fig.savefig(out / "figures" / f"{name}.pdf")
        fig.savefig(out / "figures" / f"{name}.png", dpi=300)
        plt.close(fig)

    pooled = t["table2_pooled"].pivot(index="method", columns="metric", values="mean").loc[METHODS]
    print("\nTable 2 (pooled means)")
    print(pooled[["nps", "sps", "cap_hit_pct"]].round(3).to_string())
    sat = t["nps_saturation"].set_index("dataset")
    print(
        f"\nCap hits: {sat.loc['all', 'cap_hits']} / {sat.loc['all', 'terms']} terms; "
        f"per dataset " + ", ".join(f"{d} {sat.loc[d, 'cap_hit_pct']:.2f}%" for d in DATASETS)
    )
    print(f"\nWrote {len(t)} tables and {len(figs)} figures to {out}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="physfidelity3d")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate", help="check the released records")
    rep = sub.add_parser("reproduce", help="regenerate all tables and figures")
    rep.add_argument("--out", type=Path, default=Path("outputs"))
    args = parser.parse_args()
    if args.command == "validate":
        sys.exit(0 if validate() else 1)
    reproduce(args.out)


if __name__ == "__main__":
    main()
