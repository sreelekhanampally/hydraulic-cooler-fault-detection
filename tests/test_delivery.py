"""Check the interfaces and files a student receives in the complete ZIP."""
import json
from html.parser import HTMLParser
from pathlib import Path
import re
import subprocess
import sys
import unittest
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from predict import predict_frame


class Links(HTMLParser):
    def __init__(self):
        super().__init__(); self.paths = []
    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key in ['src', 'href'] and value and not value.startswith(('#', 'http', 'data:')):
                self.paths.append(value.split('#')[0])


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.sample = pd.read_csv(ROOT / 'data/sample_inputs.csv')

    def test_batch_prediction_traceability(self):
        expected = pd.read_csv(ROOT / 'data/cycle_features.csv').set_index('cycle_id')
        for outage in [False, True]:
            actual = predict_frame(self.sample, without_temperature=outage)
            np.testing.assert_array_equal(actual.predicted_cooler, expected.loc[self.sample.cycle_id].cooler)
            probs = actual[[f'probability_{k}' for k in [100,20,3]]]
            np.testing.assert_allclose(probs.sum(axis=1), 1)

    def test_truly_absent_temperature_columns(self):
        reduced = self.sample.drop(columns=['TS2_mean', 'TS2_slope'])
        full = predict_frame(self.sample, without_temperature=True)
        absent = predict_frame(reduced, without_temperature=True)
        pd.testing.assert_frame_equal(full, absent)
        with self.assertRaisesRegex(ValueError, 'Missing required'):
            predict_frame(reduced)

    def test_bad_batch_input_rejected(self):
        for value in [np.nan, np.inf, 'not a number']:
            broken = self.sample.astype(object).copy(); broken.loc[0, 'FS1_mean'] = value
            with self.assertRaisesRegex(ValueError, 'finite'):
                predict_frame(broken)
        with self.assertRaisesRegex(ValueError, 'no data'):
            predict_frame(self.sample.iloc[:0])

    def test_cli_runs_from_another_directory(self):
        run = subprocess.run([sys.executable, str(ROOT/'src/predict.py'),
                              str(ROOT/'data/sample_inputs.csv'), '--without-temperature'],
                             cwd=ROOT.parent, capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn('predicted_cooler', run.stdout)
        self.assertEqual(len(run.stdout.strip().splitlines()), len(self.sample)+1)

    def test_model_export_agrees_with_full_results(self):
        b=json.loads((ROOT/'results/diagnostic_model.json').read_text())
        r=json.loads((ROOT/'results/analysis.json').read_text())
        self.assertEqual(b['model'], r['models'][r['selected_model']])
        self.assertEqual(b['scale'], r['prediction_scale'])

    def test_local_html_links_and_scripts_exist(self):
        for name in ['START_HERE.html','dist/index.html']:
            p=ROOT/name;parser=Links();parser.feed(p.read_text())
            for path in parser.paths:
                self.assertTrue((p.parent/path).is_file(), f'{name}: missing {path}')

    def test_offline_math_fonts_exist(self):
        css=ROOT/'dist/vendor/katex.min.css'
        paths=re.findall(r'url\(([^)]+)\)',css.read_text())
        self.assertEqual(len(paths),20)
        for path in paths:self.assertTrue((css.parent/path).is_file())

    def test_all_exported_figures(self):
        self.assertEqual(len(list((ROOT/'figures').glob('*.png'))),16)
        self.assertEqual(len(list((ROOT/'figures').glob('*.pdf'))),16)
        for p in (ROOT/'figures').glob('*.png'):
            self.assertEqual(p.read_bytes(),(ROOT/'dist/figures'/p.name).read_bytes())

    def test_report_is_built_and_copied(self):
        p=ROOT/'reports/Hydraulic_Statistics_Report.pdf'
        self.assertTrue(p.read_bytes().startswith(b'%PDF-'))
        self.assertGreater(p.stat().st_size, 100000)
        self.assertEqual(p.read_bytes(),(ROOT/'dist/reports'/p.name).read_bytes())

    def test_notebook_contains_executed_outputs(self):
        n=json.loads((ROOT/'notebooks/Hydraulic_Statistics_Walkthrough.ipynb').read_text())
        code=[c for c in n['cells'] if c['cell_type']=='code']
        self.assertEqual(len(code),14)
        for i,cell in enumerate(code,1):
            source=''.join(cell['source'])
            compile(source, f'cell-{i}', 'exec')
            self.assertEqual(cell['execution_count'],i)
            self.assertTrue(cell['outputs'])
            self.assertFalse(any(o['output_type']=='error' for o in cell['outputs']))


if __name__ == '__main__':
    unittest.main(verbosity=2)
