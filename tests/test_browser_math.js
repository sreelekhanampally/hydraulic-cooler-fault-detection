const assert=require('assert');
const fs=require('fs');
const path=require('path');
const model=require('../dist/model.js');
const vm=require('vm');
const fixture=fs.existsSync(path.join(__dirname,'js_oracle_R.json'))?'js_oracle_R.json':'js_oracle.json';
const oracle=JSON.parse(fs.readFileSync(path.join(__dirname,fixture),'utf8'));
const sandbox={window:{}};vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../dist/lab-data.js'),'utf8'),sandbox);
const displayed=sandbox.window.LAB_DATA.analysis;
assert.strictEqual(displayed.language,'R');
assert.deepStrictEqual(JSON.parse(JSON.stringify(displayed.models)),oracle.models);
assert.deepStrictEqual(JSON.parse(JSON.stringify(displayed.prediction_scale)),oracle.scale);
let scoreError=0, probabilityError=0;
for(const item of oracle.cases) {
  const result=model.predict(oracle.models[item.model],oracle.scale,item.raw,item.available);
  result.probabilities.forEach((p,i)=>probabilityError=Math.max(probabilityError,Math.abs(p-item.probabilities[i])));
  result.details.forEach((d,i)=>scoreError=Math.max(scoreError,Math.abs(d.score-item.scores[i])));
  assert(Math.abs(result.probabilities.reduce((a,b)=>a+b,0)-1)<1e-12);
}
assert(scoreError<1e-7,`Log-score discrepancy: ${scoreError}`);
assert(probabilityError<1e-9,`Probability discrepancy: ${probabilityError}`);
assert.throws(()=>model.cholesky([[1,2],[2,1]]));
assert.throws(()=>model.predict(oracle.models.shared,oracle.scale,[NaN,0,0,0,0,0]));
assert.throws(()=>model.predict(oracle.models.shared,oracle.scale,[0,0,0,0,0,0],[1,1]));
// A truly unavailable channel may contain no reading. It must not enter the score.
const example=oracle.cases.find(x=>x.model==='shared'&&x.available.join(',')==='2,3,4,5');
const missing=example.raw.slice();missing[0]=NaN;missing[1]=NaN;
const absent=model.predict(oracle.models.shared,oracle.scale,missing,[2,3,4,5]);
absent.probabilities.forEach((p,i)=>assert(Math.abs(p-example.probabilities[i])<1e-9));
const priors=model.predict(oracle.models.temperature,oracle.scale,[NaN,NaN,NaN,NaN,NaN,NaN],[]);
priors.probabilities.forEach((p,i)=>assert(Math.abs(p-oracle.models.temperature.priors[i])<1e-12));
console.log(JSON.stringify({source:fixture,cases:oracle.cases.length,maxLogScoreError:scoreError,maxProbabilityError:probabilityError,invalidInputGuards:'pass'}));
