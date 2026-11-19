# Diagnostic model card

**Task:** classify the recorded cooler grade (100 full efficiency, 20 reduced efficiency, 3 near failure) from a 60-second hydraulic cycle. This is a course research prototype.

**Data:** UCI 447, one laboratory rig, 2,205 cycles. Primary fitting/evaluation uses the 1,449 source-labelled stable cycles. The 756 remaining cycles are kept separately. Cooler condition forms three consecutive recording phases.

**Inputs:** TS2 mean (°C), TS2 OLS slope (°C/s), FS1 mean (L/min), PS2 sample SD (bar), EPS1 mean (W), VS1 mean (mm/s). Derived CE/CP/SE efficiency channels are excluded. Labels, cycle order and component settings never enter the diagnostic score.

**Development:** 36 valve × pump × accumulator settings, 1,089 stable cycles. Six-fold grouped development selection evaluates covariance types diagonal/shared/full and alpha in {0, .0001, .001, .01, .05, .1}. The prespecified criterion is average intact/TS2-outage log loss. Scalers are fitted inside each fold and then on all development data for the final model.

**Selected fit:** Gaussian class means and ML shared covariance; alpha = 0. Empirical development class priors. Fitted in R and saved in `R/models/trained_gaussian_model.rds`. The JSON export supplies the same numerical parameters to the browser.

**Final holdout:** 12 disjoint settings, 360 stable cycles, 120 per grade. Selected model ordinary and balanced accuracy are 100% with all inputs and 100% after removing both TS2 coordinates. Temperature baseline is 100% intact and 33.33% balanced accuracy without TS2. This comparison demonstrates fallback, not a gain in intact accuracy.

**Transition stress set:** 266 nonstable cycles from those 12 held-out settings. Selected-model ordinary accuracy 87.22%, balanced accuracy 94.89%. This is a distinct, more difficult distribution, not part of final fitting or selection.

**Missing input:** the live prototype supports arbitrary coordinate masks; complete TS2 failure removes its mean and slope together. A Gaussian marginal is evaluated on the observed mean subvector and covariance submatrix. With no coordinates, scores equal class log priors. The batch CLI supports intact or complete-TS2-outage modes.

**Uncertainty:** probabilities are conditional on a Gaussian working model. Within-group normality diagnostics show departures. Very small or large probabilities may be overconfident. A setting bootstrap of an all-correct holdout necessarily gives [1,1]; this is not a valid guarantee of perfect future performance. The optional one-sided 22.1% iid-setting failure bound uses a different estimand and a strong independent-setting assumption.

**Main limitation:** cooler condition is perfectly confounded with recording phase. Holding out settings controls configuration overlap but does not produce a new rig, new campaign, or random cooler assignment. Inference is about recorded cooler/phase-associated profiles. No causal cooling effect or deployment performance is established.

**Other limits:** source labels describe rig states, not remaining useful life. Repeated adjacent cycles are dependent. Matched averaging and clustered resampling retain important structure but cannot prove independence or eliminate drift. The model has no out-of-distribution rejection rule. New input units, sensor calibration or machine regime may invalidate the score.

**Next study:** collect repeated, randomized cooler campaigns across several rigs, preserve chronological recording IDs, validate on unseen rig/campaign combinations, assess probability calibration and a reject option, then examine fault detection costs. The current data cannot supply that external validation.
