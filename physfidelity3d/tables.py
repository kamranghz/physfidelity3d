"""Every table and in-text statistic of the paper, one function each.

Results computed from the released records are recomputed here. Tables 3-5 and the
data of Figs. 7-9 depend on reconstructions and ground truth that are not
redistributed, so they are read from ``data/recorded/``.
"""

import pandas as pd

from . import bootstrap
from .config import DATASETS, METHODS, NPS_CAP_MM, RECORDED_DIR, SEED
from .records import Records

# Bootstrap seeds used for the published numbers.
SEEDS = {
    "pooled_mean": SEED,
    "pooled_cap_hit": SEED + 1,
    "dataset_mean": SEED + 10,  # + dataset index
    "paired": SEED + 100,
    "dataset_spearman": SEED + 200,
    "pooled_spearman": SEED + 210,
    "rank_nps": SEED + 300,
    "rank_sps": SEED + 301,
}


def _recorded(name: str) -> pd.DataFrame:
    return pd.read_csv(RECORDED_DIR / f"{name}.csv")


def table2_pooled(rec: Records) -> pd.DataFrame:
    """Table 2: pooled NPS [mm], SPS [J] and pair-weighted cap-hit rate [%] with 95% CIs."""
    parts = []
    for metric in ("nps", "sps"):
        parts.append(bootstrap.mean_ci(rec.scenes, metric, SEEDS["pooled_mean"]).assign(metric=metric))
    cap = bootstrap.cap_hit_rate_ci(rec.scenes, SEEDS["pooled_cap_hit"])
    cap[["mean", "ci_low", "ci_high"]] *= 100
    parts.append(cap.assign(metric="cap_hit_pct"))
    return pd.concat(parts)[["metric", "method", "mean", "ci_low", "ci_high"]].reset_index(drop=True)


def dataset_means(rec: Records) -> pd.DataFrame:
    """Fig. 4: per-dataset mean NPS and SPS with 95% CIs."""
    parts = []
    for k, dataset in enumerate(DATASETS):
        for metric in ("nps", "sps"):
            ci = bootstrap.mean_ci(rec.scenes, metric, SEEDS["dataset_mean"] + k, dataset)
            parts.append(ci.assign(dataset=dataset, metric=metric))
    return pd.concat(parts)[["dataset", "metric", "method", "mean", "ci_low", "ci_high"]].reset_index(drop=True)


def rank_probabilities(rec: Records) -> pd.DataFrame:
    """Fig. 3(a, b): bootstrap rank probabilities."""
    return pd.concat(
        [
            bootstrap.rank_probabilities(rec.scenes, "nps", SEEDS["rank_nps"]).assign(metric="nps"),
            bootstrap.rank_probabilities(rec.scenes, "sps", SEEDS["rank_sps"]).assign(metric="sps"),
        ]
    ).reset_index(drop=True)


def paired_vs_dust3r(rec: Records) -> pd.DataFrame:
    """Fig. 3(c, d): paired scene-level differences, comparison - DUSt3R."""
    rows = [
        {"metric": metric, **bootstrap.paired_difference_ci(rec.scenes, metric, m, "dust3r", SEEDS["paired"])}
        for metric in ("nps", "sps")
        for m in METHODS[1:]
    ]
    return pd.DataFrame(rows)


def nps_sps_correlation(rec: Records) -> pd.DataFrame:
    """Section 4.4 / Fig. 5: Spearman rho between NPS and SPS, per dataset and pooled."""
    rows = [
        {"dataset": d, **bootstrap.spearman_ci(rec.scenes, "nps", "sps", SEEDS["dataset_spearman"], d)}
        for d in DATASETS
    ]
    rows.append({"dataset": "all", **bootstrap.spearman_ci(rec.scenes, "nps", "sps", SEEDS["pooled_spearman"])})
    return pd.DataFrame(rows)


def nps_saturation(rec: Records) -> pd.DataFrame:
    """Section 4.5 / Fig. 6: penetration terms at the 10 mm cap and uncapped maxima."""
    rows = []
    for dataset in [*DATASETS, "all"]:
        pairs = rec.pairs if dataset == "all" else rec.pairs[rec.pairs["dataset"] == dataset]
        planes = rec.planes if dataset == "all" else rec.planes[rec.planes["dataset"] == dataset]
        rows.append(
            {
                "dataset": dataset,
                "terms": len(pairs),
                "cap_hits": int(pairs["cap_hit"].sum()),
                "cap_hit_pct": 100 * pairs["cap_hit"].mean(),
                "max_pair_raw_mm": pairs["pen_raw_mm"].max(),
                "max_plane_raw_mm": planes["pen_raw_mm"].max(),
            }
        )
    return pd.DataFrame(rows)


def cap_hit_by_dataset_method(rec: Records) -> pd.DataFrame:
    """Fig. 6(a): pair-weighted cap-hit rate per dataset and method."""
    g = rec.pairs.groupby(["dataset", "method"])["cap_hit"]
    return (100 * g.mean()).rename("cap_hit_pct").reset_index()


