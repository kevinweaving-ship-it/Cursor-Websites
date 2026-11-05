// SailingSA syntax gate: parse every active classic JS script without executing it.
// Does not mutate source or contact the production website.
const fs=require('node:fs'), vm=require('node:vm');
let failures=0, passed=0;
for(const p of ['js/landing-app.js','js/landing-bootstrap.js']){
 try{new vm.Script(fs.readFileSync(p,'utf8'),{filename:p});passed++;console.log('PASS',p)}
 catch(e){failures++;console.error('FAIL',p,String(e))}
}
const html=fs.readFileSync('index.html','utf8');
let index=0;
for(const match of html.matchAll(/<script([^>]*)>([\s\S]*?)<\/script>/gi)){
 const attrs=match[1], src=/\bsrc\s*=/.test(attrs), data=/\btype\s*=\s*["']application\/ld\+json["']/.test(attrs);
 if(src||data) continue;
 const line=html.slice(0,match.index).split('\n').length;
 try{new vm.Script(match[2],{filename:'index.html:'+line});passed++;console.log('PASS','index.html:'+line)}
 catch(e){failures++;console.error('FAIL','index.html:'+line,String(e))}
 index++;
}
console.log(JSON.stringify({passed,failures,inlineScripts:index}));
if(failures)process.exitCode=1;
