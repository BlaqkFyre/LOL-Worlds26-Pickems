/* P[a][b] = chance team a beats team b in one game: average over sides, D AI drafts, N sims each */
const { chromium } = require('playwright');const fs=require('fs');
(async()=>{const b=await chromium.launch({executablePath:'/opt/pw-browsers/chromium'});const p=await b.newPage();
 await p.goto('file://'+require('path').resolve('index.html')+'');await p.waitForTimeout(300);
 const M=await p.evaluate(([D,N])=>{const ids=TEAMS.map(t=>t.id),P={};ids.forEach(a=>P[a]={});
  for(const a of ids)for(const c of ids){if(a===c)continue;let w=0;
   for(let d=0;d<D;d++)withDS({blue:a,red:c,fmt:"bo1",locked:[]},()=>{while(DS.steps.length<20)autoStep();for(let i=0;i<N;i++)if(simGame(true).winner==="blue")w++});
   P[a][c]=(P[a][c]||0)+w/(D*N)/2;P[c][a]=(P[c][a]||0)+(1-w/(D*N))/2}
  return {P,ov:Object.fromEntries(TEAMS.map(t=>[t.id,t.ov]))}},[+process.env.D||6,+process.env.N||150]);
 fs.writeFileSync(process.argv[2]||'research/backtest/matrix.json',JSON.stringify(M));console.log('ok',Object.keys(M.P).length);await b.close();})();
