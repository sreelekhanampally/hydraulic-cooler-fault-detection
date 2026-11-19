"""Publication-style figures from computed results, never invented data."""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse
from scipy import stats
from extract_features import ROOT, CORE

ORDER = [100, 20, 3]
COLORS = {100: "#176b73", 20: "#b57516", 3: "#ac493b"}
NAMES = {100: "Full efficiency", 20: "Reduced efficiency", 3: "Near failure"}
SHORT = ["Temperature", "Temp. trend", "Flow", "Pressure SD", "Motor power", "Vibration"]
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11,
    "axes.spines.top": False, "axes.spines.right": False, "axes.labelcolor": "#243848",
    "text.color": "#243848", "xtick.color": "#425969", "ytick.color": "#425969",
    "axes.titleweight": "semibold", "figure.facecolor": "white", "axes.facecolor": "white",
    "savefig.facecolor": "white", "axes.grid": False, "pdf.fonttype": 42})


def save(fig, name):
    fig.savefig(ROOT / "figures" / (name + ".png"), dpi=190, bbox_inches="tight")
    fig.savefig(ROOT / "figures" / (name + ".pdf"), bbox_inches="tight")
    plt.close(fig)


def heatmap(ax, a, title, limit=1):
    im = ax.imshow(a, vmin=-limit, vmax=limit, cmap="RdBu_r")
    ax.set_xticks(range(6), SHORT, rotation=48, ha="right", fontsize=9)
    ax.set_yticks(range(6), SHORT, fontsize=9)
    for i in range(6):
        for j in range(6):
            ax.text(j, i, f"{a[i,j]:.2f}", ha="center", va="center", fontsize=8.5,
                    color="white" if abs(a[i,j]) > .6 else "#243848")
    ax.set_title(title, fontsize=12, pad=10)
    return im


def ellipse(ax, mean, covariance, radius, color, label=None, fill=False):
    values, vectors = np.linalg.eigh(covariance)
    order = values.argsort()[::-1]; values, vectors = values[order], vectors[:, order]
    angle = np.degrees(np.arctan2(vectors[1, 0], vectors[0, 0]))
    e = Ellipse(mean, 2 * radius * np.sqrt(values[0]), 2 * radius * np.sqrt(values[1]),
                angle=angle, facecolor=color if fill else "none", edgecolor=color,
                alpha=.12 if fill else .9, linewidth=1.8, label=label)
    ax.add_patch(e)


