# Independent formula, data, training and presentation-integrity checks in R.
run_tests_R <- function(root,r) {
  rows <- list();count <- 0L
  close_enough <- function(a,b,tol=1e-8) {
    a<-as.numeric(a);b<-as.numeric(b)
    length(a)==length(b)&&all(is.finite(a))&&all(is.finite(b))&&max(abs(a-b)/(1+abs(b)))<tol
  }
  check <- function(name,expr) {
    count <<- count+1L
    outcome <- tryCatch({stopifnot(isTRUE(eval(substitute(expr),parent.frame())));list(pass=TRUE,detail='')},
                        error=function(e)list(pass=FALSE,detail=conditionMessage(e)))
    rows[[count]] <<- data.frame(check=name,passed=outcome$pass,detail=outcome$detail,stringsAsFactors=FALSE)
    cat(if(outcome$pass)'PASS' else 'FAIL',name,'\n')
  }
  d<-read.csv(file.path(root,'R/data/cycle_features_R.csv'));profile<-read.csv(file.path(root,'R/data/matched_profiles_R.csv'))
  legacy<-jsonlite::read_json(file.path(root,'results/analysis.json'),simplifyVector=FALSE)
  vec<-function(x)as.numeric(unlist(x,use.names=FALSE))
  mat<-function(x)do.call(rbind,lapply(x,vec))
  z<-apply_scaler(profile[,CORE],r$reference_scale)
  groups<-lapply(CLASS_ORDER,function(k)z[profile$cooler==k,,drop=FALSE])
  bundle<-readRDS(file.path(root,'R/models/trained_gaussian_model.rds'))
  set.seed(4601);x<-matrix(rnorm(60*4),60,4);s<-covariance_matrix(x)
  check('sample covariance agrees with stats::cov',close_enough(s,cov(x),1e-12))
  check('ML covariance uses n instead of n-1',close_enough(covariance_matrix(x,TRUE),59/60*cov(x),1e-12))
  check('Cholesky log determinant agrees with determinant()',abs(logdet_spd(s)-as.numeric(determinant(s,logarithm=TRUE)$modulus))<1e-12)
  check('all original cycles extracted in R',nrow(d)==2205L&&ncol(d)==78L&&all(is.finite(as.matrix(d[,CORE]))))
  check('stable and transition counts agree with source',sum(d$unstable==0L)==1449L&&sum(d$unstable==1L)==756L)
  original_features<-read.csv(file.path(root,'data/cycle_features.csv'))
  raw_difference<-max(abs(as.matrix(d[,CORE])-as.matrix(original_features[,CORE])))
  check('R raw extraction reproduces supplied core features',raw_difference<1e-7)
  check('48 complete settings matched under every condition',nrow(profile)==144L&&all(table(profile$cooler)==48L)&&all(table(profile$setting)==3L))
  check('mean vectors reproduce presentation values',all(vapply(seq_along(groups),function(j)close_enough(r$group_summaries[[j]]$mean_raw,vec(legacy$group_summaries[[j]]$mean_raw)),logical(1))))
  check('condition covariance matrices reproduce presentation values',all(vapply(seq_along(groups),function(j)close_enough(r$group_summaries[[j]]$covariance_z,mat(legacy$group_summaries[[j]]$covariance_z),1e-7),logical(1))))
  check('condition correlations reproduce presentation values',all(vapply(seq_along(groups),function(j)close_enough(r$group_summaries[[j]]$correlation,mat(legacy$group_summaries[[j]]$correlation),1e-7),logical(1))))
  transform<-diag(c(2,3,4,5));changed<-covariance_matrix(x%*%transform)
  check('generalized variance obeys congruence scaling',abs(logdet_spd(changed)-logdet_spd(s)-2*log(abs(det(transform))))<1e-10)
  check('generalized variances match the slides',all(vapply(seq_along(groups),function(j)close_enough(r$group_summaries[[j]]$log_generalized_variance,legacy$group_summaries[[j]]$log_generalized_variance),logical(1))))
  m<-mardia_statistics(x);dcenter<-sweep(x,2,colMeans(x),'-');gram<-dcenter%*%solve(covariance_matrix(x,TRUE))%*%t(dcenter)
  check('Mardia skewness agrees with direct matrix formula',abs(m$skewness-mean(gram^3))<1e-10)
  check('Mardia kurtosis agrees with stats::mahalanobis',abs(m$kurtosis-mean(mahalanobis(x,colMeans(x),covariance_matrix(x,TRUE))^2))<1e-10)
  shifted<-sweep(x%*%transform,2,1:4,'+');ma<-mardia_statistics(shifted)
  check('Mardia measures are affine invariant',close_enough(c(m$skewness,m$kurtosis),c(ma$skewness,ma$kurtosis),1e-10))
  check('R distribution statistics match recorded profile statistics',all(vapply(seq_along(groups),function(j)close_enough(c(r$distribution_checks$groups[[j]]$skewness,r$distribution_checks$groups[[j]]$kurtosis),c(legacy$distribution_checks$groups[[j]]$skewness,legacy$distribution_checks$groups[[j]]$kurtosis),1e-7),logical(1))))
  check('numerical optim() Gaussian MLE converges',r$numerical_MLE$optimizer_success&&r$numerical_MLE$convergence_code==0L)
  check('numerical MLE agrees with analytical parameters',r$numerical_MLE$max_parameter_gap<1e-6&&r$numerical_MLE$objective_gap<1e-7)
  check('manual MANOVA agrees with stats::manova Wilks',abs(r$manova$wilks-r$manova$conventional_reference$Wilks$value)<1e-10)
  check('MANOVA roots and traces match slide calculations',close_enough(c(r$manova$roy,r$manova$wilks,r$manova$pillai,r$manova$hotelling_lawley),c(legacy$manova$roy,legacy$manova$wilks,legacy$manova$pillai,legacy$manova$hotelling_lawley),1e-7))
  design<-model.matrix(~factor(setting)+factor(cooler),data=profile);e<-crossprod(lm.fit(design,z)$residuals)
  check('MANOVA residual SSCP agrees with independent lm.fit()',close_enough(r$manova$E,e,1e-8))
  hl<-hl_presentation_reference_R(r$manova);old_hl<-legacy$manova$conventional_reference[['Hotelling-Lawley trace']]
  check('R also reproduces the slide Hotelling-Lawley F approximation',close_enough(c(hl$approx_F,hl$den_df),c(old_hl[['F Value']],old_hl[['Den DF']]),1e-7))
  check('presentation-compatible Hotelling-Lawley p is reproduced',abs(log(hl$p_iid)-log(old_hl[['Pr > F']]))<1e-5)
  one<-matrix(rnorm(50,.4),ncol=1);h<-paired_hotelling(one)
  check('Hotelling T2 reduces to ordinary t squared for p=1',abs(h$T2-as.numeric(t.test(one)$statistic)^2)<1e-10)
  h<-paired_hotelling(x);ha<-paired_hotelling(x%*%transform)
  check('Hotelling T2 is invariant to nonsingular linear scaling',abs(h$T2-ha$T2)<1e-10)
  check('all three paired T2 statistics match the slides',all(vapply(1:3,function(j)close_enough(r$hotelling[[j]]$T2,legacy$hotelling[[j]]$T2,1e-7),logical(1))))
  expected_holm<-p.adjust(vapply(r$hotelling,function(h)h$p_iid,numeric(1)),method='holm')
  check('three planned comparisons use Holm adjustment',close_enough(expected_holm,vapply(r$hotelling,function(h)h$p_holm_iid,numeric(1)),1e-12))
  check('Box M correction and degrees of freedom are correct',r$covariance_tests$box_m$df==42L&&close_enough(r$covariance_tests$box_m$chi2,legacy$covariance_tests$box_m$chi2,1e-7))
  counts<-vapply(groups,nrow,integer(1));covs<-lapply(groups,covariance_matrix,mle=TRUE)
  pooled<-Reduce('+',Map(function(s,n)n*s,covs,counts))/sum(counts)
  ll<-function(a,s){ev<-eigen(s,symmetric=TRUE,only.values=TRUE)$values;delta<-sweep(a,2,colMeans(a),'-');-.5*(nrow(a)*(ncol(a)*log(2*pi)+sum(log(ev)))+sum(delta*(delta%*%solve(s))))}
  lr_oracle<-2*(sum(vapply(seq_along(groups),function(j)ll(groups[[j]],covs[[j]]),numeric(1)))-sum(vapply(groups,function(g)ll(g,pooled),numeric(1))))
  check('covariance LRT agrees with direct maximized log likelihood',abs(lr_oracle-r$covariance_tests$gaussian_lrt$LR)<1e-6)
  check('partial correlations match recorded-factor regression',close_enough(r$partial_regression$adjusted_correlation,mat(legacy$partial_regression$adjusted_correlation),1e-7))
  check('training and test settings do not overlap',!any(r$split$development_settings%in%r$split$test_settings))
  development<-d[d$cycle_id%in%r$development_cycles,];test<-d[d$cycle_id%in%r$test_cycles,]
  check('training and holdout sample sizes are correct',nrow(development)==1089L&&nrow(test)==360L&&all(table(test$cooler)==120L))
  check('prediction scaler uses development cycles only',close_enough(r$prediction_scale$mean,colMeans(development[,CORE]),1e-12)&&close_enough(r$prediction_scale$sd,sqrt(colMeans(sweep(as.matrix(development[,CORE]),2,colMeans(development[,CORE]),'-')^2)),1e-12))
  check('cross-validation contains 36 indivisible setting blocks',nrow(r$fold_plan)==36L&&!anyDuplicated(r$fold_plan$setting)&&all(sort(unique(r$fold_plan$fold))==1:6)&&sum(r$fold_plan$cycles)==1089L)
  check('R independently selects shared covariance with alpha zero',r$selected_model=='shared'&&r$models$shared$alpha==0)
  for(kind in names(r$models)) {
    check(paste('held-out',kind,'intact/outage confusion matches slides'),
      all(r$predictive_results[[kind]]$intact$confusion==mat(legacy$predictive_results[[kind]]$intact$confusion))&&
      all(r$predictive_results[[kind]]$TS2_unavailable$confusion==mat(legacy$predictive_results[[kind]]$TS2_unavailable$confusion)))
  }
  check('selected R model retains all stable holdout predictions without TS2',r$predictive_results[[r$selected_model]]$intact$accuracy==1&&r$predictive_results[[r$selected_model]]$TS2_unavailable$accuracy==1)
  check('transition stress results reproduce original confusion',r$transition_stress$n==266L&&all(r$transition_stress$confusion==mat(legacy$transition_stress$confusion)))
  check('artificial sensor-offset results reproduce the frozen experiment',all(vapply(seq_along(r$offset_simulation),function(i)all(vapply(names(r$models),function(k)abs(r$offset_simulation[[i]][[k]]-legacy$offset_simulation[[i]][[k]])<1e-10,logical(1))),logical(1))))
  exported<-jsonlite::read_json(file.path(root,'R/models/trained_gaussian_model.json'),simplifyVector=TRUE)
  check('portable JSON and native RDS coordinate conventions are explicit',all(exported$model$feature_indices==0:5)&&all(bundle$model$feature_indices==1:6))
  ztest<-apply_scaler(test[,CORE],r$prediction_scale);model<-bundle$model
  own<-score_model(model,ztest[1:8,,drop=FALSE]);oracle<-sapply(1:3,function(j)log(model$priors[j])-.5*(6*log(2*pi)+as.numeric(determinant(model$covariances[[j]],logarithm=TRUE)$modulus)+mahalanobis(ztest[1:8,,drop=FALSE],model$means[j,],model$covariances[[j]])))
  check('Gaussian scores agree with independent base-R density formula',max(abs(own-oracle))<1e-7)
  observed<-3:6;subset_model<-model;subset_model$feature_indices<-observed;subset_model$means<-model$means[,observed];subset_model$covariances<-lapply(model$covariances,function(s)s[observed,observed])
  check('missing TS2 uses a covariance submatrix marginal',close_enough(score_model(model,ztest,observed),score_model(subset_model,ztest,observed),1e-10))
  prior_only<-predict_gaussian(r$models$temperature,ztest,3:6)
  check('temperature-only model without TS2 returns priors',max(abs(prior_only-matrix(r$models$temperature$priors,nrow(ztest),3,byrow=TRUE)))<1e-12)
  batch<-test[1:6,];a<-predict_frame_R(bundle,batch,TRUE);b<-predict_frame_R(bundle,batch[,setdiff(names(batch),CORE[1:2])],TRUE)
  check('batch prediction accepts truly absent temperature columns',isTRUE(all.equal(a,b)))
  factor_input<-batch;factor_input$FS1_mean<-factor(as.character(factor_input$FS1_mean))
  check('R factor inputs use their numeric labels rather than level codes',isTRUE(all.equal(predict_frame_R(bundle,batch),predict_frame_R(bundle,factor_input))))
  bad<-batch;bad$FS1_mean[1]<-NA
  check('invalid observed readings are rejected',inherits(try(predict_frame_R(bundle,bad),silent=TRUE),'try-error'))
  check('duplicate observed coordinate masks are rejected',inherits(try(score_model(model,ztest,c(1,1)),silent=TRUE),'try-error'))
  bins<-circular_block_indices(48,8)
  check('circular block bootstrap indices stay in bounds',length(bins)==48L&&all(bins>=1L&bins<=48L))
  check('Monte Carlo p-values have the plus-one minimum',all(vapply(r$manova$resampling,function(s)s$p_mc>=1/(s$B+1)&&s$p_mc<=1,logical(1))))
  check('perfect empirical bootstrap interval is retained and labelled',r$holdout_block_bootstrap$intact$lower==1&&r$holdout_block_bootstrap$intact$upper==1)
  # Frozen browser oracle values are validation data only, not inputs to R fitting.
  js<-jsonlite::read_json(file.path(root,'tests/js_oracle.json'),simplifyVector=FALSE)
  maximum_score<-maximum_relative_score<-maximum_probability<-0
  for(item in js$cases) {
    raw<-matrix(vec(item$raw),nrow=1);available<-vec(item$available)+1L
    zz<-apply_scaler(raw,r$prediction_scale);scores<-score_model(r$models[[item$model]],zz,available)
    expected<-vec(item$scores);prob<-softmax(scores)
    maximum_score<-max(maximum_score,abs(scores-expected))
    maximum_relative_score<-max(maximum_relative_score,abs(scores-expected)/(1+abs(expected)))
    maximum_probability<-max(maximum_probability,abs(prob-vec(item$probabilities)))
  }
  check('304 browser oracle cases agree with R-trained scores',maximum_relative_score<1e-7)
  check('304 browser oracle cases agree with R probabilities',maximum_probability<1e-7)
  exported_slides<-jsonlite::read_json(file.path(root,'R/results/presentation_analysis_R.json'),simplifyVector=FALSE)
  export_record<-jsonlite::read_json(file.path(root,'R/results/presentation_export_R.json'),simplifyVector=TRUE)
  check('presentation data are exported from the current R analysis',exported_slides$language=='R'&&export_record$analysis_sha256==digest::digest(file=file.path(root,'R/results/analysis_R.rds'),algo='sha256'))
  check('presentation browser data match the R export record',export_record$browser_data_sha256==digest::digest(file=file.path(root,'dist/lab-data.js'),algo='sha256'))
  check('presentation contains all R cycles and matched profiles',export_record$cycles==2205L&&export_record$profiles==144L)
  check('presentation reports native R MANOVA p values',close_enough(exported_slides$manova$conventional_reference$`Hotelling-Lawley`$`Pr > F`,r$manova$conventional_reference$`Hotelling-Lawley`$p_iid,1e-12))
  check('presentation uses the new R distribution p values',all(vapply(1:3,function(j)exported_slides$distribution_checks$groups[[j]]$skew_p_mc==r$distribution_checks$groups[[j]]$skew_p_mc,logical(1))))
  slide_models_match<-all(vapply(names(r$models),function(k){m<-exported_slides$models[[k]];all(vec(m$feature_indices)==r$models[[k]]$feature_indices-1L)&&close_enough(mat(m$means),r$models[[k]]$means,1e-12)},logical(1)))
  check('all four slide models use the fitted R parameters',slide_models_match)
  slide_assets<-c('07_MLE_likelihood_R','09_Hotelling_intervals_R','11_covariance_null_R')
  check('static slide figures are copied from the R plots',all(vapply(slide_assets,function(n)digest::digest(file=file.path(root,'R/figures',paste0(n,'.png')),algo='sha256')==digest::digest(file=file.path(root,'dist/figures',paste0(n,'.png')),algo='sha256'),logical(1))))
  check('sixteen complete R-generated figure pairs exist',length(list.files(file.path(root,'R/figures'),pattern='\\.png$'))==16L&&length(list.files(file.path(root,'R/figures'),pattern='\\.pdf$'))==16L)
  results<-do.call(rbind,rows);write.csv(results,file.path(root,'R/results/test_results_R.csv'),row.names=FALSE)
  qa<-list(language='R',status=if(all(results$passed))'passed' else 'failed',checks=nrow(results),
    passed=sum(results$passed),failed=sum(!results$passed),R_version=R.version.string,
    raw_feature_max_absolute_difference=raw_difference,
    browser_oracle_cases=length(js$cases),browser_max_log_score_absolute_difference=maximum_score,
    browser_max_log_score_relative_difference=maximum_relative_score,
    browser_max_probability_difference=maximum_probability,
    presentation_results_from_R=TRUE,browser_data_sha256=export_record$browser_data_sha256,
    implementation='Native R statistical calculations, resampling, training, prediction, plotting and checks; no Python runtime invoked.',
    note='Original JSON and browser oracle cases are read only for post-fit verification. R simulations use their own RNG stream.')
  jsonlite::write_json(qa,file.path(root,'R/results/QA_R.json'),auto_unbox=TRUE,pretty=TRUE,digits=16)
  if(!all(results$passed))stop('R validation failed: ',paste(results$check[!results$passed],collapse='; '))
  cat('All',nrow(results),'R checks passed. Slide data come from R.\n')
  qa
}
