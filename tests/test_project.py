"""Integrity and independence checks on the actual exported project."""
import hashlib
import json
from pathlib import Path
import sys
import unittest
import numpy as np
import pandas as pd
from scipy import stats
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from analyze import fit_gaussian, metrics, probability
from statistics_core import gaussian_log_scores
from extract_features import ROOT, CORE, SHA256


class ProjectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = json.loads((ROOT / "results/analysis.json").read_text())
        cls.d = pd.read_csv(ROOT / "data/cycle_features.csv")

    def test_original_source_checksum(self):
        p = ROOT / "data/raw/hydraulic_original.zip"
        if not p.exists(): self.skipTest("Raw source archive not present in this copy")
        self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(), SHA256)

    def test_feature_integrity_and_units(self):
        self.assertEqual(len(self.d), 2205)
        self.assertTrue(np.isfinite(self.d[CORE]).all().all())
        self.assertEqual((self.d.unstable==0).sum(), 1449)
        for col in ['PS2_std', 'FS1_mean', 'EPS1_mean', 'VS1_mean']:
            self.assertTrue((self.d[col]>0).all())

    def test_no_nuisance_setting_leakage(self):
        split = self.r['split']
        self.assertFalse(set(split['development_settings']) & set(split['test_settings']))
        self.assertEqual(len(split['development_settings']),36)
        self.assertEqual(len(split['test_settings']),12)
        self.assertFalse(set(split['development_cycles']) & set(split['test_cycles']))

    def test_holdout_balance_and_profile_matching(self):
        test = self.d[self.d.cycle_id.isin(self.r['split']['test_cycles'])]
        self.assertEqual(len(test),360)
        self.assertEqual(test.groupby('setting').cooler.nunique().min(),3)
        p = pd.read_csv(ROOT / 'data/matched_profiles.csv')
        self.assertEqual(len(p),144)
        self.assertEqual(p.groupby('cooler').size().tolist(),[48,48,48])

    def test_scaler_fits_development_only(self):
        dev = self.d[self.d.cycle_id.isin(self.r['split']['development_cycles'])]
        np.testing.assert_allclose(dev[CORE].mean().to_numpy(),self.r['prediction_scale']['mean'],rtol=1e-10)
        np.testing.assert_allclose(dev[CORE].std(ddof=0).to_numpy(),self.r['prediction_scale']['sd'],rtol=1e-10)

    def test_saved_models_reconstruct_from_development(self):
        dev = self.d[self.d.cycle_id.isin(self.r['split']['development_cycles'])]
        scale=self.r['prediction_scale'];z=(dev[CORE].to_numpy()-scale['mean'])/scale['sd']
        for name,m in self.r['models'].items():
            fitted=fit_gaussian(z,dev.cooler.to_numpy(),name,m['alpha'],m['feature_indices'])
            np.testing.assert_allclose(fitted['means'],m['means'],atol=1e-10)
            np.testing.assert_allclose(fitted['covariances'],m['covariances'],atol=1e-10)

    def test_heldout_metrics_reproduce(self):
        test=self.d[self.d.cycle_id.isin(self.r['split']['test_cycles'])]
        scale=self.r['prediction_scale'];z=(test[CORE].to_numpy()-scale['mean'])/scale['sd']
        for name,m in self.r['models'].items():
            m={**m,'means':np.array(m['means']),'covariances':np.array(m['covariances']),'priors':np.array(m['priors'])}
            for scenario,observed in [('intact',list(range(6))),('TS2_unavailable',[2,3,4,5])]:
                actual=metrics(test.cooler.to_numpy(),probability(m,z,observed))
                stored=self.r['predictive_results'][name][scenario]
                np.testing.assert_array_equal(actual['confusion'],stored['confusion'])
                self.assertAlmostEqual(actual['log_loss'],stored['log_loss'],places=11)

    def test_numerical_mle_agrees(self):
        m=self.r['numerical_MLE']
        self.assertTrue(m['optimizer_success'])
        self.assertLess(m['max_parameter_gap'],1e-6)
        self.assertLess(m['objective_gap'],1e-7)

    def test_monte_carlo_p_resolution(self):
        for sim in self.r['manova']['resampling'].values():
            self.assertGreaterEqual(sim['p_mc'],1/(sim['B']+1))
            self.assertLessEqual(sim['p_mc'],1)

    def test_gaussian_oracle_error(self):
        self.assertLess(self.r['density_oracle_max_error'],1e-7)

    def test_input_feature_safeguards(self):
        self.assertFalse(any(x in CORE for x in ['CE','CP','SE','cooler','cycle_id','valve','pump','accumulator']))
        self.assertEqual(CORE[:2],['TS2_mean','TS2_slope'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
