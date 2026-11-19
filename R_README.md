# Statistics and model training in R

The statistics and model training run in R. The 14-slide presentation now uses these R results and fitted model parameters. Its layout and interactive controls are retained.

## Start in RStudio

1. Extract the entire project ZIP.
2. Open **Hydraulic_Cooler_Statistics.Rproj** in RStudio.
3. Run these commands in the Console:

```r
source("R/setup.R")     # install jsonlite and digest if needed
source("run_project.R") # extract, analyze, train, plot and check
```

The run creates the `hydraulic_results` object. The computed report is **R/results/R_Analysis_Report.html**. Open it in your browser or from RStudio's Files pane.

The first run reads the original sensor recordings. Allow a few minutes and about 1–2 GB of free memory. Later runs reuse the R-generated feature table. Once the two packages are installed, the bundled-data workflow works offline.

## What R does

| Method / task | Native R implementation |
| --- | --- |
| Original sensor preparation | `R/extract_features.R`: reads the ZIP, verifies SHA-256, computes cycle means, SDs, slopes and first/last 10-second means |
| Mean vectors | `colMeans()` and matched setting-condition averages |
| Covariance and correlation | Explicit sample scatter calculations, `cov()`, `cor()` and `cov2cor()` checks |
| Generalized variance | Cholesky log determinant, determinant and sixth-root determinant on one common scale |
| Distribution checks | Mardia skewness/kurtosis, bias-corrected marginal measures, `shapiro.test()`, Q-Q plots and R Monte Carlo references |
| Maximum likelihood | Analytical Gaussian estimation plus `optim(method="BFGS")` with an analytical gradient |
| MANOVA | Explicit H/E matrices and generalized roots, checked independently with `stats::manova()` and `summary()` |
| Hotelling T² | Paired six-feature differences, F reference, `p.adjust(method="holm")`, sign flips and block intervals |
| Covariance equality | Box M with correction and a separate Gaussian ML covariance likelihood ratio |
| Partial correlation / regression | `model.matrix()`, `lm.fit()` and residual correlations |
| Simulation and resampling | R Gaussian nulls, matched wild references, circular blocks, whole-setting holdout bootstrap and sensor-offset tests |
| Model training | Diagonal/shared/class-specific Gaussian candidates; grouped six-fold development cross-validation; train-only scaling |
| Prediction | R-trained model saved as RDS; exact Gaussian marginal when TS2 is unavailable |
| Visualizations | Sixteen new R-generated PNG/PDF figure pairs in `R/figures/` |
| Verification | Native R checks in `R/tests/run_tests.R`, including independent formulas and checks that the slides use the R results |

These scripts perform the calculations themselves. They do not call Python or load a Python-trained model for fitting. Original outputs and browser fixtures are read only after fitting, to verify compatibility.

## Inspect your results

```r
# After source("run_project.R"):
hydraulic_results$manova$conventional_reference
hydraulic_results$hotelling
hydraulic_results$covariance_tests
hydraulic_results$partial_regression$adjusted_correlation
hydraulic_results$development_cv
hydraulic_results$predictive_results
```

For saved results without recomputing:

```r
result <- readRDS("R/results/analysis_R.rds")
model <- readRDS("R/models/trained_gaussian_model.rds")
View(read.csv("R/results/development_cv_R.csv"))
View(read.csv("R/results/holdout_predictions_R.csv"))
```

## Predict a new CSV in R

```r
source("R/statistics_core.R")
source("R/predict.R")
model <- readRDS("R/models/trained_gaussian_model.rds")
x <- read.csv("data/sample_inputs.csv")

predict_frame_R(model, x)
predict_frame_R(model, x, without_temperature = TRUE)
```

The six inputs use the original units: TS2 mean in °C, TS2 slope in °C/s, FS1 mean in L/min, PS2 SD in bar, EPS1 mean in W and VS1 mean in mm/s. Removing TS2 removes both temperature coordinates; the other four are still required. Invalid observed inputs are rejected.

From a terminal:

```bash
Rscript run_project.R
Rscript run_project.R --extract
Rscript run_project.R --tests-only
Rscript R/predict.R data/sample_inputs.csv --output=predictions.csv
Rscript R/predict.R data/sample_inputs.csv --without-temperature --output=outage_predictions.csv
```

