# End-to-end statistical analysis. No Python process, Python API or Python model is used.
analyze_project_R <- function(root,resamples=999L,force_extract=FALSE) {
  started <- proc.time()[3L]
  set.seed(20261115)
  for(name in c('data','results','models','figures'))dir.create(file.path(root,'R',name),recursive=TRUE,showWarnings=FALSE)
  d <- extract_features_R(root,force=force_extract)
  stable <- d[d$unstable==0L,]
  profile <- aggregate(stable[,CORE],stable[,c('setting','cooler','valve','pump','accumulator')],mean)
  first <- tapply(d$cycle_id,d$setting,min)
  setting_order <- names(sort(first))
  profile$setting_order <- match(profile$setting,setting_order)-1L
  profile <- profile[order(profile$setting_order,profile$cooler),];rownames(profile)<-NULL
  stopifnot(nrow(profile)==144L,nrow(stable)==1449L)
  write.csv(profile,file.path(root,'R/data/matched_profiles_R.csv'),row.names=FALSE)
  scale <- fit_scaler(profile[,CORE]);z <- apply_scaler(profile[,CORE],scale)
  groups <- lapply(CLASS_ORDER,function(k)z[profile$cooler==k,,drop=FALSE])
  group_results <- lapply(seq_along(CLASS_ORDER),function(j) {
    k <- CLASS_ORDER[j];x <- groups[[j]];raw <- as.matrix(profile[profile$cooler==k,CORE])
    s <- covariance_matrix(x);ld <- logdet_spd(s)
    list(cooler=k,label=unname(LABELS[as.character(k)]),n_profiles=nrow(x),
      n_stable_cycles=sum(stable$cooler==k),mean_raw=unname(colMeans(raw)),sd_raw=unname(apply(raw,2L,sd)),
      mean_z=unname(colMeans(x)),covariance_z=unname(s),covariance_raw=unname(covariance_matrix(raw)),
      correlation=unname(cor(x)),mle_covariance_z=unname(covariance_matrix(x,mle=TRUE)),
      generalized_variance=exp(ld),log_generalized_variance=ld,
      standardized_generalized_variance=exp(ld/length(CORE)))
  })
  tensor <- array(0,c(length(setting_order),length(CLASS_ORDER),length(CORE)))
  for(i in seq_along(setting_order))for(j in seq_along(CLASS_ORDER))
    tensor[i,j,] <- z[profile$setting==setting_order[i]&profile$cooler==CLASS_ORDER[j],]
  man <- balanced_manova(tensor)
  reference <- manova_reference_R(profile,z)
  stopifnot(abs(man$wilks-reference$tables$Wilks$value)<1e-9)
  infer <- man[setdiff(names(man),c('residual','null_residual','null_fitted','fitted'))]
  infer$conventional_reference <- reference$tables
  infer$presentation_compatible_HL <- hl_presentation_reference_R(man)
  saveRDS(reference$fit,file.path(root,'R/models/manova_fit.rds'))
  message('R inference: MANOVA agrees with stats::manova; computing matched simulations')
  infer$resampling <- resample_manova_R(tensor,resamples)
  hotelling <- paired_contrasts_R(tensor,resamples)
  covariance_tests <- covariance_checks_R(groups,resamples)
  distribution <- distribution_checks_R(groups,resamples)
  mle <- numerical_mle_R(groups[[1L]])
  partial <- partial_regression_R(profile,z)
  split <- jsonlite::read_json(file.path(root,'data/split_manifest.json'),simplifyVector=TRUE)
  training <- train_and_evaluate_R(d,split,root,resamples)
  lag_rows <- lapply(CLASS_ORDER,function(k) {
    v <- stable[stable$cooler==k,];same <- diff(v$cycle_id)==1L
    list(cooler=k,lag1_contiguous_temperature=cor(head(v$TS2_mean,-1)[same],tail(v$TS2_mean,-1)[same]))
  })
  result <- c(list(language='R',R_version=R.version.string,seed=20261115,resamples=resamples,
    total_cycles=nrow(d),stable_cycles=nrow(stable),transition_cycles=sum(d$unstable==1L),
    matched_settings=48L,profile_rows=nrow(profile),features=CORE,class_order=CLASS_ORDER,
    class_labels=as.list(LABELS),reference_scale=scale,group_summaries=group_results,
    manova=infer,hotelling=hotelling,covariance_tests=covariance_tests,
    distribution_checks=distribution,numerical_MLE=mle,partial_regression=partial,split=split,
    contiguous_lag1=lag_rows,
    assumptions=c('Cooler and recording phase are perfectly confounded.',
      'Classical p-values use independent Gaussian references; they do not identify causation.',
      'Matched setting resampling retains pairing but cannot establish setting independence or remove drift.',
      'Predictions concern one rig and its recorded conditions, not an externally validated machine fleet.'),
    random_stream_note='All simulations are newly generated in R. R and the earlier implementation use different RNG streams; Monte Carlo p-values and intervals may therefore differ within simulation error.'),
    training[setdiff(names(training),'bundle')])
  result$elapsed_seconds <- proc.time()[3L]-started
  saveRDS(result,file.path(root,'R/results/analysis_R.rds'))
  jsonlite::write_json(result,file.path(root,'R/results/analysis_R.json'),auto_unbox=TRUE,
                       pretty=TRUE,digits=16,matrix='rowmajor',null='null',na='null')
  write.csv(do.call(rbind,lapply(group_results,function(g)
    data.frame(condition=g$label,feature=CORE,mean=g$mean_raw,sd=g$sd_raw))),
    file.path(root,'R/results/mean_vectors_R.csv'),row.names=FALSE)
  write.csv(do.call(rbind,lapply(hotelling,function(h)data.frame(from=h$from,to=h$to,T2=h$T2,
    F=h$F,p_iid=h$p_iid,p_holm_iid=h$p_holm_iid,sign_flip_p=h$sign_flip_p))),
    file.path(root,'R/results/hotelling_tests_R.csv'),row.names=FALSE)
  write.csv(do.call(rbind,lapply(distribution$groups,function(g)data.frame(cooler=g$cooler,
    skewness=g$skewness,kurtosis=g$kurtosis,skew_p_mc=g$skew_p_mc,kurtosis_p_mc=g$kurtosis_p_mc))),
    file.path(root,'R/results/distribution_checks_R.csv'),row.names=FALSE)
  for(j in seq_along(group_results)) {
    k <- CLASS_ORDER[j];g <- group_results[[j]]
    write.csv(g$covariance_raw,file.path(root,paste0('R/results/covariance_',k,'_R.csv')),row.names=FALSE)
    write.csv(g$correlation,file.path(root,paste0('R/results/correlation_',k,'_R.csv')),row.names=FALSE)
  }
  capture.output(sessionInfo(),file=file.path(root,'R/results/sessionInfo.txt'))
  cat('R analysis complete. Selected:',result$selected_model,'alpha',result$models[[result$selected_model]]$alpha,'\n')
  for(kind in names(result$models))cat(kind,'intact BA:',result$predictive_results[[kind]]$intact$balanced_accuracy,
    '| without TS2:',result$predictive_results[[kind]]$TS2_unavailable$balanced_accuracy,'\n')
  result
}
