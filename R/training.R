# Grouped model selection and evaluation. Test settings never enter fitting or tuning.
make_grouped_folds_R <- function(development,nfold=6L) {
  settings <- sort(unique(development$setting))
  counts <- as.numeric(table(factor(development$setting,levels=settings)))
  # Greedy balancing by setting size; lexicographic ties are resolved deterministically.
  order_groups <- order(-counts,-seq_along(settings))
  loads <- numeric(nfold);assignment <- integer(length(settings))
  for (j in order_groups) {
    fold <- which.min(loads);assignment[j] <- fold;loads[fold] <- loads[fold]+counts[j]
  }
  data.frame(setting=settings,fold=assignment,cycles=counts,stringsAsFactors=FALSE)
}

select_models_R <- function(development,root) {
  x <- as.matrix(development[,CORE]);y <- development$cooler
  plan <- make_grouped_folds_R(development)
  write.csv(plan,file.path(root,'R/results/development_fold_plan_R.csv'),row.names=FALSE)
  candidates <- expand.grid(alpha=c(0,.0001,.001,.01,.05,.1),kind=c('diagonal','shared','full'),stringsAsFactors=FALSE)
  candidates <- rbind(candidates,data.frame(alpha=0,kind='temperature'))
  rows <- vector('list',nrow(candidates))
  for (j in seq_len(nrow(candidates))) {
    kind <- candidates$kind[j];alpha <- candidates$alpha[j]
    indices <- if(kind=='temperature') 1L else seq_along(CORE)
    losses <- intact_ba <- outage_ba <- numeric(6L)
    for (fold in 1:6) {
      validation <- development$setting%in%plan$setting[plan$fold==fold]
      train <- !validation
      scale <- fit_scaler(x[train,,drop=FALSE])
      z_train <- apply_scaler(x[train,,drop=FALSE],scale)
      z_valid <- apply_scaler(x[validation,,drop=FALSE],scale)
      m <- fit_gaussian(z_train,y[train],kind,alpha,indices)
      intact <- classification_metrics(y[validation],predict_gaussian(m,z_valid))
      outage <- classification_metrics(y[validation],predict_gaussian(m,z_valid,3:6))
      losses[fold] <- (intact$log_loss+outage$log_loss)/2
      intact_ba[fold] <- intact$balanced_accuracy;outage_ba[fold] <- outage$balanced_accuracy
    }
    rows[[j]] <- data.frame(kind=kind,alpha=alpha,objective=mean(losses),
      cv_intact_balanced_accuracy=mean(intact_ba),cv_outage_balanced_accuracy=mean(outage_ba))
  }
  cv <- do.call(rbind,rows)
  scale <- fit_scaler(x);z <- apply_scaler(x,scale);models <- list()
  for (kind in c('temperature','diagonal','shared','full')) {
    subset <- cv[cv$kind==kind,];best <- subset[order(subset$objective,subset$alpha),][1,]
    models[[kind]] <- fit_gaussian(z,y,kind,best$alpha,if(kind=='temperature')1L else seq_along(CORE))
  }
  joint <- cv[cv$kind!='temperature',];selected <- joint[order(joint$objective,joint$alpha),]$kind[1]
  write.csv(cv,file.path(root,'R/results/development_cv_R.csv'),row.names=FALSE)
  list(models=models,selected_kind=selected,scale=scale,cv=cv,fold_plan=plan)
}

portable_model_R <- function(model) {
  # Browser-compatible JSON uses zero-based feature indices; native R RDS uses one-based.
  model$feature_indices <- model$feature_indices-1L
  model
}

