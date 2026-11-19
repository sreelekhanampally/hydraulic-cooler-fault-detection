"""Reproduce the supplied project from the bundled original archive.

python run_project.py                 # complete analysis, figures and documents
python run_project.py --extract       # also re-read every original sensor file
python run_project.py --tests-only    # verify the supplied results
"""
from __future__ import annotations
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--extract', action='store_true')
    p.add_argument('--tests-only', action='store_true')
    p.add_argument('--resamples', type=int, default=999)
    args = p.parse_args()
    if args.resamples < 99:
        p.error('Use at least 99 resamples. Supplied results use 999.')
    env = os.environ.copy()
    env.setdefault('OPENBLAS_NUM_THREADS', '1')
    env.setdefault('OMP_NUM_THREADS', '1')

    def run(*command):
        print('\nRunning ' + ' '.join(str(x) for x in command), flush=True)
        subprocess.run(list(map(str, command)), cwd=ROOT, env=env, check=True)

    if not args.tests_only:
        if args.extract:
            run(sys.executable, 'src/extract_features.py', '--force')
        run(sys.executable, 'src/analyze.py', '--resamples', args.resamples)
        run(sys.executable, 'src/make_figures.py')
        run(sys.executable, 'src/export_prototype.py')
        run(sys.executable, 'src/build_report.py')
        run(sys.executable, 'src/build_notebook.py')
    run(sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v')
    if shutil.which('node'):
        run('node', 'tests/test_browser_math.js')
    else:
        print('Node.js unavailable: Python checks complete; JavaScript cross-language checks skipped.')
    print('\nComplete. Open START_HERE.html for the offline prototype and report.')


if __name__ == '__main__':
    main()
