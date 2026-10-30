// Full-shell regression shared by the disposable HTTP/browser suite.
const assert = require('node:assert/strict');
module.exports = async function verifyBreakpoints(page, url) {
 const widths=[1000,901,900,850,840,831,830,829,820,800,769,768,767,740,641,640];
 const rows=[];
 async function measure(kind,width,height) {
  await page.setViewportSize({width,height});
  if(kind==='direct') {await page.goto(url+'/');await page.waitForFunction(()=>document.querySelector('#emptyState')?.dataset.artwork==='photo');}
  await page.locator('.welcome-photo img').evaluate(e=>e.decode());
  await page.waitForTimeout(300);
  rows.push(await page.evaluate(({kind,width,height})=>{
   const img=document.querySelector('.welcome-photo img'),host=document.querySelector('#emptyState'),group=document.querySelector('.welcome-group'),box=img.parentElement;
   const a=img.getBoundingClientRect(),b=box.getBoundingClientRect(),s=document.querySelector('.sidebar').getBoundingClientRect();
   const mode=host.dataset.artwork;host.dataset.artwork='none';const baseline=document.documentElement.scrollWidth;host.dataset.artwork=mode;
   const shell=Object.fromEntries(['html','body','.layout','.main','.app-titlebar','.rail','.sidebar','.topbar','.messages','#emptyState','.welcome-group','#emptyState h2','#emptyState p','.suggestion','.composer-wrap','.composer-footer'].map(selector=>{const e=document.querySelector(selector);if(!e)return [selector,null];const c=getComputedStyle(e),r=e.getBoundingClientRect();return [selector,{font:c.fontSize,zoom:c.zoom,transform:c.transform,display:c.display,visibility:c.visibility,padding:c.padding,gap:c.gap,width:r.width,height:r.height}];}));
   return {shell,footerClass:document.querySelector('.composer-footer').className,viewport:{innerWidth,innerHeight,clientWidth:document.documentElement.clientWidth,scale:visualViewport.scale},kind,width,height,imageHeight:a.height,imageWidth:a.width,natural:[img.naturalWidth,img.naturalHeight],maskWidth:b.width,center:(a.left+a.right-b.left-b.right)/2,groupHeight:group.getBoundingClientRect().height,sidebarWidth:s.width,sidebarLeft:s.left,scrollWidth:document.documentElement.scrollWidth,baseline,mobile:matchMedia('(max-width:768px)').matches,mask:getComputedStyle(box).maskImage};
  },{kind,width,height}));
 }
 for(const height of [1000,800,600,430]) {
  for(const width of widths) await measure('direct',width,height);
  await measure('seed',1000,height);
  for(const width of widths) await measure('down',width,height);
  for(const width of [...widths].reverse()) await measure('up',width,height);
 }
 if(process.env.EVIDENCE_DIR) {const fs=require('node:fs'),path=require('node:path');fs.mkdirSync(process.env.EVIDENCE_DIR,{recursive:true});fs.writeFileSync(path.join(process.env.EVIDENCE_DIR,'breakpoints.json'),JSON.stringify(rows,null,2));}
 const frames=[];
 await page.setViewportSize({width:880,height:1000});await page.waitForTimeout(350);
 await page.evaluate(()=>{window._breakpointFrames=[];window._captureBreakpoints=true;const tick=time=>{if(!window._captureBreakpoints)return;const rect=s=>{const r=document.querySelector(s).getBoundingClientRect();return [r.x,r.y,r.width,r.height];};window._breakpointFrames.push({time,width:innerWidth,classes:document.querySelector('.layout').className,photo:rect('.welcome-photo img'),mask:rect('.welcome-photo'),main:rect('.main'),sidebar:rect('.sidebar'),composer:rect('.composer-wrap'),footer:document.querySelector('.composer-footer').className});requestAnimationFrame(tick);};requestAnimationFrame(tick);});
 for(const width of [890,899,900,901,902,910,920,910,902,901,900,899,890,880,680,670,661,660,659,650,641,640,639,630,639,640,641,650,659,660,661,670,680]) {await page.setViewportSize({width,height:1000});await page.waitForTimeout(350);}
 frames.push(...await page.evaluate(()=>{window._captureBreakpoints=false;return window._breakpointFrames;}));
 if(process.env.EVIDENCE_DIR) {const fs=require('node:fs'),path=require('node:path');fs.mkdirSync(process.env.EVIDENCE_DIR,{recursive:true});fs.writeFileSync(path.join(process.env.EVIDENCE_DIR,'breakpoint-frames.json'),JSON.stringify(frames,null,2));}
 for(const f of frames) assert.equal(f.photo[3],f.width<=768?160:240,`Transient artwork height: ${JSON.stringify(f)}`);
 for(let i=1;i<frames.length;i++) {
  if((frames[i-1].width===900&&frames[i].width===901)||(frames[i-1].width===640&&frames[i].width===641)) {
   const expansion=frames.slice(i).filter(f=>f.width===frames[i].width);
   const final=expansion[expansion.length-1].main[2];
   assert.ok(expansion.every(f=>f.main[2]>=final-1),`Expansion must not undershoot settled main width ${final}: ${JSON.stringify(expansion.slice(0,4))}`);
  }
 }
 console.log(`PASS transient 630–680 and 880–920 breakpoint samples: ${frames.length} frames`);
 // Zero-width parking must not erase real drawer sizes or their closing slides.
 for(const [width,selector,open,close,expected] of [[640,'.sidebar',()=>toggleMobileSidebar(),()=>closeMobileSidebar(),640],[850,'.rightpanel',()=>openWorkspacePanel('browse'),()=>_setWorkspacePanelMode('closed'),300]]) {
  await page.setViewportSize({width,height:1000});await page.waitForTimeout(350);
  await page.evaluate(`(${open.toString()})()`);await page.waitForTimeout(300);
  assert.equal(await page.locator(selector).evaluate(e=>e.getBoundingClientRect().width),expected);
  await page.evaluate(`(${close.toString()})()`);await page.waitForTimeout(70);
  assert.equal(await page.locator(selector).evaluate(e=>e.getBoundingClientRect().width),expected,'Retain width throughout the closing slide');
  await page.waitForTimeout(300);
  assert.ok(await page.locator(selector).evaluate(e=>e.getBoundingClientRect().width)<=1,'Park closed drawers at zero width');
 }
 console.log(`PASS breakpoint measurements: ${rows.length} direct-load/descending/ascending samples`);
 for(const height of [1000,800,600,430]) {
  for(const kind of ['direct','down','up']) {
   const band=rows.filter(r=>r.height===height&&r.kind===kind&&r.width>=769&&r.width<=850);
   assert.equal(new Set(band.map(r=>r.imageHeight)).size,1,`Width-only artwork drift: ${height}/${kind}`);
   for(const r of band) for(const selector of ['html','body','.layout','.main','.app-titlebar','.rail','#emptyState h2','#emptyState p','.composer-wrap']) {
    const sample=r.shell[selector],reference=band[0].shell[selector];
    for(const key of ['font','zoom','transform','display','visibility','padding','gap','height']) assert.equal(sample[key],reference[key],`${selector}/${key} changed at ${r.width}`);
   }
  }
 }
 for(const r of rows) {
  const expected=r.mobile?160:240;
  if(r.height>=800) assert.equal(r.imageHeight,expected,JSON.stringify(r));
  else assert.ok(r.imageHeight>0&&r.imageHeight<=expected,JSON.stringify(r));
  assert.ok(Math.abs(r.imageWidth/r.imageHeight-r.natural[0]/r.natural[1])<.01,JSON.stringify(r));
  assert.ok(Math.abs(r.center)<1,JSON.stringify(r));
  assert.ok(r.scrollWidth<=r.baseline,JSON.stringify(r));
  assert.match(r.mask,/linear-gradient/);
 }
};