`--extract` re-reads all original sensor matrices even if the R feature table exists. The default uses 999 simulation/resampling draws. For a deliberately shorter exploratory run you can use `--resamples=199`; its Monte Carlo results have coarser resolution and are not the supplied final results.

## The final model

The R workflow independently selects **shared covariance with alpha = 0**. It is fitted on 1,089 stable development cycles from 36 settings. The final test set contains 360 stable cycles from 12 different settings.

| Model | Intact balanced accuracy | TS2 unavailable balanced accuracy |
| --- | ---: | ---: |
| Temperature only | 100% | 33.33% |
| Diagonal covariance | 100% | 99.44% |
| Shared covariance | 100% | 100% |
| Separate covariances | 100% | 99.72% |

All final confusion matrices are exported from R to the presentation. The browser predictions are checked against a new set of R-generated prediction cases.

The separate transition evaluation contains 266 cycles: ordinary accuracy is 87.22%, balanced accuracy is 94.89%. These cycles are never used for fitting or selection.

## How the displayed results are reproduced

- **Simulation:** the slides, R report and tables use the same saved 999-draw R simulations. A rerun with a different draw count can change Monte Carlo p-values and intervals.
- **MANOVA:** the slides use native `summary.manova()` test references. An alternative Hotelling-Lawley approximation is retained in the source for comparison with the original implementation.
- **Training:** R uses the saved development/test settings and its own deterministic six-fold allocation. The final shared-covariance model and test confusion matrices are computed in R.
- **Slide export:** `R/export_presentation.R` writes the results, all four fitted models and their R-generated prediction checks. The browser displays the results and evaluates edited readings using these saved parameters.

## Explain the R code during the presentation

Open **R/Presentation_Demo.R** in RStudio. Select a few lines and press Ctrl + Enter to run them. Start with the mean vector, covariance and correlation. Later sections reproduce MANOVA, the paired test, covariance checks and the final model predictions. A complete executed example is saved in **R/results/Presentation_Demo_output.txt**.

Use **R/PRESENTATION_CODE_MAP.md** to find the section matching each slide. The main analysis is still `source("run_project.R")`; the shorter file is for showing the main calculations in class.

## Main files

| File | Use |
| --- | --- |
| `run_project.R` | One-command entry point |
| `R/Presentation_Demo.R` | Short, commented calculations in slide order |
| `R/export_presentation.R` | Export the R results and trained parameters to the slides |
| `R/statistics_core.R` | Main matrix formulas and Gaussian classifier |
| `R/inference.R` | MLE, MANOVA reference, distribution checks and resampling |
| `R/training.R` | Grouped model selection, freezing, fitting and evaluation |
| `R/predict.R` | Data-frame and CSV prediction |
| `R/Walkthrough.Rmd` | Optional annotated R Markdown notebook with formulas |
| `R/results/analysis_R.rds` | Complete native R results |
| `R/results/analysis_R.json` | Portable numerical results |
| `R/models/trained_gaussian_model.rds` | Selected fitted R model with scaler and labels |
| `R/models/trained_gaussian_model.json` | Portable model; its coordinate indices are explicitly zero-based |
| `R/results/QA_R.json` | Passed checks and checks of the R results used by the slides |
| `R/results/sessionInfo.txt` | Exact R and package versions used |

Native R objects use one-based feature indices. The JSON model uses zero-based indices for compatibility with browser code. The predictor uses the RDS model, so users do not need to convert indices.

To knit the optional notebook in RStudio, install `rmarkdown` and `knitr` first. They are not needed for the main workflow or the generated R report.

## Scientific scope

The experiment uses one rig. Cooler condition and recording phase coincide. Matching measured settings and holding out complete settings do not remove this confounding or establish performance on a new machine. The Gaussian probabilities are working-model probabilities, not guaranteed physical confidence. A perfect empirical bootstrap interval is not proof of zero future error.

The existing Python reference files remain in the archive for continuity. **Use the R project for the statistics and training submission; Python is not required for this workflow.** The browser presentation uses JavaScript for display and interaction, with the same model behaviour verified against the R fit.

Source: Helwig, Pignanelli and Schütze, UCI 447, [DOI 10.24432/C5CW21](https://doi.org/10.24432/C5CW21), CC BY 4.0. R references: [summary.manova](https://search.r-project.org/R/refmans/stats/html/summary.manova.html), [optim](https://stat.ethz.ch/R-manual/R-patched/library/stats/html/optim.html).
