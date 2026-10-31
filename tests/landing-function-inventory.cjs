// Inventory every JS function in the landing entry graph. No automatic deletions.
const fs=require('fs'),path=require('path'),crypto=require('crypto');
const acorn=require('acorn'),walk=require('acorn-walk');
const entry=fs.readFileSync('index.html','utf8');
const paths=[...entry.matchAll(/<script\b[^>]*\bsrc=["']([^"']+)/g)].map(m=>m[1].split('?')[0].replace(/^\//,'')).filter(p=>fs.existsSync(p));
const inline=[...entry.matchAll(/<script\b(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/gi)].map(m=>m[1]).filter(x=>x.trim());
const inputs=[...paths.map(p=>({file:p,code:fs.readFileSync(p,'utf8')})),...inline.map((code,i)=>({file:'index.html:inline:'+i,code}))];
const definitions=[],errors=[];
for(const {file,code} of inputs){
 let ast;try{ast=acorn.parse(code,{ecmaVersion:'latest',sourceType:'script',locations:true,allowReturnOutsideFunction:true});}catch(e){errors.push({file,error:e.message});continue;}
 const visitor={
 FunctionDeclaration(n,st,c){add(n,n.id?.name,'declaration');walk.base.FunctionDeclaration(n,st,c);},
 FunctionExpression(n,st,c){add(n,n.id?.name||'', 'expression');walk.base.FunctionExpression(n,st,c);},
 ArrowFunctionExpression(n,st,c){add(n,'','arrow');walk.base.ArrowFunctionExpression(n,st,c);}
 };
 function add(n,name,kind){const body=code.slice(n.start,n.end);definitions.push({file,line:n.loc.start.line,name:name||'(anonymous)',kind,start:n.start,end:n.end,sha256:crypto.createHash('sha256').update(body).digest('hex')});}
 walk.recursive(ast,null,visitor);
}
const named=definitions.filter(x=>x.name!=='(anonymous)');
const duplicates=Object.values(Object.groupBy(named,x=>x.name)).filter(a=>a.length>1).map(a=>({name:a[0].name,locations:a.map(x=>({file:x.file,line:x.line,sha256:x.sha256})),sameText:a.every(x=>x.sha256===a[0].sha256)}));
const report={scannedFiles:inputs.map(x=>x.file),functionCount:definitions.length,namedCount:named.length,anonymousCount:definitions.length-named.length,duplicateNames:duplicates,parseErrors:errors,functions:definitions,limitations:['Dynamic function calls, globals, event handlers and cross-route references require runtime verification.','Identical names in separate lexical scopes are not necessarily redundant.','Unexecuted browser coverage does not prove dead code.']};
fs.mkdirSync('artifacts/landing-coverage',{recursive:true});
fs.writeFileSync('artifacts/landing-coverage/function-inventory.json',JSON.stringify(report,null,2));
console.log(JSON.stringify({scannedFiles:report.scannedFiles,functionCount:report.functionCount,namedCount:report.namedCount,duplicateNames:duplicates.length,parseErrors:errors},null,2));
if(errors.length)process.exitCode=1;
