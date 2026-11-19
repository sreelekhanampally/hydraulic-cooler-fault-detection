(function(root) {
  'use strict';
  function cholesky(a) {
    const n=a.length, L=Array.from({length:n},()=>Array(n).fill(0));
    for(let i=0;i<n;i++) for(let j=0;j<=i;j++) {
      let sum=a[i][j];
      for(let k=0;k<j;k++) sum-=L[i][k]*L[j][k];
      if(i===j) { if(!(sum>0)) throw new Error('Covariance must be positive definite'); L[i][j]=Math.sqrt(sum); }
      else L[i][j]=sum/L[j][j];
    }
    return L;
  }
  function forward(L,x) {
    const y=[];
    for(let i=0;i<x.length;i++) { let a=x[i]; for(let j=0;j<i;j++) a-=L[i][j]*y[j]; y.push(a/L[i][i]); }
    return y;
  }
  function predict(model, scale, raw, available) {
    if(raw.length!==scale.mean.length) throw new Error('Provide one slot per feature');
    const active=available===undefined?raw.map((_,i)=>i):available;
    if(new Set(active).size!==active.length || active.some(i=>!Number.isInteger(i)||i<0||i>=raw.length)) throw new Error('Invalid observed-coordinate indices');
    const local=model.feature_indices.map((v,i)=>({global:v,local:i})).filter(v=>active.includes(v.global));
    if(local.some(i=>!Number.isFinite(raw[i.global]))) throw new Error('Available model readings must be finite numbers');
    const z=raw.map((x,i)=>(x-scale.mean[i])/scale.sd[i]);
    const details=model.means.map((mu,k)=> {
      const prior=Math.log(model.priors[k]);
      if(!local.length) return {score:prior,logPrior:prior,logDeterminant:0,distance:0,dimensions:0};
      const cov=local.map(i=>local.map(j=>model.covariances[k][i.local][j.local]));
      const L=cholesky(cov);
      const delta=local.map(i=>z[i.global]-mu[i.local]);
      const whitened=forward(L,delta);
      const distance=whitened.reduce((s,x)=>s+x*x,0);
      const ld=2*L.reduce((s,row,i)=>s+Math.log(row[i]),0);
      return {score:prior-.5*(local.length*Math.log(2*Math.PI)+ld+distance),
              logPrior:prior,logDeterminant:ld,distance,dimensions:local.length};
    });
    const top=Math.max(...details.map(x=>x.score));
    const numerators=details.map(x=>Math.exp(x.score-top)),total=numerators.reduce((a,b)=>a+b,0);
    const probabilities=numerators.map(x=>x/total);
    return {probabilities,details,predictedIndex:probabilities.indexOf(Math.max(...probabilities)),observedDimensions:local.length};
  }
  const api={cholesky,forward,predict};
  root.HydraulicModel=api;
  if(typeof module!=='undefined'&&module.exports) module.exports=api;
})(typeof window!=='undefined'?window:globalThis);
