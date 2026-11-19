"""Export the full student project, including original data and a SHA-256 manifest."""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
FOLDER = 'Hydraulic_Cooler_Statistics_Project'
DIRECTORIES = {'data', 'src', 'tests', 'figures', 'reports', 'dist', 'notebooks', 'results', 'R'}
FILES = {'README.md', 'START_HERE.html', 'MODEL_CARD.md', 'METHODS_MAP.md',
         'PRESENTATION_GUIDE.md', 'LICENSE', 'DATA_LICENSE.md', 'THIRD_PARTY_LICENSES.md',
         'requirements.txt', 'run_project.py', 'PROJECT_PLAN.md', 'run_project.R', 'R_README.md',
         'Hydraulic_Cooler_Statistics.Rproj'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT.parent/(FOLDER+'.zip'))
    args = parser.parse_args()
    output = args.output.resolve()
    if ROOT == output or ROOT in output.parents:
        parser.error('Write the ZIP outside the project folder to avoid recursive packaging')
    paths = []
    for path in ROOT.rglob('*'):
        if not path.is_file() or path.is_symlink(): continue
        rel = path.relative_to(ROOT)
        if any(part.startswith('.') or part == '__pycache__' for part in rel.parts): continue
        if path.suffix == '.pyc': continue
        if (len(rel.parts)==1 and rel.name in FILES) or rel.parts[0] in DIRECTORIES:
            paths.append(path)
    paths.sort()
    output.parent.mkdir(parents=True, exist_ok=True)
    manifest = []
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in paths:
            rel = path.relative_to(ROOT).as_posix()
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            manifest.append(f'{digest}  {rel}')
            archive.write(path, f'{FOLDER}/{rel}',
                          compress_type=zipfile.ZIP_STORED if path.suffix=='.zip' else zipfile.ZIP_DEFLATED)
        archive.writestr(f'{FOLDER}/MANIFEST_SHA256.txt', '\n'.join(manifest)+'\n')
    with zipfile.ZipFile(output) as archive:
        bad = archive.testzip()
        if bad: raise RuntimeError(f'ZIP CRC failure: {bad}')
    print(f'Complete ZIP: {output}')
    print(f'{len(paths)} project files + checksum manifest; {output.stat().st_size:,} bytes; CRC check passed')
    print('ZIP SHA-256:', hashlib.sha256(output.read_bytes()).hexdigest())


if __name__ == '__main__':
    main()
