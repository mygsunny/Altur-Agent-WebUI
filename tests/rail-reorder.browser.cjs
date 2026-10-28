const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..');
(async()=>{
 const browser=await chromium.launch({headless:true});
 const page=await browser.newPage({viewport:{width:1200,height:900}});
 await page.route('**/*',route=>route.request().url()==='http://rail.test/'?route.fulfill({body:'<html></html>',contentType:'text/html'}):route.abort());
 await page.goto('http://rail.test/');
 const html=fs.readFileSync(path.join(root,'static/index.html'),'utf8');
 const rail=html.match(/<nav class="rail"[\s\S]*?<\/nav>/)[0];
 const panels=fs.readFileSync(path.join(root,'static/panels.js'),'utf8');
 const orderCode=panels.slice(panels.indexOf('const _ALWAYS_VISIBLE_TABS'),panels.indexOf('function _dashboardPanelMode'));
 const applyCode=panels.slice(panels.indexOf('function _applyTabOrder('),panels.indexOf('function _applyTabVisibility('));
 const moveCode=panels.slice(panels.indexOf('function _moveTabOrderPanel('),panels.indexOf('function _handleTabVisibilityChipDrop('));
 async function mount(){
  await page.goto('http://rail.test/');
  await page.setContent(`<html><head><style>${fs.readFileSync(path.join(root,'static/style.css'),'utf8')}</style></head><body><div class="layout">${rail}<main id="outside" style="margin-left:80px;width:500px;height:600px">Outside</main></div><button id="btnNewChat">New</button></body></html>`);
  await page.addScriptTag({content:`window.$=id=>document.getElementById(id);window.activations=0;window.saves=0;window.created=0;window.switchPanel=()=>activations++;$('btnNewChat').onclick=()=>created++;window._renderTabVisibilityChips=()=>{};window._scheduleAppearanceAutosave=()=>{throw new Error('Rail reorder must not save unrelated appearance fields');};window.api=async(url,opts)=>{const payload=JSON.parse(opts.body);if(Object.keys(payload).join()!=='tab_order')throw new Error('Non-order fields leaked');saves++;return payload;};${orderCode}\n${applyCode}\n${moveCode}\n_applyTabOrder(_getTabOrder());`});
  const p=path.join(root,'static/rail-reorder.js');if(fs.existsSync(p))await page.addScriptTag({path:p});
 }
 await mount();
 assert.equal(await page.locator('#btnRailNewChat').count(),1);
 const chat=page.locator('.rail [data-panel="chat"]'),tasks=page.locator('.rail [data-panel="tasks"]');
 for(const panel of ['tasks','settings','skills','memory','kanban','chat']){
  await page.evaluate(name=>{window.currentPanel=name;window.switchPanel=async target=>{window.currentPanel=target;activations++;return true;};},panel);
  const before=await page.evaluate(()=>created);await page.locator('#btnRailNewChat').click();
  assert.equal(await page.evaluate(()=>currentPanel),'chat','Compose navigates to Chat from '+panel);
  assert.equal(await page.evaluate(()=>created),before+1,'Compose starts exactly one new chat from '+panel);
 }
 await page.evaluate(()=>{window.created=0;window.activations=0;});
 await page.locator('#btnRailNewChat').click();assert.equal(await page.evaluate(()=>created),1);
 await page.evaluate(()=>{window.activations=0;});
 await chat.click();assert.equal(await page.evaluate(()=>activations),1);
 const a=await chat.boundingBox(),b=await tasks.boundingBox();
 await page.mouse.move(a.x+a.width/2,a.y+a.height/2);await page.mouse.down();await page.waitForTimeout(600);
 assert(await page.locator('.rail').evaluate(el=>el.classList.contains('rail-editing')),'long press enters wiggle mode');
 await page.mouse.move(b.x+b.width/2,b.y+b.height*.8,{steps:12});await page.mouse.up();
 assert.equal(await page.evaluate(()=>activations),1,'long press/drag must not navigate');
 const order=await page.evaluate(()=>_getTabOrder());assert(order.indexOf('chat')>order.indexOf('tasks'),'Chat moves below Tasks');assert.equal(await page.evaluate(()=>saves),1);
 await page.keyboard.press('Escape');assert(!(await page.locator('.rail').evaluate(el=>el.classList.contains('rail-editing'))));
 await mount();
 const current=await page.locator('.rail .nav-tab[data-panel]').evaluateAll(els=>els.map(el=>el.dataset.panel));assert(current.indexOf('chat')>current.indexOf('tasks'),'saved order restores');
 await tasks.focus();await page.keyboard.press('Alt+ArrowDown');assert.equal(await page.evaluate(()=>saves),1,'keyboard reorder saves');
 await page.locator('#outside').click({position:{x:200,y:200}});assert(!(await page.locator('.rail').evaluate(el=>el.classList.contains('rail-editing'))));
 // A moving press before the threshold must not start editing.
 await tasks.dispatchEvent('pointerdown',{pointerId:22,pointerType:'touch',button:0,clientX:20,clientY:100,isPrimary:true});
 await tasks.dispatchEvent('pointermove',{pointerId:22,pointerType:'touch',clientX:40,clientY:100});await page.waitForTimeout(600);
 assert(!(await page.locator('.rail').evaluate(el=>el.classList.contains('rail-editing'))));
 await tasks.dispatchEvent('pointercancel',{pointerId:22,pointerType:'touch'});
 // Touch long press and cancellation must release all drag state.
 await tasks.dispatchEvent('pointerdown',{pointerId:23,pointerType:'touch',button:0,clientX:20,clientY:100,isPrimary:true});await page.waitForTimeout(600);
 assert(await page.locator('.rail').evaluate(el=>el.classList.contains('rail-editing')));
 await tasks.dispatchEvent('pointercancel',{pointerId:23,pointerType:'touch'});await page.keyboard.press('Escape');
 assert.equal(await page.locator('.rail-dragging').count(),0);
 // Escaping while still holding a long press must not disable future clicks.
 await page.mouse.move(a.x+a.width/2,a.y+a.height/2);await page.mouse.down();await page.waitForTimeout(600);await page.keyboard.press('Escape');await page.mouse.up();await page.waitForTimeout(450);
 const beforeClick=await page.evaluate(()=>activations);await chat.click();assert.equal(await page.evaluate(()=>activations),beforeClick+1,'Escape during drag restores normal clicks');
 // Opening Settings immediately waits for the order write before reading settings.
 const settingsPrefix=panels.slice(panels.indexOf('async function loadSettingsPanel(){'),panels.indexOf('    checkWebUIVersionSkew(settings);',panels.indexOf('async function loadSettingsPanel(){')));
 await page.addScriptTag({content:settingsPrefix+'return settings;}catch(error){throw error;}}'});
 assert(await page.evaluate(async()=>{
  let release;let read=false;
  _tabOrderSaveQueue=new Promise(resolve=>release=resolve);
  window.api=async()=>{read=true;return {tab_order:['tasks','chat']};};
  const pending=loadSettingsPanel();await Promise.resolve();
  if(read) return false;
  release();await pending;return read;
 }),'Settings hydration waits for pending order persistence');
 // New chat itself must wiggle, drag, persist, and still activate normally afterward.
 await page.keyboard.press('Escape');
 const compose=page.locator('#btnRailNewChat');const c=await compose.boundingBox(),tbox=await tasks.boundingBox();
 await page.mouse.move(c.x+c.width/2,c.y+c.height/2);await page.mouse.down();await page.waitForTimeout(600);
 assert(await compose.evaluate(el=>el.classList.contains('rail-dragging')),'New chat participates in long press');
 await page.mouse.move(tbox.x+tbox.width/2,tbox.y+tbox.height*.8,{steps:10});await page.mouse.up();
 assert.equal(await compose.evaluate(el=>getComputedStyle(el).animationName),'railWiggle','New chat wiggles after dragging');
 const sequence=await page.locator('.rail > button').evaluateAll(els=>els.map(el=>el.id||el.dataset.panel));
 assert(sequence.indexOf('btnRailNewChat')>sequence.indexOf('tasks'),'New chat moves below Tasks');
 assert((await page.evaluate(()=>_getTabOrder())).includes('__new_chat__'));
 const motion=await compose.evaluate(el=>getComputedStyle(el).animationDuration);assert.equal(motion,'0.28s');
 assert(await compose.evaluate(el=>el.getAnimations().find(a=>a.animationName==='railWiggle').effect.getKeyframes().some(frame=>{const matrix=new DOMMatrix(frame.transform);return Math.abs(Math.atan2(matrix.b,matrix.a))>0.15;})),'stronger nine-degree wiggle');
 await page.emulateMedia({reducedMotion:'reduce'});assert.equal(await compose.evaluate(el=>getComputedStyle(el).animationName),'none');await page.emulateMedia({reducedMotion:'no-preference'});
 await page.keyboard.press('Escape');await page.waitForTimeout(450);const createdBefore=await page.evaluate(()=>created);await compose.click();assert.equal(await page.evaluate(()=>created),createdBefore+1);
 await mount();const restored=await page.locator('.rail > button').evaluateAll(els=>els.map(el=>el.id||el.dataset.panel));assert(restored.indexOf('btnRailNewChat')>restored.indexOf('tasks'),'New chat placement survives reload');
 const out=path.join(root,'evidence/rail-reorder');fs.mkdirSync(out,{recursive:true});
 for(const dark of [false,true]){
  await page.evaluate(d=>document.documentElement.classList.toggle('dark',d),dark);
  await page.waitForTimeout(400);
  assert.equal(await page.evaluate(()=>getComputedStyle(document.documentElement).getPropertyValue('--sidebar').trim()),dark?'#141425':'#FAF7F0');
  await page.screenshot({path:path.join(out,dark?'dark.png':'light.png')});
 }
 assert.equal(await page.locator('#btnRailNewChat').count(),1);
 assert.equal(await page.locator('.rail > :last-child').getAttribute('data-panel'),'settings');
 fs.writeFileSync(path.join(out,'results.json'),JSON.stringify({passed:true,checks:['global compose from each page','New chat wiggle and drag','New chat saved placement','slower strong wiggle','reduced motion','normal click','long press wiggle','Chat drag','no accidental navigation','saved reload','order-only persistence','Settings hydration waits for save','keyboard reorder','outside exit','touch movement cancels','touch long press','pointer cancellation','Escape during drag restores clicks','Settings fixed','light/dark rendering']},null,2));
 await browser.close();console.log('PASS: navigation rail gesture, persistence, keyboard and rendering checks');
})().catch(e=>{console.error(e);process.exit(1)});
