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

  function overview(){return heading('Multivariate Statistical Diagnosis of Hydraulic Cooler Faults','Detecting cooler faults from multiple sensor signals')+
    points([
      'A hydraulic cooler removes heat from the system. We study how its recorded condition is reflected in temperature, flow, pressure, power and vibration.',
      'Our aim is to distinguish <strong>full efficiency, reduced efficiency and near failure</strong> from these readings, and check whether the model still works without its temperature sensor.',
      'In R, we compare the mean profiles and covariance, use MANOVA and Hotelling’s T² to test differences, and train a Gaussian model to predict the condition.'
    ])+`<p class="source-line">Data: <a href="https://doi.org/10.24432/C5CW21" target="_blank" rel="noopener">UCI hydraulic systems dataset</a>, collected on a laboratory test rig.</p>`;}

  function design(){return heading('The data and our approach')+points([
    'We read the sensor data in R and kept the <strong>1,449 stable cycles</strong> from 2,205 recorded cycles. Each cycle lasts 60 seconds.',
    'In R, we summarized each cycle using six measurements: temperature mean and trend, mean flow, pressure fluctuation, mean motor power and mean vibration.',
    'The same 48 valve, pump and accumulator settings occur under all three cooler conditions. We match these settings for comparisons, and keep 12 complete settings aside for model testing.'
  ])+chart('recording-order','Temperature and cooler condition across the recording sequence')+points([
    'The graph also shows a limitation: each cooler condition was recorded in a separate phase. We can describe their differences, but cannot separate a cooler effect from changes over time.'
  ],'insights');}

  function means(){const full=groupSummary(100),near=groupSummary(3);return heading('Mean vector: how do the conditions differ?')+points([
    'We used <code>colMeans()</code> in R to find the six averages for each condition. This mean vector describes its typical sensor profile.'
  ])+math(String.raw`\bar{\mathbf{x}}_k=\frac{1}{48}\sum_{s=1}^{48}\mathbf{x}_{sk}`)+chart('mean-vector','Mean sensor profiles for the three cooler conditions')+points([
    `Mean temperature rises from <strong>${num(full.mean_raw[0],1)} °C to ${num(near.mean_raw[0],1)} °C</strong>, while mean flow falls from ${num(full.mean_raw[2],2)} to ${num(near.mean_raw[2],2)} L/min between full efficiency and near failure.`,
    'This gives us the first useful pattern: the near-failure group is hotter and has lower flow. Temperature alone is therefore an important baseline to test.'
  ],'insights');}

  function covariancePage(){return heading('Covariance and correlation: which readings move together?')+points([
    'We used <code>cov()</code> and <code>cor()</code> in R to see which readings vary together. Correlation puts this relationship on a scale from −1 to +1.',
    'Choose a condition to see whether its sensors follow the same pattern.'
  ])+math(String.raw`r_{ij}=\frac{s_{ij}}{\sqrt{s_{ii}s_{jj}}}`)+groupSelect('cov-group')+chart('cov-heat','Within-condition sensor correlations')+`<ul id="cov-insight" class="points insights" aria-live="polite"></ul>`+
    `<details><summary>View the covariance matrix</summary><div id="cov-matrix"></div></details>`;}

  function generalized(){const a=groupSummary(100),b=groupSummary(3);return heading('Generalized variance: how much does the whole profile vary?')+points([
    'We calculated the covariance determinant in R using <code>det(S)</code>. It summarizes how much the six measurements vary together.',
    'We use the same scale for every condition so the comparison is meaningful.'
  ])+math(String.raw`GV=|S|,\qquad SGV=|S|^{1/6}`)+chart('gv-chart','Sixth root of the covariance determinant by cooler condition')+points([
    `The near-failure value is <strong>${num(b.standardized_generalized_variance/a.standardized_generalized_variance,1)} times</strong> the full-efficiency value on this common scale.`,
    'The fault profile differs in spread as well as average readings. Our model therefore needs to account for both the centre and the covariance.'
  ],'insights');}

  function distributions(){return heading('Skewness, kurtosis and distribution checks')+points([
    'In R, we checked skewness for asymmetry and kurtosis for tail behaviour. Mardia’s measures check these jointly across the six features.',
    'We checked each condition separately and compared its measures with 999 normal samples generated in R.'
  ])+groupSelect('normal-group')+`<div class="two-plots">${chart('normal-qq','Temperature normal quantile plot')}${chart('normal-skew','Skewness of each feature')}</div><ul id="normal-insight" class="points insights" aria-live="polite"></ul>`+
    `<details><summary>View the multivariate check</summary><div id="normal-results"></div><p class="caption">Monte Carlo p-values use 999 Gaussian samples at n = 48 and p = 6.</p></details>`;}

  function mle(){return heading('Maximum likelihood estimation: fitting the model')+points([
    'In R, we fitted a Gaussian model to each condition by estimating its mean vector and covariance.',
    'Maximum likelihood chooses the estimates that best fit the observed readings. The classifier uses this fitted centre and spread to score a new cycle.'
  ])+math(String.raw`\widehat\mu=\bar{\mathbf{x}},\qquad\widehat\Sigma_{ML}=\frac{1}{n}\sum_i(\mathbf{x}_i-\bar{\mathbf{x}})(\mathbf{x}_i-\bar{\mathbf{x}})^\top`)+
    chart('mle-surface','R log-likelihood surface for the temperature and power means')+`<p>.</p>`+points([
      'We also used <code>optim()</code> in R to check the formula. Both methods gave the same answer to numerical precision.',
      'For Gaussian MLE the covariance divisor is n; the unbiased sample covariance uses n − 1.'
    ],'insights');}

  function manova(){return heading('MANOVA: do the six mean readings differ together?')+points([
    'We used <code>manova()</code> in R to test whether the three conditions have the same mean profile across all six measurements.',
    'We included the operating setting in the model, so each comparison allows for the recorded valve, pump and accumulator settings.'
  ])+math(String.raw`H_0:\boldsymbol\mu_{100}=\boldsymbol\mu_{20}=\boldsymbol\mu_{3}`)+chart('manova-roots','MANOVA generalized eigenvalues')+points([
    `Roy’s largest root is <strong>${num(R.manova.roy,2)}</strong> and Wilks’ lambda is ${num(R.manova.wilks,6)}. The reference tests strongly reject equal mean profiles.`,
    'We conclude that the recorded conditions are separated in their joint means. The recording-phase limitation still applies.'
  ],'insights')+`<details><summary>View MANOVA test values</summary>${table(['Test','Value','R reference p'],Object.entries(R.manova.conventional_reference).map(([name,v])=>[name,num(v.Value,5),pval(v['Pr > F'])]))}</details>`;}

  function hotelling(){return heading('Hotelling’s T²: which pairs of conditions differ?')+points([
    'In R, we matched the same operating settings and subtracted each pair of condition profiles. We then applied Hotelling’s T² to the 48 difference vectors.'
  ])+math(String.raw`T^2=48\,\bar{\mathbf d}^{\top}S_d^{-1}\bar{\mathbf d}`)+
    chart('paired-intervals','R pointwise temperature-difference intervals for the three matched comparisons')+`<p class="caption">Pointwise 95% resampling intervals calculated in R. The T² test uses all six measurements.</p>`+
    points([
      'All three pairs differ in their joint means. We used <code>p.adjust()</code> in R to account for making three comparisons.',
      'The temperature intervals stay above zero: reduced efficiency is hotter than full efficiency, and near failure is hotter than both.'
    ],'insights')+`<details><summary>View the three paired tests</summary>${table(['Difference','T²','Holm-adjusted reference p'],R.hotelling.map(h=>[`${label(h.to)} minus ${label(h.from)}`,num(h.T2,1),pval(h.p_holm_iid)]))}<p class="caption">The F reference assumes independent Gaussian difference vectors. The full report includes sign-flip and block-resampling checks.</p></details>`;}

  function covtest(){const b=R.covariance_tests.box_m;return heading('Covariance equality: is the pattern of variation the same?')+points([
    'We calculated Box’s M and a Gaussian likelihood-ratio test in R to compare the three covariance matrices.',
    `The corrected Box’s M statistic was <strong>${num(b.chi2,2)}</strong>, with p &lt; 0.001. Both tests show that the patterns of variation differ.`
  ])+chart('covariance-null','Box M statistics simulated under the equal-covariance reference in R')+`<p class="caption">.</p>`+points([
    'The conditions do not share the same covariance under these reference tests. Their joint variability changes along with their means.',
    'We still compare shared and separate covariance models on development data. A covariance test alone does not tell us which model predicts best.'
  ],'insights');}

  function partial(){const a=R.partial_regression;return heading('Partial correlation: what remains after adjustment?')+points([
    'In R, we used regression to allow for the recorded cooler, valve, pump and accumulator groups. We then correlated the residuals: the parts left after adjustment.'
  ])+`<div class="two-plots">${chart('partial-raw','Sensor correlations before adjustment')}${chart('partial-adjusted','Sensor correlations after recorded-factor adjustment')}</div>`+
    points([
      `Temperature and vibration have a raw correlation of <strong>${num(a.raw_correlation[0][5],2)}</strong>. After adjustment it falls to <strong>${num(a.adjusted_correlation[0][5],2)}</strong>.`,
      'Much of their original association reflects differences between the recorded groups. They are less closely related once those differences are accounted for.'
    ],'insights')+math(String.raw`r_{ij\cdot X}=\operatorname{Corr}(R_i,R_j),\qquad R=Y-X\widehat B`);}

  function resampling(){return heading('Simulation, resampling and model testing')+points([
    'We trained the Gaussian models in R using 36 settings. We compared them using six training-validation splits, keeping each setting together. A shared covariance matrix worked best.',
    'We then tested on 12 settings kept out of training. Temperature alone and the joint model both classified all 360 stable cycles correctly.',
    'When TS2 is removed, the joint model stays at 100% balanced accuracy; the temperature-only model falls to 33.3%. This is the added value of using other sensors.'
  ])+chart('benchmark-chart','Held-out balanced accuracy with and without temperature')+
    points([
      'In R, we repeated MANOVA on 999 simulated or resampled datasets. All three checks gave p = 0.001. This supports the recorded mean differences, but cannot remove the recording-phase limitation.'
    ],'insights')+
    `<details id="simulation-details"><summary>View the MANOVA simulations</summary><div class="controls"><label for="null-kind">Reference</label><select id="null-kind"><option value="gaussian_iid_null">Independent Gaussian null</option><option value="wild_restricted">Matched restricted wild</option><option value="wild_full_residual">Matched full-residual wild</option></select><label for="null-draws">Draws shown</label><select id="null-draws"><option value="100">100</option><option value="500">500</option><option value="999" selected>999</option></select></div>${chart('null-hist','Simulated Roy statistics under the equal-mean null')}<p id="null-output" class="caption" aria-live="polite"></p></details>`+
    `<details><summary>What does a perfect test score tell us?</summary>${points(['Resampling already-correct test settings gives a bootstrap interval of [100%, 100%]. It cannot create mistakes that have not been observed.','This interval does not guarantee perfect performance on a new machine or recording campaign.'])}</details>`;}

  const examples=ORDER.map(k=>D.cycles.find(c=>c.cooler===k&&c.stable&&c.split==='holdout'));
  let selectedCycle=examples[0], readings=selectedCycle.values.slice(), modelKind=R.selected_model, temperatureAvailable=true;
  const modelNames={temperature:'Temperature only',diagonal:'Diagonal covariance',shared:'Shared covariance',full:'Separate class covariances'};
  function prototype(){return heading('Test our model by changing its readings')+points([
    'Choose a recorded example, then change a reading to see how the prediction changes.',
    'The model was trained in R. This demo uses its saved means and covariance to score each condition and show the highest-scoring one.',
    'Turn off TS2 to test the other four measurements. You can repeat this check in <code>R/Presentation_Demo.R</code>.'
  ])+`<div class="controls example-controls"><label for="example-condition">Recorded example</label><select id="example-condition">${examples.map(c=>`<option value="${c.cooler}" ${c.id===selectedCycle.id?'selected':''}>${label(c.cooler)}</option>`).join('')}</select></div><p id="cycle-context" class="caption"></p>`+
    `<div class="model-layout"><section class="sensor-inputs"><h2>Sensor readings</h2><div class="controls"><label for="model-select">Model</label><select id="model-select">${Object.keys(R.models).map(k=>`<option value="${k}" ${k===modelKind?'selected':''}>${modelNames[k]}</option>`).join('')}</select></div><label class="temperature-control"><input id="temperature-available" type="checkbox" ${temperatureAvailable?'checked':''}> TS2 temperature sensor available</label><div class="reading-controls">${meta.map((m,i)=>{const values=D.cycles.map(c=>c.values[i]),lo=Math.min(...values),hi=Math.max(...values);return `<div class="reading" data-reading="${i}"><div class="reading-head"><label for="reading-${i}">${m.name}</label><input id="reading-${i}" type="number" step="any" value="${readings[i]}"></div><input aria-label="Adjust ${m.name}" data-slider="${i}" type="range" min="${lo}" max="${hi}" step="${(hi-lo)/1000}" value="${readings[i]}"><small>${m.unit}</small></div>`;}).join('')}</div><p id="prototype-error" class="input-error" role="alert"></p></section>`+
    `<section class="model-output"><h2>Predicted condition</h2><p id="scenario-kind" class="caption">Recorded readings</p><div id="prediction-label" class="prediction-label"></div><p id="prediction-context"></p><div id="probabilities" aria-live="polite"></div><p class="caption">These are probabilities from the fitted model, not a guarantee about the machine.</p><details><summary>How is the prediction calculated?</summary><div id="score-table"></div>${math(String.raw`\log q_k=\log\pi_k-\frac12\left[p\log(2\pi)+\log|\Sigma_k|+D_k^2\right]`)}<p class="caption">The score combines the class prior, covariance and joint distance. With TS2 unavailable, we use the mean subvector and covariance submatrix for the remaining four measurements.</p></details></section></div>`;}

  function conclusion() {
  return heading('Conclusion') + points([
    'Our R analysis showed a clear change between full efficiency and near failure: mean temperature rose from 41.6 °C to 60.2 °C, while mean flow fell from 6.53 to 4.92 L/min. Covariance and generalized variance also showed greater joint variation near failure.',

    'MANOVA compared all six mean readings together, and paired Hotelling’s T² found differences between every condition pair after matching operating settings. Simulation and resampling supported these findings under the stated assumptions.',

    'A strong correlation did not always mean a strong relationship after adjustment. The temperature and vibration correlation fell from 0.94 to 0.21 after accounting for the recorded groups. Partial correlation helped us understand how much of the original association came from group differences.',

    'MLE gave us the fitted Gaussian models in R. Normality and covariance tests showed that their assumptions were imperfect, yet shared covariance gave the best cross-validation result. We therefore chose the final model by checking its predictions, alongside examining its assumptions.',

    'On the 360 stable test cycles, temperature alone and the multi-sensor model both achieved 100% accuracy. The advantage of using several sensors became clear when TS2 was removed: the multi-sensor model retained 100% balanced accuracy, while the temperature-only model fell to 33.3%.',

    `Accuracy fell to ${pct(R.transition_stress.accuracy)} on transition cycles, showing that the stable-cycle result did not cover every operating condition. Since the data came from one rig and each condition was recorded at a different time, further testing needs fresh recordings and other machines.`
  ]) + `
    <p class="source-line">
      Dataset: Helwig, Pignanelli &amp; Schütze,
      <a href="https://doi.org/10.24432/C5CW21"
         target="_blank" rel="noopener">UCI 447</a>
      (CC BY 4.0).
    </p>
  `;
}
  function mlePlot(){const g=R.presentation_charts.mle,m=R.numerical_MLE;
    draw('mle-surface',[{x:g.x,y:g.y,z:g.log_likelihood,type:'contour',showscale:false,contours:{coloring:'lines'},line:{width:1.2},colorscale:[[0,'#cadcdf'],[1,C[100]]],hovertemplate:'Temperature mean: %{x:.4f}<br>Power mean: %{y:.4f}<br>Log likelihood: %{z:.3f}<extra>R calculation</extra>'},
      {x:[m.analytic_parameters[0]],y:[m.analytic_parameters[1]],type:'scatter',mode:'markers',name:'Formula estimate',marker:{symbol:'cross',size:13,color:C[100]}},
      {x:[m.numerical_parameters[0]],y:[m.numerical_parameters[1]],type:'scatter',mode:'markers',name:'R optim() estimate',marker:{symbol:'circle-open',size:18,color:C[20],line:{width:2}}}],
      {height:290,xaxis:{title:'Temperature mean parameter (common scale)'},yaxis:{title:'Power mean parameter (common scale)'},margin:{l:78,r:25,t:45,b:60}});
  }
  function hotellingPlot(){const rows=R.presentation_charts.paired_temperature_intervals;
    draw('paired-intervals',[1,4,8].map((size,j)=>({x:rows.map(h=>h.mean),y:rows.map((_,i)=>i+1+(j-1)*.13),type:'scatter',mode:'markers',name:size===1?'1 setting at a time':size+' consecutive settings',marker:{color:[C[100],C[20],C[3]][j],size:7},
      error_x:{type:'data',symmetric:false,array:rows.map(h=>h.blocks[j].upper-h.mean),arrayminus:rows.map(h=>h.mean-h.blocks[j].lower),color:[C[100],C[20],C[3]][j],thickness:2,width:4},hovertemplate:'Mean difference: %{x:.2f} °C<extra>'+size+'-setting resampling</extra>'})),
      {height:290,xaxis:{title:'Mean temperature difference (°C)'},yaxis:{tickmode:'array',tickvals:[1,2,3],ticktext:['Reduced minus full','Near failure minus full','Near failure minus reduced'],range:[.5,3.5]},margin:{l:205,r:25,t:48,b:60}});
  }
  function covarianceNullPlot(){const b=R.covariance_tests.box_m,s=R.covariance_tests.matched_gaussian_null;
    draw('covariance-null',[{type:'histogram',x:s.M_samples,nbinsx:28,marker:{color:C[100]},hovertemplate:'Box M: %{x:.1f}<br>Count: %{y}<extra>R simulation</extra>'}],
      {height:290,xaxis:{title:'Simulated Box M under equal covariance'},yaxis:{title:'Count'},annotations:[{text:'Observed M = '+num(b.M,2)+' (beyond this axis); simulation p = '+num(s.p_mc,3),xref:'paper',yref:'paper',x:1,y:1.13,xanchor:'right',showarrow:false,font:{size:13,color:MUTED}}],margin:{l:70,r:25,t:45,b:60}});
  }
  function orderPlot(){draw('recording-order',ORDER.map(k=>{const rows=D.cycles.filter(c=>c.cooler===k);return{x:rows.map(c=>c.id),y:rows.map(c=>c.values[0]),type:'scatter',mode:'lines',name:label(k),line:{color:C[k],width:1.5},hovertemplate:'Cycle %{x}<br>Temperature %{y:.2f} °C<extra>'+label(k)+'</extra>'};}),{height:290,xaxis:{title:'Original cycle number'},yaxis:{title:'Mean temperature (°C)'}});}
  function meanPlot(){draw('mean-vector',R.group_summaries.map((g,i)=>({x:short,y:g.mean_z,error_y:{type:'data',array:g.covariance_z.map((row,j)=>Math.sqrt(row[j])),visible:true,thickness:1,width:4},type:'scatter',mode:'lines+markers',name:g.label,line:{color:C[g.cooler]},marker:{size:8,symbol:['circle','square','triangle-up'][i]}})),{height:300,yaxis:{title:'Common-scale value'},xaxis:{tickangle:-15}});}
  function covariancePlot(k){const g=groupSummary(k);heatmap('cov-heat',g.correlation,label(k));const pair=k===3?[2,3]:[2,4],v=g.correlation[pair[0]][pair[1]];
    document.getElementById('cov-insight').innerHTML=`<li>For ${label(k).toLowerCase()}, ${short[pair[0]].toLowerCase()} and ${pair[1]===3?'pressure fluctuation':'motor power'} have correlation <strong>${num(v,3)}</strong>. Higher flow tends to accompany ${pair[1]===3?'lower pressure fluctuation':'lower motor power'} across these settings.</li><li>These relationships show why we should compare readings jointly, rather than treat each sensor as unrelated.</li>`;
    document.getElementById('cov-matrix').innerHTML=table(['',...short],g.covariance_z.map((row,i)=>[short[i],...row.map(v=>num(v,3))]));}
  function gvPlot(){draw('gv-chart',[{x:R.group_summaries.map(g=>g.label),y:R.group_summaries.map(g=>g.standardized_generalized_variance),type:'bar',marker:{color:ORDER.map(k=>C[k])},text:R.group_summaries.map(g=>g.standardized_generalized_variance.toFixed(4)),textposition:'outside'}],{height:300,yaxis:{title:'Sixth root of covariance determinant',range:[0,.049]},margin:{l:80,r:25,t:25,b:60}});}
  function normalPlots(k){
    const values=D.profiles.filter(c=>c.cooler===k).map(c=>c.values[0]).sort((a,b)=>a-b),n=values.length,mu=values.reduce((a,b)=>a+b,0)/n,sd=Math.sqrt(values.reduce((s,x)=>s+(x-mu)**2,0)/(n-1));
    function inverseNormal(p){let lo=-8,hi=8;for(let i=0;i<50;i++){const mid=(lo+hi)/2,t=1/(1+.2316419*Math.abs(mid)),density=Math.exp(-mid*mid/2)/Math.sqrt(2*Math.PI),tail=density*t*(.319381530+t*(-.356563782+t*(1.781477937+t*(-1.821255978+t*1.330274429)))),cdf=mid>=0?1-tail:tail;if(cdf<p)lo=mid;else hi=mid;}return(lo+hi)/2;}
    const q=values.map((_,i)=>inverseNormal((i+.5)/n)),g=R.distribution_checks.groups.find(g=>g.cooler===k);
    draw('normal-qq',[{x:q,y:values,type:'scatter',mode:'markers',marker:{color:C[k],size:7},name:'Observed profiles'},{x:[q[0],q.at(-1)],y:[mu+sd*q[0],mu+sd*q.at(-1)],type:'scatter',mode:'lines',line:{color:MUTED,width:1},name:'Normal reference'}],{height:310,xaxis:{title:'Normal quantile'},yaxis:{title:'Mean temperature (°C)'},margin:{l:60,r:15,t:45,b:60},legend:{orientation:'h',font:{size:11},y:1.17}});
    draw('normal-skew',[{x:short,y:g.univariate_skewness,type:'bar',marker:{color:C[k]}}],{height:310,xaxis:{tickangle:-30,tickfont:{size:11}},yaxis:{title:'Feature skewness'},showlegend:false,margin:{l:60,r:15,t:30,b:80}});
    document.getElementById('normal-insight').innerHTML=`<li>${label(k)}: skewness p = <strong>${pval(g.skew_p_mc)}</strong>; kurtosis p = <strong>${pval(g.kurtosis_p_mc)}</strong>. ${g.skew_p_mc<.05?'The skewness result suggests that a Gaussian fit is imperfect.':'Neither check gives strong evidence against a Gaussian fit.'}</li><li>We treat the Gaussian distribution as an approximation, then check its predictions on data excluded from fitting.</li>`;
    document.getElementById('normal-results').innerHTML=table(['Check','Value','Monte Carlo p'],[['Mardia skewness',num(g.skewness),pval(g.skew_p_mc)],['Mardia kurtosis',num(g.kurtosis),pval(g.kurtosis_p_mc)]]);
  }
  function manovaPlot(){draw('manova-roots',[{x:['Largest root','Second root'],y:R.manova.roots.slice(0,2),type:'bar',marker:{color:[C[100],C[20]]},text:R.manova.roots.slice(0,2).map(v=>v.toFixed(2)),textposition:'outside'}],{height:280,yaxis:{title:'Generalized eigenvalue',range:[0,285]},margin:{l:65,r:20,t:25,b:55}});}
  function benchmarkPlot(){const kinds=Object.keys(R.predictive_results);draw('benchmark-chart',[{x:kinds.map(k=>({temperature:'Temperature only',diagonal:'Diagonal',shared:'Shared',full:'Separate covariances'})[k]),y:kinds.map(k=>100*R.predictive_results[k].intact.balanced_accuracy),type:'bar',name:'All measurements',marker:{color:C[100]},text:kinds.map(k=>pct(R.predictive_results[k].intact.balanced_accuracy)),textposition:'outside'},{x:kinds.map(k=>({temperature:'Temperature only',diagonal:'Diagonal',shared:'Shared',full:'Separate covariances'})[k]),y:kinds.map(k=>100*R.predictive_results[k].TS2_unavailable.balanced_accuracy),type:'bar',name:'TS2 unavailable',marker:{color:C[20]},text:kinds.map(k=>pct(R.predictive_results[k].TS2_unavailable.balanced_accuracy)),textposition:'outside'}],{height:300,barmode:'group',yaxis:{title:'Test balanced accuracy (%)',range:[0,116]},margin:{l:70,r:20,t:35,b:55}});}
  function nullPlot(){const key=document.getElementById('null-kind').value,n=Number(document.getElementById('null-draws').value),values=R.manova.resampling[key].roy_samples.slice(0,n),exceed=values.filter(x=>x>=R.manova.roy).length,p=(1+exceed)/(n+1);
    draw('null-hist',[{type:'histogram',x:values,nbinsx:28,marker:{color:C[100]}}],{height:290,xaxis:{title:'Roy statistic under the null'},yaxis:{title:'Simulation count'},annotations:[{text:'Observed Roy = '+num(R.manova.roy,2)+' (beyond this axis)',xref:'paper',yref:'paper',x:1,y:1.12,xanchor:'right',showarrow:false,font:{size:12,color:MUTED}}]});
    document.getElementById('null-output').textContent=`${n} draws shown; ${exceed} exceed the observed statistic. Replay p = ${num(p,5)}; full 999-draw p = ${R.manova.resampling[key].p_mc.toFixed(3)}.`;
  }
  function bindPrototype(){
    function load(k){selectedCycle=examples.find(c=>c.cooler===k)||examples[0];readings=selectedCycle.values.slice();meta.forEach((_,i)=>{document.getElementById('reading-'+i).value=readings[i];document.querySelector('[data-slider="'+i+'"]').value=readings[i];});document.getElementById('cycle-context').textContent=`Cycle ${selectedCycle.id}, recorded as ${label(selectedCycle.cooler).toLowerCase()}`;document.getElementById('scenario-kind').textContent='Recorded readings';updatePrototype();}
    document.getElementById('example-condition').addEventListener('change',e=>load(Number(e.target.value)));
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
    ['means','Mean vector',means,meanPlot],
    ['covariance','Covariance and correlation',covariancePage,()=>bindGroup('cov-group',covariancePlot)],
    ['generalized','Generalized variance',generalized,gvPlot],
    ['distributions','Distribution checks',distributions,()=>bindGroup('normal-group',normalPlots)],
    ['mle','Maximum likelihood estimation',mle,mlePlot],
    ['manova','MANOVA',manova,manovaPlot],
    ['hotelling','Hotelling’s T²',hotelling,hotellingPlot],
    ['covtest','Covariance equality tests',covtest,covarianceNullPlot],
    ['partial','Partial correlation',partial,()=>{heatmap('partial-raw',R.partial_regression.raw_correlation,'Before adjustment');heatmap('partial-adjusted',R.partial_regression.adjusted_correlation,'After adjustment');}],
    ['resampling','Simulation and model testing',resampling,()=>{benchmarkPlot();document.getElementById('null-kind').addEventListener('change',nullPlot);document.getElementById('null-draws').addEventListener('change',nullPlot);document.getElementById('simulation-details').addEventListener('toggle',e=>{if(e.target.open)nullPlot();});}],
    ['prototype','Test our model',prototype,bindPrototype],
    ['conclusion','Conclusion',conclusion,()=>{}]
  ];
  let index=0;
  function render(){const hash=location.hash.slice(1),found=sections.findIndex(s=>s[0]===hash);index=found<0?0:found;document.querySelectorAll('#navigation a').forEach((a,i)=>{a.classList.toggle('active',i===index);if(i===index)a.setAttribute('aria-current','page');else a.removeAttribute('aria-current');});document.getElementById('mobile-chapter').value=sections[index][0];document.getElementById('chapter-label').textContent=sections[index][1];main.innerHTML=sections[index][2]();hydrateMath();sections[index][3]();document.getElementById('page-counter').textContent=`Slide ${index+1} of ${sections.length}`;document.getElementById('presentation-counter').textContent=`${index+1} / ${sections.length}`;window.scrollTo(0,0);}
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
