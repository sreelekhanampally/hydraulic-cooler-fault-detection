# Main workflow function; the root-level run_project.R is the entry point.
run_project_R <- function(root,args=character()) {
  root<-normalizePath(root,mustWork=TRUE)
  if(getRversion()<'4.2.0')stop('Please use R 4.2 or later')
  required<-c('jsonlite','digest')
  missing<-required[!vapply(required,requireNamespace,logical(1),quietly=TRUE)]
  if(length(missing))stop('Install the required packages first: source("R/setup.R")')
  known<-args%in%c('--extract','--tests-only')|grepl('^--resamples=',args)
  if(any(!known))stop('Unknown options: ',paste(args[!known],collapse=', '))
  value<-grep('^--resamples=',args,value=TRUE)
  resamples<-if(length(value))as.integer(sub('^--resamples=','',value[1])) else 999L
  if(!is.finite(resamples)||resamples<99L)stop('Use at least 99 resamples; supplied final results use 999')
  env<-new.env(parent=globalenv())
  for(file in c('statistics_core.R','extract_features.R','inference.R','training.R','predict.R',
               'analyze.R','make_figures.R','make_report.R','export_presentation.R','tests/run_tests.R'))
    source(file.path(root,'R',file),local=env)
  if('--tests-only'%in%args) {
    r<-readRDS(file.path(root,'R/results/analysis_R.rds'))
  } else {
    r<-env$analyze_project_R(root,resamples,force_extract='--extract'%in%args)
    env$make_figures_R(root,r)
  }
  env$export_presentation_R(root,r)
  qa<-env$run_tests_R(root,r)
  env$make_report_R(root,r,qa)
  cat('\nComplete. R results: R/results/analysis_R.rds\n')
  cat('Trained model: R/models/trained_gaussian_model.rds\n')
  cat('Read R/results/R_Analysis_Report.html for the computed R report.\n')
  cat('The slides now display these R results and R-trained models.\n')
  invisible(r)
}
