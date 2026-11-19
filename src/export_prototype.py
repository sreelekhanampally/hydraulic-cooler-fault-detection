"""Prepare self-contained browser data and Python/JavaScript oracle cases."""
import json
import shutil
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.special import softmax
from analyze import clean, probability, scores
from extract_features import ROOT, CORE


def main():
    r = json.loads((ROOT / "results/analysis.json").read_text())
    d = pd.read_csv(ROOT / "data/cycle_features.csv")
    bundle = {"features": CORE, "class_order": r["class_order"],
              "class_labels": r["class_labels"], "scale": r["prediction_scale"],
              "selected_kind": r["selected_model"], "model": r["models"][r["selected_model"]],
              "scope": r["split"]["interpretation"]}
    (ROOT / "results/diagnostic_model.json").write_text(json.dumps(bundle, indent=2), encoding="utf-8")
    holdout = d[d.cycle_id.isin(r["split"]["test_cycles"])]
    sample = holdout.groupby("cooler", sort=False).head(2)
    sample[["cycle_id"] + CORE].to_csv(ROOT / "data/sample_inputs.csv", index=False)
    profiles = pd.read_csv(ROOT / "data/matched_profiles.csv")
    development = set(r["split"]["development_settings"])
    holdout = set(r["split"]["test_settings"])
    cycles = []
    for row in d.itertuples(index=False):
        cycles.append({"id": row.cycle_id, "cooler": row.cooler, "setting": row.setting,
                       "valve": row.valve, "pump": row.pump, "accumulator": row.accumulator,
                       "stable": row.unstable == 0, "split": "holdout" if row.setting in holdout else "development",
                       "values": [getattr(row, k) for k in CORE]})
    profile_rows = [{"setting": row.setting, "cooler": row.cooler,
                     "values": [getattr(row, k) for k in CORE]} for row in profiles.itertuples(index=False)]
    data = {"analysis": r, "cycles": cycles, "profiles": profile_rows,
            "traces": json.loads((ROOT / "data/trace_samples.json").read_text()),
            "provenance": json.loads((ROOT / "data/provenance.json").read_text())}
    target = ROOT / "dist/lab-data.js"
    target.write_text("window.LAB_DATA = " + json.dumps(clean(data), separators=(",", ":"), allow_nan=False) + ";\n")
    # Cross-language cases cover real stable/transition cycles and all models.
    indices = sorted(set(np.linspace(0, len(d) - 1, 17, dtype=int).tolist() + [732, 1464]))
    x = d.iloc[indices][CORE].to_numpy()
    scale = r["prediction_scale"]
    z = (x - np.array(scale["mean"])) / np.array(scale["sd"])
    cases = []
    for name, m in r["models"].items():
        model = {**m, "means": np.array(m["means"]), "covariances": np.array(m["covariances"]), "priors": np.array(m["priors"])}
        for available in [list(range(6)), [2, 3, 4, 5], [0, 4], []]:
            expected_scores = scores(model, z, available)
            expected_probs = softmax(expected_scores, axis=1)
            for i, raw in enumerate(x):
                cases.append({"model": name, "raw": raw.tolist(), "available": available,
                              "scores": expected_scores[i].tolist(), "probabilities": expected_probs[i].tolist()})
    (ROOT / "tests/js_oracle.json").write_text(json.dumps({"models": r["models"], "scale": scale, "cases": cases}))
    assets = ROOT / "dist/figures"; assets.mkdir(exist_ok=True)
    for path in (ROOT / "figures").glob("*.png"):
        shutil.copy2(path, assets / path.name)
    print("Browser data:", target.stat().st_size, "bytes;", len(cases), "cross-language cases")


if __name__ == "__main__":
    main()
