# Inference and simulation. Each result keeps its sampling assumptions explicit.
numerical_mle_R <- function(x) {
  x <- as.matrix(x)[,c(1L,5L),drop=FALSE];n <- nrow(x)
  mu <- colMeans(x);s <- covariance_matrix(x,mle=TRUE);sd <- sqrt(diag(s))
  rho <- s[1L,2L]/prod(sd);analytic <- c(mu,log(sd),atanh(rho))
  unpack <- function(t) {
    a <- exp(t[3:4]);r <- tanh(t[5])
    list(mu=t[1:2],covariance=matrix(c(a[1]^2,r*prod(a),r*prod(a),a[2]^2),2,2))
  }
  objective <- function(t) {
    u <- unpack(t);difference <- sweep(x,2L,u$mu,'-')
    white <- forwardsolve(t(chol(u$covariance)),t(difference))
    .5*(n*(2*log(2*pi)+logdet_spd(u$covariance))+sum(white^2))
  }
  gradient <- function(t) {
    u <- unpack(t);inv <- solve(u$covariance);difference <- sweep(x,2L,u$mu,'-')
    gcov <- .5*(n*inv-inv%*%crossprod(difference)%*%inv)
    a <- exp(t[3:4]);r <- tanh(t[5]);cross <- prod(a)
    derivatives <- list(matrix(c(2*a[1]^2,r*cross,r*cross,0),2,2),
      matrix(c(0,r*cross,r*cross,2*a[2]^2),2,2),
      matrix(c(0,(1-r*r)*cross,(1-r*r)*cross,0),2,2))
    c(-drop(inv%*%colSums(difference)),vapply(derivatives,function(v)sum(gcov*v),numeric(1)))
  }
  initial <- analytic+c(.05,-.05,.15,-.1,.1)
  fitted <- optim(initial,objective,gr=gradient,method='BFGS',control=list(maxit=2000,reltol=1e-14))
  list(features=CORE[c(1,5)],analytic_parameters=unname(analytic),numerical_parameters=unname(fitted$par),
       analytic_loglik=-objective(analytic),numeric_loglik=-fitted$value,
       objective_gap=abs(fitted$value-objective(analytic)),
       max_parameter_gap=max(abs(fitted$par-analytic)),optimizer_success=fitted$convergence==0L,
       convergence_code=fitted$convergence,parameterization='mu1, mu2, log(sd1), log(sd2), atanh(rho)')
}

manova_reference_R <- function(profile,z) {
  factors <- data.frame(setting=factor(profile$setting),cooler=factor(profile$cooler))
  fitted <- manova(z~setting+cooler,data=factors)
  tables <- lapply(c('Wilks','Pillai','Hotelling-Lawley','Roy'),function(test) {
    a <- summary(fitted,test=test)$stats['cooler',]
    list(statistic=test,value=unname(a[2]),approx_F=unname(a[3]),num_df=unname(a[4]),den_df=unname(a[5]),p_iid=unname(a[6]))
  })
  names(tables) <- c('Wilks','Pillai','Hotelling-Lawley','Roy')
  list(fit=fitted,tables=tables)
}

resample_manova_R <- function(y,count) {
  fit <- balanced_manova(y);b <- dim(y)[1];k <- dim(y)[2];p <- dim(y)[3]
  out <- list()
  for (variant in c('gaussian_iid_null','wild_restricted','wild_full_residual')) {
    values <- numeric(count)
    for (iteration in seq_len(count)) {
      if (variant=='gaussian_iid_null') {
        noise <- array(0,dim(y))
        for (j in seq_len(k)) noise[,j,] <- rmvn(b,rep(0,p),fit$E/fit$df_e)
      } else {
        source <- if (variant=='wild_restricted') fit$null_residual else fit$residual
        noise <- sweep(source,1L,sample(c(-1,1),b,replace=TRUE),'*')
        if (variant=='wild_full_residual') noise <- noise*sqrt(b/(b-1))
      }
      values[iteration] <- balanced_manova(fit$null_fitted+noise)$roy
    }
    out[[variant]] <- list(B=count,roy_samples=values,critical_95=unname(quantile(values,.95)),
                          p_mc=(1+sum(values>=fit$roy))/(count+1))
  }
  out
}

