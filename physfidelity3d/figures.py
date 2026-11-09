"""Figures 2-9 of the paper. Each function takes table data and returns a matplotlib figure."""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D

from .config import DATASET_LABELS, DATASETS, METHOD_LABELS, METHODS, NPS_CAP_MM

COLORS = {"dust3r": "#0072B2", "mast3r": "#E69F00", "vggt": "#009E73", "vggt_omega": "#CC79A7", "vgg_t3": "#D55E00"}
MARKERS = {"dust3r": "o", "mast3r": "s", "vggt": "^", "vggt_omega": "D", "vgg_t3": "v"}
DATASET_MARKERS = {"ycbv": "o", "tless": "s", "picasso": "^"}
UNITS = {"nps": "NPS [mm]", "sps": "SPS [J]"}
WIDTH = 6.8  # inches, ACM double column

plt.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Liberation Sans", "DejaVu Sans"],
        "font.size": 8,
        "axes.labelsize": 8.5,
        "xtick.labelsize": 7.5,
        "ytick.labelsize": 7.5,
        "legend.fontsize": 7.5,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.color": "#E6E6E6",
        "grid.linewidth": 0.6,
        "axes.axisbelow": True,
        "axes.unicode_minus": False,
        "pdf.fonttype": 42,
        "savefig.bbox": "tight",
    }
)


def _panel(ax: plt.Axes, label: str) -> None:
    ax.text(-0.12, 1.04, label, transform=ax.transAxes, fontsize=9, fontweight="bold", va="bottom")


def _errorbar(ax: plt.Axes, x: float, y: float, lo: float, hi: float, method: str, horizontal=False, **kw) -> None:
    err = [[y - lo], [hi - y]]
    args = (y, x) if horizontal else (x, y)
    ax.errorbar(
        *args,
        **({"xerr": err} if horizontal else {"yerr": err}),
        fmt=MARKERS[method],
        color=COLORS[method],
        ecolor="#333333",
        elinewidth=0.9,
        capsize=2.5,
        markersize=5,
        markeredgecolor="white",
        markeredgewidth=0.5,
        zorder=3,
        **kw,
    )


def _method_axis(ax: plt.Axes, methods=METHODS, rotate=0) -> None:
    ax.set_xticks(range(len(methods)))
    ax.set_xticklabels([METHOD_LABELS[m] for m in methods], rotation=rotate, ha="right" if rotate else "center")
    ax.grid(axis="x", visible=False)


def fig2_pooled(table2: pd.DataFrame) -> plt.Figure:
    """Pooled mean NPS and SPS with scene-bootstrap 95% CIs."""
    fig, axes = plt.subplots(1, 2, figsize=(WIDTH, 2.8), constrained_layout=True)
    for ax, metric, label in zip(axes, ("nps", "sps"), "ab", strict=True):
        t = table2[table2["metric"] == metric].set_index("method").loc[METHODS]
        for x, (m, r) in enumerate(t.iterrows()):
            _errorbar(ax, x, r["mean"], r["ci_low"], r["ci_high"], m)
        _method_axis(ax)
        ax.set_ylabel(f"Mean {UNITS[metric]}")
        _panel(ax, f"({label})")
    return fig


def fig3_ranking_uncertainty(ranks: pd.DataFrame, paired: pd.DataFrame) -> plt.Figure:
    """(a, b) bootstrap rank probabilities; (c, d) paired differences vs DUSt3R."""
    fig, axes = plt.subplots(2, 2, figsize=(WIDTH, 5.0), constrained_layout=True)
    rank_cols = [c for c in ranks.columns if c.startswith("rank")]
    for ax, metric, label in zip(axes[0], ("nps", "sps"), "ab", strict=True):
        p = ranks[ranks["metric"] == metric].set_index("method").loc[METHODS, rank_cols].to_numpy()
        im = ax.imshow(p, cmap="Blues", vmin=0, vmax=1, aspect="auto")
        for (i, j), v in np.ndenumerate(p):
            ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=7, color="white" if v > 0.55 else "#222222")
        ax.set_xticks(range(len(rank_cols)), [f"R{k}" for k in range(1, len(rank_cols) + 1)])
        ax.set_yticks(range(len(METHODS)), [METHOD_LABELS[m] for m in METHODS])
        ax.grid(False)
        ax.set_xlabel("Rank (R1 = lowest mean)")
        _panel(ax, f"({label}) {metric.upper()}")
    fig.colorbar(im, ax=axes[0], fraction=0.03, pad=0.02, label="Probability")
    others = METHODS[1:]
    for ax, metric, label in zip(axes[1], ("nps", "sps"), "cd", strict=True):
        d = paired[paired["metric"] == metric].set_index("method").loc[others]
        for y, (m, r) in enumerate(d.iterrows()):
            _errorbar(ax, y, r["diff"], r["ci_low"], r["ci_high"], m, horizontal=True)
        ax.axvline(0, color="#333333", linewidth=0.9)
        ax.set_yticks(range(len(others)), [METHOD_LABELS[m] for m in others])
        ax.invert_yaxis()
        ax.grid(axis="y", visible=False)
        ax.set_xlabel(f"Paired {UNITS[metric]}: comparison − DUSt3R")
        _panel(ax, f"({label}) {metric.upper()}")
    return fig


