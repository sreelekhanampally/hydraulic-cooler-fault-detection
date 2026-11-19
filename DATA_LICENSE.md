# Dataset license and attribution

**Condition monitoring of hydraulic systems**, UCI Machine Learning Repository, dataset 447.

Creators: **Nikolai Helwig, Eliseo Pignanelli and Andreas Schütze**.

Dataset DOI: https://doi.org/10.24432/C5CW21

Source: https://archive.ics.uci.edu/dataset/447/condition+monitoring+of+hydraulic+systems

License stated by the repository: **Creative Commons Attribution 4.0 International (CC BY 4.0)**.
License text: https://creativecommons.org/licenses/by/4.0/legalcode

The original archive is included unchanged as `data/raw/hydraulic_original.zip`.
Its exact SHA-256 is `24128aad2ee45eea7e6b63ebbd9992cdf25d0483a2cebefbfc13bc69079af1f2`.

Changes made in this project: physical sensor readings are summarized per 60-second
cycle into means, sample standard deviations, OLS slopes, and first/last 10-second means.
Stable cycles are also averaged within recorded setting-by-condition cells. Figures,
tables and statistical outputs are derived from these transformations. Illustrative
source traces are downsampled to 1 Hz. Simulated null distributions, missing-sensor
experiments and input offsets are explicitly labelled as simulations.

The original data creators do not endorse the derived model or this project.

Original data paper: Helwig, N., Pignanelli, E., & Schütze, A. (2015).
*Condition Monitoring of a Complex Hydraulic System Using Multivariate Statistics*.
IEEE International Instrumentation and Measurement Technology Conference (I2MTC).
https://doi.org/10.1109/I2MTC.2015.7151267
