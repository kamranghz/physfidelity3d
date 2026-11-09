"""Every number printed in the paper, checked at the precision it is printed with."""

import pandas as pd
import pytest

from physfidelity3d import tables
from physfidelity3d.records import load_records


@pytest.fixture(scope="module")
def rec():
    return load_records()


@pytest.fixture(scope="module")
def t(rec):
    return {
        "table2": tables.table2_pooled(rec),
        "ranks": tables.rank_probabilities(rec),
        "paired": tables.paired_vs_dust3r(rec),
        "rho": tables.nps_sps_correlation(rec).set_index("dataset"),
        "datasets": tables.dataset_means(rec),
    }


def check(value: float, printed: str) -> None:
    """``value`` must round to ``printed`` at the number of decimals the paper prints."""
    decimals = len(printed.split(".")[1]) if "." in printed else 0
    assert abs(value - float(printed)) <= 0.5 * 10**-decimals + 1e-12, f"got {value}, paper prints {printed}"


TABLE2 = {  # method: (NPS mean, lo, hi), (SPS mean, lo, hi), (cap-hit %, lo, hi)
    "dust3r": (("2.351", "1.841", "2.906"), ("3.430", "1.031", "6.643"), ("7.9", "5.9", "10.4")),
    "mast3r": (("2.785", "2.253", "3.341"), ("2.628", "1.057", "4.982"), ("12.3", "8.9", "16.7")),
    "vggt": (("3.165", "2.622", "3.719"), ("2.727", "1.523", "4.140"), ("17.1", "12.6", "22.4")),
    "vggt_omega": (("2.779", "2.275", "3.265"), ("1.467", "0.723", "2.596"), ("12.5", "8.5", "17.6")),
    "vgg_t3": (("3.321", "2.766", "3.898"), ("2.550", "1.538", "3.719"), ("16.4", "11.3", "22.9")),
}


@pytest.mark.parametrize("method", TABLE2)
def test_table2(t, method):
    for metric, values in zip(("nps", "sps", "cap_hit_pct"), TABLE2[method], strict=True):
        table = t["table2"]
        row = table[(table["metric"] == metric) & (table["method"] == method)].iloc[0]
        for col, expected in zip(("mean", "ci_low", "ci_high"), values, strict=True):
            check(row[col], expected)


def test_rank_probabilities(t):  # Section "4.1"
    r = t["ranks"].set_index(["metric", "method"])["rank1"]
    check(100 * r["nps", "dust3r"], "86.04")
    check(100 * r["sps", "vggt_omega"], "77.47")


def test_paired_differences(t):  # Section "4.1"
    p = t["paired"].query("metric == 'nps'").set_index("method")
    for method, values in {"vggt": ("0.815", "0.070", "1.523"), "vgg_t3": ("0.971", "0.234", "1.679")}.items():
        for col, expected in zip(("diff", "ci_low", "ci_high"), values, strict=True):
            check(p.loc[method, col], expected)
    others = t["paired"].query("not (metric == 'nps' and method in ['vggt', 'vgg_t3'])")
    assert ((others["ci_low"] < 0) & (others["ci_high"] > 0)).all(), "other intervals must include zero"


def test_dataset_lowest_means(t):  # Section "4.3"
    d = t["datasets"]
    expected = {
        ("ycbv", "nps"): ("dust3r", "2.804"),
        ("tless", "nps"): ("dust3r", "1.410"),
        ("picasso", "nps"): ("vggt_omega", "3.229"),
        ("ycbv", "sps"): ("mast3r", "1.956"),
        ("tless", "sps"): ("vgg_t3", "0.366"),
        ("picasso", "sps"): ("vggt_omega", "0.649"),
    }
    for (dataset, metric), (method, value) in expected.items():
        best = d[(d["dataset"] == dataset) & (d["metric"] == metric)].nsmallest(1, "mean").iloc[0]
        assert best["method"] == method
        check(best["mean"], value)


