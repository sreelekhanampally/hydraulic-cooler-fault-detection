"""End-to-end analysis. All predictive choices use development settings only.

Run from any directory: python src/analyze.py [--resamples 999]
The original raw archive or the supplied cycle_features.csv is sufficient.
"""
from __future__ import annotations

import argparse
import json
import platform
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import linalg, optimize, special, stats
from sklearn.metrics import (accuracy_score, balanced_accuracy_score, confusion_matrix,
                             f1_score, log_loss)
from sklearn.model_selection import GroupKFold, GroupShuffleSplit
from sklearn.preprocessing import StandardScaler
from statsmodels.multivariate.manova import MANOVA

from extract_features import ROOT, CORE, LABELS, extract
from statistics_core import (balanced_manova, box_m, circular_block_indices, covariance,
                             covariance_lrt, gaussian_log_scores, holm_adjust, logdet,
                             manova_roots, mardia, marginal_scores, paired_hotelling)

ORDER = [100, 20, 3]
SEED = 20261115
META = [
    {"key": "TS2_mean", "name": "Mean oil temperature", "short": "Temperature", "unit": "deg C", "sensor": "TS2"},
    {"key": "TS2_slope", "name": "Temperature trend", "short": "Temperature trend", "unit": "deg C/s", "sensor": "TS2"},
    {"key": "FS1_mean", "name": "Mean volume flow", "short": "Flow", "unit": "L/min", "sensor": "FS1"},
    {"key": "PS2_std", "name": "Pressure fluctuation", "short": "Pressure SD", "unit": "bar", "sensor": "PS2"},
    {"key": "EPS1_mean", "name": "Mean motor power", "short": "Motor power", "unit": "W", "sensor": "EPS1"},
    {"key": "VS1_mean", "name": "Mean vibration", "short": "Vibration", "unit": "mm/s", "sensor": "VS1"},
]


def clean(value):
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    if isinstance(value, np.ndarray):
        return clean(value.tolist())
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return float(value) if np.isfinite(value) else None
    if isinstance(value, (np.bool_,)):
        return bool(value)
    return value


def write_json(path, value):
    Path(path).write_text(json.dumps(clean(value), indent=2, allow_nan=False), encoding="utf-8")


def fit_gaussian(x, y, kind, alpha=0.0, indices=None):
    indices = list(range(x.shape[1])) if indices is None else list(indices)
    x = x[:, indices]
    means = np.array([x[y == k].mean(axis=0) for k in ORDER])
    counts = np.array([np.sum(y == k) for k in ORDER])
    covs = np.array([covariance(x[y == k], mle=True) for k in ORDER])
    if kind == "shared":
        pooled = np.average(covs, axis=0, weights=counts)
        covs = np.tile(pooled, (3, 1, 1))
    if kind == "diagonal":
        covs = np.array([np.diag(np.diag(s)) for s in covs])
    for j, s in enumerate(covs):
        covs[j] = (1 - alpha) * s + alpha * np.trace(s) / len(s) * np.eye(len(s))
        if linalg.eigvalsh(covs[j])[0] <= 0:
            raise ValueError("Gaussian covariance is not positive definite")
    return {"kind": kind, "alpha": float(alpha), "feature_indices": indices,
            "means": means, "covariances": covs, "priors": counts / counts.sum(),
            "counts": counts}


def scores(model, z, available=None):
    available = list(range(z.shape[1])) if available is None else list(available)
    indices = model["feature_indices"]
    local = [j for j, i in enumerate(indices) if i in available]
    return marginal_scores(z[:, indices], model["means"], model["covariances"],
                           model["priors"], local)


def probability(model, z, available=None):
    return special.softmax(scores(model, z, available), axis=1)


def metrics(y, prob):
    encoded = np.array([ORDER.index(int(k)) for k in y])
    prediction = prob.argmax(axis=1)
    cm = confusion_matrix(encoded, prediction, labels=[0, 1, 2])
    return {"n": len(y), "accuracy": float(accuracy_score(encoded, prediction)),
            "balanced_accuracy": float(balanced_accuracy_score(encoded, prediction)),
            "macro_f1": float(f1_score(encoded, prediction, average="macro")),
            "log_loss": float(log_loss(encoded, prob, labels=[0, 1, 2])),
            "brier": float(np.mean(np.sum((prob - np.eye(3)[encoded]) ** 2, axis=1))),
            "confusion": cm, "recall": np.diag(cm) / cm.sum(axis=1),
            "healthy_false_alarm": float(1 - cm[0, 0] / cm[0].sum()),
            "near_failure_as_healthy": float(cm[2, 0] / cm[2].sum())}


