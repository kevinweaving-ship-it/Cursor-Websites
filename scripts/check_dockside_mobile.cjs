#!/usr/bin/env node
/**
 * Dockside mobile viewport regression check (read-only).
 *
 * Usage:
 *   node scripts/check_dockside_mobile.cjs [https://sailingsa.co.za/]
 *
 * Uses Chrome DevTools Protocol with true mobile device-metric emulation.
 * Chromium's --window-size=390,844 alone is NOT a mobile viewport: Chrome
 * may keep a wider layout viewport while cropping the PNG to 390px.
 * No dependencies, no screenshot uploads, no mutations of the target site.
 */
'use strict';
const { spawn } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');

const target = process.argv[2] || 'https://sailingsa.co.za/';
const chromePath = process.env.CHROME_PATH ||
    ['/opt/chromium/chrome', '/usr/bin/chromium', '/usr/bin/google-chrome']
      .find(p => fs.existsSync(p));
if (!chromePath) { console.error('FAIL: Chromium binary not found. Set CHROME_PATH.'); process.exit(2); }
const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'dockside-cdp-'));
const browser = spawn(chromePath, [
  '--headless', '--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage',
  '--remote-debugging-port=0', '--remote-allow-origins=*',
  '--user-data-dir=' + profile, 'about:blank'
], { stdio: 'ignore' });

const sleep = t => new Promise(r => setTimeout(r,t));
let ws;
let count = 0;
const pending = new Map();
async function rpc(method, params={}) {
  const id = ++count;
  return await new Promise((resolve,reject)=>{
    const timeout=setTimeout(()=>{pending.delete(id);reject(new Error(method+' timed out'));},10000);
    pending.set(id, v=>{clearTimeout(timeout);resolve(v);});
    ws.send(JSON.stringify({id,method,params}));
  });
}
async function run(){
  let endpoint;
  for(let i=0;i<65;i++){
    try {
      const port=fs.readFileSync(path.join(profile,'DevToolsActivePort'),'utf8').split('\n')[0];
      const tabs=await(await fetch('http://127.0.0.1:'+port+'/json')).json();
      endpoint=tabs.find(x=>x.type==='page')?.webSocketDebuggerUrl;
      if(endpoint) break;
    } catch(e) {}
    await sleep(150);
  }
  if(!endpoint) throw new Error('Chromium CDP startup failed');
  ws=new WebSocket(endpoint);
  await new Promise((resolve,reject)=>{ws.onopen=resolve;ws.onerror=reject;});
  ws.onmessage=e=>{
    const msg=JSON.parse(e.data);
    if(msg.id && pending.has(msg.id)){pending.get(msg.id)(msg);pending.delete(msg.id);}
  };
  let failed=false;
  for(const [width,height] of [[320,740],[360,780],[390,844],[430,932],[844,390]]){
    await rpc('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:true});
    await rpc('Page.navigate',{url:target});
    await sleep(2200);
    const result=await rpc('Runtime.evaluate',{returnByValue:true,expression:`(()=>{
      const card=document.querySelector('#dockside-landing');
      const r=card?.getBoundingClientRect();
      const nodes=card ? [...card.querySelectorAll('*')].filter(e=>{
        const b=e.getBoundingClientRect(),s=getComputedStyle(e);
        return b.width>0&&b.height>0&&s.visibility!=='hidden'&&b.right>Math.min(innerWidth,r.right)+1;
      }) : [];
      return {
        viewport:innerWidth, documentWidth:document.documentElement.scrollWidth,
        cardExists:!!card, cardRight:r?.right??null,
        textCount:card?.querySelectorAll('.dockside-body').length??0,
        clampedTexts:[...(card?.querySelectorAll('.dockside-body')||[])].filter(e=>{
          const css=getComputedStyle(e),clamp=css.webkitLineClamp;
          return (clamp!=='none'&&clamp!=='unset'&&clamp!=='0') ||
            css.textOverflow==='ellipsis' || e.scrollHeight>e.clientHeight+1;
        }).length,
        newestNav:(()=>{
          const p=document.getElementById('landing-roundup-prev');
          const n=document.getElementById('landing-roundup-next');
          return !!p&&!!n&&p.hidden&&!n.hidden&&!n.disabled&&n.getBoundingClientRect().width>0;
        })(),
        overflowCount:nodes.length,
        overflowing:nodes.slice(0,4).map(n=>n.className)
      };
    })()`});
    const d=result.result?.result?.value;
    const ok=d?.cardExists && d.textCount>0 && d.viewport===width &&
      d.documentWidth<=width && d.cardRight<=width+1 && d.overflowCount===0 &&
      d.clampedTexts===0 && d.newestNav;
    if(!ok) failed=true;
    console.log((ok?'PASS':'FAIL')+' '+width+'x'+height+' '+JSON.stringify(d));
  }
  if(failed)process.exitCode=1;
}
run().catch(e=>{console.error('FAIL:',e.message);process.exitCode=1;})
.finally(()=>{try{ws?.close()}catch(e){}browser.kill('SIGTERM');fs.rmSync(profile,{recursive:true,force:true});});