train_and_evaluate_R <- function(d,split,root,resamples) {
  development <- d[d$unstable==0 & d$setting%in%split$development_settings,]
  test <- d[d$unstable==0 & d$setting%in%split$test_settings,]
  stopifnot(nrow(development)==1089L,nrow(test)==360L,
    !any(development$setting%in%test$setting),length(unique(development$setting))==36L,
    length(unique(test$setting))==12L)
  message('R training: grouped development selection (19 covariance candidates x 6 folds)')
  chosen <- select_models_R(development,root)
  frozen <- list(features=CORE,selected_kind=chosen$selected_kind,
    selection_objective='Mean development log loss, equally weighted intact and complete TS2 outage',
    candidate_grid=chosen$cv,fold_plan=chosen$fold_plan,
    model_alphas=lapply(chosen$models,function(m)m$alpha),
    development_settings=split$development_settings,test_settings=split$test_settings)
  # This specification is saved before any final test metrics are computed.
  jsonlite::write_json(frozen,file.path(root,'R/results/frozen_model_specification_R.json'),
                       auto_unbox=TRUE,pretty=TRUE,digits=16)
  selected <- chosen$models[[chosen$selected_kind]]
  bundle <- list(features=CORE,units=FEATURE_UNITS,class_order=CLASS_ORDER,class_labels=LABELS,
                 scale=chosen$scale,selected_kind=chosen$selected_kind,model=selected,
                 scope='Unseen component settings within one rig; cooler and recording phase coincide')
  saveRDS(bundle,file.path(root,'R/models/trained_gaussian_model.rds'))
  saveRDS(chosen$models,file.path(root,'R/models/all_candidate_families.rds'))
  portable <- bundle;portable$model <- portable_model_R(selected)
  portable$class_labels <- as.list(LABELS)
  jsonlite::write_json(portable,file.path(root,'R/models/trained_gaussian_model.json'),
                       auto_unbox=TRUE,pretty=TRUE,digits=16,matrix='rowmajor')
  ztest <- apply_scaler(test[,CORE],chosen$scale)
  results <- lapply(chosen$models,function(m)list(
    intact=classification_metrics(test$cooler,predict_gaussian(m,ztest)),
    TS2_unavailable=classification_metrics(test$cooler,predict_gaussian(m,ztest,3:6))))
  intact_prob <- predict_gaussian(selected,ztest)
  outage_prob <- predict_gaussian(selected,ztest,3:6)
  predictions <- test[,c('cycle_id','setting','cooler')]
  predictions$predicted <- CLASS_ORDER[max.col(intact_prob,ties.method='first')]
  predictions$predicted_without_TS2 <- CLASS_ORDER[max.col(outage_prob,ties.method='first')]
  for (j in seq_along(CLASS_ORDER)) predictions[[paste0('prob_',CLASS_ORDER[j])]] <- intact_prob[,j]
  write.csv(predictions,file.path(root,'R/results/holdout_predictions_R.csv'),row.names=FALSE)
  # Keep each held-out setting (all its cooler levels) together in the bootstrap.
  settings <- sort(unique(test$setting));blocks <- lapply(settings,function(s)which(test$setting==s))
  bootstrap <- list(intact=numeric(resamples),TS2_unavailable=numeric(resamples))
  for (i in seq_len(resamples)) {
    indices <- unlist(blocks[sample.int(length(blocks),length(blocks),replace=TRUE)],use.names=FALSE)
    bootstrap$intact[i] <- classification_metrics(test$cooler[indices],intact_prob[indices,,drop=FALSE])$balanced_accuracy
    bootstrap$TS2_unavailable[i] <- classification_metrics(test$cooler[indices],outage_prob[indices,,drop=FALSE])$balanced_accuracy
  }
  bootstrap <- lapply(bootstrap,function(values)list(lower=unname(quantile(values,.025)),
    upper=unname(quantile(values,.975)),samples=values))
  transition <- d[d$unstable==1 & d$setting%in%settings,]
  transition_result <- classification_metrics(transition$cooler,
    predict_gaussian(selected,apply_scaler(transition[,CORE],chosen$scale)))
  offsets <- lapply(c(-8,-4,0,4,8),function(offset) {
    shifted <- as.matrix(test[,CORE]);shifted[,1] <- shifted[,1]+offset
    z <- apply_scaler(shifted,chosen$scale)
    c(list(temperature_offset_C=offset),lapply(chosen$models,function(m)
      classification_metrics(test$cooler,predict_gaussian(m,z))$balanced_accuracy))
  })
  list(models=chosen$models,selected_model=chosen$selected_kind,prediction_scale=chosen$scale,
       development_cv=chosen$cv,fold_plan=chosen$fold_plan,predictive_results=results,
       holdout_block_bootstrap=bootstrap,transition_stress=transition_result,offset_simulation=offsets,
       bundle=bundle,development_cycles=development$cycle_id,test_cycles=test$cycle_id)
}
