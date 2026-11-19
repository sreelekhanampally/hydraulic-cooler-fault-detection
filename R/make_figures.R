# All figures in this folder are computed and rendered by R graphics.
make_figures_R <- function(root,r) {
  d <- read.csv(file.path(root,'R/data/cycle_features_R.csv'))
  profile <- read.csv(file.path(root,'R/data/matched_profiles_R.csv'))
  z <- apply_scaler(profile[,CORE],r$reference_scale)
  colours <- c('#176b73','#b57516','#ac493b');names(colours)<-as.character(CLASS_ORDER)
  short <- c('Temp.','Temp. trend','Flow','Pressure SD','Power','Vibration')
  ink <- '#173344';muted <- '#60717b'
  plot_file <- function(name,fun,width=11,height=6.2) {
    for(format in c('png','pdf')) {
      path <- file.path(root,'R/figures',paste0(name,'.',format))
      if(format=='png')png(path,width=width*160,height=height*160,res=160,type='cairo')
      else pdf(path,width=width,height=height,useDingbats=FALSE)
      tryCatch({par(mar=c(5.2,5,3.4,1.5),mgp=c(3.1,.8,0),las=1,fg=ink,col.axis=ink,col.lab=ink,
                    col.main=ink,cex=.95,family='sans');fun()},finally=dev.off())
    }
  }
  heat <- function(a,title,names_x=short,names_y=short,zlim=c(-1,1),numbers=TRUE) {
    nr<-nrow(a);nc<-ncol(a)
    palette <- if(zlim[1]<0)colorRampPalette(c('#2c5d99','white','#ae4135'))(101) else colorRampPalette(c('white','#176b73'))(101)
    image(seq_len(nc),seq_len(nr),t(a[nr:1,,drop=FALSE]),zlim=zlim,col=palette,
          axes=FALSE,xlab='',ylab='',main=title,xlim=c(.5,nc+.5),ylim=c(.5,nr+.5))
    axis(1,at=seq_len(nc),labels=names_x,las=2,cex.axis=.8,tick=FALSE)
    axis(2,at=seq_len(nr),labels=rev(names_y),las=2,cex.axis=.8,tick=FALSE)
    if(numbers)for(i in seq_len(nr))for(j in seq_len(nc))text(j,nr-i+1,
      if(zlim[1]<0)sprintf('%.3f',a[i,j]) else as.character(a[i,j]),
      col=if((zlim[1]<0&&abs(a[i,j])>.65*max(abs(zlim)))||(zlim[1]>=0&&a[i,j]>.65*zlim[2]))'white' else ink,cex=.68)
    box(col='#cbd6da')
  }
  plot_file('01_recording_order_R',function(){
    plot(d$cycle_id,d$TS2_mean,type='n',xlab='Original cycle number',ylab='Mean oil temperature (deg C)',main='Cooler condition occupies separate recording phases')
    for(k in CLASS_ORDER){v<-d[d$cooler==k,];lines(v$cycle_id,v$TS2_mean,col=colours[as.character(k)],lwd=1.5)}
    legend('topright',legend=LABELS,col=colours,lty=1,bty='n',cex=.9)
  })
  plot_file('02_mean_vectors_R',function(){
    means<-sapply(r$group_summaries,function(g)g$mean_z);sds<-sapply(r$group_summaries,function(g)sqrt(diag(g$covariance_z)))
    plot(1:6,means[,1],type='n',ylim=range(means-sds,means+sds),xaxt='n',xlab='',ylab='Common-scale standardized value',main='Mean profiles and between-setting standard deviations')
    abline(h=0,col='#dce4e6');axis(1,at=1:6,labels=short)
    for(j in 1:3){x<-1:6+(j-2)*.08;lines(x,means[,j],type='b',pch=14+j,col=colours[j],lwd=1.5);arrows(x,means[,j]-sds[,j],x,means[,j]+sds[,j],angle=90,code=3,length=.035,col=colours[j])}
    legend('top',legend=LABELS,col=colours,pch=15:17,lty=1,bty='n',horiz=TRUE,cex=.9)
  })
  plot_file('03_correlations_R',function(){par(mfrow=c(1,3),mar=c(7,6,3,1));for(g in r$group_summaries)heat(g$correlation,g$label)},width=15,height=5.8)
  plot_file('04_generalized_variance_R',function(){
    par(mfrow=c(1,2),mar=c(5.7,5,3,1));labels<-c('Full','Reduced','Near failure')
    a<-vapply(r$group_summaries,function(g)g$log_generalized_variance,numeric(1));b<-vapply(r$group_summaries,function(g)g$standardized_generalized_variance,numeric(1))
    barplot(a,names.arg=labels,col=colours,border=NA,ylab='log determinant',main='Joint covariance spread')
    pos<-barplot(b,names.arg=labels,col=colours,border=NA,ylim=c(0,max(b)*1.25),ylab='Sixth root of determinant',main='One common scale for all conditions');text(pos,b,labels=sprintf('%.4f',b),pos=3,cex=.85)
  })
  plot_file('05_distribution_qq_R',function(){
    par(mfrow=c(1,3),mar=c(4.8,4.5,3,1));for(j in 1:3){x<-profile$TS2_mean[profile$cooler==CLASS_ORDER[j]];qqnorm(x,pch=16,col=colours[j],main=unname(LABELS[j]),ylab='Mean temperature (deg C)');qqline(x,col=muted)}
  },width=14,height=5.2)
  plot_file('06_mardia_simulations_R',function(){
    par(mfrow=c(1,2),mar=c(4.5,4.5,3,1));dist<-r$distribution_checks
    hist(dist$skew_reference,breaks=30,col='#a9c7cb',border='white',xlab='Fitted Mardia skewness',main='R Gaussian finite-sample reference',xlim=range(dist$skew_reference,vapply(dist$groups,function(g)g$skewness,numeric(1))));for(j in 1:3)abline(v=dist$groups[[j]]$skewness,col=colours[j],lwd=2)
    hist(dist$kurtosis_reference,breaks=30,col='#a9c7cb',border='white',xlab='Fitted Mardia kurtosis',main='Same n = 48 and p = 6');for(j in 1:3)abline(v=dist$groups[[j]]$kurtosis,col=colours[j],lwd=2)
    legend('topright',legend=LABELS,col=colours,lty=1,bty='n',cex=.75)
  })
  plot_file('07_MLE_likelihood_R',function(){
    x<-z[profile$cooler==100,c(1,5)];s<-covariance_matrix(x,mle=TRUE);m<-colMeans(x);inv<-solve(s)
    a<-seq(m[1]-.6*sqrt(s[1,1]),m[1]+.6*sqrt(s[1,1]),length.out=80)
    b<-seq(m[2]-.6*sqrt(s[2,2]),m[2]+.6*sqrt(s[2,2]),length.out=80)
    ll<-outer(a,b,Vectorize(function(u,v){delta<-c(u,v)-m;r$numerical_MLE$analytic_loglik-.5*nrow(x)*drop(crossprod(delta,inv%*%delta))}))
    contour(a,b,ll,nlevels=12,col='#699fa7',xlab='Temperature mean parameter (common standardized units)',ylab='Power mean parameter',main='Gaussian log likelihood: analytical and numerical fit')
    points(m[1],m[2],pch=4,cex=1.4,col=colours[1],lwd=2)
    points(r$numerical_MLE$numerical_parameters[1],r$numerical_MLE$numerical_parameters[2],pch=1,cex=1.3,col=colours[2],lwd=2)
    legend('topright',legend=c('Analytical MLE','Numerical optim() fit'),pch=c(4,1),col=colours[1:2],bty='n')
  })
  plot_file('08_MANOVA_null_R',function(){
    par(mfrow=c(1,3),mar=c(4.8,4.2,3.5,1));for(name in names(r$manova$resampling)){sim<-r$manova$resampling[[name]];hist(sim$roy_samples,breaks=28,col='#92b8bf',border='white',main=gsub('_',' ',name),xlab='Roy statistic under null');mtext(sprintf('Observed Roy = %.2f; p = %.3f',r$manova$roy,sim$p_mc),side=3,line=.3,cex=.8)}
  },width=15,height=5.1)
  plot_file('09_Hotelling_intervals_R',function(){
    means<-vapply(r$hotelling,function(h)h$mean_difference[1],numeric(1))*r$reference_scale$sd[1]
    all_lower<-all_upper<-numeric()
    for(h in r$hotelling)for(len in c(1,4,8)){ci<-h[[paste0('bootstrap_length_',len)]];all_lower<-c(all_lower,ci$lower[1]*r$reference_scale$sd[1]);all_upper<-c(all_upper,ci$upper[1]*r$reference_scale$sd[1])}
    par(mar=c(5,12,3,1));plot(0,0,type='n',xlim=range(all_lower,all_upper)*c(.96,1.03),ylim=c(.5,3.5),yaxt='n',xlab='Mean matched temperature difference (deg C)',ylab='',main='R pointwise 95% block-bootstrap intervals')
    axis(2,at=1:3,labels=c('Reduced minus full','Near failure minus full','Near failure minus reduced'),las=1,cex.axis=.85)
    for(j in 1:3)for(l in 1:3){len<-c(1,4,8)[l];ci<-r$hotelling[[j]][[paste0('bootstrap_length_',len)]];yy<-j+(l-2)*.12;lo<-ci$lower[1]*r$reference_scale$sd[1];hi<-ci$upper[1]*r$reference_scale$sd[1];segments(lo,yy,hi,yy,col=colours[l],lwd=2);points(means[j],yy,pch=15+l,col=colours[l])}
    legend('topright',legend=paste('Block length',c(1,4,8)),col=colours,lty=1,pch=16:18,bty='n',cex=.85)
  },width=12,height=6)
  plot_file('10_Hotelling_mean_region_R',function(){
    h<-r$hotelling[[1]];raw<-sweep(h$difference_rows,2L,r$reference_scale$sd,'*');xy<-raw[,c(1,3)];s<-cov(xy);e<-eigen(s,symmetric=TRUE);angle<-seq(0,2*pi,length.out=201)
    ellipse<-t(e$vectors%*%diag(sqrt(e$values*h$critical_T2_95/h$n))%*%rbind(cos(angle),sin(angle)));ellipse<-sweep(ellipse,2L,colMeans(xy),'+')
    plot(xy,pch=16,col='#8aadb580',xlab='Temperature difference (deg C)',ylab='Flow difference (L/min)',main='Reduced minus full efficiency: mean uncertainty and individual spread')
    polygon(ellipse,col='#b5751630',border=colours[2],lwd=2);points(mean(xy[,1]),mean(xy[,2]),pch=4,col=ink,lwd=2,cex=1.3)
    legend('topright',legend=c('Matched setting differences','Projected six-dimensional mean region'),pch=c(16,NA),lty=c(NA,1),col=c('#8aadb5',colours[2]),bty='n',cex=.8)
    mtext('The ellipse is for the mean difference, not a new individual cycle.',side=3,line=.3,cex=.8)
  })
  plot_file('11_covariance_null_R',function(){
    par(mfrow=c(1,2),mar=c(5.8,5,3.5,1));s<-r$covariance_tests$matched_gaussian_null
    hist(s$M_samples,breaks=30,col='#a4c2c9',border='white',xlab="Simulated Box's M",main='Equal-covariance Gaussian sensitivity')
    mtext(sprintf('Observed M = %.2f; p = %.3f',r$covariance_tests$box_m$M,s$p_mc),side=3,line=.3,cex=.8)
    heat(r$group_summaries[[3]]$covariance_z,'Near-failure covariance',zlim=c(-1,1)*max(abs(r$group_summaries[[3]]$covariance_z)),numbers=TRUE)
  },width=12,height=6)
  plot_file('12_partial_correlations_R',function(){par(mfrow=c(1,2),mar=c(7,7,3,1));heat(r$partial_regression$raw_correlation,'Before recorded-factor adjustment');heat(r$partial_regression$adjusted_correlation,'Residual correlations after adjustment')},width=13,height=6)
  plot_file('13_model_comparison_R',function(){
    kinds<-names(r$predictive_results);a<-sapply(r$predictive_results,function(v)c(v$intact$balanced_accuracy,v$TS2_unavailable$balanced_accuracy))*100
    pos<-barplot(a,beside=TRUE,names.arg=c('Temperature only','Diagonal','Shared','Separate covariance'),col=colours[1:2],border=NA,ylim=c(0,118),ylab='Held-out balanced accuracy (%)',main='R-trained models: complete readings and TS2 unavailable')
    text(pos,a,labels=sprintf('%.1f%%',a),pos=3,cex=.8);legend('top',legend=c('All readings','TS2 unavailable'),fill=colours[1:2],border=NA,bty='n',horiz=TRUE,cex=.85)
  })
  plot_file('14_outage_confusion_R',function(){par(mfrow=c(1,2),mar=c(6,7,3,1));lab<-c('Full','Reduced','Near failure');heat(r$predictive_results$temperature$TS2_unavailable$confusion,'Temperature-only model',lab,lab,c(0,120));heat(r$predictive_results[[r$selected_model]]$TS2_unavailable$confusion,'Selected R model without TS2',lab,lab,c(0,120))},width=11,height=5.5)
  plot_file('15_sensor_offset_R',function(){
    x<-vapply(r$offset_simulation,function(v)v$temperature_offset_C,numeric(1));kinds<-names(r$models);cols<-c(colours,'#7d66a1')
    plot(x,x,type='n',ylim=c(0,105),xlab='Artificial offset in TS2 mean (deg C)',ylab='Held-out balanced accuracy (%)',main='Input-offset sensitivity; physical readings otherwise unchanged')
    for(j in seq_along(kinds))lines(x,100*vapply(r$offset_simulation,function(v)v[[kinds[j]]],numeric(1)),type='b',pch=14+j,col=cols[j],lwd=2)
    legend('bottomleft',legend=kinds,col=cols,pch=15:18,lty=1,bty='n',cex=.85)
  })
  plot_file('16_transition_stress_R',function(){
    par(mfrow=c(1,2),mar=c(6,6,3.5,1));lab<-c('Full','Reduced','Near failure');heat(r$transition_stress$confusion,'Transition-cycle confusion',lab,lab,c(0,max(r$transition_stress$confusion)))
    barplot(100*r$transition_stress$recall,names.arg=lab,col=colours,border=NA,ylim=c(0,110),ylab='Recall (%)',main='Class recall on held-out transition cycles')
    mtext(sprintf('n = %d; accuracy %.2f%%; balanced accuracy %.2f%%',r$transition_stress$n,100*r$transition_stress$accuracy,100*r$transition_stress$balanced_accuracy),side=3,line=.3,cex=.75)
  },width=12,height=6)
  message('R figures complete: 16 PNG/PDF pairs in R/figures')
}