def fig4_dataset_specific(means: pd.DataFrame) -> plt.Figure:
    """Per-dataset mean NPS and SPS with 95% CIs."""
    fig, axes = plt.subplots(2, 3, figsize=(WIDTH, 3.8), sharey="row", constrained_layout=True)
    for col, (dataset, label) in enumerate(zip(DATASETS, "abc", strict=True)):
        for row, metric in enumerate(("nps", "sps")):
            ax = axes[row, col]
            t = means[(means["dataset"] == dataset) & (means["metric"] == metric)].set_index("method").loc[METHODS]
            for x, (m, r) in enumerate(t.iterrows()):
                _errorbar(ax, x, r["mean"], r["ci_low"], r["ci_high"], m)
            _method_axis(ax, rotate=30)
            if row == 0:
                ax.set_xticklabels([])
                ax.set_title(DATASET_LABELS[dataset], fontsize=8.5)
                _panel(ax, f"({label})")
            if col == 0:
                ax.set_ylabel(f"Mean {UNITS[metric]}")
    return fig


def fig5_nps_sps(scenes: pd.DataFrame) -> plt.Figure:
    """NPS vs SPS for all 210 evaluations (colour = method, marker = dataset)."""
    fig, ax = plt.subplots(figsize=(WIDTH, 3.0), constrained_layout=True)
    for dataset in DATASETS:
        for m in METHODS:
            s = scenes[(scenes["dataset"] == dataset) & (scenes["method"] == m)]
            ax.scatter(
                s["nps"],
                s["sps"],
                s=22,
                alpha=0.75,
                color=COLORS[m],
                marker=DATASET_MARKERS[dataset],
                edgecolors="white",
                linewidths=0.35,
                zorder=3,
            )
    datasets = [
        Line2D([], [], marker=DATASET_MARKERS[d], color="#444444", ls="", label=DATASET_LABELS[d]) for d in DATASETS
    ]
    methods = [Line2D([], [], marker=MARKERS[m], color=COLORS[m], ls="", label=METHOD_LABELS[m]) for m in METHODS]
    ax.add_artist(
        ax.legend(handles=datasets, title="Dataset", loc="upper left", bbox_to_anchor=(1.01, 1), frameon=False)
    )
    ax.legend(handles=methods, title="Method", loc="upper left", bbox_to_anchor=(1.01, 0.58), frameon=False)
    ax.set_xlabel(UNITS["nps"])
    ax.set_ylabel(UNITS["sps"])
    return fig


def fig6_saturation(cap_rates: pd.DataFrame, pairs: pd.DataFrame) -> plt.Figure:
    """(a) pair-weighted cap-hit rates; (b) capped vs raw penetration for all 1,955 terms."""
    fig, (a, b) = plt.subplots(1, 2, figsize=(WIDTH, 2.8), constrained_layout=True)
    width = 0.15
    for k, m in enumerate(METHODS):
        r = cap_rates[cap_rates["method"] == m].set_index("dataset").loc[DATASETS, "cap_hit_pct"]
        a.bar(np.arange(3) + (k - 2) * width, r, width, color=COLORS[m], label=METHOD_LABELS[m])
    a.set_xticks(range(3), [DATASET_LABELS[d] for d in DATASETS])
    a.grid(axis="x", visible=False)
    a.set_ylabel("Pair-weighted cap-hit rate [%]")
    a.legend(frameon=False, loc="upper left", bbox_to_anchor=(1.0, 1.0))
    _panel(a, "(a)")
    b.scatter(pairs["pen_mm"], pairs["pen_raw_mm"], s=8, alpha=0.3, color="#0072B2", edgecolors="none")
    b.axhline(NPS_CAP_MM, color="#333333", ls="--", lw=0.8, label="10 mm cap")
    raw_max = pairs["pen_raw_mm"].max()
    b.annotate(
        f"max raw = {raw_max:.3f} mm",
        xy=(NPS_CAP_MM, raw_max),
        xytext=(0.45, 0.92),
        textcoords="axes fraction",
        fontsize=7.5,
        arrowprops={"arrowstyle": "->", "lw": 0.7},
    )
    b.set_xlabel("Capped penetration [mm]")
    b.set_ylabel("Raw penetration [mm]")
    b.legend(frameon=False, loc="upper left")
    _panel(b, "(b)")
    return fig


