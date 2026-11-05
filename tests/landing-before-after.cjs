const {chromium}=require('playwright');
const fs=require('fs'),http=require('http'),path=require('path');
const ROOT=process.cwd(),ORIGINAL=path.resolve(ROOT,'../landing-original');
const targets=[{name:'original',root:ORIGINAL},{name:'cleanup',root:ROOT}];
const contentTypes={'.html':'text/html','.js':'text/javascript','.css':'text/css','.json':'application/json','.png':'image/png','.svg':'image/svg+xml','.jpg':'image/jpeg','.webp':'image/webp','.woff2':'font/woff2'};
function serve(root){return new Promise(resolve=>{const server=http.createServer((req,res)=>{const requested=decodeURIComponent((req.url||'/').split('?')[0]);const file=path.resolve(root,'.'+(requested==='/'?'/index.html':requested));if(!file.startsWith(root+path.sep)){res.writeHead(403);return res.end();}fs.readFile(file,(error,bytes)=>{if(error){res.writeHead(404);return res.end();}res.writeHead(200,{'content-type':contentTypes[path.extname(file)]||'application/octet-stream','cache-control':'no-store'});res.end(bytes);});});server.listen(0,'127.0.0.1',()=>resolve({server,url:'http://127.0.0.1:'+server.address().port+'/'}));});}
function median(a){const x=[...a].sort((a,b)=>a-b);return x[Math.floor(x.length/2)];}
(async()=>{
 const browser=await chromium.launch({headless:true});const servers=await Promise.all(targets.map(t=>serve(t.root)));const results={method:'Local static servers, external requests blocked, 5 fresh browser contexts each; no server/API performance measured',modes:{}};
 try{
  for(const mode of [{name:'desktop',width:1280,height:800},{name:'mobile',width:390,height:844}]){
   const runs={};
   for(let j=0;j<5;j++)for(let i=0;i<2;i++){const t=targets[i],target=servers[i],ctx=await browser.newContext({viewport:{width:mode.width,height:mode.height},serviceWorkers:'block',reducedMotion:'reduce'}),page=await ctx.newPage();let bytes=0,requests=0,errors=[];
    page.on('pageerror',e=>errors.push(e.message));page.on('response',async r=>{if(new URL(r.url()).origin===new URL(target.url).origin&&r.ok()){requests++;bytes+=Number(r.headers()['content-length'])||0;}});
    await page.route('**/*',route=>{if(new URL(route.request().url()).origin!==new URL(target.url).origin)return route.abort('blockedbyclient');return route.continue();});
    const start=Date.now();try{await page.goto(target.url,{waitUntil:'domcontentloaded',timeout:20000});await page.waitForTimeout(750);const timing=await page.evaluate(()=>({dcl:performance.getEntriesByType('navigation')[0]?.domContentLoadedEventEnd||null,load:performance.getEntriesByType('navigation')[0]?.loadEventEnd||null,resources:performance.getEntriesByType('resource').filter(e=>e.name.startsWith(location.origin)).reduce((n,e)=>n+(e.transferSize||0),0),search:!!document.querySelector('#sailor-search-input'),regatta:!!document.querySelector('#public-regattas-list'),overflow:document.documentElement.scrollWidth>innerWidth+2}));(runs[t.name]??=[]).push({...timing,elapsed:Date.now()-start,requests,errors});}catch(e){(runs[t.name]??=[]).push({error:String(e)});}await ctx.close();
   }
   results.modes[mode.name]=Object.fromEntries(Object.entries(runs).map(([k,v])=>[k,{samples:v,medianDCL:median(v.map(x=>x.dcl).filter(Number.isFinite)),medianResourceBytes:median(v.map(x=>x.resources).filter(Number.isFinite))}]));
  }
 }finally{await browser.close();await Promise.all(servers.map(x=>new Promise(resolve=>x.server.close(resolve))));}
 fs.mkdirSync('artifacts/landing-coverage',{recursive:true});fs.writeFileSync('artifacts/landing-coverage/before-after.json',JSON.stringify(results,null,2));console.log('BENCHMARK_SUMMARY '+JSON.stringify(Object.fromEntries(Object.entries(results.modes).map(([k,v])=>[k,Object.fromEntries(Object.entries(v).map(([p,d])=>[p,{medianDCL:d.medianDCL,medianResourceBytes:d.medianResourceBytes,errors:d.samples.flatMap(x=>x.errors||[]).length,failures:d.samples.filter(x=>x.error).length}]))]))));
})().catch(e=>{console.error(e);process.exitCode=1;});