def prepare_splits(stable):
    splitter = GroupShuffleSplit(n_splits=1, test_size=.25, random_state=SEED)
    development, test = next(splitter.split(stable, groups=stable.setting))
    dev_settings = sorted(stable.iloc[development].setting.unique())
    test_settings = sorted(stable.iloc[test].setting.unique())
    split = {"seed": SEED, "unit": "valve x pump x accumulator setting",
             "development_settings": dev_settings, "test_settings": test_settings,
             "development_cycles": stable.iloc[development].cycle_id.tolist(),
             "test_cycles": stable.iloc[test].cycle_id.tolist(),
             "interpretation": "Unseen nuisance settings within one rig and its three cooler phases; not future-machine validation"}
    assert not set(dev_settings) & set(test_settings)
    write_json(ROOT / "data" / "split_manifest.json", split)
    return stable.iloc[development].copy(), stable.iloc[test].copy(), split


def select_models(dev):
    """Selection score fixed in advance: mean intact/outage development log loss."""
    x, y = dev[CORE].to_numpy(), dev.cooler.to_numpy()
    candidates = []
    for kind in ["diagonal", "shared", "full"]:
        for alpha in [0., .0001, .001, .01, .05, .1]:
            candidates.append((kind, alpha, list(range(6))))
    candidates.append(("temperature", 0., [0]))
    rows = []
    folds = list(GroupKFold(n_splits=6).split(x, y, groups=dev.setting))
    for kind, alpha, inds in candidates:
        losses, intact_acc, outage_acc = [], [], []
        for train, validation in folds:
            scaler = StandardScaler().fit(x[train])
            zt, zv = scaler.transform(x[train]), scaler.transform(x[validation])
            model = fit_gaussian(zt, y[train], kind, alpha, inds)
            intact = metrics(y[validation], probability(model, zv))
            outage = metrics(y[validation], probability(model, zv, [2, 3, 4, 5]))
            losses.append((intact["log_loss"] + outage["log_loss"]) / 2)
            intact_acc.append(intact["balanced_accuracy"])
            outage_acc.append(outage["balanced_accuracy"])
        rows.append({"kind": kind, "alpha": alpha, "objective": float(np.mean(losses)),
                     "cv_intact_balanced_accuracy": float(np.mean(intact_acc)),
                     "cv_outage_balanced_accuracy": float(np.mean(outage_acc))})
    selected = {}
    scaler = StandardScaler().fit(x)
    z = scaler.transform(x)
    for kind in ["temperature", "diagonal", "shared", "full"]:
        best = min((r for r in rows if r["kind"] == kind), key=lambda r: (r["objective"], r["alpha"]))
        selected[kind] = fit_gaussian(z, y, kind, best["alpha"], [0] if kind == "temperature" else None)
    selected_kind = min((r for r in rows if r["kind"] != "temperature"), key=lambda r: (r["objective"], r["alpha"]))["kind"]
    pd.DataFrame(rows).to_csv(ROOT / "results" / "development_cv.csv", index=False)
    return selected, selected_kind, scaler, rows


def resample_balanced_manova(y, observed, count, rng):
    b, k, p = y.shape
    fit = balanced_manova(y)
    simulations = {}
    for variant in ["gaussian_iid_null", "wild_restricted", "wild_full_residual"]:
        values = []
        for _ in range(count):
            if variant == "gaussian_iid_null":
                noise = rng.multivariate_normal(np.zeros(p), fit["E"] / fit["df_e"], size=(b, k))
            else:
                source = fit["null_residual"] if variant == "wild_restricted" else fit["residual"]
                # One sign per complete matched setting preserves its internal
                # three-condition and cross-outcome dependence.
                noise = rng.choice([-1., 1.], size=(b, 1, 1)) * source
                if variant == "wild_full_residual":
                    noise = noise * np.sqrt(b / (b - 1))
            sim = balanced_manova(fit["null_fitted"] + noise)
            values.append(sim["roy"])
        values = np.array(values)
        simulations[variant] = {"B": count, "roy_samples": values,
                                "critical_95": float(np.quantile(values, .95)),
                                "p_mc": float((1 + np.sum(values >= observed)) / (count + 1))}
    return simulations