def table3_geometry(rec: Records) -> pd.DataFrame:
    """Table 3: conventional geometry (recorded) next to NPS and SPS (from records)."""
    physics = rec.scenes.groupby("method")[["nps", "sps"]].mean()
    return _recorded("geometry_metrics").join(physics, on="method")


def geometry_correlations() -> pd.DataFrame:
    """Section 4.2: Spearman rho between geometry and physical-fidelity metrics (recorded)."""
    return _recorded("geometry_correlations")


def table4_gt_aligned() -> pd.DataFrame:
    """Table 4 / Fig. 7: pooled means and ranks, original vs GT-aligned protocol (recorded)."""
    return _recorded("gt_aligned_pooled")


def table5_vggt_family() -> pd.DataFrame:
    """Table 5 / Fig. 8: VGGT-family aligned - native paired differences (recorded)."""
    return _recorded("gt_aligned_paired")


def scale_perturbation() -> pd.DataFrame:
    """Fig. 9: pooled NPS/SPS under global scale perturbation, three scenes (recorded)."""
    return _recorded("scale_perturbation")


def table6_coverage(rec: Records) -> pd.DataFrame:
    """Table 6: evaluated objects per dataset; identical object sets across methods."""
    objects = rec.pairs.groupby(["dataset", "scene_id", "method"])[["object_i", "object_j"]].apply(
        lambda g: frozenset(g.to_numpy().ravel())
    )
    same_set = objects.groupby(["dataset", "scene_id"]).nunique().eq(1)
    per_scene = rec.scenes.groupby(["dataset", "scene_id"])["n_objects"].first()
    rows = [
        {
            "dataset": d,
            "scenes": int(per_scene.loc[d].size),
            "mean_objects": per_scene.loc[d].mean(),
            "identical_object_sets": bool(same_set.loc[d].all()),
        }
        for d in DATASETS
    ]
    rows.append(
        {
            "dataset": "all",
            "scenes": int(per_scene.size),
            "mean_objects": per_scene.mean(),
            "identical_object_sets": bool(same_set.all()),
        }
    )
    return pd.DataFrame(rows)


def table7_collision_geometry(rec: Records) -> pd.DataFrame:
    """Table 7: CoACD (watertight mesh) vs convex-hull fallback counts per method."""
    t = rec.scenes.groupby("method")[["n_objects", "watertight_meshes"]].sum().loc[METHODS]
    t = t.rename(columns={"n_objects": "meshes", "watertight_meshes": "coacd"}).reset_index()
    t["hull_fallback"] = t["meshes"] - t["coacd"]
    t["coacd_pct"] = 100 * t["coacd"] / t["meshes"]
    return t


# Representative failure cases listed in Table 8: (case, method, dataset, scene_id).
FAILURE_CASES = [
    ("max_pairwise_raw", "vgg_t3", "ycbv", "000054"),
    ("max_plane_raw", "vggt_omega", "ycbv", "000054"),
    ("high_plane_raw", "vggt_omega", "ycbv", "000049"),
    ("high_plane_raw", "dust3r", "ycbv", "000049"),
    ("high_plane_raw", "mast3r", "ycbv", "000052"),
    ("max_sps", "dust3r", "ycbv", "000059"),
    ("high_sps", "dust3r", "picasso", "pan_spatula_steak_broccoli"),
    ("high_sps", "mast3r", "picasso", "pan_spatula_steak_broccoli"),
    ("high_sps", "vggt", "ycbv", "000049"),
    ("high_nps_capped", "dust3r", "picasso", "holder_bowl"),
]


def table8_failure_cases(rec: Records) -> pd.DataFrame:
    """Table 8: uncapped penetration, NPS and SPS for the representative failure cases."""
    keys = ["dataset", "scene_id", "method"]
    pair_max = rec.pairs.groupby(keys)["pen_raw_mm"].max().rename("max_pair_raw_mm")
    plane_max = rec.planes.groupby(keys)["pen_raw_mm"].max().rename("max_plane_raw_mm")
    scores = rec.scenes.set_index(keys)[["nps", "sps"]]
    rows = []
    for case, method, dataset, scene in FAILURE_CASES:
        k = (dataset, scene, method)
        rows.append(
            {
                "case": case,
                "method": method,
                "dataset": dataset,
                "scene_id": scene,
                "max_pair_raw_mm": pair_max[k],
                "max_plane_raw_mm": plane_max[k],
                **scores.loc[k],
            }
        )
    return pd.DataFrame(rows)


def cap_parity(rec: Records) -> float:
    """Largest |min(raw, 10 mm) - stored capped term| over all 1,955 terms (Section 2.3.1)."""
    return float((rec.pairs["pen_raw_mm"].clip(upper=NPS_CAP_MM) - rec.pairs["pen_mm"]).abs().max())
