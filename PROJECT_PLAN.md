# Hydraulic Fault Statistics Lab

## Objective
Diagnose recorded cooler condition (100, 20, 3) from physical sensor summaries.
Explain all ten requested multivariate methods with actual computations and figures.

## Scientific decisions fixed before final holdout evaluation
- Unit: a full 60-second cycle. Primary inference uses stable cycle means within
  48 matched nuisance settings crossed with the three cooler levels.
- Raw sensors only. CE, CP, SE, cycle IDs and true component condition labels are
  excluded from diagnostic features.
- Six domain-selected core summaries: TS2 mean and slope, FS1 mean, PS2 standard
  deviation, EPS1 mean, VS1 mean. Auxiliary extraction remains available.
- Cooler occupies three long phases. Associations cannot identify a causal
  cooler effect separately from unmeasured long-term rig drift.
- Predictive evaluation holds out whole nuisance settings across all cooler
  levels. Tune solely in development settings. Preserve original order for
  dependence diagnostics. No claim of a prospective fleet evaluation.
- Inferential references under independent multivariate normal sampling are
  separated from matched-setting bootstrap sensitivity analyses.
- Required methods: mean vector; covariance and correlation; generalized
  variance; skewness, kurtosis and distribution checks; ML estimation; MANOVA;
  Hotelling T2; covariance equality; partial correlation/regression; simulation
  and resampling.

## Deliverables
- Reproducible source, verified real data, dependency and source provenance.
- Interactive browser prototype with mathematical walkthroughs and offline use.
- Scientific PDF report, annotated R walkthrough and presentation guide.
- Tests, independent numerical cross-checks and a QA record.
- One final project ZIP with instructions.

## Review checkpoints
1. Audit data layout, missingness, labels, stability, temporal ordering.
2. Check each test formula independently and respect its assumptions.
3. Evaluate single-sensor baselines before claiming multivariate improvement.
4. Freeze predictive choices before opening the held-out settings.
5. Check browser computations against the R-trained model and test every main interaction.
6. Render report pages, inspect labels and equations, then package and save.