def distribution_checks(groups, count, rng):
    results = []
    # The same finite-sample Gaussian reference applies to all 48-row groups
    # because Mardia statistics are affine-invariant.
    n, p = groups[0].shape
    reference = [mardia(rng.normal(size=(n, p))) for _ in range(count)]
    skew_ref = np.array([a["skewness"] for a in reference])
    kurt_ref = np.array([a["kurtosis"] for a in reference])
    center = np.median(kurt_ref)
    for cooler, x in zip(ORDER, groups):
        m = mardia(x)
        m["cooler"] = cooler
        m["skew_p_mc"] = float((1 + np.sum(skew_ref >= m["skewness"])) / (count + 1))
        m["kurtosis_p_mc"] = float((1 + np.sum(np.abs(kurt_ref - center) >= abs(m["kurtosis"] - center))) / (count + 1))
        m["univariate_skewness"] = stats.skew(x, axis=0, bias=False)
        m["univariate_excess_kurtosis"] = stats.kurtosis(x, axis=0, bias=False)
        m["shapiro_p_iid"] = [float(stats.shapiro(x[:, j]).pvalue) for j in range(p)]
        results.append(m)
    return {"groups": results, "B": count, "skew_reference": skew_ref,
            "kurtosis_reference": kurt_ref,
            "reference": "Finite-sample independent Gaussian simulations, n=48, p=6"}


def numeric_mle(x):
    """Independent numerical fit for an interpretable two-response example."""
    x = x[:, [0, 4]]
    mu = x.mean(axis=0)
    s = covariance(x, mle=True)
    sd = np.sqrt(np.diag(s))
    rho = s[0, 1] / np.prod(sd)
    analytic = np.r_[mu, np.log(sd), np.arctanh(rho)]
    def unpack(t):
        ss = np.exp(t[2:4]); r = np.tanh(t[4])
        return t[:2], np.array([[ss[0] ** 2, r * ss.prod()], [r * ss.prod(), ss[1] ** 2]])
    def objective(t):
        m, c = unpack(t)
        return -float(stats.multivariate_normal.logpdf(x, mean=m, cov=c).sum())
    def gradient(t):
        m, c = unpack(t)
        inverse = linalg.inv(c)
        difference = x - m
        scatter = difference.T @ difference
        g_cov = .5 * (len(x) * inverse - inverse @ scatter @ inverse)
        ss = np.exp(t[2:4]); r = np.tanh(t[4]); cross = ss.prod()
        derivatives = [np.array([[2 * ss[0] ** 2, r * cross], [r * cross, 0.]]),
                       np.array([[0., r * cross], [r * cross, 2 * ss[1] ** 2]]),
                       np.array([[0., (1 - r * r) * cross], [(1 - r * r) * cross, 0.]])]
        return np.r_[-inverse @ difference.sum(axis=0), [np.sum(g_cov * v) for v in derivatives]]
    initial = analytic + np.array([.05, -.05, .15, -.1, .1])
    fitted = optimize.minimize(objective, initial, jac=gradient, method="BFGS", options={"maxiter": 2000, "gtol": 1e-6})
    return {"features": [CORE[0], CORE[4]], "analytic_parameters": analytic,
            "numerical_parameters": fitted.x, "start_parameters": initial,
            "analytic_loglik": -objective(analytic), "numeric_loglik": -fitted.fun,
            "objective_gap": float(abs(fitted.fun - objective(analytic))),
            "max_parameter_gap": float(np.max(np.abs(fitted.x - analytic))),
            "optimizer_success": bool(fitted.success), "optimizer_message": str(fitted.message),
            "parameterization": "mu1,mu2,log(sd1),log(sd2),atanh(rho)"}


