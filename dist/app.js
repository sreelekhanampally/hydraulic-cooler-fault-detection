/* Slides display statistical results and Gaussian models fitted in R. */
(() => {
  'use strict';
  const D = window.LAB_DATA, R = D.analysis, ORDER = R.class_order;
  const C = {100:'#176b73',20:'#b57516',3:'#ac493b'}, INK='#173344', MUTED='#526d7a';
  const meta=R.feature_metadata, short=meta.map(m=>m.short), main=document.getElementById('main');
  const label=k=>R.class_labels[String(k)];
  const esc=s=>String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
  const num=(x,d=3)=>Number.isFinite(x)?(Math.abs(x)>0&&(Math.abs(x)<.001||Math.abs(x)>=1e5)?x.toExponential(2):x.toLocaleString('en-US',{maximumFractionDigits:d})):'—';
  const pct=x=>(100*x).toFixed(1)+'%';
  const pval=x=>x<.0001?x.toExponential(2):num(x,4);
  const points=(items,cls='')=>`<ul class="points ${cls}">${items.map(t=>`<li>${t}</li>`).join('')}</ul>`;
  const heading=(title,subtitle='')=>`<header class="slide-heading"><h1>${title}</h1>${subtitle?`<p class="subtitle">${subtitle}</p>`:''}</header>`;
  const math=tex=>`<div class="formula" data-math="${esc(tex)}"></div>`;
  const chart=(id,description)=>`<div id="${id}" class="chart" role="img" aria-label="${esc(description)}"></div>`;
  const figure=(name,caption)=>`<figure class="data-figure"><img src="figures/${name}.png" alt="${esc(caption)}"><figcaption>${caption}</figcaption></figure>`;
  const table=(heads,rows)=>`<div class="table-wrap"><table><thead><tr>${heads.map(t=>`<th>${t}</th>`).join('')}</tr></thead><tbody>${rows.map(row=>`<tr>${row.map(t=>`<td>${t}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
  const groupSummary=k=>R.group_summaries.find(g=>g.cooler===Number(k));
  const groupSelect=id=>`<div class="controls"><label for="${id}">Cooler condition</label><select id="${id}">${ORDER.map(k=>`<option value="${k}">${label(k)}</option>`).join('')}</select></div>`;
  const bindGroup=(id,fn)=>{const control=document.getElementById(id);control.addEventListener('change',()=>fn(Number(control.value)));fn(Number(control.value));};
  const commonLayout={font:{family:'Segoe UI, Arial, sans-serif',size:13,color:INK},paper_bgcolor:'#ffffff',plot_bgcolor:'#ffffff',margin:{l:68,r:28,t:40,b:62},legend:{orientation:'h',y:1.15,x:0,font:{size:12}},xaxis:{gridcolor:'#edf1f1',zerolinecolor:'#cbd6da'},yaxis:{gridcolor:'#edf1f1',zerolinecolor:'#cbd6da'},hoverlabel:{font:{family:'Segoe UI, Arial',size:13}}};
  function draw(id,traces,layout={}) {
    const node=document.getElementById(id);if(!node)return;node.style.height=(layout.height||300)+'px';
    Plotly.newPlot(node,traces,{...commonLayout,...layout},{responsive:true,displaylogo:false,modeBarButtonsToRemove:['select2d','lasso2d'],toImageButtonOptions:{format:'png',filename:'hydraulic-statistics',scale:2}}).catch(error=>{node.textContent='Chart could not load: '+error.message;console.error(error);});
  }
  const heatmap=(id,a,title)=>draw(id,[{type:'heatmap',z:a,x:short,y:short,zmin:-1,zmax:1,colorscale:'RdBu',reversescale:true,text:a.map(row=>row.map(v=>v.toFixed(3))),texttemplate:'%{text}',textfont:{size:11},colorbar:{thickness:10,len:.8},hovertemplate:'%{y} and %{x}<br>Correlation = %{z:.3f}<extra></extra>'}],{title:{text:title,font:{size:15}},height:350,margin:{l:110,r:45,t:38,b:85},xaxis:{tickangle:-25,tickfont:{size:11}},yaxis:{autorange:'reversed',tickfont:{size:11}}});
  function hydrateMath(){document.querySelectorAll('[data-math]').forEach(node=>katex.render(node.dataset.math,node,{displayMode:true,throwOnError:false,strict:'ignore'}));}


  function overview(){return heading('Multivariate Statistical Diagnosis of Hydraulic Cooler Faults','Detecting machine faults from multiple sensor signals')+points([
    'A hydraulic cooler removes heat from the system. We study how its recorded condition is reflected in temperature, flow, pressure, power and vibration.',
    'Our aim is to distinguish full efficiency, reduced efficiency and near failure from these readings, and check whether the model still works without its temperature sensor.',
    'In R, we compare the mean profiles and covariance, use MANOVA and Hotelling’s T² to test differences, and train a Gaussian model to predict the condition.'
  ])+`<p class="source-line">Dataset: <a href="https://doi.org/10.24432/C5CW21" target="_blank" rel="noopener">UCI Condition Monitoring of Hydraulic Systems</a> · Helwig, Pignanelli &amp; Schütze · CC BY 4.0</p>`;}

  function design(){return heading('The data and our approach')+points([
    '<strong>2,205 cycles</strong>, each lasting 60 seconds. We use the 1,449 cycles marked stable for the main analysis.',
    'Six features: temperature mean and trend, mean flow, pressure fluctuation, mean power and mean vibration.',
    'R averages stable cycles within 48 matched operating settings for comparison. For prediction, 12 settings are kept out of training.'
  ])+chart('recording-order','Mean temperature across the recording sequence');}

  function means(){return heading('Mean vector: the typical sensor profile')+points([
    'R calculates the six averages for each condition. Together, they describe its typical profile.'
  ])+math(String.raw`\bar{\mathbf{x}}_k=\frac{1}{48}\sum_{s=1}^{48}\mathbf{x}_{sk}`)+`<div class="controls"><label for="mean-group">Cooler condition</label><select id="mean-group"><option value="all">Compare all three</option>${ORDER.map(k=>`<option value="${k}">${label(k)}</option>`).join('')}</select></div>`+chart('mean-vector','Mean profiles, with a choice of cooler condition');}

  function covariancePage(){return heading('Covariance and correlation')+points([
    'Covariance shows which readings vary together. Correlation puts this relationship on a scale from −1 to +1.'
  ])+math(String.raw`r_{ij}=\frac{s_{ij}}{\sqrt{s_{ii}s_{jj}}}`)+groupSelect('cov-group')+chart('cov-heat','Sensor correlations for the selected condition')+`<ul id="cov-insight" class="points insights" aria-live="polite"></ul><details><summary>Covariance values</summary><div id="cov-matrix"></div></details>`;}

  function generalized(){const full=groupSummary(100),near=groupSummary(3);return heading('Generalized variance: joint spread')+points([
    'The covariance determinant summarises spread across all six features. We compare its sixth root using the same scale for every group.'
  ])+math(String.raw`GV=|S|,\qquad SGV=|S|^{1/6}`)+chart('gv-chart','Joint spread by recorded cooler condition')+points([
    `Near failure has a <strong>${num(near.standardized_generalized_variance/full.standardized_generalized_variance,1)} times larger</strong> value than full efficiency. The conditions differ in variation as well as their averages.`
  ],'insights');}

  function distributions(){return heading('Skewness, kurtosis and normality')+points([
    'Skewness checks asymmetry. Kurtosis checks fourth-order spread and tail behaviour. Mardia’s measures check the six features together.',
    'R compares each condition with 999 simulated normal samples of the same size.'
  ])+groupSelect('normal-group')+`<div class="two-plots">${chart('normal-qq','Temperature normal quantile plot')}${chart('normal-skew','Skewness of the six features')}</div><ul id="normal-insight" class="points insights" aria-live="polite"></ul><details><summary>Mardia test values</summary><div id="normal-results"></div></details>`;}

  function mle(){return heading('Maximum likelihood estimation')+points([
    'We fit a Gaussian model by estimating each condition’s mean and covariance. Maximum likelihood chooses the estimates that best describe the observed readings.'
  ])+math(String.raw`\widehat\mu=\bar{\mathbf{x}},\qquad\widehat\Sigma_{ML}=\frac{1}{n}\sum_i(\mathbf{x}_i-\bar{\mathbf{x}})(\mathbf{x}_i-\bar{\mathbf{x}})^\top`)+chart('mle-surface','Likelihood contour and the two matching R estimates')+points([
    'The formula and R’s numerical fit agree to numerical precision. These fitted means and covariances are what the classifier uses.'
  ],'insights');}

  function manova(){const refs=R.manova.conventional_reference;return heading('MANOVA: testing the six means together')+points([
    'MANOVA tests whether the three conditions share the same six-feature mean profile.',
    'We include the matched operating setting in the R model, so its differences are taken into account.'
  ])+math(String.raw`H_0:\boldsymbol\mu_{100}=\boldsymbol\mu_{20}=\boldsymbol\mu_{3}`)+chart('manova-scatter','Two-feature view of the 144 matched profiles')+points([
    `R gives <strong>Pillai’s trace = ${num(R.manova.pillai,4)}, p &lt; 0.001</strong>. The 999-draw simulation checks agree (p = 0.001): the recorded mean profiles differ.`
  ],'insights')+`<summary>Other MANOVA summaries</summary>${table(['Criterion','Value','Reference p'],Object.entries(refs).map(([name,v])=>[name,num(v.Value??v.value,5),pval(v['Pr > F']??v.p_iid)]))}</details>`;}

  function hotelling(){return heading('Hotelling’s T²: which pairs differ?')+points([
    'We subtract the six profiles at the same setting, then test the 48 matched difference vectors. R adjusts the three pairwise p-values using Holm’s method.'
  ])+math(String.raw`T^2=48\,\bar{\mathbf d}^{\top}S_d^{-1}\bar{\mathbf d}`)+chart('paired-intervals','Paired temperature differences and 95 percent bootstrap intervals')+points([
    'All three pairs differ in their joint means. The temperature intervals stay above zero: near failure is hotter than reduced efficiency, and reduced is hotter than full efficiency.'
  ],'insights')+`<p class="caption">Pointwise 95% temperature intervals from 999 resamples of 4-setting blocks. T² uses all six features. The setting-block order may not capture every time effect.</p><details><summary>Paired test values</summary>${table(['Matched difference','T²','Holm-adjusted reference p'],R.hotelling.map(h=>[`${label(h.to)} minus ${label(h.from)}`,num(h.T2,1),pval(h.p_holm_iid)]))}<p class="caption">The F reference assumes independent Gaussian difference vectors. The report gives the sign-flip sensitivity checks.</p></details>`;}

  function covtest(){const box=R.covariance_tests.box_m,lrt=R.covariance_tests.gaussian_lrt;return heading('Covariance equality: does the spread pattern change?')+points([
    'Box’s M and a Gaussian likelihood-ratio test compare the three covariance matrices.'
  ])+math(String.raw`H_0:\Sigma_{100}=\Sigma_{20}=\Sigma_{3}`)+table(['R test','Statistic','Reference p'],[
    ['Box’s M, corrected chi-square',num(box.chi2,2),pval(box.p_iid)],
    ['Gaussian likelihood ratio',num(lrt.LR,2),pval(lrt.p_iid)]
  ])+points([
    'Both tests reject equal covariance under their reference assumptions. The groups vary differently, as well as having different means.',
    'We therefore compare shared and separate covariance models. The prediction checks decide which one to keep.'
  ],'insights')+`<p class="caption">These comparisons use the matched profiles. Both reference tests have 42 degrees of freedom.</p>`;}

  function partial(){const a=R.partial_regression;return heading('Partial correlation: what remains after adjustment?')+points([
    'R removes the recorded cooler, valve, pump and accumulator group differences using regression. We then correlate what remains.'
  ])+math(String.raw`r_{adjusted}=\operatorname{Corr}(\text{temperature residual},\text{vibration residual})`)+chart('partial-compare','Temperature and vibration correlation before and after adjustment')+points([
    `The correlation falls from <strong>${num(a.raw_correlation[0][5],2)} to ${num(a.adjusted_correlation[0][5],2)}</strong>. Much of the original association comes from differences between the recorded groups.`
  ],'insights')+`<p class="caption">This explains an association in the data. It does not establish a causal effect.</p>`;}

  const mainRCode=String.raw`model <- fit_gaussian(z_train, train$cooler, "shared", alpha = 0)
p <- predict_gaussian(model, z_test, available = 3:6)
pred <- CLASS_ORDER[max.col(p, ties.method = "first")]
mean(pred == test$cooler)  # 1 = all 360 correct`;
  function resampling(){return heading('Model training in R and test results')+points([
    'We train on <strong>1,089 stable cycles from 36 settings</strong>. Six grouped validation folds select the shared covariance model.',
    'The final test uses 360 stable cycles from 12 other settings. Temperature alone already gets all 360 right when TS2 is available.'
  ])+chart('benchmark-chart','Temperature baseline and shared model, with and without TS2')+points([
    'Without TS2, the shared model still gets <strong>360/360 correct</strong>. The temperature-only model falls to 33.3%. The other sensors provide the useful fallback.'
  ],'insights')+`<details id="r-implementation"><summary>Main R implementation</summary><pre class="r-snippet"><code>${esc(mainRCode)}</code></pre><p class="caption">The training and test matrices use scaling learned from training rows. available = 3:6 keeps flow, pressure fluctuation, power and vibration. The project functions and full steps are in R/Presentation_Demo.R and R/statistics_core.R.</p></details>`;}
  const examples=ORDER.map(k=>D.cycles.find(c=>c.cooler===k&&c.stable&&c.split==='holdout'));
  let selectedCycle=examples[0], readings=selectedCycle.values.slice(), modelKind=R.selected_model, temperatureAvailable=true;
  const modelNames={temperature:'Temperature only',diagonal:'Diagonal covariance',shared:'Shared covariance',full:'Separate class covariances'};
  function prototype(){return heading('Test our model by changing its readings')+points([
    'Choose Full efficiency, Reduced efficiency or Near failure. Change a reading and watch the model prediction.',
    'Turn TS2 off to test the four remaining features. The model uses the parameters fitted in R.'
  ])+`<div class="controls example-controls"><label for="example-condition">Recorded example</label><select id="example-condition">${examples.map(c=>`<option value="${c.cooler}" ${c.id===selectedCycle.id?'selected':''}>${label(c.cooler)}</option>`).join('')}</select><button id="reset-example" type="button">Reset readings</button></div><p id="cycle-context" class="caption"></p>`+
    `<div class="model-layout"><section class="sensor-inputs"><h2>Sensor readings</h2><div class="controls"><label for="model-select">Model</label><select id="model-select">${Object.keys(R.models).map(k=>`<option value="${k}" ${k===modelKind?'selected':''}>${modelNames[k]}</option>`).join('')}</select></div><label class="temperature-control"><input id="temperature-available" type="checkbox" ${temperatureAvailable?'checked':''}> TS2 temperature sensor available</label><div class="reading-controls">${meta.map((m,i)=>{const values=D.cycles.map(c=>c.values[i]),lo=Math.min(...values),hi=Math.max(...values);return `<div class="reading" data-reading="${i}"><div class="reading-head"><label for="reading-${i}">${m.name}</label><input id="reading-${i}" type="number" step="any" value="${readings[i]}"></div><input aria-label="Adjust ${m.name}" data-slider="${i}" type="range" min="${lo}" max="${hi}" step="${(hi-lo)/1000}" value="${readings[i]}"><small>${m.unit}</small></div>`;}).join('')}</div><p id="prototype-error" class="input-error" role="alert"></p></section>`+
    `<section class="model-output"><h2>Predicted condition</h2><p id="scenario-kind" class="caption">Recorded readings</p><div id="prediction-label" class="prediction-label"></div><p id="prediction-context"></p><div id="probabilities" aria-live="polite"></div><p class="caption">These are probabilities from the fitted model, not a guarantee about the machine.</p><details><summary>How is the prediction calculated?</summary><div id="score-table"></div>${math(String.raw`\log q_k=\log\pi_k-\frac12\left[p\log(2\pi)+\log|\Sigma_k|+D_k^2\right]`)}<p class="caption">The score combines the class prior, covariance and joint distance. With TS2 unavailable, we use the mean subvector and covariance submatrix for the remaining four measurements.</p></details></section></div>`;}


  function conclusion(){return heading('Conclusion')+points([
    '<strong>Near failure has a clear sensor pattern:</strong> higher temperature, lower flow and greater joint variation in these recordings.',
    '<strong>The mean differences remain after matching operating settings.</strong> MANOVA and paired Hotelling’s T² separate the recorded conditions.',
    '<strong>The main modelling benefit is a fallback without TS2.</strong> The joint model keeps its 360/360 stable test result when both TS2 features are removed.',
    `<strong>The test conditions matter.</strong> Accuracy falls to ${pct(R.transition_stress.accuracy)} on cycles flagged as possibly not stable. New recording sessions and other machines are needed before wider use.`
  ])+`<p class="source-line">Dataset: Helwig, Pignanelli &amp; Schütze · <a href="https://doi.org/10.24432/C5CW21" target="_blank" rel="noopener">UCI 447</a> · CC BY 4.0</p>`;}

  function mlePlot(){const g=R.presentation_charts.mle,m=R.numerical_MLE;
    draw('mle-surface',[{x:g.x,y:g.y,z:g.log_likelihood,type:'contour',showscale:false,contours:{coloring:'lines'},line:{width:1.2},colorscale:[[0,'#cadcdf'],[1,C[100]]],hovertemplate:'Temperature mean: %{x:.4f}<br>Power mean: %{y:.4f}<br>Log likelihood: %{z:.3f}<extra>R calculation</extra>'},
      {x:[m.analytic_parameters[0]],y:[m.analytic_parameters[1]],type:'scatter',mode:'markers',name:'Formula estimate',marker:{symbol:'cross',size:13,color:C[100]}},
      {x:[m.numerical_parameters[0]],y:[m.numerical_parameters[1]],type:'scatter',mode:'markers',name:'R optim() estimate',marker:{symbol:'circle-open',size:18,color:C[20],line:{width:2}}}],
      {height:290,xaxis:{title:'Temperature mean parameter (common scale)'},yaxis:{title:'Power mean parameter (common scale)'},margin:{l:78,r:25,t:45,b:60}});
  }

  function hotellingPlot(){const rows=R.presentation_charts.paired_temperature_intervals,j=1;
    draw('paired-intervals',[{x:rows.map(h=>h.mean),y:[1,2,3],type:'scatter',mode:'markers',showlegend:false,marker:{color:C[100],size:10},error_x:{type:'data',symmetric:false,array:rows.map(h=>h.blocks[j].upper-h.mean),arrayminus:rows.map(h=>h.mean-h.blocks[j].lower),color:C[100],thickness:2,width:7},hovertemplate:'Mean difference %{x:.2f} °C<extra>95% block-bootstrap interval</extra>'}],{height:290,xaxis:{title:'Mean temperature difference (°C)',range:[0,21]},yaxis:{tickmode:'array',tickvals:[1,2,3],ticktext:['Reduced minus full','Near failure minus full','Near failure minus reduced'],range:[.5,3.5]},margin:{l:205,r:30,t:15,b:60},shapes:[{type:'line',x0:0,x1:0,y0:.5,y1:3.5,line:{color:MUTED,dash:'dot',width:1}}]});
  }
  function orderPlot(){draw('recording-order',ORDER.map(k=>{const rows=D.cycles.filter(c=>c.cooler===k);return{x:rows.map(c=>c.id),y:rows.map(c=>c.values[0]),type:'scatter',mode:'lines',name:label(k),line:{color:C[k],width:1.5},hovertemplate:'Cycle %{x}<br>Temperature %{y:.2f} °C<extra>'+label(k)+'</extra>'};}),{height:290,xaxis:{title:'Original cycle number'},yaxis:{title:'Mean temperature (°C)'}});}

  function meanPlot(){const selected=document.getElementById('mean-group').value,groups=selected==='all'?R.group_summaries:[groupSummary(Number(selected))];
    draw('mean-vector',groups.map(g=>({x:short,y:g.mean_z,error_y:{type:'data',array:g.covariance_z.map((row,j)=>Math.sqrt(row[j])),visible:true,thickness:1,width:4},type:'scatter',mode:'lines+markers',name:g.label,line:{color:C[g.cooler],width:2},marker:{size:8}})),{height:290,yaxis:{title:'Common-scale value',range:[-2.5,2.5]},xaxis:{tickangle:-15}});
    const g=groups[0];document.getElementById('mean-insight').innerHTML=selected==='all'?'<li>From full efficiency to near failure, mean temperature rises from <strong>41.6 to 60.2 °C</strong> and mean flow falls from <strong>6.53 to 4.92 L/min</strong>.</li>':`<li><strong>${g.label}:</strong> temperature ${num(g.mean_raw[0],1)} °C, flow ${num(g.mean_raw[2],2)} L/min and vibration ${num(g.mean_raw[5],3)} mm/s.</li>`;
  }
  function covariancePlot(k){const g=groupSummary(k);heatmap('cov-heat',g.correlation,label(k));const pair=k===3?[2,3]:[2,4],v=g.correlation[pair[0]][pair[1]];
    document.getElementById('cov-insight').innerHTML=`<li>For ${label(k).toLowerCase()}, ${short[pair[0]].toLowerCase()} and ${pair[1]===3?'pressure fluctuation':'motor power'} have correlation <strong>${num(v,3)}</strong>. Higher flow tends to accompany ${pair[1]===3?'lower pressure fluctuation':'lower motor power'} across these settings.</li>`;
    document.getElementById('cov-matrix').innerHTML=table(['',...short],g.covariance_z.map((row,i)=>[short[i],...row.map(v=>num(v,3))]));}
  function gvPlot(){draw('gv-chart',[{x:R.group_summaries.map(g=>g.label),y:R.group_summaries.map(g=>g.standardized_generalized_variance),type:'bar',marker:{color:ORDER.map(k=>C[k])},text:R.group_summaries.map(g=>g.standardized_generalized_variance.toFixed(4)),textposition:'outside'}],{height:300,yaxis:{title:'Sixth root of covariance determinant',range:[0,.049]},margin:{l:80,r:25,t:25,b:60}});}
  function normalPlots(k){
    const values=D.profiles.filter(c=>c.cooler===k).map(c=>c.values[0]).sort((a,b)=>a-b),n=values.length,mu=values.reduce((a,b)=>a+b,0)/n,sd=Math.sqrt(values.reduce((s,x)=>s+(x-mu)**2,0)/(n-1));
    function inverseNormal(p){let lo=-8,hi=8;for(let i=0;i<50;i++){const mid=(lo+hi)/2,t=1/(1+.2316419*Math.abs(mid)),density=Math.exp(-mid*mid/2)/Math.sqrt(2*Math.PI),tail=density*t*(.319381530+t*(-.356563782+t*(1.781477937+t*(-1.821255978+t*1.330274429)))),cdf=mid>=0?1-tail:tail;if(cdf<p)lo=mid;else hi=mid;}return(lo+hi)/2;}
    const q=values.map((_,i)=>inverseNormal((i+.5)/n)),g=R.distribution_checks.groups.find(g=>g.cooler===k);
    draw('normal-qq',[{x:q,y:values,type:'scatter',mode:'markers',marker:{color:C[k],size:7},name:'Observed profiles'},{x:[q[0],q.at(-1)],y:[mu+sd*q[0],mu+sd*q.at(-1)],type:'scatter',mode:'lines',line:{color:MUTED,width:1},name:'Normal reference'}],{height:310,xaxis:{title:'Normal quantile'},yaxis:{title:'Mean temperature (°C)'},margin:{l:60,r:15,t:45,b:60},legend:{orientation:'h',font:{size:11},y:1.17}});
    draw('normal-skew',[{x:short,y:g.univariate_skewness,type:'bar',marker:{color:C[k]}}],{height:310,xaxis:{tickangle:-30,tickfont:{size:11}},yaxis:{title:'Feature skewness'},showlegend:false,margin:{l:60,r:15,t:30,b:80}});
    document.getElementById('normal-insight').innerHTML=`<li>${label(k)}: skewness p = <strong>${pval(g.skew_p_mc)}</strong>; kurtosis p = <strong>${pval(g.kurtosis_p_mc)}</strong>. ${g.skew_p_mc<.05?'The skewness result suggests that a Gaussian fit is imperfect.':'Neither check gives strong evidence against a Gaussian fit.'}</li><li>We use Gaussian models as an approximation and check them on held-out settings.</li>`;
    document.getElementById('normal-results').innerHTML=table(['Check','Value','Monte Carlo p'],[['Mardia skewness',num(g.skewness),pval(g.skew_p_mc)],['Mardia kurtosis',num(g.kurtosis),pval(g.kurtosis_p_mc)]]);
  }

  function manovaPlot(){draw('manova-scatter',ORDER.map(k=>{const rows=D.profiles.filter(p=>p.cooler===k);return{x:rows.map(p=>p.values[0]),y:rows.map(p=>p.values[2]),type:'scatter',mode:'markers',name:label(k),marker:{color:C[k],size:8,opacity:.75},hovertemplate:'Temperature %{x:.2f} °C<br>Flow %{y:.2f} L/min<extra>'+label(k)+'</extra>'};}),{height:280,xaxis:{title:'Mean temperature (°C)'},yaxis:{title:'Mean flow (L/min)'},margin:{l:70,r:25,t:38,b:58}});}
  function partialPlot(){const a=R.partial_regression,values=[a.raw_correlation[0][5],a.adjusted_correlation[0][5]];draw('partial-compare',[{type:'bar',x:['Before adjustment','After adjustment'],y:values,text:values.map(v=>v.toFixed(2)),textposition:'outside',marker:{color:[C[20],C[100]]},hovertemplate:'Correlation %{y:.3f}<extra></extra>'}],{height:280,yaxis:{title:'Correlation r',range:[0,1.1]},margin:{l:70,r:25,t:20,b:58}});}
  function benchmarkPlot(){const kinds=['temperature','shared'];draw('benchmark-chart',[{x:['Temperature only','Shared multi-sensor model'],y:kinds.map(k=>100*R.predictive_results[k].intact.balanced_accuracy),type:'bar',name:'All readings',marker:{color:C[100]},text:kinds.map(k=>pct(R.predictive_results[k].intact.balanced_accuracy)),textposition:'outside'},{x:['Temperature only','Shared multi-sensor model'],y:kinds.map(k=>100*R.predictive_results[k].TS2_unavailable.balanced_accuracy),type:'bar',name:'TS2 unavailable',marker:{color:C[20]},text:kinds.map(k=>pct(R.predictive_results[k].TS2_unavailable.balanced_accuracy)),textposition:'outside'}],{height:280,barmode:'group',yaxis:{title:'Test balanced accuracy (%)',range:[0,116]},margin:{l:75,r:25,t:42,b:60}});}
  function bindPrototype(){
    function load(k){selectedCycle=examples.find(c=>c.cooler===k)||examples[0];readings=selectedCycle.values.slice();meta.forEach((_,i)=>{document.getElementById('reading-'+i).value=readings[i];document.querySelector('[data-slider="'+i+'"]').value=readings[i];});document.getElementById('cycle-context').textContent=`Cycle ${selectedCycle.id}, recorded as ${label(selectedCycle.cooler).toLowerCase()}`;document.getElementById('scenario-kind').textContent='Recorded readings';updatePrototype();}
    document.getElementById('example-condition').addEventListener('change',e=>load(Number(e.target.value)));
    document.getElementById('reset-example').addEventListener('click',()=>load(Number(document.getElementById('example-condition').value)));
    meta.forEach((_,i)=>{const number=document.getElementById('reading-'+i),slider=document.querySelector('[data-slider="'+i+'"]');number.addEventListener('input',()=>{readings[i]=number.value===''?NaN:Number(number.value);if(Number.isFinite(readings[i]))slider.value=readings[i];document.getElementById('scenario-kind').textContent='Edited readings';updatePrototype();});slider.addEventListener('input',()=>{readings[i]=Number(slider.value);number.value=readings[i];document.getElementById('scenario-kind').textContent='Edited readings';updatePrototype();});});
    document.getElementById('temperature-available').addEventListener('change',e=>{temperatureAvailable=e.target.checked;updatePrototype();});
    document.getElementById('model-select').addEventListener('change',e=>{modelKind=e.target.value;updatePrototype();});load(selectedCycle.cooler);
  }
  function updatePrototype(){const available=temperatureAvailable?[0,1,2,3,4,5]:[2,3,4,5];[0,1].forEach(i=>{document.querySelector('[data-reading="'+i+'"]').classList.toggle('disabled',!temperatureAvailable);document.getElementById('reading-'+i).disabled=!temperatureAvailable;document.querySelector('[data-slider="'+i+'"]').disabled=!temperatureAvailable;});
    try{const output=HydraulicModel.predict(R.models[modelKind],R.prediction_scale,readings,available);document.getElementById('prototype-error').textContent='';document.getElementById('prediction-label').textContent=output.observedDimensions?label(ORDER[output.predictedIndex]):'No temperature reading';document.getElementById('prediction-context').textContent=output.observedDimensions?`${output.observedDimensions} measurements used. ${label(ORDER[output.predictedIndex])} has the highest model score.`:'The temperature-only model has no input here, so it returns the proportions learned from training.';
      document.getElementById('probabilities').innerHTML=output.probabilities.map((p,i)=>`<div class="probability-row"><span>${label(ORDER[i])}</span><div class="probability-track"><div class="probability-fill" style="width:${100*p}%;background:${C[ORDER[i]]}"></div></div><strong>${pct(p)}</strong></div>`).join('');document.getElementById('score-table').innerHTML=table(['Condition','Log prior','Log |Σ|','D²','Log score'],output.details.map((d,i)=>[label(ORDER[i]),num(d.logPrior,3),num(d.logDeterminant,3),num(d.distance,3),num(d.score,3)]));
    }catch(error){document.getElementById('prototype-error').textContent=error.message;document.getElementById('prediction-label').textContent='Check the readings';document.getElementById('prediction-context').textContent='Enter a number for each available measurement.';document.getElementById('probabilities').innerHTML='';document.getElementById('score-table').innerHTML='';}
  }
  const sections=[
    ['overview','Project title and objective',overview,()=>{}],
    ['design','Data and approach',design,orderPlot],
    ['means','Mean vector',means,()=>{document.getElementById('mean-group').addEventListener('change',meanPlot);meanPlot();}],
    ['covariance','Covariance and correlation',covariancePage,()=>bindGroup('cov-group',covariancePlot)],
    ['generalized','Generalized variance',generalized,gvPlot],
    ['distributions','Distribution checks',distributions,()=>bindGroup('normal-group',normalPlots)],
    ['mle','Maximum likelihood estimation',mle,mlePlot],
    ['manova','MANOVA',manova,manovaPlot],
    ['hotelling','Hotelling’s T²',hotelling,hotellingPlot],
    ['covtest','Covariance equality tests',covtest,()=>{}],
    ['partial','Partial correlation',partial,partialPlot],
    ['resampling','R training and test results',resampling,()=>{benchmarkPlot();document.getElementById('r-implementation').addEventListener('toggle',resizePlots);}],
    ['prototype','Test our model',prototype,bindPrototype],
    ['conclusion','Conclusion',conclusion,()=>{}]
  ];
  let index=0;
  function render(){const hash=location.hash.slice(1),found=sections.findIndex(s=>s[0]===hash);index=found<0?0:found;document.querySelectorAll('#navigation a').forEach((a,i)=>{a.classList.toggle('active',i===index);if(i===index)a.setAttribute('aria-current','page');else a.removeAttribute('aria-current');});document.getElementById('mobile-chapter').value=sections[index][0];document.getElementById('chapter-label').textContent=sections[index][1];document.querySelectorAll('.js-plotly-plot').forEach(node=>Plotly.purge(node));main.dataset.slideId=sections[index][0];main.innerHTML=sections[index][2]();hydrateMath();sections[index][3]();document.getElementById('page-counter').textContent=`Slide ${index+1} of ${sections.length}`;document.getElementById('presentation-counter').textContent=`${index+1} / ${sections.length}`;document.getElementById('previous').disabled=index===0;document.getElementById('next').disabled=index===sections.length-1;window.scrollTo(0,0);}
  document.getElementById('navigation').innerHTML=sections.map((s,i)=>`<a href="#${s[0]}"><span class="nav-number">${i+1}</span><span>${s[1]}</span></a>`).join('');
  document.getElementById('mobile-chapter').innerHTML=sections.map((s,i)=>`<option value="${s[0]}">${i+1}. ${s[1]}</option>`).join('');
  document.getElementById('mobile-chapter').addEventListener('change',e=>location.hash=e.target.value);
  const move=delta=>{index=Math.max(0,Math.min(sections.length-1,index+delta));location.hash=sections[index][0];};
  document.getElementById('present').addEventListener('click',()=>{document.body.classList.add('presenting');document.getElementById('next').focus();resizePlots();});
  document.getElementById('exit-presentation').addEventListener('click',()=>{document.body.classList.remove('presenting');resizePlots();});
  document.getElementById('previous').addEventListener('click',()=>move(-1));document.getElementById('next').addEventListener('click',()=>move(1));
  function resizePlots(){requestAnimationFrame(()=>document.querySelectorAll('.js-plotly-plot').forEach(node=>Plotly.Plots.resize(node)));}
  document.addEventListener('keydown',e=>{if(!document.body.classList.contains('presenting'))return;if(e.key==='Escape'){document.body.classList.remove('presenting');resizePlots();return;}if(['INPUT','SELECT','TEXTAREA'].includes(e.target.tagName))return;if(e.key==='ArrowRight'){e.preventDefault();move(1);}if(e.key==='ArrowLeft'){e.preventDefault();move(-1);}});
  window.addEventListener('hashchange',render);render();
})();
