#!/usr/bin/env node
/** Dependency-free repository contract check for every website PR. */
'use strict';
const fs=require('node:fs');
const path=require('node:path');
const cp=require('node:child_process');
const root=path.resolve(__dirname,'..');
let failures=0;
function check(label,condition,detail=''){
  console.log((condition?'PASS':'FAIL')+' '+label+(detail?' — '+detail:''));
  if(!condition)failures++;
}
function read(file){
  const p=path.join(root,file);
  check('file '+file,fs.existsSync(p));
  return fs.existsSync(p)?fs.readFileSync(p,'utf8'):'';
}
const agent=read('AGENTS.md');
const sop=read('docs/WEBSITE_DEVELOPMENT_SOP.md');
const router=read('docs/DEVELOPMENT_TOOL_ROUTER.md');
const design=read('docs/design_system.md');
const stitchDesign=read('DESIGN.md');
const mcp=read('.cursor/mcp.json');
const rule=read('.cursor/rules/motionsites.mdc');
const skill=read('.agents/skills/motionsites-web-builder/SKILL.md');
const examples=read('.agents/skills/motionsites-web-builder/examples/INDEX.md');
const css=read('sailingsa/frontend/css/dockside-chat.css');
const roundup=read('sailingsa/frontend/js/landing-roundup-cards.js');
const mobile=read('scripts/check_dockside_mobile.cjs');
const readme=read('README.md');
check('AGENTS points to mandatory SOP',agent.includes('docs/WEBSITE_DEVELOPMENT_SOP.md'));
check('AGENTS points to tool router',agent.includes('docs/DEVELOPMENT_TOOL_ROUTER.md'));
check('README points to SOP',readme.includes('docs/WEBSITE_DEVELOPMENT_SOP.md'));
check('SOP requires REA capabilities',sop.includes('rea-admin <target> -- capabilities'));
check('SOP requires mobile-first 390x844',sop.includes('390×844'));
check('SOP requires screenshots and post-deploy verification',/Visual QA/.test(sop)&&/Verify live asset versions/.test(sop));
check('router covers all tools',['MotionSites','Stitch','REA','GitHub','Codex','Cursor'].every(s=>router.includes(s)));
check('design system available',design.includes('Source of truth'));
check('Stitch DESIGN.md respects canonical tokens and mobile master',stitchDesign.includes('docs/design_system.md')&&stitchDesign.includes('390×844')&&stitchDesign.includes('#001f3f')&&stitchDesign.includes('locked'));
check('MotionSites skill & examples available',skill.includes('MotionSites Web Builder')&&examples.includes('Examples index'));
check('MotionSites always-on Cursor rule',rule.includes('alwaysApply: true')&&rule.includes('390×844'));
try {
  const config=JSON.parse(mcp);
  check('MotionSites MCP registered',config.mcpServers?.MotionSites?.url==='https://motionsites.ai/api/mcp');
  const stitch=config.mcpServers?.Stitch;
  check('Google Stitch MCP registered (not proof of authentication)',stitch?.command==='npx'&&Array.isArray(stitch.args)&&stitch.args.includes('@google/stitch@0.12.1')&&stitch.args.includes('mcp')&&stitch.args.includes('start'));
} catch(e) { check('MCP config valid JSON',false,e.message); }
check('Dockside comments not clamped',!/\#dockside-landing \.dockside-body\s*\{[^}]*-webkit-line-clamp:\s*3/.test(css)&&!/\#dockside-landing \.dockside-op \.dockside-body\s*\{[^}]*-webkit-line-clamp:\s*3/.test(css));
check('Roundup arrows have no-hero fallback',roundup.includes('if (box && box.height)')&&roundup.includes('var title = slide.querySelector(".landing-roundup-title")'));
check('Roundup newest navigation and older navigation',roundup.includes('prevBtn.hidden = !multi || index <= 0')&&roundup.includes('nextBtn.hidden = !multi || index >= count - 1'));
check('Mobile CDP test checks clipping and arrows',mobile.includes('clampedTexts===0')&&mobile.includes('d.newestNav'));
for(const file of ['scripts/check_website_workflow.cjs','scripts/check_dockside_mobile.cjs','sailingsa/frontend/js/landing-roundup-cards.js']){
  const p=cp.spawnSync(process.execPath,['--check',path.join(root,file)],{encoding:'utf8'});
  check('JavaScript syntax '+file,p.status===0,(p.stderr||'').trim().slice(0,200));
}
if(failures){console.error(failures+' website workflow contract check(s) failed');process.exitCode=1;}
else console.log('All website repository contract checks passed. This is not a visual/live deployment assertion.');
