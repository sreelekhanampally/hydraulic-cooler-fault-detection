# Data dictionary

`cycle_features.csv` has one row per original 60-second cycle. `cycle_id` is the 1-based source row; the order is never shuffled in the saved table.

| Column | Meaning |
| --- | --- |
| cooler | Source grade: 100 full efficiency, 20 reduced efficiency, 3 near failure |
| valve | Source valve condition code: 100, 90, 80 or 73 |
| pump | Source pump leakage code: 0, 1 or 2 |
| accumulator | Source pressure grade: 130, 115, 100 or 90 bar |
| unstable | 0 = stable conditions reached; 1 = not stable |
| setting | Valve_pump_accumulator identifier, such as 100_0_130 |
| *_mean | Arithmetic mean of every within-cycle reading |
| *_std | Sample standard deviation, divisor m−1 |
| *_slope | OLS slope against seconds, using every reading |
| *_early | Mean of the first 10 seconds |
| *_late | Mean of the last 10 seconds |

Only physical channels PS1–PS6, EPS1, FS1, FS2, TS1–TS4 and VS1 are summarized. CE, CP and SE are derived source channels and are not diagnostic inputs.

## Required diagnostic inputs

| Column | Unit | Source channel / summary |
| --- | --- | --- |
| TS2_mean | °C | Temperature sensor 2 mean |
| TS2_slope | °C/s | Temperature sensor 2 within-cycle trend |
| FS1_mean | L/min | Volume flow sensor 1 mean |
| PS2_std | bar | Pressure sensor 2 fluctuations |
| EPS1_mean | W | Motor electrical power mean |
| VS1_mean | mm/s | Vibration mean |

`sample_inputs.csv` contains six actual final holdout cycles, two per condition. Labels are deliberately omitted from this input example. Their original cycle IDs allow tracing back to the main feature table.

`matched_profiles.csv` averages stable core features inside each cooler × setting cell. It has 48 complete settings × 3 conditions = 144 rows. It is used for matched inference and descriptive profiles, not as the diagnostic cycle training table.

`trace_samples.json` stores downsampled real source traces for illustrative cycles. Trace plots are examples, not matched causal comparisons. The complete original matrices remain in `raw/hydraulic_original.zip`.

`split_manifest.json` saves the final diagnostic split. Development and test sets contain disjoint **settings** and all three conditions. The split does not establish independence between recording phases.

Source documentation (`description.txt`, `documentation.txt`) is copied from the original archive. Source details, credits and checksum are in `provenance.json`.
