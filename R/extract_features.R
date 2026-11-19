# Rebuild the features from the original UCI recordings, entirely in R.
extract_features_R <- function(root,force=FALSE) {
  archive <- file.path(root,'data','raw','hydraulic_original.zip')
  expected <- '24128aad2ee45eea7e6b63ebbd9992cdf25d0483a2cebefbfc13bc69079af1f2'
  if (!file.exists(archive)) {
    dir.create(dirname(archive),recursive=TRUE,showWarnings=FALSE)
    download.file('https://archive.ics.uci.edu/static/public/447/condition+monitoring+of+hydraulic+systems.zip',
                  archive,mode='wb',quiet=FALSE)
  }
  if (digest::digest(file=archive,algo='sha256')!=expected) stop('Original archive checksum does not match')
  target <- file.path(root,'R','data','cycle_features_R.csv')
  if (file.exists(target)&&!force) return(read.csv(target,stringsAsFactors=FALSE))
  dir.create(dirname(target),recursive=TRUE,showWarnings=FALSE)
  profile_connection <- unz(archive,'profile.txt',open='r')
  profile <- read.table(profile_connection,header=FALSE,col.names=c('cooler','valve','pump','accumulator','unstable'))
  close(profile_connection)
  stopifnot(nrow(profile)==2205L,ncol(profile)==5L)
  d <- data.frame(cycle_id=seq_len(nrow(profile)),profile)
  d$condition <- unname(LABELS[as.character(d$cooler)])
  d$setting <- paste(d$valve,d$pump,d$accumulator,sep='_')
  hz <- c(setNames(rep(100,6),paste0('PS',1:6)),setNames(rep(1,4),paste0('TS',1:4)),
          FS1=10,FS2=10,EPS1=100,VS1=1)
  read_sensor <- function(name,frequency) {
    con <- unz(archive,paste0(name,'.txt'),open='r');on.exit(close(con))
    values <- scan(con,what=double(),quiet=TRUE)
    stopifnot(length(values)==2205L*60L*frequency,all(is.finite(values)))
    matrix(values,nrow=2205L,byrow=TRUE)
  }
  for (name in names(hz)) {
    frequency <- hz[[name]];x <- read_sensor(name,frequency)
    mu <- rowMeans(x);centered_time <- (seq_len(ncol(x))-1)/frequency
    centered_time <- centered_time-mean(centered_time)
    d[[paste0(name,'_mean')]] <- mu
    d[[paste0(name,'_std')]] <- sqrt(rowSums(sweep(x,1L,mu,'-')^2)/(ncol(x)-1))
    d[[paste0(name,'_slope')]] <- drop(x%*%centered_time)/sum(centered_time^2)
    d[[paste0(name,'_early')]] <- rowMeans(x[,seq_len(10L*frequency),drop=FALSE])
    d[[paste0(name,'_late')]] <- rowMeans(x[,(ncol(x)-10L*frequency+1L):ncol(x),drop=FALSE])
    message('R extraction: ',name,' (',nrow(x),' cycles x ',ncol(x),' readings)')
    rm(x);invisible(gc(FALSE))
  }
  stopifnot(ncol(d)==78L,nrow(d)==2205L)
  write.csv(d,target,row.names=FALSE)
  d
}