distribution_checks_R <- function(groups,count) {
  n <- nrow(groups[[1]]);p <- ncol(groups[[1]])
  reference <- replicate(count,{m <- mardia_statistics(matrix(rnorm(n*p),n,p));c(m$skewness,m$kurtosis)})
  center <- median(reference[2,]);rows <- list()
  for (j in seq_along(groups)) {
    m <- mardia_statistics(groups[[j]]);m$cooler <- CLASS_ORDER[j]
    m$skew_p_mc <- (1+sum(reference[1,]>=m$skewness))/(count+1)
    m$kurtosis_p_mc <- (1+sum(abs(reference[2,]-center)>=abs(m$kurtosis-center)))/(count+1)
    m <- c(m,marginal_shape(groups[[j]]));rows[[j]] <- m
  }
  list(groups=rows,B=count,skew_reference=reference[1,],kurtosis_reference=reference[2,],
       reference='Independent Gaussian simulations at the actual n=48 and p=6; generated in R')
}

paired_contrasts_R <- function(y,count) {
  pairs <- list(c(1L,2L),c(1L,3L),c(2L,3L));out <- list()
  for (j in seq_along(pairs)) {
    a <- pairs[[j]][1];b <- pairs[[j]][2];d <- y[,b,]-y[,a,]
    h <- paired_hotelling(d);h$from <- CLASS_ORDER[a];h$to <- CLASS_ORDER[b];h$difference_rows <- d
    for (length in c(1L,4L,8L)) {
      means <- replicate(count,colMeans(d[circular_block_indices(nrow(d),length),,drop=FALSE]))
      h[[paste0('bootstrap_length_',length)]] <- list(lower=apply(means,1L,quantile,.025),
        upper=apply(means,1L,quantile,.975),temperature_mean_samples=means[1,])
    }
    flips <- replicate(count,paired_hotelling(sweep(d,1L,sample(c(-1,1),nrow(d),replace=TRUE),'*'))$T2)
    h$sign_flip_p <- (1+sum(flips>=h$T2))/(count+1);out[[j]] <- h
  }
  adjusted <- p.adjust(vapply(out,function(h)h$p_iid,numeric(1)),method='holm')
  for (j in seq_along(out)) out[[j]]$p_holm_iid <- adjusted[j]
  out
}

covariance_checks_R <- function(groups,count) {
  bm <- box_m(groups);n <- nrow(groups[[1]]);p <- ncol(groups[[1]])
  simulated <- replicate(count,{
    common <- rmvn(n,rep(0,p),bm$pooled_covariance/2)
    samples <- lapply(groups,function(g)common+rmvn(n,rep(0,p),bm$pooled_covariance/2))
    box_m(samples)$M
  })
  list(box_m=bm,gaussian_lrt=covariance_lrt(groups),matched_gaussian_null=list(B=count,
       shared_fraction=.5,M_samples=simulated,p_mc=(1+sum(simulated>=bm$M))/(count+1)))
}

partial_regression_R <- function(profile,z) {
  factors <- data.frame(cooler=factor(profile$cooler),valve=factor(profile$valve),
                        pump=factor(profile$pump),accumulator=factor(profile$accumulator))
  design <- model.matrix(~cooler+valve+pump+accumulator,data=factors)
  fit <- lm.fit(design,z);residual <- fit$residuals
  r2 <- 1-sum(residual[,1]^2)/sum((z[,1]-mean(z[,1]))^2)
  list(raw_correlation=cor(z),adjusted_correlation=cor(residual),
       adjustment=c('cooler/phase','valve','pump','accumulator'),
       temperature_R2_in_sample=r2,coefficients=fit$coefficients[,1],
       design_names=colnames(design),residuals=residual,
       interpretation='Explanatory adjustment uses recorded component labels; those labels never enter the diagnostic score')
}

# R's native Hotelling-Lawley F approximation differs from the SAS-style
# approximation used in the existing slides. Compute that second reference in R
# as well, keeping both labels rather than silently substituting p-values.
hl_presentation_reference_R <- function(man) {
  p <- man$responses;q <- man$df_h;n <- (man$df_e-p-1)/2
  if(n<=1)stop('This compatibility approximation requires (df_e-p-1)/2 > 1')
  b <- (p+2*n)*(q+2*n)/(2*(2*n+1)*(n-1))
  df1 <- p*q;df2 <- 4+(p*q+2)/(b-1);adjustment <- (df2-2)/(2*n)
  f <- df2/df1*man$hotelling_lawley/adjustment
  list(statistic='Hotelling-Lawley, presentation-compatible F approximation',
       value=man$hotelling_lawley,approx_F=f,num_df=df1,den_df=df2,
       p_iid=pf(f,df1,df2,lower.tail=FALSE),
       reference='SAS-style approximation; formula also documented in statsmodels multivariate_stats')
}