def main():
    r = json.loads((ROOT / "results" / "analysis.json").read_text())
    d = pd.read_csv(ROOT / "data" / "cycle_features.csv")
    p = pd.read_csv(ROOT / "data" / "matched_profiles.csv")
    z = (p[CORE].to_numpy() - np.array(r["reference_scale"]["mean"])) / np.array(r["reference_scale"]["sd"])
    means = np.array([g["mean_z"] for g in r["group_summaries"]])
    fig, axes = plt.subplots(2, 1, figsize=(11, 6), sharex=True, gridspec_kw={"height_ratios": [3, 1]})
    for k in ORDER:
        a = d[d.cooler == k]
        axes[0].plot(a.cycle_id, a.TS2_mean, color=COLORS[k], lw=1.3, label=NAMES[k])
        axes[1].scatter(a.cycle_id, np.full(len(a), ORDER.index(k)), c=COLORS[k], s=5, marker="s")
    axes[0].set_ylabel("Mean TS2 temperature (deg C)")
    axes[0].legend(frameon=False, loc="upper right")
    axes[0].set_title("Cooler condition and recording phase are perfectly confounded")
    axes[1].set_yticks(range(3), ["100", "20", "3"]); axes[1].set_ylabel("Cooler code")
    axes[1].set_xlabel("Original cycle number")
    fig.tight_layout(); save(fig, "01_experiment_order")

    traces = json.loads((ROOT / "data" / "trace_samples.json").read_text())
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    for ax, sensor, title in zip(axes, ["TS2", "FS1"], ["Oil temperature", "Volume flow"]):
        for ex in traces[sensor]["examples"]:
            ax.plot(ex["time"], ex["value"], color=COLORS[ex["cooler"]],
                    label=f"{NAMES[ex['cooler']]}: cycle {ex['cycle_id']}")
        ax.set(xlabel="Time in operating cycle (s)", ylabel=traces[sensor]["unit"], title=title)
        ax.legend(frameon=False, fontsize=8)
    fig.tight_layout(); save(fig, "02_recorded_cycles")

    fig, ax = plt.subplots(figsize=(11, 5))
    for i, (k, g) in enumerate(zip(ORDER, r["group_summaries"])):
        sd = np.sqrt(np.diag(g["covariance_z"]))
        ax.errorbar(np.arange(6) + (i - 1) * .15, g["mean_z"], yerr=sd,
                    fmt=["o", "s", "^"][i], color=COLORS[k], capsize=3, label=NAMES[k])
    ax.axhline(0, color="#99a7af", lw=.8)
    ax.set_xticks(range(6), SHORT); ax.set_ylabel("Common-scale standardized profile value")
    ax.set_title("Mean vectors and between-setting standard deviations")
    ax.legend(frameon=False, ncol=3, loc="lower center", bbox_to_anchor=(.5, 1.02))
    fig.tight_layout(); save(fig, "03_mean_vectors")

    fig, axes = plt.subplots(1, 3, figsize=(14, 5.3))
    for ax, g in zip(axes, r["group_summaries"]):
        im = heatmap(ax, np.array(g["correlation"]), g["label"])
    fig.colorbar(im, ax=axes, fraction=.022, pad=.02, label="Pearson correlation")
    fig.subplots_adjust(bottom=.29, top=.88, wspace=.4, right=.92)
    save(fig, "04_correlation_matrices")

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))
    for ax, key, label in zip(axes, ["log_generalized_variance", "standardized_generalized_variance"],
                              ["log determinant of sample covariance", "det(S)^(1/6), variance scale"]):
        values = [g[key] for g in r["group_summaries"]]
        ax.bar(range(3), values, color=[COLORS[k] for k in ORDER], width=.6)
        ax.set_xticks(range(3), ["Full", "Reduced", "Near failure"]); ax.set_ylabel(label)
        for i, value in enumerate(values):
            ax.annotate(f"{value:.3g}", (i, value), xytext=(0, 7 if value >= 0 else -15),
                        textcoords="offset points", ha="center", fontsize=10)
    axes[0].set_title("Overall multivariate variability")
    axes[1].set_title("A common scale keeps comparisons meaningful")
    fig.tight_layout(); save(fig, "05_generalized_variance")

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))
    values = p.TS2_mean.to_numpy()
    axes[0].hist(values, bins=22, density=True, color="#d9e5e7", edgecolor="white", label="Pooled profiles")
    for k in ORDER:
        a = p[p.cooler == k].TS2_mean
        grid = np.linspace(a.min() - 1, a.max() + 1, 150)
        axes[0].plot(grid, stats.norm.pdf(grid, a.mean(), a.std(ddof=0)) / 3,
                     color=COLORS[k], lw=2, label=NAMES[k])
    axes[0].set(xlabel="Mean temperature (deg C)", ylabel="Density", title="Pooling conditions creates a mixture")
    axes[0].legend(frameon=False, fontsize=8)
    a = p[p.cooler == 3].TS2_mean.to_numpy()
    (qq, ordered), (slope, intercept, _) = stats.probplot(a, dist="norm")
    axes[1].scatter(qq, ordered, color=COLORS[3], s=22)
    axes[1].plot(qq, slope * qq + intercept, color="#425969", lw=1)
    axes[1].set(xlabel="Normal theoretical quantile", ylabel="Mean temperature (deg C)", title="Within-condition Q-Q assessment")
    fig.tight_layout(); save(fig, "06_distribution_checks")

    fig, axes = plt.subplots(1, 3, figsize=(12, 4))
    for ax, k, g in zip(axes, ORDER, r["group_summaries"]):
        xx = z[p.cooler.to_numpy() == k]
        delta = xx - xx.mean(axis=0)
        cov = np.array(g["mle_covariance_z"])
        distances = np.sort(np.sum(delta * np.linalg.solve(cov, delta.T).T, axis=1))
        theory = stats.chi2.ppf((np.arange(48) + .5) / 48, 6)
        ax.scatter(theory, distances, color=COLORS[k], s=18)
        bound = max(theory.max(), distances.max()); ax.plot([0, bound], [0, bound], color="#80949e", lw=1)
        ax.set(xlabel="Chi-square(6) reference quantile", ylabel="Fitted squared distance", title=NAMES[k])
    fig.tight_layout(); save(fig, "07_multivariate_qq")

    g = r["group_summaries"][0]
    mu = np.array(g["mean_z"])[[0, 4]]; cov = np.array(g["mle_covariance_z"])[np.ix_([0, 4], [0, 4])]
    a = np.linspace(mu[0] - 4 * np.sqrt(cov[0, 0] / 48), mu[0] + 4 * np.sqrt(cov[0, 0] / 48), 100)
    b = np.linspace(mu[1] - 4 * np.sqrt(cov[1, 1] / 48), mu[1] + 4 * np.sqrt(cov[1, 1] / 48), 100)
    aa, bb = np.meshgrid(a, b); delta = np.stack([aa - mu[0], bb - mu[1]], axis=-1)
    surface = -.5 * 48 * np.einsum("...i,ij,...j->...", delta, np.linalg.inv(cov), delta)
    fig, ax = plt.subplots(figsize=(8, 5))
    cs = ax.contour(aa, bb, surface, levels=[-12, -8, -5, -3, -1, -.25], cmap="Blues_r")
    ax.clabel(cs, inline=True, fontsize=9, fmt="%.2g")
    ax.scatter(*mu, color=COLORS[100], marker="x", s=100, label="Analytical MLE")
    numeric = r["numerical_MLE"]["numerical_parameters"]
    ax.scatter(numeric[0], numeric[1], facecolors="none", edgecolors=COLORS[20], s=120, label="Numerical MLE")
    ax.set(xlabel="Temperature mean parameter (common z scale)", ylabel="Power mean parameter (common z scale)",
           title="Log-likelihood slice with covariance fixed at its MLE")
    ax.legend(frameon=False); fig.tight_layout(); save(fig, "08_MLE_likelihood")

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    axes[0].bar(["First root", "Second root"], r["manova"]["roots"][:2], color=[COLORS[100], COLORS[20]], width=.5)
    axes[0].set(ylabel="Generalized eigenvalue of (H, E)", title="Roy's statistic uses the largest root")
    for j, value in enumerate(r["manova"]["roots"][:2]):
        axes[0].text(j, value + 4, f"{value:.3f}", ha="center")
    for key, label, color in [("gaussian_iid_null", "Gaussian iid null", COLORS[100]),
                              ("wild_restricted", "Matched restricted wild", COLORS[20]),
                              ("wild_full_residual", "Matched full-residual wild", COLORS[3])]:
        samples = r["manova"]["resampling"][key]["roy_samples"]
        axes[1].hist(samples, bins=35, histtype="step", density=True, color=color, label=label)
    axes[1].set(xlabel="Simulated Roy statistic under the stated null", ylabel="Density", title="Null values are much smaller than observed")
    axes[1].legend(frameon=False, fontsize=8)
    axes[1].text(.97, .95, f"Observed Roy = {r['manova']['roy']:.2f}\nNot shown on null-scale x axis", transform=axes[1].transAxes,
                 ha="right", va="top", fontsize=9)
    fig.tight_layout(); save(fig, "09_MANOVA_simulation")

    fig, ax = plt.subplots(figsize=(10, 5))
    offsets = [-.19, 0, .19]
    for row, h in enumerate(r["hotelling"]):
        for j, length in enumerate([1, 4, 8]):
            ci = h[f"bootstrap_length_{length}"]
            # Convert the temperature contrast to original Celsius units.
            scale = r["reference_scale"]["sd"][0]
            mean = h["mean_difference"][0] * scale
            lo, hi = ci["lower"][0] * scale, ci["upper"][0] * scale
            ax.errorbar(mean, row + offsets[j], xerr=[[mean - lo], [hi - mean]], fmt="o",
                        color=[COLORS[100], COLORS[20], COLORS[3]][j], capsize=4,
                        label=f"Bootstrap block length {length}" if row == 0 else None)
    ax.set_yticks(range(3), [f"{NAMES[h['to']]} minus {NAMES[h['from']]}" for h in r["hotelling"]])
    ax.set(xlabel="Mean matched temperature difference (deg C)", title="Pointwise 95% bootstrap intervals across 48 matched settings")
    ax.legend(frameon=False, fontsize=9); fig.tight_layout(); save(fig, "10_matched_contrast_intervals")

    h = r["hotelling"][0]; dims = [0, 2]
    fig, ax = plt.subplots(figsize=(8, 5))
    dif = np.array(h["difference_rows"])[:, dims]
    ax.scatter(dif[:, 0], dif[:, 1], color="#9eb5bd", s=20, label="48 matched differences")
    center = np.array(h["mean_difference"])[dims]
    cov = np.array(h["covariance"])[np.ix_(dims, dims)] / 48
    ellipse(ax, center, cov, np.sqrt(h["critical_T2_95"]), COLORS[20], "Projection of 95% six-dimensional mean region")
    ax.scatter(*center, color=COLORS[20], marker="x", s=90)
    ax.scatter(0, 0, color="#243848", marker="+", s=100, label="Zero mean difference")
    ax.set(xlabel="Temperature difference (common z units)", ylabel="Flow difference (common z units)",
           title="A mean confidence region is different from individual-cycle spread")
    ax.autoscale_view(); ax.legend(frameon=False, fontsize=8); fig.tight_layout(); save(fig, "11_Hotelling_region")

    fig, axes = plt.subplots(1, 2, figsize=(11, 5))
    ref = r["covariance_tests"]["matched_gaussian_null"]["M_samples"]
    axes[0].hist(ref, bins=32, color="#a5c8cb", edgecolor="white")
    axes[0].set(xlabel="Simulated Box M", ylabel="Count", title="Matched Gaussian equal-covariance null")
    axes[0].text(.97, .95, f"Observed M = {r['covariance_tests']['box_m']['M']:.2f}\nOutside this null-scale panel", transform=axes[0].transAxes, ha="right", va="top", fontsize=9)
    matrix = np.array(r["group_summaries"][2]["covariance_z"])
    im = axes[1].imshow(matrix, cmap="Blues"); axes[1].set_xticks(range(6), SHORT, rotation=45, ha="right", fontsize=8)
    axes[1].set_yticks(range(6), SHORT, fontsize=8); axes[1].set_title("Near-failure covariance on the common scale")
    fig.colorbar(im, ax=axes[1], shrink=.75); fig.tight_layout(); save(fig, "12_covariance_equality")

    fig, axes = plt.subplots(1, 2, figsize=(11, 5.8))
    for ax, key, title in zip(axes, ["raw_correlation", "adjusted_correlation"],
                              ["Unadjusted profile correlations", "After recorded-component adjustment"]):
        im = heatmap(ax, np.array(r["partial_regression"][key]), title)
    fig.colorbar(im, ax=axes, fraction=.025, pad=.03)
    fig.subplots_adjust(bottom=.28, wspace=.42, right=.91); save(fig, "13_partial_correlations")

    fig, ax = plt.subplots(figsize=(11, 5))
    names = ["Temperature only", "Diagonal covariance", "Shared covariance", "Class covariance"]
    kinds = ["temperature", "diagonal", "shared", "full"]
    for j, (scenario, label, color) in enumerate([("intact", "All required sensors available", COLORS[100]),
                                               ("TS2_unavailable", "Simulated TS2 sensor outage", COLORS[20])]):
        values = [r["predictive_results"][k][scenario]["balanced_accuracy"] * 100 for k in kinds]
        bars = ax.bar(np.arange(4) + (j - .5) * .34, values, width=.34, label=label, color=color)
        for bar, value in zip(bars, values):
            ax.annotate(f"{value:.1f}%", (bar.get_x() + bar.get_width()/2, value), xytext=(0, 4), textcoords="offset points", ha="center", fontsize=9)
    ax.set_xticks(range(4), names); ax.set_ylim(0, 113)
    ax.set(ylabel="Held-out balanced accuracy (%)", title="Temperature is already sufficient here; other sensors add outage resilience")
    ax.legend(frameon=False, loc="lower right"); fig.tight_layout(); save(fig, "14_predictive_comparison")

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))
    for ax, kind, title in zip(axes, ["temperature", r["selected_model"]], ["Temperature-only model with TS2 unavailable", "Selected joint model with TS2 unavailable"]):
        cm = np.array(r["predictive_results"][kind]["TS2_unavailable"]["confusion"])
        ax.imshow(cm, cmap="Blues", vmin=0, vmax=cm.max())
        for i in range(3):
            for j in range(3):
                ax.text(j, i, str(cm[i, j]), ha="center", va="center", color="white" if cm[i,j] > cm.max()/2 else "#243848", fontsize=15)
        ax.set_xticks(range(3), ["Full", "Reduced", "Near fail"]); ax.set_yticks(range(3), ["Full", "Reduced", "Near fail"])
        ax.set(xlabel="Predicted condition", ylabel="Recorded condition", title=title)
    fig.tight_layout(); save(fig, "15_outage_confusion")

    fig, ax = plt.subplots(figsize=(10, 4.7))
    for kind, label, color in [("temperature", "Temperature only", COLORS[3]), ("diagonal", "Diagonal", "#7a6ab0"),
                               ("shared", "Shared covariance", COLORS[100]), ("full", "Class covariance", COLORS[20])]:
        ax.plot([a["temperature_offset_C"] for a in r["offset_simulation"]], [100*a[kind] for a in r["offset_simulation"]], marker="o", color=color, label=label)
    ax.set(xlabel="Artificial offset added to TS2 mean (deg C)", ylabel="Held-out balanced accuracy (%)",
           title="Sensitivity experiment: simulated bias is distinct from measured faults")
    ax.legend(frameon=False); ax.set_ylim(0, 105); fig.tight_layout(); save(fig, "16_sensor_bias_simulation")
    print("Created 16 figure pairs (PNG and vector PDF).")


if __name__ == "__main__":
    main()