def partial_regression(profile, z):
    nuisance = pd.get_dummies(profile[["cooler", "valve", "pump", "accumulator"]].astype(str), drop_first=True, dtype=float)
    design = np.column_stack([np.ones(len(z)), nuisance.to_numpy()])
    residual = z - design @ np.linalg.lstsq(design, z, rcond=None)[0]
    raw = np.corrcoef(z.T)
    adjusted = np.corrcoef(residual.T)
    # Additive recorded-component associations in mean temperature. This is
    # an explanatory in-sample R2, separate from the diagnostic grouped CV.
    response = z[:, 0]
    fitted = design @ np.linalg.lstsq(design, response, rcond=None)[0]
    r2 = 1 - np.sum((response - fitted) ** 2) / np.sum((response - response.mean()) ** 2)
    coeff = np.linalg.lstsq(design, response, rcond=None)[0]
    return {"raw_correlation": raw, "adjusted_correlation": adjusted,
            "adjustment": ["cooler/phase", "valve", "pump", "accumulator"],
            "temperature_R2_in_sample": float(r2), "coefficients": coeff,
            "design_names": ["Intercept"] + nuisance.columns.tolist(),
            "residuals": residual,
            "interpretation": "Associations after additive adjustment; recorded fault labels are explanatory only, never diagnostic inputs"}


