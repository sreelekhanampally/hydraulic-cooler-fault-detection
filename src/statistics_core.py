"""Transparent multivariate calculations used by the report and prototype.

These functions separate unbiased sample covariance from Gaussian MLE
covariance and deliberately do not regularize inferential test statistics.
"""
from __future__ import annotations
import numpy as np
from scipy import linalg, stats


def covariance(x, mle=False):
    x = np.asarray(x, dtype=float)
    d = x - x.mean(axis=0)
    return d.T @ d / (len(x) if mle else len(x) - 1)


def logdet(a):
    sign, value = np.linalg.slogdet(a)
    if sign <= 0:
        raise ValueError("A positive-definite covariance is required")
    return float(value)


def manova_roots(h, e):
    roots = linalg.eigvalsh((h + h.T) / 2, (e + e.T) / 2)
    roots = np.maximum(roots, 0)
    return {"roots": roots[::-1],
            "roy": float(roots[-1]),
            "wilks": float(np.prod(1 / (1 + roots))),
            "pillai": float(np.sum(roots / (1 + roots))),
            "hotelling_lawley": float(roots.sum())}


def balanced_manova(y):
    """y: matched setting x cooler condition x response (48 x 3 x p).

    This is an additive fixed-block MANOVA. Cooler-by-setting interaction and
    profile estimation noise remain in the residual, since there is one
    aggregated profile in every cell.
    """
    y = np.asarray(y, dtype=float)
    b, k, p = y.shape
    setting = y.mean(axis=1, keepdims=True)
    condition = y.mean(axis=0, keepdims=True)
    grand = y.mean(axis=(0, 1), keepdims=True)
    fitted = setting + condition - grand
    residual = y - fitted
    delta = (condition - grand).reshape(k, p)
    h = b * delta.T @ delta
    e = residual.reshape(-1, p).T @ residual.reshape(-1, p)
    return {**manova_roots(h, e), "H": h, "E": e,
            "residual": residual, "null_residual": y - setting,
            "null_fitted": setting, "fitted": fitted,
            "df_h": k - 1, "df_e": (b - 1) * (k - 1),
            "settings": b, "responses": p}


def paired_hotelling(d):
    """One-sample T2 on matched profile differences; iid normal reference."""
    d = np.asarray(d, dtype=float)
    n, p = d.shape
    mu = d.mean(axis=0)
    s = covariance(d)
    t2 = float(n * mu @ linalg.solve(s, mu, assume_a="pos"))
    f = (n - p) * t2 / (p * (n - 1))
    return {"n": n, "p": p, "mean_difference": mu, "covariance": s,
            "T2": t2, "F": float(f), "df1": p, "df2": n - p,
            "p_iid": float(stats.f.sf(f, p, n - p)),
            "critical_T2_95": float(p * (n - 1) / (n - p) * stats.f.ppf(.95, p, n - p))}


def box_m(groups):
    """Box M with its conventional first-order chi-square correction."""
    groups = [np.asarray(x, dtype=float) for x in groups]
    ns = np.array([len(x) for x in groups])
    k, p = len(groups), groups[0].shape[1]
    dfs = ns - 1
    ss = [covariance(x) for x in groups]
    pooled = sum(df * s for df, s in zip(dfs, ss)) / dfs.sum()
    m = float(dfs.sum() * logdet(pooled) - sum(df * logdet(s) for df, s in zip(dfs, ss)))
    correction = float((np.sum(1 / dfs) - 1 / dfs.sum()) *
                       (2 * p * p + 3 * p - 1) / (6 * (p + 1) * (k - 1)))
    corrected = (1 - correction) * m
    df = (k - 1) * p * (p + 1) // 2
    return {"M": m, "correction": correction, "chi2": corrected, "df": df,
            "p_iid": float(stats.chi2.sf(corrected, df)), "pooled_covariance": pooled,
            "covariances": ss, "counts": ns}


def covariance_lrt(groups):
    """Gaussian unrestricted-vs-common covariance LRT, with ML divisors n_k."""
    ns = [len(x) for x in groups]
    covs = [covariance(x, mle=True) for x in groups]
    pooled = sum(n * s for n, s in zip(ns, covs)) / sum(ns)
    lr = float(sum(ns) * logdet(pooled) - sum(n * logdet(s) for n, s in zip(ns, covs)))
    p, k = groups[0].shape[1], len(groups)
    df = (k - 1) * p * (p + 1) // 2
    return {"LR": lr, "df": df, "p_iid": float(stats.chi2.sf(lr, df))}


def mardia(x):
    x = np.asarray(x, dtype=float)
    n, p = x.shape
    d = x - x.mean(axis=0)
    s = covariance(x, mle=True)
    gram = d @ linalg.solve(s, d.T, assume_a="pos")
    skew = float(np.mean(gram ** 3))
    kurt = float(np.mean(np.diag(gram) ** 2))
    skew_stat = n * skew / 6
    skew_df = p * (p + 1) * (p + 2) // 6
    z = (kurt - p * (p + 2)) / np.sqrt(8 * p * (p + 2) / n)
    return {"n": n, "p": p, "skewness": skew, "kurtosis": kurt,
            "normal_kurtosis": p * (p + 2), "skew_chi2": skew_stat,
            "skew_df": skew_df, "skew_p_asymptotic": float(stats.chi2.sf(skew_stat, skew_df)),
            "kurtosis_z": float(z), "kurtosis_p_asymptotic": float(2 * stats.norm.sf(abs(z)))}


def gaussian_log_scores(x, means, covs, priors):
    x = np.atleast_2d(x).astype(float)
    out = []
    for mu, s, prior in zip(means, covs, priors):
        d = x - mu
        quadratic = np.sum(d * linalg.solve(s, d.T, assume_a="pos").T, axis=1)
        out.append(np.log(prior) - .5 * (x.shape[1] * np.log(2 * np.pi) + logdet(s) + quadratic))
    return np.column_stack(out)


def marginal_scores(x, means, covs, priors, observed):
    observed = np.asarray(observed, dtype=int)
    x = np.atleast_2d(x)
    if not len(observed):
        return np.tile(np.log(priors), (len(x), 1))
    return gaussian_log_scores(x[:, observed], means[:, observed],
                               covs[:, observed][:, :, observed], priors)


def holm_adjust(pvalues):
    pvalues = np.asarray(pvalues, dtype=float)
    order = np.argsort(pvalues)
    adjusted_sorted = np.minimum(1, np.maximum.accumulate(pvalues[order] * np.arange(len(order), 0, -1)))
    adjusted = np.empty_like(pvalues)
    adjusted[order] = adjusted_sorted
    return adjusted


def circular_block_indices(n, length, rng):
    starts = rng.integers(0, n, size=int(np.ceil(n / length)))
    return ((starts[:, None] + np.arange(length)) % n).ravel()[:n]