@pytest.mark.parametrize(
    "dataset, values",
    [
        ("ycbv", ("0.057", "-0.181", "0.289")),
        ("tless", ("0.117", "-0.128", "0.336")),
        ("picasso", ("0.495", "0.182", "0.710")),
        ("all", ("0.369", "0.228", "0.492")),
    ],
)
def test_nps_sps_correlation(t, dataset, values):  # Section "4.4"
    for col, expected in zip(("rho", "ci_low", "ci_high"), values, strict=True):
        check(t["rho"].loc[dataset, col], expected)


def test_saturation(rec):  # Sections "2.3".1, "4.5"
    s = tables.nps_saturation(rec).set_index("dataset")
    assert (s.loc["all", "cap_hits"], s.loc["all", "terms"]) == (259, 1955)
    check(s.loc["all", "cap_hit_pct"], "13.25")
    for dataset, pct in {"ycbv": "25.38", "tless": "5.49", "picasso": "21.31"}.items():
        check(s.loc[dataset, "cap_hit_pct"], pct)
    check(s.loc["all", "max_pair_raw_mm"], "78.325")
    check(s.loc["all", "max_plane_raw_mm"], "652.0")
    worst = rec.pairs.loc[rec.pairs["pen_raw_mm"].idxmax()]
    assert (worst["method"], worst["dataset"], worst["scene_id"]) == ("vgg_t3", "ycbv", "000054")
    assert tables.cap_parity(rec) == 0.0


def test_table3(rec):
    t3 = tables.table3_geometry(rec).set_index("method")
    expected = {
        "dust3r": ("215.7", "85.8", "2.351", "3.430"),
        "mast3r": ("228.1", "94.5", "2.785", "2.628"),
        "vggt": ("388.4", "167.1", "3.165", "2.727"),
        "vggt_omega": ("319.7", "121.8", "2.779", "1.467"),
        "vgg_t3": ("362.4", "156.0", "3.321", "2.550"),
    }
    for method, values in expected.items():
        for col, value in zip(("depth_rmse_mm", "cad_chamfer_mm", "nps", "sps"), values, strict=True):
            check(t3.loc[method, col], value)


def test_geometry_correlations():  # Section "4.2"
    g = tables.geometry_correlations().set_index(["x", "y", "dataset"])
    expected = {
        ("depth_rmse", "nps", "all"): ("0.258", "0.072", "0.426"),
        ("cad_chamfer", "nps", "all"): ("0.168", "-0.034", "0.347"),
        ("cad_chamfer", "nps", "picasso"): ("0.467", "0.063", "0.694"),
    }
    for key, values in expected.items():
        for col, value in zip(("rho", "ci_low", "ci_high"), values, strict=True):
            check(g.loc[key, col], value)
    check(g.loc[("depth_rmse", "sps", "all"), "rho"], "0.061")
    check(g.loc[("cad_chamfer", "sps", "all"), "rho"], "0.007")
    for x in ("depth_rmse", "cad_chamfer"):
        assert g.loc[(x, "sps", "all"), "ci_low"] < 0 < g.loc[(x, "sps", "all"), "ci_high"]


def test_table4():
    t4 = tables.table4_gt_aligned().set_index(["metric", "protocol", "method"])
    expected = {
        ("nps", "dust3r"): ("2.351", 1, "2.351", 1),
        ("nps", "mast3r"): ("2.785", 3, "2.785", 2),
        ("nps", "vggt_omega"): ("2.779", 2, "3.365", 3),
        ("nps", "vggt"): ("3.165", 4, "3.832", 5),
        ("nps", "vgg_t3"): ("3.321", 5, "3.756", 4),
        ("sps", "vggt_omega"): ("1.467", 1, "1.888", 2),
        ("sps", "vgg_t3"): ("2.550", 2, "1.441", 1),
        ("sps", "mast3r"): ("2.628", 3, "2.628", 3),
        ("sps", "vggt"): ("2.727", 4, "2.846", 4),
        ("sps", "dust3r"): ("3.430", 5, "3.430", 5),
    }
    for (metric, method), (mean_o, rank_o, mean_a, rank_a) in expected.items():
        check(t4.loc[(metric, "original", method), "mean"], mean_o)
        check(t4.loc[(metric, "gt_aligned", method), "mean"], mean_a)
        assert t4.loc[(metric, "original", method), "rank"] == rank_o
        assert t4.loc[(metric, "gt_aligned", method), "rank"] == rank_a


