"""Batch diagnosis with the saved, development-only Gaussian model.

python src/predict.py data/sample_inputs.csv --output predictions.csv
python src/predict.py data/sample_inputs.csv --without-temperature
No fitting or network access occurs here. Raw feature units are required.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.special import softmax
from statistics_core import marginal_scores

ROOT = Path(__file__).resolve().parents[1]


def predict_frame(frame, model_path=None, without_temperature=False):
    model_path = Path(model_path) if model_path else ROOT / 'results/diagnostic_model.json'
    bundle = json.loads(model_path.read_text(encoding='utf-8'))
    features = bundle['features']
    available = [2, 3, 4, 5] if without_temperature else list(range(6))
    required = [features[i] for i in available]
    missing = [c for c in required if c not in frame.columns]
    if missing:
        raise ValueError('Missing required feature columns: ' + ', '.join(missing))
    if frame.empty:
        raise ValueError('Input CSV has no data rows')
    observed = frame[required].apply(pd.to_numeric, errors='coerce').to_numpy()
    if not np.isfinite(observed).all():
        raise ValueError('Observed features must be finite numbers; check blanks and text')
    scale = bundle['scale']
    z = np.zeros((len(frame), 6), dtype=float)
    # Only observed coordinates enter the marginal density. Unobserved zeros
    # below are placeholders and are never treated as sensor measurements.
    z[:, available] = (observed - np.array(scale['mean'])[available]) / np.array(scale['sd'])[available]
    m = bundle['model']
    log_scores = marginal_scores(z, np.array(m['means']), np.array(m['covariances']),
                                 np.array(m['priors']), available)
    probs = softmax(log_scores, axis=1)
    order = np.array(bundle['class_order'])
    predicted = order[probs.argmax(axis=1)]
    out = pd.DataFrame(index=frame.index)
    if 'cycle_id' in frame:
        out['cycle_id'] = frame['cycle_id']
    out['predicted_cooler'] = predicted
    out['predicted_condition'] = [bundle['class_labels'][str(k)] for k in predicted]
    for i, k in enumerate(order):
        out[f'probability_{k}'] = probs[:, i]
        out[f'log_score_{k}'] = log_scores[:, i]
    out['observed_coordinates'] = len(available)
    out['scenario'] = 'TS2 unavailable' if without_temperature else 'intact'
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input_csv', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--without-temperature', action='store_true')
    parser.add_argument('--model', type=Path)
    args = parser.parse_args()
    try:
        result = predict_frame(pd.read_csv(args.input_csv), args.model, args.without_temperature)
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(2, f'Cannot predict: {exc}\n')
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        result.to_csv(args.output, index=False)
        print(f'Saved {len(result)} predictions to {args.output}')
    else:
        print(result.to_csv(index=False), end='')


if __name__ == '__main__':
    main()
