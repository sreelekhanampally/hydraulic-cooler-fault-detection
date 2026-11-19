# Run once in RStudio: source('R/setup.R')
# The complete analysis uses base R plus these two small data/verification packages.
required_packages <- c('jsonlite','digest')
missing_packages <- required_packages[!vapply(required_packages,requireNamespace,logical(1),quietly=TRUE)]
if(length(missing_packages))install.packages(missing_packages,repos='https://cloud.r-project.org')
stopifnot(all(vapply(required_packages,requireNamespace,logical(1),quietly=TRUE)))
cat('Ready: R',as.character(getRversion()),'with jsonlite and digest.\n')