def run(resamples=999):
    started = time.perf_counter()
    rng = np.random.default_rng(SEED)
    for name in ["results", "figures", "reports", "dist"]:
        (ROOT / name).mkdir(exist_ok=True)
    d = pd.read_csv(ROOT / "data" / "cycle_features.csv") if (ROOT / "data" / "cycle_features.csv").exists() else extract()
    assert len(d) == 2205 and d[CORE].notna().all().all()
    stable = d[d.unstable == 0].copy()
    profile = stable.groupby(["setting", "cooler", "valve", "pump", "accumulator"], as_index=False)[CORE].mean()
    first_order = d.groupby("setting").cycle_id.min().sort_values().index.tolist()
    profile["setting_order"] = profile.setting.map({s: j for j, s in enumerate(first_order)})
    profile = profile.sort_values(["setting_order", "cooler"]).reset_index(drop=True)
    assert profile.shape[0] == 144
    profile.to_csv(ROOT / "data" / "matched_profiles.csv", index=False, float_format="%.12g")
    reference_scaler = StandardScaler().fit(profile[CORE])
    z = reference_scaler.transform(profile[CORE])
    groups = [z[profile.cooler == k] for k in ORDER]
    group_results = []
    for k, x in zip(ORDER, groups):
        raw = profile.loc[profile.cooler == k, CORE].to_numpy()
        s = covariance(x)
        group_results.append({"cooler": k, "label": LABELS[k], "n_profiles": len(x),
                              "n_stable_cycles": int((stable.cooler == k).sum()),
                              "mean_raw": raw.mean(axis=0), "sd_raw": raw.std(axis=0, ddof=1),
                              "mean_z": x.mean(axis=0), "covariance_z": s,
                              "covariance_raw": covariance(raw), "correlation": np.corrcoef(x.T),
                              "mle_covariance_z": covariance(x, mle=True),
                              "generalized_variance": float(np.exp(logdet(s))),
                              "log_generalized_variance": logdet(s),
                              "standardized_generalized_variance": float(np.exp(logdet(s) / 6)),
                              "condition_number": float(np.linalg.cond(s))})
    tensor = np.stack([np.stack([z[(profile.setting == setting) & (profile.cooler == k)][0] for k in ORDER])
                       for setting in first_order])
    man = balanced_manova(tensor)
    # An independent implementation provides all conventional MANOVA F references.
    block_dummies = pd.get_dummies(profile.setting, drop_first=True, dtype=float).to_numpy()
    cooler_dummies = np.column_stack([(profile.cooler == 20).astype(float), (profile.cooler == 3).astype(float)])
    design = np.column_stack([np.ones(len(profile)), block_dummies, cooler_dummies])
    contrast = np.zeros((2, design.shape[1])); contrast[:, -2:] = np.eye(2)
    oracle = MANOVA(z, design).mv_test([("Cooler", contrast)])
    oracle_table = oracle.results["Cooler"]["stat"]
    assert np.isclose(man["wilks"], oracle_table.loc["Wilks' lambda", "Value"], rtol=1e-8)
    infer = {k: v for k, v in man.items() if k not in ["residual", "null_residual", "null_fitted", "fitted"]}
    infer["conventional_reference"] = {str(idx): {str(col): clean(value) for col, value in row.items()}
                                         for idx, row in oracle_table.iterrows()}
    print("MANOVA and independent matrix check complete", flush=True)
    infer["resampling"] = resample_balanced_manova(tensor, man["roy"], resamples, rng)
    hotelling = []
    for a, b in [(0, 1), (0, 2), (1, 2)]:
        differences = tensor[:, b, :] - tensor[:, a, :]
        h = paired_hotelling(differences)
        h.update({"from": ORDER[a], "to": ORDER[b], "difference_rows": differences})
        for length in [1, 4, 8]:
            means = np.array([differences[circular_block_indices(48, length, rng)].mean(axis=0)
                              for _ in range(resamples)])
            h[f"bootstrap_length_{length}"] = {"lower": np.quantile(means, .025, axis=0),
                                                "upper": np.quantile(means, .975, axis=0),
                                                "temperature_mean_samples": means[:, 0]}
        flips = []
        for _ in range(resamples):
            flips.append(paired_hotelling(differences * rng.choice([-1., 1.], size=(48, 1)))["T2"])
        h["sign_flip_p"] = float((1 + np.sum(np.array(flips) >= h["T2"])) / (resamples + 1))
        hotelling.append(h)
    for h, p in zip(hotelling, holm_adjust([r["p_iid"] for r in hotelling])):
        h["p_holm_iid"] = float(p)
    covtest = {"box_m": box_m(groups), "gaussian_lrt": covariance_lrt(groups)}
    # Null simulation preserves dependence across the 3 matched conditions
    # through a shared within-setting normal component. It is an explicit
    # matched Gaussian sensitivity, not a distribution-free correction.
    shared_s = covtest["box_m"]["pooled_covariance"]
    box_reference = []
    for _ in range(resamples):
        common = rng.multivariate_normal(np.zeros(6), shared_s / 2, size=48)
        simulated = [common + rng.multivariate_normal(np.zeros(6), shared_s / 2, size=48) for _ in ORDER]
        box_reference.append(box_m(simulated)["M"])
    covtest["matched_gaussian_null"] = {"B": resamples, "shared_fraction": .5,
        "M_samples": box_reference,
        "p_mc": float((1 + np.sum(np.array(box_reference) >= covtest["box_m"]["M"])) / (resamples + 1))}
    print("Hotelling and covariance tests complete", flush=True)
    dist = distribution_checks(groups, resamples, rng)
    mle = numeric_mle(groups[0])
    partial = partial_regression(profile, z)
    dev, test, split = prepare_splits(stable)
    print("Selecting predictive covariance models on development settings only ...", flush=True)
    models, selected_kind, scaler, cv = select_models(dev)
    # Freeze all choices before evaluating this holdout.
    write_json(ROOT / "results" / "frozen_model_specification.json", {
        "features": CORE, "candidate_grid": cv, "selected_kind": selected_kind,
        "selection_objective": "Mean development log loss: intact and complete TS2 sensor outage, equally weighted",
        "model_alphas": {k: m["alpha"] for k, m in models.items()}, "split": split})
    results = {}
    test_z = scaler.transform(test[CORE].to_numpy())
    for kind, model in models.items():
        results[kind] = {"intact": metrics(test.cooler.to_numpy(), probability(model, test_z)),
                         "TS2_unavailable": metrics(test.cooler.to_numpy(), probability(model, test_z, [2, 3, 4, 5]))}
    selected = models[selected_kind]
    selected_prob = probability(selected, test_z)
    selected_outage = probability(selected, test_z, [2, 3, 4, 5])
    test_settings = sorted(test.setting.unique())
    block_rows = {s: np.flatnonzero(test.setting.to_numpy() == s) for s in test_settings}
    bootstrap_accuracy = {"intact": [], "TS2_unavailable": []}
    for _ in range(resamples):
        indices = np.concatenate([block_rows[s] for s in rng.choice(test_settings, len(test_settings))])
        for label, prob in [("intact", selected_prob), ("TS2_unavailable", selected_outage)]:
            bootstrap_accuracy[label].append(metrics(test.cooler.to_numpy()[indices], prob[indices])["balanced_accuracy"])
    confidence = {k: {"lower": float(np.quantile(v, .025)), "upper": float(np.quantile(v, .975)), "samples": v}
                  for k, v in bootstrap_accuracy.items()}
    # Transitional cycles are a separately named stress subset under the same
    # held-out settings. They never enter model selection.
    transition = d[(d.unstable == 1) & d.setting.isin(test_settings)]
    transition_result = metrics(transition.cooler.to_numpy(), probability(selected, scaler.transform(transition[CORE].to_numpy())))
    # Artificial offsets are a simulation, not additional measured data.
    offsets = []
    for offset in [-8., -4., 0., 4., 8.]:
        shifted = test[CORE].to_numpy().copy(); shifted[:, 0] += offset
        zz = scaler.transform(shifted)
        offsets.append({"temperature_offset_C": offset, **{
            k: metrics(test.cooler.to_numpy(), probability(m, zz))["balanced_accuracy"] for k, m in models.items()}})
    # Independent Gaussian density oracle, including a missing-coordinate case.
    maximum_score_error = 0.
    for mask in [list(range(6)), [2, 3, 4, 5], [0, 4]]:
        own = scores(selected, test_z[:10], mask)
        ref = np.column_stack([np.log(prior) + stats.multivariate_normal.logpdf(
            test_z[:10, mask], mean=mu[mask], cov=cov[np.ix_(mask, mask)])
            for mu, cov, prior in zip(selected["means"], selected["covariances"], selected["priors"])])
        maximum_score_error = max(maximum_score_error, float(np.max(np.abs(own - ref))))
    predictions = test[["cycle_id", "setting", "cooler"]].copy()
    predictions["predicted"] = np.array(ORDER)[selected_prob.argmax(axis=1)]
    predictions["predicted_without_TS2"] = np.array(ORDER)[selected_outage.argmax(axis=1)]
    for j, k in enumerate(ORDER):
        predictions[f"prob_{k}"] = selected_prob[:, j]
    predictions.to_csv(ROOT / "results" / "holdout_predictions.csv", index=False)
    # Detect strong temporal continuity without treating the abrupt cooler
    # phase changes as stationarity. Use contiguous stable-cycle pairs.
    lag_rows = []
    for k in ORDER:
        v = stable[stable.cooler == k]
        same = v.cycle_id.diff().to_numpy()[1:] == 1
        lag_rows.append({"cooler": k, "lag1_contiguous_temperature": float(np.corrcoef(
            v.TS2_mean.to_numpy()[:-1][same], v.TS2_mean.to_numpy()[1:][same])[0, 1])})
    result = {"seed": SEED, "feature_metadata": META, "class_order": ORDER,
        "class_labels": LABELS, "total_cycles": len(d), "stable_cycles": len(stable),
        "transition_cycles": int((d.unstable == 1).sum()), "matched_settings": 48,
        "profile_rows": 144, "stable_cycles_per_cell": stable.groupby(["setting", "cooler"]).size().describe().to_dict(),
        "reference_scale": {"mean": reference_scaler.mean_, "sd": reference_scaler.scale_},
        "group_summaries": group_results, "manova": infer, "hotelling": hotelling,
        "covariance_tests": covtest, "distribution_checks": dist, "numerical_MLE": mle,
        "partial_regression": partial, "predictive_results": results,
        "selected_model": selected_kind, "models": models,
        "prediction_scale": {"mean": scaler.mean_, "sd": scaler.scale_},
        "development_cv": cv, "split": split, "holdout_block_bootstrap": confidence,
        "transition_stress": transition_result, "offset_simulation": offsets,
        "contiguous_lag1": lag_rows, "density_oracle_max_error": maximum_score_error,
        "resamples": resamples,
        "assumptions": ["Cooler and recording phase are perfectly confounded.",
                        "Matched setting resampling assumes independent/exchangeable settings or the specified block sensitivity.",
                        "Classical p-values are iid Gaussian references, not causal evidence.",
                        "Model probabilities use a Gaussian working model; covariance regularization is considered only in development selection.",
                        "One experimental rig cannot establish performance on unseen machines."],
        "elapsed_seconds": time.perf_counter() - started,
        "python_version": platform.python_version()}
    write_json(ROOT / "results" / "analysis.json", result)
    print("Selected model:", selected_kind, "alpha", selected["alpha"], flush=True)
    print("Held-out settings:", len(test_settings), "cycles", len(test), flush=True)
    for k, v in results.items():
        print(k, "intact", round(v["intact"]["balanced_accuracy"], 4), "TS2 outage", round(v["TS2_unavailable"]["balanced_accuracy"], 4), flush=True)
    print("Analysis complete in", round(result["elapsed_seconds"], 1), "seconds", flush=True)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--resamples", type=int, default=999)
    args = parser.parse_args()
    run(args.resamples)
