# Export the actual R results and fitted models for the offline slides.
# JavaScript displays these values and evaluates the already-fitted model.
export_presentation_R <- function(root,r) {
  d <- read.csv(file.path(root,'R/data/cycle_features_R.csv'),stringsAsFactors=FALSE)
  profiles <- read.csv(file.path(root,'R/data/matched_profiles_R.csv'),stringsAsFactors=FALSE)
  out <- r
  out$feature_metadata <- lapply(seq_along(CORE),function(i)list(
    key=CORE[i],name=c('Mean oil temperature','Temperature trend','Mean volume flow',
      'Pressure fluctuation','Mean motor power','Mean vibration')[i],
    short=FEATURE_NAMES[i],unit=FEATURE_UNITS[i],sensor=c('TS2','TS2','FS1','PS2','EPS1','VS1')[i]))
  out$models <- lapply(r$models,function(m) {
    m <- portable_model_R(m)
    m$feature_indices <- I(as.integer(m$feature_indices))
    m
  })
  # Only the display field names change. These are native summary.manova() results.
  out$manova$conventional_reference <- lapply(r$manova$conventional_reference,function(v)
    list(Value=v$value,'F Value'=v$approx_F,'Num DF'=v$num_df,'Den DF'=v$den_df,
         'Pr > F'=v$p_iid,source='R stats::summary.manova'))
  out$presentation_source <- list(language='R',
    analysis='R/results/analysis_R.rds',models='R/models/all_candidate_families.rds',
    demonstration='R/Presentation_Demo.R',
    analysis_sha256=digest::digest(file=file.path(root,'R/results/analysis_R.rds'),algo='sha256'))
  # Compute chart coordinates in R; the browser only renders the exported values.
  zprofiles <- apply_scaler(profiles[,CORE],r$reference_scale)
  x <- zprofiles[profiles$cooler==100,c(1,5)]
  sigma <- covariance_matrix(x,mle=TRUE);mu <- colMeans(x);inverse <- solve(sigma)
  a <- seq(mu[1]-.6*sqrt(sigma[1,1]),mu[1]+.6*sqrt(sigma[1,1]),length.out=41)
  b <- seq(mu[2]-.6*sqrt(sigma[2,2]),mu[2]+.6*sqrt(sigma[2,2]),length.out=41)
  likelihood <- outer(a,b,Vectorize(function(u,v){delta<-c(u,v)-mu
    r$numerical_MLE$analytic_loglik-.5*nrow(x)*drop(crossprod(delta,inverse%*%delta))}))
  intervals <- lapply(r$hotelling,function(h)list(from=h$from,to=h$to,
    mean=h$mean_difference[1]*r$reference_scale$sd[1],
    blocks=lapply(c(1L,4L,8L),function(size){ci<-h[[paste0('bootstrap_length_',size)]]
      list(size=size,lower=ci$lower[1]*r$reference_scale$sd[1],upper=ci$upper[1]*r$reference_scale$sd[1])})))
  out$presentation_charts <- list(mle=list(x=a,y=b,log_likelihood=t(likelihood)),
                                  paired_temperature_intervals=intervals)
  out$stable_cycles_per_cell <- as.list(range(table(interaction(
    d$setting[d$unstable==0],d$cooler[d$unstable==0],drop=TRUE))))
  cells <- lapply(seq_len(nrow(d)),function(i)list(id=d$cycle_id[i],cooler=d$cooler[i],
    setting=d$setting[i],valve=d$valve[i],pump=d$pump[i],accumulator=d$accumulator[i],
    stable=d$unstable[i]==0,split=if(d$setting[i]%in%r$split$test_settings)'holdout' else 'development',
    values=unname(as.numeric(d[i,CORE]))))
  rows <- lapply(seq_len(nrow(profiles)),function(i)list(setting=profiles$setting[i],
    cooler=profiles$cooler[i],values=unname(as.numeric(profiles[i,CORE]))))
  payload <- list(analysis=out,cycles=cells,profiles=rows,
    traces=jsonlite::read_json(file.path(root,'data/trace_samples.json'),simplifyVector=FALSE),
    provenance=jsonlite::read_json(file.path(root,'data/provenance.json'),simplifyVector=FALSE))
  encode <- function(x,pretty=FALSE)jsonlite::toJSON(x,auto_unbox=TRUE,pretty=pretty,
    digits=16,matrix='rowmajor',null='null',na='null')
  writeLines(paste0('window.LAB_DATA = ',encode(payload),';'),file.path(root,'dist/lab-data.js'),useBytes=TRUE)
  writeLines(encode(out,TRUE),file.path(root,'R/results/presentation_analysis_R.json'),useBytes=TRUE)
  assets <- c('07_MLE_likelihood_R','09_Hotelling_intervals_R','11_covariance_null_R')
  dir.create(file.path(root,'dist/figures'),showWarnings=FALSE,recursive=TRUE)
  for(name in assets)file.copy(file.path(root,'R/figures',paste0(name,'.png')),
                             file.path(root,'dist/figures',paste0(name,'.png')),overwrite=TRUE)
  # R-generated reference cases independently check browser prediction arithmetic.
  indices <- sort(unique(c(as.integer(seq(1,nrow(d),length.out=17)),733L,1465L)))
  raw <- as.matrix(d[indices,CORE]);z <- apply_scaler(raw,r$prediction_scale)
  cases <- list()
  for(kind in names(r$models))for(observed in list(1:6,3:6,c(1L,5L),integer())) {
    scores <- score_model(r$models[[kind]],z,observed);prob <- softmax(scores)
    for(i in seq_len(nrow(raw)))cases[[length(cases)+1L]] <- list(model=kind,
      raw=unname(raw[i,]),available=I(as.integer(observed-1L)),
      scores=unname(scores[i,]),probabilities=unname(prob[i,]))
  }
  writeLines(encode(list(language='R',models=out$models,scale=r$prediction_scale,cases=cases)),
             file.path(root,'tests/js_oracle_R.json'),useBytes=TRUE)
  record <- list(language='R',analysis_sha256=out$presentation_source$analysis_sha256,
    browser_data_sha256=digest::digest(file=file.path(root,'dist/lab-data.js'),algo='sha256'),
    cycles=length(cells),profiles=length(rows),oracle_cases=length(cases),
    note='Statistical results and all fitted parameters exported by R; browser scripts display results and score inputs.')
  writeLines(encode(record,TRUE),file.path(root,'R/results/presentation_export_R.json'),useBytes=TRUE)
  message('Exported R results, R-trained models and prediction checks to the presentation.')
  invisible(out)
}
