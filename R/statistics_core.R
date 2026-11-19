# Core calculations in native R. All tests use unregularized sample covariance.
# Covariance for Gaussian likelihood uses n; unbiased covariance uses n - 1.
CORE <- c('TS2_mean','TS2_slope','FS1_mean','PS2_std','EPS1_mean','VS1_mean')
CLASS_ORDER <- c(100L,20L,3L)
LABELS <- c('100'='Full efficiency','20'='Reduced efficiency','3'='Near failure')
FEATURE_NAMES <- c('Temperature','Temperature trend','Flow','Pressure SD','Motor power','Vibration')
FEATURE_UNITS <- c('deg C','deg C/s','L/min','bar','W','mm/s')

covariance_matrix <- function(x, mle=FALSE) {
  x <- as.matrix(x)
  stopifnot(nrow(x)>1L, ncol(x)>0L, all(is.finite(x)))
  d <- sweep(x,2L,colMeans(x),'-')
  crossprod(d) / if (mle) nrow(x) else (nrow(x)-1L)
}

logdet_spd <- function(s) {
  s <- as.matrix(s)
  if (!isTRUE(all.equal(s,t(s),tolerance=1e-10))) stop('Covariance must be symmetric')
  2*sum(log(diag(chol(s))))
}

manova_roots <- function(h,e) {
  p <- ncol(e)
  inv_l <- forwardsolve(t(chol(e)),diag(p))
  a <- inv_l %*% h %*% t(inv_l)
  roots <- pmax(eigen((a+t(a))/2,symmetric=TRUE,only.values=TRUE)$values,0)
  list(roots=roots,roy=max(roots),wilks=prod(1/(1+roots)),
       pillai=sum(roots/(1+roots)),hotelling_lawley=sum(roots))
}

balanced_manova <- function(y) {
  # y[setting, condition, feature]; all conditions matched within each setting.
  b <- dim(y)[1L]; k <- dim(y)[2L]; p <- dim(y)[3L]
  setting_mean <- apply(y,c(1L,3L),mean)
  condition_mean <- apply(y,c(2L,3L),mean)
  grand <- colMeans(setting_mean)
  fitted <- residual <- null_residual <- null_fitted <- array(0,dim(y))
  e <- matrix(0,p,p)
  for (j in seq_len(k)) {
    fitted[,j,] <- sweep(setting_mean,2L,condition_mean[j,]-grand,'+')
    residual[,j,] <- y[,j,]-fitted[,j,]
    null_fitted[,j,] <- setting_mean
    null_residual[,j,] <- y[,j,]-setting_mean
    e <- e+crossprod(residual[,j,])
  }
  delta <- sweep(condition_mean,2L,grand,'-')
  h <- b*crossprod(delta)
  c(manova_roots(h,e),list(H=h,E=e,residual=residual,null_residual=null_residual,
    null_fitted=null_fitted,fitted=fitted,df_h=k-1L,df_e=(b-1L)*(k-1L),settings=b,responses=p))
}

paired_hotelling <- function(d) {
  d <- as.matrix(d); n <- nrow(d); p <- ncol(d)
  if (n<=p) stop('Hotelling T2 needs more independent difference vectors than features')
  mu <- colMeans(d); s <- covariance_matrix(d)
  t2 <- as.numeric(n*crossprod(mu,solve(s,mu)))
  f <- (n-p)*t2/(p*(n-1))
  list(n=n,p=p,mean_difference=mu,covariance=s,T2=t2,F=f,df1=p,df2=n-p,
       p_iid=pf(f,p,n-p,lower.tail=FALSE),critical_T2_95=p*(n-1)/(n-p)*qf(.95,p,n-p))
}

box_m <- function(groups) {
  ns <- vapply(groups,nrow,integer(1)); dfs <- ns-1L
  k <- length(groups); p <- ncol(groups[[1L]])
  ss <- lapply(groups,covariance_matrix)
  pooled <- Reduce('+',Map(function(s,df)df*s,ss,dfs))/sum(dfs)
  m <- sum(dfs)*logdet_spd(pooled)-sum(dfs*vapply(ss,logdet_spd,numeric(1)))
  correction <- (sum(1/dfs)-1/sum(dfs))*(2*p*p+3*p-1)/(6*(p+1)*(k-1))
  df <- (k-1)*p*(p+1)/2
  list(M=m,correction=correction,chi2=(1-correction)*m,df=df,
       p_iid=pchisq((1-correction)*m,df,lower.tail=FALSE),
       pooled_covariance=pooled,covariances=ss,counts=ns)
}

covariance_lrt <- function(groups) {
  ns <- vapply(groups,nrow,integer(1)); p <- ncol(groups[[1L]])
  ss <- lapply(groups,covariance_matrix,mle=TRUE)
  pooled <- Reduce('+',Map(function(s,n)n*s,ss,ns))/sum(ns)
  lr <- sum(ns)*logdet_spd(pooled)-sum(ns*vapply(ss,logdet_spd,numeric(1)))
  df <- (length(groups)-1)*p*(p+1)/2
  list(LR=lr,df=df,p_iid=pchisq(lr,df,lower.tail=FALSE))
}

mardia_statistics <- function(x) {
  x <- as.matrix(x); n <- nrow(x); p <- ncol(x)
  d <- sweep(x,2L,colMeans(x),'-')
  whitened <- forwardsolve(t(chol(covariance_matrix(x,mle=TRUE))),t(d))
  gram <- crossprod(whitened)
  skew <- mean(gram^3); kurt <- mean(diag(gram)^2)
  skew_df <- p*(p+1)*(p+2)/6
  kurt_z <- (kurt-p*(p+2))/sqrt(8*p*(p+2)/n)
  list(n=n,p=p,skewness=skew,kurtosis=kurt,normal_kurtosis=p*(p+2),
       skew_chi2=n*skew/6,skew_df=skew_df,
       skew_p_asymptotic=pchisq(n*skew/6,skew_df,lower.tail=FALSE),
       kurtosis_z=kurt_z,kurtosis_p_asymptotic=2*pnorm(-abs(kurt_z)))
}

