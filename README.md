# Multivariate Statistical Diagnosis of Hydraulic Cooler Faults

The statistics and model training are implemented in **R**. The 14-slide presentation now shows the R results, with short explanations of the code.

## Run the R project

Extract the full ZIP, open **Hydraulic_Cooler_Statistics.Rproj** in RStudio, and run:

```r
source("R/setup.R")
source("run_project.R")
```

This reads the original data, applies all ten statistical methods, trains and tests the Gaussian models, creates R figures and runs the verification checks. Open **R/results/R_Analysis_Report.html** for the computed results.

To explain the code during your presentation, open **R/Presentation_Demo.R**. Its sections follow the slides and can be run one at a time with Ctrl + Enter.

See **[R_README.md](R_README.md)** for the full RStudio instructions, file map and prediction examples.

## Open the presentation

Open **START_HERE.html**, then select the interactive presentation. Use **Present** and the arrow keys. It has 14 slides, including the model test on slide 13 and conclusion on slide 14. The plots and model parameters come from the R workflow.

## What is included

- Native R source for all ten requested methods, grouped training, evaluation and prediction.
- An RStudio project, optional R Markdown walkthrough, RDS model and portable JSON model.
- The original UCI recordings, R-extracted feature table, output tables and sixteen R-generated figure pairs.
- Verification against independent R formulas, the saved presentation calculations and the browser model.
- The R-based presentation, updated research report and a short `R/Presentation_Demo.R` file to run alongside the slides.
- The original notebook and Python implementation retained as reference files.

No Python installation is needed for the R analysis. The two required R packages are `jsonlite` and `digest`; `R/setup.R` installs them if necessary.

The selected R model is shared-covariance Gaussian classification with alpha zero. All four models reproduce the final intact and TS2-outage confusion matrices shown in the presentation. The checks verify that the presentation contains the current R results and fitted models.

The study concerns one experimental rig. Cooler condition and recording phase coincide, so neither a tiny p-value nor a perfect stable holdout score establishes causation or guaranteed accuracy on future machines.

Data: Helwig, Pignanelli and Schütze, **Condition monitoring of hydraulic systems**, UCI dataset 447, DOI [10.24432/C5CW21](https://doi.org/10.24432/C5CW21), CC BY 4.0. Project code retains the MIT license; see LICENSE, DATA_LICENSE.md and THIRD_PARTY_LICENSES.md.