def fig7_gt_aligned(table4: pd.DataFrame) -> plt.Figure:
    """Original (open) vs GT-aligned (filled) pooled means with CIs; ranks annotated."""
    fig, axes = plt.subplots(1, 2, figsize=(WIDTH, 2.9), constrained_layout=True)
    for ax, metric, label in zip(axes, ("nps", "sps"), "ab", strict=True):
        for x, m in enumerate(METHODS):
            for dx, protocol in ((-0.13, "original"), (0.13, "gt_aligned")):
                r = table4[
                    (table4["metric"] == metric) & (table4["method"] == m) & (table4["protocol"] == protocol)
                ].iloc[0]
                face = "white" if protocol == "original" else COLORS[m]
                ax.errorbar(
                    x + dx,
                    r["mean"],
                    yerr=[[r["mean"] - r["ci_low"]], [r["ci_high"] - r["mean"]]],
                    fmt=MARKERS[m],
                    color=COLORS[m],
                    mfc=face,
                    ecolor="#333333",
                    elinewidth=0.9,
                    capsize=2.5,
                    markersize=5.5,
                    zorder=3,
                )
                ax.annotate(
                    f"#{int(r['rank'])}",
                    (x + dx, r["ci_high"]),
                    xytext=(0, 4),
                    textcoords="offset points",
                    ha="center",
                    fontsize=7,
                    color=COLORS[m],
                )
        _method_axis(ax)
        ax.set_ylabel(UNITS[metric])
        _panel(ax, f"({label})")
    handles = [
        Line2D([], [], marker="o", color="#444444", mfc=f, ls="", label=t)
        for f, t in (("white", "Original protocol"), ("#444444", "GT-aligned protocol"))
    ]
    fig.legend(handles=handles, loc="outside upper center", ncol=2, frameon=False)
    return fig


def fig8_vggt_family(table5: pd.DataFrame) -> plt.Figure:
    """Aligned - native paired differences for the VGGT family."""
    methods = ["vggt", "vggt_omega", "vgg_t3"]
    fig, axes = plt.subplots(1, 2, figsize=(WIDTH, 2.4), constrained_layout=True)
    for ax, metric, label in zip(axes, ("nps", "sps"), "ab", strict=True):
        t = table5[table5["metric"] == metric].set_index("method").loc[methods]
        for y, (m, r) in enumerate(t.iterrows()):
            _errorbar(ax, y, r["diff"], r["ci_low"], r["ci_high"], m, horizontal=True)
        ax.axvline(0, color="#333333", linewidth=0.9)
        ax.set_yticks(range(len(methods)), [METHOD_LABELS[m] for m in methods])
        ax.invert_yaxis()
        ax.grid(axis="y", visible=False)
        ax.set_xlabel(f"Aligned − native {UNITS[metric]}")
        _panel(ax, f"({label})")
    return fig


def fig9_scale_perturbation(perturbation: pd.DataFrame) -> plt.Figure:
    """Pooled NPS/SPS under global scale perturbation (three scenes, one per dataset)."""
    fig, axes = plt.subplots(1, 2, figsize=(WIDTH, 2.8), constrained_layout=True)
    for ax, metric, label in zip(axes, ("nps", "sps"), "ab", strict=True):
        for m in METHODS:
            s = perturbation[(perturbation["metric"] == metric) & (perturbation["method"] == m)]
            ax.plot(
                s["scale_pct"],
                s["mean"],
                marker=MARKERS[m],
                color=COLORS[m],
                markersize=4.5,
                markeredgecolor="white",
                markeredgewidth=0.4,
                label=METHOD_LABELS[m],
            )
        ax.axvline(0, color="#666666", ls=":", lw=0.8)
        ax.set_xticks(sorted(perturbation["scale_pct"].unique()))
        ax.set_xlabel("Scale perturbation [%]")
        ax.set_ylabel(UNITS[metric])
        _panel(ax, f"({label})")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="outside upper center", ncol=5, frameon=False)
    return fig
