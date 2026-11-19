"""Independent mathematical oracles and invariance checks."""
import sys
from pathlib import Path
import unittest
import numpy as np
from scipy import linalg, stats
from statsmodels.multivariate.manova import MANOVA
from statsmodels.stats.multitest import multipletests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from statistics_core import (balanced_manova, box_m, covariance, covariance_lrt,
    gaussian_log_scores, holm_adjust, mardia, marginal_scores, paired_hotelling,
    circular_block_indices)


class StatisticalTests(unittest.TestCase):
    def setUp(self):
        self.rng = np.random.default_rng(314159)
        a = self.rng.normal(size=(6, 6))
        self.sigma = a @ a.T + np.eye(6)
        self.x = self.rng.multivariate_normal(np.arange(6), self.sigma, size=80)

    def test_unbiased_covariance_oracle(self):
        np.testing.assert_allclose(covariance(self.x), np.cov(self.x, rowvar=False))

    def test_mle_covariance_oracle(self):
        np.testing.assert_allclose(covariance(self.x, mle=True), np.cov(self.x, rowvar=False, bias=True))

    def test_mle_denominator_relation(self):
        np.testing.assert_allclose(covariance(self.x, True), 79/80 * covariance(self.x))

    def test_balanced_manova_against_ols_projection(self):
        y = self.rng.normal(size=(48, 3, 6)) + np.arange(3)[None, :, None] / 3
        out = balanced_manova(y)
        rows = y.reshape(-1, 6)
        b = np.repeat(np.eye(48), 3, axis=0)
        c = np.tile(np.eye(3)[:, 1:], (48, 1))
        full = np.column_stack([b, c])
        e0 = rows - b @ np.linalg.lstsq(b, rows, rcond=None)[0]
        e1 = rows - full @ np.linalg.lstsq(full, rows, rcond=None)[0]
        np.testing.assert_allclose(out["E"], e1.T @ e1, atol=1e-10)
        np.testing.assert_allclose(out["H"], e0.T @ e0 - e1.T @ e1, atol=1e-10)
        contrasts = np.zeros((2, 50)); contrasts[:, -2:] = np.eye(2)
        oracle = MANOVA(rows, full).mv_test([("cooler", contrasts)]).results["cooler"]["stat"]
        for key, row in [("wilks", "Wilks' lambda"), ("pillai", "Pillai's trace"),
                         ("roy", "Roy's greatest root"), ("hotelling_lawley", "Hotelling-Lawley trace")]:
            self.assertAlmostEqual(out[key], oracle.loc[row, "Value"], places=10)

    def test_manova_affine_invariance(self):
        y = self.rng.normal(size=(48, 3, 6))
        transform = self.rng.normal(size=(6, 6)) + 5 * np.eye(6)
        a, b = balanced_manova(y), balanced_manova(y @ transform)
        for key in ["roy", "wilks", "pillai", "hotelling_lawley"]:
            self.assertAlmostEqual(a[key], b[key], places=11)

    def test_hotelling_reduces_to_t_squared(self):
        d = self.x[:, :1]
        out = paired_hotelling(d)
        oracle = stats.ttest_1samp(d[:, 0], 0)
        self.assertAlmostEqual(out["T2"], oracle.statistic ** 2)
        self.assertAlmostEqual(out["p_iid"], oracle.pvalue)

    def test_hotelling_affine_invariance(self):
        a = self.rng.normal(size=(6, 6)) + 5 * np.eye(6)
        self.assertAlmostEqual(paired_hotelling(self.x)["T2"], paired_hotelling(self.x @ a)["T2"], places=9)

    def test_gaussian_density_scipy_oracle(self):
        means = np.stack([self.x.mean(axis=0), self.x.mean(axis=0) + 1])
        covs = np.stack([self.sigma, self.sigma * 2])
        priors = np.array([.3, .7])
        ours = gaussian_log_scores(self.x, means, covs, priors)
        expected = np.column_stack([np.log(priors[k]) + stats.multivariate_normal.logpdf(self.x, means[k], covs[k]) for k in range(2)])
        np.testing.assert_allclose(ours, expected, atol=1e-10)

    def test_dropout_marginals_and_reordering(self):
        means = np.stack([self.x.mean(axis=0)] * 3)
        covs = np.stack([self.sigma] * 3)
        priors = np.array([.2, .3, .5])
        for observed in [[0, 2, 5], [5, 2, 0], [3], list(range(6))]:
            out = marginal_scores(self.x, means, covs, priors, observed)
            oracle = np.column_stack([np.log(p) + stats.multivariate_normal.logpdf(
                self.x[:, observed], means[k, observed], covs[k][np.ix_(observed, observed)]) for k, p in enumerate(priors)])
            np.testing.assert_allclose(out, oracle, atol=1e-10)

    def test_no_observations_returns_prior(self):
        priors = np.array([.2, .3, .5])
        scores = marginal_scores(self.x, np.zeros((3, 6)), np.stack([self.sigma]*3), priors, [])
        np.testing.assert_allclose(scores, np.tile(np.log(priors), (len(self.x), 1)))

    def test_covariance_lrt_likelihood_oracle(self):
        groups = [self.x[:40], self.x[40:] * 1.3]
        out = covariance_lrt(groups)
        covs = [np.cov(x, rowvar=False, bias=True) for x in groups]
        pooled = sum(len(x)*s for x,s in zip(groups,covs)) / 80
        alt = sum(stats.multivariate_normal.logpdf(x, x.mean(axis=0), s).sum() for x,s in zip(groups,covs))
        null = sum(stats.multivariate_normal.logpdf(x, x.mean(axis=0), pooled).sum() for x in groups)
        self.assertAlmostEqual(out["LR"], 2*(alt-null), places=9)

    def test_box_m_weights_and_degrees(self):
        groups = [self.x[:25], self.x[25:50] * 1.2, self.x[50:]]
        out = box_m(groups)
        dfs = np.array([len(x)-1 for x in groups])
        covs = [np.cov(x, rowvar=False) for x in groups]
        pooled = sum(n*s for n,s in zip(dfs,covs))/dfs.sum()
        expected = dfs.sum()*np.log(np.linalg.eigvalsh(pooled)).sum() - sum(n*np.log(np.linalg.eigvalsh(s)).sum() for n,s in zip(dfs,covs))
        self.assertAlmostEqual(out["M"], expected, places=8)
        self.assertEqual(out["df"], 42)

    def test_mardia_whitening_oracle(self):
        out = mardia(self.x)
        d = self.x - self.x.mean(axis=0)
        l = linalg.cholesky(np.cov(self.x, rowvar=False, bias=True), lower=True)
        w = linalg.solve_triangular(l, d.T, lower=True).T
        gram = w @ w.T
        self.assertAlmostEqual(out["skewness"], np.mean(gram**3), places=10)
        self.assertAlmostEqual(out["kurtosis"], np.mean(np.sum(w*w, axis=1)**2), places=10)

    def test_mardia_affine_invariance(self):
        a = self.rng.normal(size=(6, 6)) + 5*np.eye(6)
        before, after = mardia(self.x), mardia(self.x @ a + 17)
        self.assertAlmostEqual(before["skewness"], after["skewness"], places=9)
        self.assertAlmostEqual(before["kurtosis"], after["kurtosis"], places=9)

    def test_holm_oracle_and_ties(self):
        ps = [.01, .03, .03, .8, .001]
        np.testing.assert_allclose(holm_adjust(ps), multipletests(ps, method="holm")[1])

    def test_generalized_variance_scaling(self):
        s = covariance(self.x)
        a = np.diag([2, 3, 4, 5, 6, 7])
        ratio = np.linalg.det(a @ s @ a.T) / np.linalg.det(s)
        self.assertAlmostEqual(ratio / np.linalg.det(a)**2, 1, places=10)

    def test_block_indices_bounds(self):
        for n in [1, 48]:
            for length in [1, 4, 8, 60]:
                indices = circular_block_indices(n, length, self.rng)
                self.assertEqual(len(indices), n)
                self.assertTrue(np.all((indices>=0)&(indices<n)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