def test_table5():
    t5 = tables.table5_vggt_family().set_index(["method", "metric"])
    expected = {
        ("vggt", "nps"): ("3.165", "3.832", "0.667", "0.185", "1.187", 1),
        ("vggt", "sps"): ("2.727", "2.846", "0.119", "-1.405", "1.524", 0),
        ("vggt_omega", "nps"): ("2.779", "3.365", "0.586", "0.227", "0.976", 1),
        ("vggt_omega", "sps"): ("1.467", "1.888", "0.422", "-1.286", "2.374", 1),
        ("vgg_t3", "nps"): ("3.321", "3.756", "0.435", "0.104", "0.766", -1),
        ("vgg_t3", "sps"): ("2.550", "1.441", "-1.109", "-2.232", "-0.045", -1),
    }
    cols = ("native_mean", "aligned_mean", "diff", "ci_low", "ci_high")
    for key, (*values, rank_change) in expected.items():
        for col, value in zip(cols, values, strict=True):
            check(t5.loc[key, col], value)
        assert t5.loc[key, "rank_change"] == rank_change


def test_table6(rec):
    t6 = tables.table6_coverage(rec).set_index("dataset")
    for dataset, (scenes, objects) in {
        "ycbv": (12, "4.58"),
        "tless": (20, "5.05"),
        "picasso": (10, "3.60"),
        "all": (42, "4.57"),
    }.items():
        assert t6.loc[dataset, "scenes"] == scenes
        check(t6.loc[dataset, "mean_objects"], objects)
    assert t6["identical_object_sets"].all()


def test_table7(rec):
    t7 = tables.table7_collision_geometry(rec).set_index("method")
    expected = {
        "dust3r": (54, 138, "28.1"),
        "mast3r": (59, 133, "30.7"),
        "vggt": (85, 107, "44.3"),
        "vggt_omega": (64, 128, "33.3"),
        "vgg_t3": (64, 128, "33.3"),
    }
    assert (t7["meshes"] == 192).all()
    for method, (coacd, hull, pct) in expected.items():
        assert (t7.loc[method, "coacd"], t7.loc[method, "hull_fallback"]) == (coacd, hull)
        check(t7.loc[method, "coacd_pct"], pct)
    check(100 * t7.loc["dust3r", "hull_fallback"] / 192, "71.9")


def test_table8(rec):
    t8 = tables.table8_failure_cases(rec)
    expected = [
        ("78.3", "132.2", "3.48", "11.9"),
        ("32.5", "652.0", "4.50", "23.0"),
        ("45.5", "528.1", "6.66", "1.29"),
        ("16.5", "399.7", "1.88", "14.1"),
        ("19.4", "377.6", "7.36", "12.4"),
        ("47.8", "261.6", "2.49", "46.8"),
        ("17.7", "246.5", "5.12", "44.8"),
        ("28.4", "255.4", "5.80", "43.1"),
        ("45.9", "206.5", "6.25", "22.8"),
        ("15.4", "69.2", "10.00", "0.72"),
    ]
    for (_, row), values in zip(t8.iterrows(), expected, strict=True):
        for col, value in zip(("max_pair_raw_mm", "max_plane_raw_mm", "nps", "sps"), values, strict=True):
            check(row[col], value)


def test_scale_perturbation_uses_three_scenes():
    assert (tables.scale_perturbation()["n_scenes"] == 3).all()


def test_evaluation_counts(rec):  # Section "3.1"
    assert rec.scenes.groupby("dataset").size().to_dict() == {"ycbv": 60, "tless": 100, "picasso": 50}
    assert pd.Series(rec.scenes["method"]).value_counts().eq(42).all()
