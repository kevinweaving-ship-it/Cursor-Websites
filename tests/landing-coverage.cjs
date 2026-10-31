// Read-only browser coverage harness for SailingSA landing cleanup.
// Runs against a local checkout, never deploys and blocks all non-GET requests.
const { chromium } = require('playwright');
const fs = require('node:fs');
const path = require('node:path');
const BASE = process.env.COVERAGE_BASE_URL || 'http://127.0.0.1:8765/';
const OUT = path.resolve('artifacts/landing-coverage');
fs.mkdirSync(OUT, { recursive: true });

function summarize(entry) {
  const fns = (entry.functions || []).map(f => ({
    name: f.functionName || '(anonymous)',
    executed: f.ranges.some(r => r.count > 0),
    ranges: f.ranges.map(r => ({ start: r.startOffset, end: r.endOffset, hits: r.count }))
  }));
  return { url: entry.url, sourceBytes: (entry.source || '').length,
    totalFunctions: fns.length, executedFunctions: fns.filter(f => f.executed).length,
    functions: fns };
}
async function main() {
  const browser = await chromium.launch({ headless: true });
  const all = [];
  try {
    for (const mode of [{name:'desktop',width:1280,height:800},{name:'mobile',width:390,height:844}]) {
      const context = await browser.newContext({viewport:{width:mode.width,height:mode.height},
        reducedMotion:'reduce', serviceWorkers:'block'});
      const page = await context.newPage();
      const errors=[], requests=[], actions=[];
      page.on('pageerror', e => errors.push(String(e)));
      page.on('request', r => requests.push({method:r.method(), url:r.url()}));
      await page.route('**/*', async route => {
        if (!['GET','HEAD','OPTIONS'].includes(route.request().method()))
          return route.abort('blockedbyclient');
        // Browser may request only local static files and read-only public APIs.
        const u = new URL(route.request().url());
        if (u.origin !== new URL(BASE).origin && !/^(sailingsa\.co\.za|www\.sailingsa\.co\.za)$/.test(u.hostname))
          return route.abort('blockedbyclient');
        return route.continue();
      });
      await page.coverage.startJSCoverage({resetOnNavigation:false,reportAnonymousScripts:true});
      await page.coverage.startCSSCoverage({resetOnNavigation:false});
      try {
        await page.goto(BASE,{waitUntil:'domcontentloaded',timeout:25000});
        await page.waitForTimeout(1800);
        actions.push({name:'initial-load',ok:true});
        await page.screenshot({path:path.join(OUT,mode.name+'-initial.png'),fullPage:true,timeout:15000});
        // Exercise existing search controls without assuming a redirect or submitting forms.
        for (const [name,selector] of [
          ['sailor-tab','.search-mode-btn[data-mode="sailor"]'],
          ['regatta-tab','.search-mode-btn[data-mode="regatta"]']]) {
          try { const loc=page.locator(selector).first();
            if(await loc.isVisible({timeout:1500})){ await loc.click({timeout:4000}); await page.waitForTimeout(500);actions.push({name,ok:true});}
            else actions.push({name,ok:false,reason:'not-visible'});
          } catch(e){actions.push({name,ok:false,reason:String(e).slice(0,160)});}
        }
        for(const [name,selector] of [
          ['regatta-search','#temp-landing-regatta-input'],
          ['sailor-search','#sailor-search-input']]) {
          try{ const loc=page.locator(selector).first();
            if(await loc.isVisible({timeout:1500})){await loc.fill('Mirror',{timeout:4000});await page.waitForTimeout(850);actions.push({name,ok:true});await loc.fill('');}
            else actions.push({name,ok:false,reason:'not-visible'});
          }catch(e){actions.push({name,ok:false,reason:String(e).slice(0,160)});}
        }
        // Inspect state rather than treating clicks alone as proof of functionality.
        const state = await page.evaluate(() => ({
          path: location.pathname,
          sailorInput: document.querySelector('#sailor-search-input')?.value ?? null,
          regattaInput: document.querySelector('#temp-landing-regatta-input')?.value ?? null,
          hasSearchResults: !!document.querySelector('#sailor-search-results'),
          hasProfileContainer: !!document.querySelector('#sailor-view'),
          hasRegattaContainer: !!document.querySelector('#public-regattas-list'),
          headerExists: !!document.querySelector('header.site-header'),
          headerLogoExists: !!document.querySelector('#headerLogoLink'),
          horizontalOverflow: document.documentElement.scrollWidth > innerWidth + 2
        }));
        actions.push({name:'state-inspection',ok:state.headerExists && state.hasSearchResults && state.hasRegattaContainer,state});
        const startingUrl=page.url();
        try { await page.goBack({waitUntil:'domcontentloaded',timeout:3500}).catch(()=>null); }
        catch(_){}
        actions.push({name:'navigation-history-inspection',ok:true,before:startingUrl,after:page.url()});
        await page.screenshot({path:path.join(OUT,mode.name+'-after.png'),fullPage:true,timeout:15000});
      } catch(e) { actions.push({name:'fatal',ok:false,reason:String(e)}); }
      const js=(await page.coverage.stopJSCoverage()).map(summarize);
      const css=(await page.coverage.stopCSSCoverage()).map(e=>({url:e.url,sourceBytes:(e.text||'').length,usedRanges:e.ranges}));
      const report={mode,base:BASE,url:page.url(),actions,errors,requests,js,css};
      fs.writeFileSync(path.join(OUT,mode.name+'.json'),JSON.stringify(report,null,2));
      all.push({mode:mode.name,actions,errors,scriptCount:js.length,
        coverageScripts:js.map(s=>({url:s.url,total:s.totalFunctions,executed:s.executedFunctions}))});
      await context.close();
    }
  }finally{await browser.close();}
  fs.writeFileSync(path.join(OUT,'summary.json'),JSON.stringify(all,null,2));
  console.log(JSON.stringify(all,null,2));
}
main().catch(e=>{console.error(e);process.exitCode=1;});
