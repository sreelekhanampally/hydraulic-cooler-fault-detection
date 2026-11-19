# Run in RStudio: source('run_project.R')
# Or from a terminal: Rscript run_project.R [--extract] [--tests-only]
source_file <- tryCatch(sys.frame(1)$ofile,error=function(e)NULL)
file_argument <- grep('^--file=',commandArgs(FALSE),value=TRUE)
if(!is.null(source_file)) {
  project_root <- dirname(normalizePath(source_file,mustWork=TRUE))
} else if(length(file_argument)) {
  project_root <- dirname(normalizePath(sub('^--file=','',file_argument[1]),mustWork=TRUE))
} else {
  project_root <- normalizePath(getwd(),mustWork=TRUE)
}
source(file.path(project_root,'R/run_project.R'))
hydraulic_results <- run_project_R(project_root,if(length(file_argument))commandArgs(TRUE) else character())
