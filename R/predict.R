# Use the R-trained model on a CSV or a data.frame. No fitting occurs here.
predict_frame_R <- function(bundle,newdata,without_temperature=FALSE) {
  available <- if(without_temperature)3:6 else 1:6
  required <- bundle$features[available]
  missing <- setdiff(required,names(newdata))
  if(length(missing))stop('Missing required columns: ',paste(missing,collapse=', '))
  if(!nrow(newdata))stop('The input has no data rows')
  observed <- as.matrix(data.frame(lapply(newdata[,required,drop=FALSE],function(x){if(is.factor(x))x<-as.character(x);suppressWarnings(as.numeric(x))})))
  if(any(!is.finite(observed)))stop('Available readings must be finite numbers')
  z <- matrix(0,nrow(newdata),length(bundle$features))
  z[,available] <- sweep(sweep(observed,2L,bundle$scale$mean[available],'-'),2L,bundle$scale$sd[available],'/')
  scores <- score_model(bundle$model,z,available);prob <- softmax(scores)
  labels <- bundle$class_order[max.col(prob,ties.method='first')]
  out <- data.frame(predicted_cooler=labels,predicted_condition=unname(bundle$class_labels[as.character(labels)]))
  if('cycle_id'%in%names(newdata))out <- cbind(cycle_id=newdata$cycle_id,out)
  for(j in seq_along(bundle$class_order)) {
    out[[paste0('probability_',bundle$class_order[j])]] <- prob[,j]
    out[[paste0('log_score_',bundle$class_order[j])]] <- scores[,j]
  }
  out$observed_coordinates <- length(available)
  out$scenario <- if(without_temperature)'TS2 unavailable' else 'intact'
  out
}

if(sys.nframe()==0L) {
  file_arg <- grep('^--file=',commandArgs(FALSE),value=TRUE)
  script <- normalizePath(sub('^--file=','',file_arg[1L]),mustWork=TRUE)
  root <- dirname(dirname(script));source(file.path(root,'R/statistics_core.R'))
  args <- commandArgs(TRUE)
  if(!length(args))stop('Usage: Rscript R/predict.R input.csv [--without-temperature] [--output=predictions.csv]')
  without <- '--without-temperature'%in%args
  output <- grep('^--output=',args,value=TRUE)
  model <- readRDS(file.path(root,'R/models/trained_gaussian_model.rds'))
  predictions <- predict_frame_R(model,read.csv(args[1L],stringsAsFactors=FALSE),without)
  if(length(output)) {
    path <- sub('^--output=','',output[1L]);dir.create(dirname(path),recursive=TRUE,showWarnings=FALSE)
    write.csv(predictions,path,row.names=FALSE);cat('Saved',nrow(predictions),'predictions to',path,'\n')
  } else write.csv(predictions,stdout(),row.names=FALSE)
}
