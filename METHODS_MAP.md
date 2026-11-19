# Where each statistical method is used in R

| Method | R implementation | Slide | Why it is used |
| --- | --- | --- | --- |
| Mean vector | `colMeans()` in `R/analyze.R` | 3 | Describe the typical six-feature condition profile. |
| Covariance and correlation | `R/statistics_core.R`, `cov()`, `cor()` | 4 | Show variability and relationships between readings. |
| Generalized variance | `logdet_spd()` and `det(S)^(1/6)` | 5 | Compare joint spread on one common scale. |
| Distribution checks | `mardia_statistics()`, `R/inference.R` | 6 | Check the Gaussian approximation within each condition. |
| Maximum likelihood | `numerical_mle_R()`, `fit_gaussian()` | 7 | Estimate the means and covariance used by the classifier. |
| MANOVA | `balanced_manova()`, checked with `stats::manova()` | 8 | Test the six mean readings jointly after matching settings. |
| Hotelling T2 | `paired_hotelling()`, `p.adjust()` | 9 | Compare the three planned pairs using matched differences. |
| Covariance equality | `box_m()`, `covariance_lrt()` | 10 | Check changes in joint variability between conditions. |
| Partial correlation | `model.matrix()`, `lm.fit()`, `cor()` | 11 | Describe relationships after adjusting for recorded groups. |
| Simulation and resampling | `R/inference.R`, `R/training.R` | 12 | Check reference results and observed prediction uncertainty. |
| Training and prediction | `R/training.R`, `R/predict.R` | 12-13 | Fit only on training settings and test on separate settings. |

For a shorter explanation and runnable examples, use `R/Presentation_Demo.R`. For the exact formulas and full checks, open `R/statistics_core.R` and `R/inference.R`.

The sample covariance uses n - 1; Gaussian maximum-likelihood covariance uses n. A small test p-value describes a difference under its assumptions. Prediction accuracy is measured separately. Matching the recorded settings does not separate cooler condition from recording phase.