marginal_shape <- function(x) {
  x <- as.matrix(x); n <- nrow(x);d <- sweep(x,2L,colMeans(x),'-')
  m2 <- colMeans(d^2); g1 <- colMeans(d^3)/m2^1.5
  g2 <- colMeans(d^4)/m2^2-3
  list(univariate_skewness=sqrt(n*(n-1))/(n-2)*g1,
       univariate_excess_kurtosis=(n-1)/((n-2)*(n-3))*((n+1)*g2+6),
       shapiro_p_iid=apply(x,2L,function(v)shapiro.test(v)$p.value))
}

circular_block_indices <- function(n,block_length) {
  starts <- sample.int(n,ceiling(n/block_length),replace=TRUE)
  unlist(lapply(starts,function(s)((s-1L+seq_len(block_length)-1L)%%n)+1L),use.names=FALSE)[seq_len(n)]
}

rmvn <- function(n,mu,sigma) {
  z <- matrix(rnorm(n*length(mu)),nrow=n)
  sweep(z%*%chol(sigma),2L,mu,'+')
}

fit_scaler <- function(x) {
  x <- as.matrix(x);mu <- colMeans(x)
  sd <- sqrt(colMeans(sweep(x,2L,mu,'-')^2))
  if (any(sd<=0)) stop('Every fitted feature needs positive variance')
  list(mean=unname(mu),sd=unname(sd))
}
apply_scaler <- function(x,scale) sweep(sweep(as.matrix(x),2L,scale$mean,'-'),2L,scale$sd,'/')

fit_gaussian <- function(x,y,kind,alpha=0,indices=seq_len(ncol(x))) {
  x <- as.matrix(x)[,indices,drop=FALSE]
  means <- do.call(rbind,lapply(CLASS_ORDER,function(k)colMeans(x[y==k,,drop=FALSE])))
  counts <- vapply(CLASS_ORDER,function(k)sum(y==k),numeric(1))
  covs <- lapply(CLASS_ORDER,function(k)covariance_matrix(x[y==k,,drop=FALSE],mle=TRUE))
  if (kind=='shared') {
    shared <- Reduce('+',Map(function(s,n)n*s,covs,counts))/sum(counts)
    covs <- rep(list(shared),length(CLASS_ORDER))
  }
  if (kind=='diagonal') covs <- lapply(covs,function(s)diag(diag(s),nrow(s)))
  covs <- lapply(covs,function(s){out <- (1-alpha)*s+alpha*sum(diag(s))/nrow(s)*diag(nrow(s));chol(out);out})
  list(kind=kind,alpha=alpha,feature_indices=as.integer(indices),means=unname(means),
       covariances=covs,priors=counts/sum(counts),counts=counts)
}

# Scores are evaluated using the exact Gaussian marginal on the observed coordinates.
# The indices in native R models are one-based. The portable JSON export is zero-based.
score_model <- function(model,z,available=seq_len(ncol(z))) {
  z <- as.matrix(z)
  if (anyDuplicated(available)||any(!available%in%seq_len(ncol(z)))) stop('Invalid available coordinates')
  local <- which(model$feature_indices%in%available)
  if (!length(local)) return(matrix(log(model$priors),nrow(z),length(CLASS_ORDER),byrow=TRUE))
  global <- model$feature_indices[local]
  if (any(!is.finite(z[,global,drop=FALSE]))) stop('Available readings must be finite numbers')
  out <- matrix(0,nrow(z),length(CLASS_ORDER))
  for (j in seq_along(CLASS_ORDER)) {
    s <- model$covariances[[j]][local,local,drop=FALSE]
    delta <- sweep(z[,global,drop=FALSE],2L,model$means[j,local],'-')
    white <- forwardsolve(t(chol(s)),t(delta))
    out[,j] <- log(model$priors[j])-.5*(length(local)*log(2*pi)+logdet_spd(s)+colSums(white^2))
  }
  out
}
softmax <- function(scores) {
  a <- exp(sweep(scores,1L,apply(scores,1L,max),'-'))
  a/rowSums(a)
}
predict_gaussian <- function(model,z,available=seq_len(ncol(z))) softmax(score_model(model,z,available))

classification_metrics <- function(y,prob) {
  truth <- match(y,CLASS_ORDER);predicted <- max.col(prob,ties.method='first')
  cm <- table(factor(truth,levels=seq_along(CLASS_ORDER)),factor(predicted,levels=seq_along(CLASS_ORDER)))
  recall <- diag(cm)/rowSums(cm);precision <- ifelse(colSums(cm)>0,diag(cm)/colSums(cm),0)
  f1 <- ifelse(precision+recall>0,2*precision*recall/(precision+recall),0)
  clipped <- pmin(pmax(prob,.Machine$double.eps),1-.Machine$double.eps)
  clipped <- clipped/rowSums(clipped)
  target <- diag(3)[truth,,drop=FALSE]
  list(n=length(y),accuracy=mean(truth==predicted),balanced_accuracy=mean(recall),macro_f1=mean(f1),
       log_loss=-mean(log(clipped[cbind(seq_along(truth),truth)])),brier=mean(rowSums((prob-target)^2)),
       confusion=matrix(as.numeric(cm),nrow(cm),ncol(cm)),recall=unname(recall),healthy_false_alarm=1-recall[1L],
       near_failure_as_healthy=as.numeric(cm[3L,1L]/sum(cm[3L,])))
}
