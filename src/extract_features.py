"""Download, verify, and summarize the original UCI 447 sensor recordings.

One row is one 60-second operating cycle. Derived efficiency channels CE, CP,
SE are intentionally excluded from diagnostic predictors.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
from urllib.request import urlopen
import zipfile

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
URL = "https://archive.ics.uci.edu/static/public/447/condition+monitoring+of+hydraulic+systems.zip"
SHA256 = "24128aad2ee45eea7e6b63ebbd9992cdf25d0483a2cebefbfc13bc69079af1f2"
SENSORS = {
    **{f"PS{i}": (100, "bar") for i in range(1, 7)},
    **{f"TS{i}": (1, "deg C") for i in range(1, 5)},
    "FS1": (10, "L/min"), "FS2": (10, "L/min"),
    "EPS1": (100, "W"), "VS1": (1, "mm/s"),
}
CORE = ["TS2_mean", "TS2_slope", "FS1_mean", "PS2_std", "EPS1_mean", "VS1_mean"]
LABELS = {100: "Full efficiency", 20: "Reduced efficiency", 3: "Near failure"}


def extract(force: bool = False) -> pd.DataFrame:
    raw = ROOT / "data" / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    archive = raw / "hydraulic_original.zip"
    if not archive.exists():
        print("Downloading original UCI archive ...", flush=True)
        with urlopen(URL, timeout=120) as response, archive.open("wb") as handle:
            while chunk := response.read(1024 * 1024):
                handle.write(chunk)
    actual_hash = hashlib.sha256(archive.read_bytes()).hexdigest()
    if actual_hash != SHA256:
        raise ValueError("Source archive checksum changed. Inspect the source before proceeding.")
    target = ROOT / "data" / "cycle_features.csv"
    if target.exists() and not force:
        return pd.read_csv(target)
    with zipfile.ZipFile(archive) as z:
        profile = pd.read_csv(io.BytesIO(z.read("profile.txt")), sep="\t", header=None,
                              names=["cooler", "valve", "pump", "accumulator", "unstable"])
        if profile.shape != (2205, 5):
            raise ValueError(f"Unexpected profile shape: {profile.shape}")
        profile.insert(0, "cycle_id", np.arange(1, len(profile) + 1))
        profile["condition"] = profile["cooler"].map(LABELS)
        profile["setting"] = profile[["valve", "pump", "accumulator"]].astype(str).agg("_".join, axis=1)
        summaries = {}
        trace_samples = {}
        for name, (hz, unit) in SENSORS.items():
            a = np.loadtxt(io.BytesIO(z.read(name + ".txt")), dtype=np.float64)
            if a.shape != (2205, hz * 60) or not np.isfinite(a).all():
                raise ValueError(f"Invalid sensor matrix {name}: {a.shape}")
            t = np.arange(a.shape[1], dtype=float) / hz
            centered = t - t.mean()
            summaries[name + "_mean"] = a.mean(axis=1)
            summaries[name + "_std"] = a.std(axis=1, ddof=1)
            summaries[name + "_slope"] = (a @ centered) / (centered @ centered)
            summaries[name + "_early"] = a[:, :hz * 10].mean(axis=1)
            summaries[name + "_late"] = a[:, -hz * 10:].mean(axis=1)
            # Compact original traces for a small, balanced demonstration set.
            examples = []
            for cooler in [100, 20, 3]:
                eligible = profile.index[(profile.cooler == cooler) & (profile.unstable == 0)]
                idx = eligible[len(eligible) // 2]
                step = max(1, hz)
                examples.append({"cycle_id": int(idx + 1), "cooler": cooler,
                                 "time": t[::step].round(3).tolist(),
                                 "value": a[idx, ::step].round(6).tolist()})
            trace_samples[name] = {"unit": unit, "examples": examples}
            print(f"Extracted {name}: {a.shape}", flush=True)
        out = pd.concat([profile, pd.DataFrame(summaries)], axis=1)
        out.to_csv(target, index=False, float_format="%.12g")
        (ROOT / "data" / "trace_samples.json").write_text(json.dumps(trace_samples, indent=2))
        for filename in ["description.txt", "documentation.txt"]:
            # Latin-1 preserves the original degree and accented characters.
            (ROOT / "data" / filename).write_text(z.read(filename).decode("latin-1"), encoding="utf-8")
    manifest = {"source_url": URL, "doi": "10.24432/C5CW21", "sha256": actual_hash,
                "archive_bytes": archive.stat().st_size, "cycles": len(out),
                "cycle_seconds": 60, "physical_sensor_count": len(SENSORS),
                "excluded_virtual_channels": ["CE", "CP", "SE"], "core_features": CORE,
                "license": "CC BY 4.0", "accessed": "2026-11-15",
                "creators": "Nikolai Helwig, Eliseo Pignanelli, Andreas Schuetze"}
    (ROOT / "data" / "provenance.json").write_text(json.dumps(manifest, indent=2))
    return out


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    frame = extract(args.force)
    print(f"Ready: {frame.shape[0]} cycles and {frame.shape[1]} columns")
