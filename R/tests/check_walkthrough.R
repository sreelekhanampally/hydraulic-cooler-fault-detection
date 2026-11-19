# Check every statistical notebook chunk with base R. Knitr display options are
# skipped here; knitting the optional document still uses knitr/rmarkdown.
check_walkthrough_R <- function(root) {
  root<-normalizePath(root,mustWork=TRUE)
  path<-file.path(root,'R/Walkthrough.Rmd');lines<-readLines(path,warn=FALSE)
  starts<-grep('^```\\{r',lines);env<-new.env(parent=globalenv());status<-list()
  previous<-getwd();on.exit(setwd(previous));setwd(file.path(root,'R'))
  for(i in seq_along(starts)) {
    start<-starts[i];after<-which(seq_along(lines)>start&lines=='```')[1L]
    code<-lines[(start+1L):(after-1L)]
    code<-code[!grepl('knitr::opts_chunk',code,fixed=TRUE)]
    result<-tryCatch({capture.output(eval(parse(text=code),envir=env));TRUE},error=function(e)conditionMessage(e))
    status[[i]]<-data.frame(chunk=lines[start],passed=isTRUE(result),detail=if(isTRUE(result))'' else result)
  }
  out<-do.call(rbind,status)
  write.csv(out,file.path(root,'R/results/walkthrough_checks_R.csv'),row.names=FALSE)
  if(!all(out$passed))stop('Notebook code check failed: ',paste(out$detail[!out$passed],collapse='; '))
  cat('Executed',nrow(out),'R Markdown code chunks successfully.\n')
  invisible(out)
}
