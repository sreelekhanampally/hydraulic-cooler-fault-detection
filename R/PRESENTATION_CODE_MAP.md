# R code to open beside the slides

Open `R/Presentation_Demo.R` after opening the RStudio project. Its numbered comments identify the sections below. Select a few lines and press Ctrl + Enter to show their output.

| Slide | Demo section | What to explain |
| --- | --- | --- |
| 1. Objective | Introduction | Predict the recorded cooler condition from several readings. |
| 2. Data | 1 | Read the tables; keep stable cycles and match the settings. |
| 3. Mean vector | 2 | `colMeans()` gives one average for each feature. |
| 4. Covariance and correlation | 3 | `cov()` keeps the units; `cor()` uses a scale from -1 to +1. |
| 5. Generalized variance | 4 | The covariance determinant describes joint spread on a common scale. |
| 6. Distribution checks | 5 | Check joint skewness and kurtosis; compare with the R simulations. |
| 7. Maximum likelihood | 6 | Estimate the centre and spread; check the formula with `optim()`. |
| 8. MANOVA | 7 | Test all six mean readings together, allowing for each setting. |
| 9. Hotelling T2 | 8 | Subtract matched profiles and compare each pair. |
| 10. Covariance equality | 9 | Check whether the three covariance matrices are equal. |
| 11. Partial correlation | 10 | Correlate what remains after the recorded groups are allowed for. |
| 12. Simulation and model testing | 11-12 | Inspect the repeated checks; fit on training data and test separately. |
| 13. Try the model | 12-13 | Show the prediction, change a reading, and remove TS2. |
| 14. Conclusion | 14 | Explain the useful result and the one-rig limitation. |

The full workflow is `source("run_project.R")`. The browser uses the saved R-trained model for its interactive demonstration. It does not start an R session when a slider is changed.
