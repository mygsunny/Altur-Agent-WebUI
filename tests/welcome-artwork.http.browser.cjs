// Real loopback server, real settings/auth/CSRF, real Chromium shell.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const {spawn}=require('node:child_process'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto'),fs=require('node:fs');
(async()=>{
 const password=crypto.randomBytes(24).toString('hex');
 const args=[...(process.env.FIXTURE_PYTHON_ARGS?JSON.parse(process.env.FIXTURE_PYTHON_ARGS):[]),path.join(__dirname,'welcome_http_fixture.py')];
 const server=spawn(process.env.FIXTURE_PYTHON||'python3',args,{env:{...process.env,FIXTURE_PASSWORD:password},stdio:['pipe','pipe','pipe']});
 let stderr='';server.stderr.on('data',d=>stderr+=d);
 let browser;
 try{
  const url=await new Promise((resolve,reject)=>{
   let output='';const timer=setTimeout(()=>reject(Error('Fixture timeout: '+stderr)),30000);
   server.stdout.on('data',d=>{output+=d;for(const line of output.split('\n')){try{const j=JSON.parse(line);if(j.url){clearTimeout(timer);resolve(j.url);}}catch{}}});
   server.once('exit',code=>{clearTimeout(timer);reject(Error('Fixture exit '+code+': '+stderr));});
  });
  browser=await chromium.launch({headless:true});
  const context=await browser.newContext({viewport:{width:1440,height:1000},reducedMotion:'reduce'});
  const page=await context.newPage();
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  const denied=await context.request.get(url+'/api/settings');assert.equal(denied.status(),401);
  await page.goto(url+'/login');
  assert.equal(await page.evaluate(()=>document.documentElement.classList.contains('dark')),false);
  assert.equal(await page.evaluate(()=>document.documentElement.dataset.skin),'ares');
  const login=await context.request.post(url+'/api/auth/login',{data:{password}});assert.equal(login.status(),200);
  await page.goto(url+'/');
  await page.waitForFunction(()=>typeof applyWelcomeArtwork==='function'&&document.querySelector('#emptyState').dataset.artwork);
  await page.evaluate(()=>skipOnboarding());
  async function post(data){return page.evaluate(async data=>{const r=await api('/api/settings',{method:'POST',body:JSON.stringify(data)});return r;},data);}
  let s=await post({welcome_artwork:'photo',welcome_artwork_height_desktop:240,welcome_artwork_height_mobile:160,show_token_usage:true});
  assert.equal(s.welcome_artwork,'photo');
  await page.reload();await page.waitForFunction(()=>document.querySelector('#emptyState').dataset.artwork==='photo');
  await page.locator('.welcome-photo img').evaluate(img=>img.decode());
  const alpha=await page.locator('.welcome-photo img').evaluate(img=>{const canvas=document.createElement('canvas');canvas.width=img.naturalWidth;canvas.height=img.naturalHeight;const ctx=canvas.getContext('2d');ctx.drawImage(img,0,0);const data=ctx.getImageData(0,0,canvas.width,canvas.height).data;let transparent=false,opaque=false;for(let i=3;i<data.length;i+=4){transparent ||= data[i]===0;opaque ||= data[i]===255;}return {transparent,opaque,background:getComputedStyle(img.parentElement).backgroundColor};});
  assert.deepEqual(alpha,{transparent:true,opaque:true,background:'rgba(0, 0, 0, 0)'});
  const height=()=>page.locator('.welcome-photo img').evaluate(e=>e.getBoundingClientRect().height);
  for(const [width,expected] of [[1440,240],[900,240],[430,160],[320,160]]){
   await page.setViewportSize({width,height:1000});await page.waitForTimeout(100);assert.equal(await height(),expected);
   const geometry=await page.evaluate(()=>{
    const img=document.querySelector('.welcome-photo img'),box=img.parentElement,a=img.getBoundingClientRect(),b=box.getBoundingClientRect(),c=document.querySelector('.composer-wrap').getBoundingClientRect();
    return {imageWidth:a.width,maskWidth:b.width,center:Math.abs((a.left+a.right-b.left-b.right)/2),ratio:a.width/a.height,natural:img.naturalWidth/img.naturalHeight,bottom:b.bottom,composer:c.top,scrollWidth:document.documentElement.scrollWidth,overflow:document.documentElement.scrollWidth>innerWidth,wide:[...document.querySelectorAll('body *')].filter(e=>{const r=e.getBoundingClientRect();return r.width&&r.right>innerWidth+1}).slice(0,12).map(e=>[e.id,e.className,e.getBoundingClientRect().right]),mask:getComputedStyle(box).maskImage};
   });
   assert.ok(geometry.maskWidth<=geometry.imageWidth+1,'Fade must meet the image edges, even when the complete image fits');
   assert.ok(geometry.center<1);assert.ok(Math.abs(geometry.ratio-geometry.natural)<.01);assert.ok(geometry.bottom<=geometry.composer,JSON.stringify(geometry));assert.ok(geometry.scrollWidth <= await page.evaluate(() => {const e=document.getElementById('emptyState'),mode=e.dataset.artwork;e.dataset.artwork='none';const baseline=document.documentElement.scrollWidth;e.dataset.artwork=mode;return baseline;}),JSON.stringify({width,...geometry}));assert.match(geometry.mask,/linear-gradient/);
  }
  for(const heightPx of [450,600,1000]){
   await page.setViewportSize({width:320,height:heightPx});await page.waitForTimeout(100);
   assert.ok(await height()<=160);
   const fit=await page.evaluate(()=>{const c=document.querySelector('.composer-wrap').getBoundingClientRect(),p=document.querySelector('#emptyState p').getBoundingClientRect(),i=document.querySelector('.welcome-photo').getBoundingClientRect();return {composerBottom:c.bottom,composerTop:c.top,textBottom:p.bottom,imageBottom:i.bottom,viewport:innerHeight};});
   assert.ok(fit.composerBottom<=fit.viewport+1,JSON.stringify(fit));
   assert.ok(fit.imageBottom<=fit.composerTop,JSON.stringify(fit));
   if(heightPx===1000)assert.equal(await height(),160);
  }
  // The maximum saved target must also leave the composer usable on short screens.
  for (const [width,heightPx] of [[1440,800],[430,600],[820,430]]) {
   await post({welcome_artwork_height_desktop:600,welcome_artwork_height_mobile:600});
   await page.reload();await page.waitForFunction(()=>document.querySelector('#emptyState').dataset.artwork==='photo');
   await page.setViewportSize({width,height:heightPx});await page.waitForTimeout(100);
   await page.locator('.messages').evaluate(e=>e.scrollTop=0);
   const fit=await page.evaluate(()=>{const c=document.querySelector('.composer-wrap').getBoundingClientRect(),i=document.querySelector('.welcome-photo').getBoundingClientRect();return {bottom:i.bottom,top:i.top,composer:c.top,end:c.bottom,viewport:innerHeight, details:[".messages","#emptyState",".welcome-group"].map(s=>{const e=document.querySelector(s),r=e.getBoundingClientRect();return [s,r.top,r.bottom,r.height,getComputedStyle(e).padding,getComputedStyle(e).minHeight]})};});
   assert.ok((fit.top>=0 || fit.bottom===fit.top) && fit.bottom<=fit.composer && fit.end<=fit.viewport+1,JSON.stringify(fit));
  }
  await post({welcome_artwork_height_desktop:240,welcome_artwork_height_mobile:160});
  await page.setViewportSize({width:320,height:1000});
  await page.reload();await page.waitForFunction(()=>document.querySelector('#emptyState').dataset.artwork==='photo');
  await page.setViewportSize({width:1440,height:1000});
  await page.locator('.rail-btn[data-panel="settings"]').click();
  await page.locator('[data-settings-section="appearance"]').click();
  await page.locator('#settingsWelcomeHeightMobile').waitFor({state:'visible'});
  const savedHeight=page.waitForResponse(r=>r.url().includes('/api/settings')&&r.request().method()==='POST'&&r.request().postDataJSON().welcome_artwork_height_mobile===190);
  await page.locator('#settingsWelcomeHeightMobile').fill('190');
  await page.locator('#settingsWelcomeHeightMobile').press('Tab');
  const savedHeightResponse=await savedHeight;
  assert.deepEqual(savedHeightResponse.request().postDataJSON(),{welcome_artwork_height_mobile:190});
  await page.waitForFunction(()=>document.getElementById('welcomeArtworkStatus').textContent==='Saved');
  for(const [selector,key,value] of [['#settingsWelcomeLogoGlow','welcome_logo_glow',false],['#settingsWelcomeOffsetDesktop','welcome_offset_desktop',-25]]){
   const response=page.waitForResponse(r=>r.url().includes('/api/settings')&&r.request().method()==='POST'&&r.request().postDataJSON()[key]===value);
   if(typeof value==='boolean')await page.locator(selector).setChecked(value);
   else {await page.locator(selector).fill(String(value));await page.locator(selector).press('Tab');}
   assert.deepEqual((await response).request().postDataJSON(),{[key]:value});
   await page.waitForFunction(selector=>!document.querySelector(selector).disabled,selector);
  }
  await page.locator('.rail-btn[data-panel="chat"]').click();
  s=await page.evaluate(()=>api('/api/settings'));assert.equal(s.welcome_artwork_height_mobile,190);assert.equal(s.welcome_artwork_height_desktop,240);assert.equal(s.show_token_usage,true);
  const invalidType=await post({welcome_artwork:[]});assert.equal(invalidType.welcome_artwork,'photo');
  const invalid=await post({welcome_artwork:'invalid',welcome_artwork_height_mobile:601});assert.equal(invalid.welcome_artwork,'photo');assert.equal(invalid.welcome_artwork_height_mobile,190);
  for(const mode of ['none','original','photo']){
   await post({welcome_artwork:mode});await page.reload();await page.waitForFunction(mode=>document.querySelector('#emptyState').dataset.artwork===mode,mode);
   assert.equal(await page.locator('.empty-logo').isVisible(),mode==='original');assert.equal(await page.locator('.welcome-photo').isVisible(),mode==='photo');assert.equal(await page.locator('#emptyState h2').isVisible(),true);
  }
  for(const mode of ['original','photo']) {
   for(const glow of [false,true]) {
    await post({welcome_artwork:mode,welcome_logo_glow:glow});await page.reload();
    await page.waitForFunction(mode=>document.querySelector('#emptyState').dataset.artwork===mode,mode);
    const pseudo=await page.locator(mode==='original'?'.empty-logo':'.welcome-photo').evaluate(e=>{const s=getComputedStyle(e,'::before');return {content:s.content,display:s.display};});
    assert.equal(pseudo.content==='none'||pseudo.display==='none',!glow,'Saved glow must control the selected artwork halo');
    if(process.env.EVIDENCE_DIR&&mode==='original'){fs.mkdirSync(process.env.EVIDENCE_DIR,{recursive:true});await page.screenshot({path:path.join(process.env.EVIDENCE_DIR,`original-glow-${glow?'on':'off'}.png`)});}
   }
  }
  await post({welcome_artwork:'none',welcome_logo_glow:true});await page.reload();await page.waitForFunction(()=>document.querySelector('#emptyState').dataset.artwork==='none');
  for(const selector of ['.empty-logo','.welcome-photo'])assert.equal(await page.locator(selector).isVisible(),false);
  await post({welcome_artwork:'photo',welcome_offset_desktop:0,welcome_offset_mobile:0});await page.reload();await page.waitForFunction(()=>document.querySelector('#emptyState').dataset.artwork==='photo');
  const positions=()=>page.evaluate(()=>({children:[...document.querySelectorAll('#emptyState .welcome-photo,#emptyState .empty-logo,#emptyState h2,#emptyState p,#emptyState .suggestion')].filter(e=>getComputedStyle(e).display!=='none').map(e=>e.getBoundingClientRect().top),composer:document.querySelector('.composer-wrap').getBoundingClientRect().top,header:document.querySelector('.app-titlebar').getBoundingClientRect().top,sidebar:document.querySelector('.sidebar').getBoundingClientRect().top}));
  for(const mode of ['photo','original','none']) for(const [width,key,offset] of [[1440,'welcome_offset_desktop',70],[430,'welcome_offset_mobile',-45]]){
   await page.setViewportSize({width,height:1000});await post({welcome_artwork:mode,[key]:0});await page.reload();await page.waitForFunction(mode=>document.querySelector('#emptyState').dataset.artwork===mode,mode);await page.locator('.welcome-photo img').evaluate(e=>e.decode());
   const before=await positions();await post({[key]:offset});await page.reload();await page.waitForFunction(mode=>document.querySelector('#emptyState').dataset.artwork===mode,mode);await page.locator('.welcome-photo img').evaluate(e=>e.decode());const after=await positions();
   assert.equal(after.children.length,mode==='none'?5:6);after.children.forEach((value,i)=>assert.ok(Math.abs(value-before.children[i]-offset)<1,JSON.stringify({mode,width,offset,before,after})));
   assert.equal(after.composer,before.composer);assert.equal(after.header,before.header);assert.equal(after.sidebar,before.sidebar);
  }
  const offsets=await page.evaluate(()=>api('/api/settings'));assert.equal(offsets.welcome_offset_desktop,70);assert.equal(offsets.welcome_offset_mobile,-45);assert.equal(offsets.welcome_logo_glow,true);
  await post({welcome_artwork:'photo',welcome_offset_desktop:300,welcome_offset_mobile:300});await page.reload();await page.waitForFunction(()=>document.querySelector('#emptyState').dataset.artwork==='photo');
  for(const [heightPx,offset] of [[600,300],[600,-300],[430,300],[430,-300]]){
   await post({welcome_offset_mobile:offset});await page.reload();await page.waitForFunction(()=>document.querySelector('#emptyState').dataset.artwork==='photo');
   await page.setViewportSize({width:430,height:heightPx});await page.waitForTimeout(100);
   const clamped=await page.evaluate(()=>{const group=document.querySelector('.welcome-group').getBoundingClientRect(),composer=document.querySelector('.composer-wrap').getBoundingClientRect(),buttons=[...document.querySelectorAll('.suggestion')].map(e=>e.getBoundingClientRect().bottom);return {top:group.top,bottom:group.bottom,composer:composer.top,buttons,offset:parseFloat(document.querySelector('.welcome-group').style.getPropertyValue('--welcome-offset'))};});
   const oversized=await page.locator('.welcome-group').evaluate(e=>e.getBoundingClientRect().height>document.querySelector('.messages').clientHeight-16);
   if(oversized){
    assert.equal(clamped.offset,0,'Oversized group retains scroll instead of unsafe translation');
    await page.locator('.suggestion').last().scrollIntoViewIfNeeded();
    assert.ok(await page.locator('.suggestion').last().evaluate(e=>e.getBoundingClientRect().bottom<=document.querySelector('.composer-wrap').getBoundingClientRect().top));
   }else{
    assert.ok(Math.abs(clamped.offset)<300&&clamped.top>=0&&clamped.bottom<=clamped.composer,JSON.stringify({heightPx,offset,...clamped}));
    assert.ok(clamped.buttons.every(bottom=>bottom<=clamped.composer));
   }
  }
  await post({welcome_offset_mobile:300});await page.reload();await page.waitForFunction(()=>document.querySelector('#emptyState').dataset.artwork==='photo');await page.setViewportSize({width:430,height:1600});await page.waitForTimeout(100);
  assert.equal(await page.locator('.welcome-group').evaluate(e=>parseFloat(e.style.getPropertyValue('--welcome-offset'))),300);
  assert.equal((await page.evaluate(()=>api('/api/settings'))).welcome_offset_mobile,300);
  await post({welcome_offset_desktop:0,welcome_offset_mobile:0});await page.setViewportSize({width:1440,height:1000});await page.reload();await page.waitForFunction(()=>document.querySelector('#emptyState').dataset.artwork==='photo');
  const phone=await browser.newContext({viewport:{width:430,height:932},isMobile:true,hasTouch:true,deviceScaleFactor:2});
  await phone.addCookies(await context.cookies());const mobile=await phone.newPage();
  await mobile.goto(url+'/');await mobile.waitForFunction(()=>document.querySelector('#emptyState').dataset.artwork==='photo');
  for(const width of [430,320]){await mobile.setViewportSize({width,height:932});await mobile.waitForTimeout(100);assert.equal(await mobile.locator('.welcome-photo img').evaluate(e=>e.getBoundingClientRect().height),190);}
  await mobile.locator('.welcome-photo img').evaluate(e=>e.decode());
  if(process.env.EVIDENCE_DIR){fs.mkdirSync(process.env.EVIDENCE_DIR,{recursive:true});await mobile.screenshot({path:path.join(process.env.EVIDENCE_DIR,'artwork-mobile.png')});await mobile.evaluate(()=>_applyTheme('dark'));await mobile.waitForTimeout(400);await mobile.screenshot({path:path.join(process.env.EVIDENCE_DIR,'artwork-mobile-dark.png')});}
  await mobile.setViewportSize({width:932,height:430});await mobile.waitForTimeout(100);
  await mobile.locator('.messages').evaluate(e=>e.scrollTop=0);
  const landscapeHeight=await mobile.locator('.welcome-photo').evaluate(e=>e.getBoundingClientRect().height);
  assert.ok(landscapeHeight>40&&landscapeHeight<240,`Landscape must retain proportional artwork: ${landscapeHeight}`);
  assert.ok(await mobile.locator('.welcome-photo').evaluate(e=>e.getBoundingClientRect().top>=document.querySelector('.messages').getBoundingClientRect().top));
  await mobile.setViewportSize({width:820,height:430});await mobile.waitForTimeout(100);
  assert.equal(await mobile.locator('.welcome-photo').evaluate(e=>e.getBoundingClientRect().height),landscapeHeight,'Short-screen width-only resize must lock photo height');
  await mobile.setViewportSize({width:932,height:430});await mobile.waitForTimeout(100);
  await mobile.locator('.messages').evaluate(e=>e.scrollTop=0);
  if(process.env.EVIDENCE_DIR)await mobile.screenshot({path:path.join(process.env.EVIDENCE_DIR,'artwork-landscape-430.png')});
  await mobile.setViewportSize({width:932,height:530});await mobile.waitForTimeout(100);
  const tallerLandscape=await mobile.locator('.welcome-photo').evaluate(e=>e.getBoundingClientRect().height);
  assert.ok(tallerLandscape>landscapeHeight&&tallerLandscape<=240);
  if(process.env.EVIDENCE_DIR)await mobile.screenshot({path:path.join(process.env.EVIDENCE_DIR,'artwork-landscape-530.png')});
  await mobile.setViewportSize({width:932,height:430});await mobile.waitForTimeout(100);
  const mobileComposer=await mobile.locator('.composer-wrap').boundingBox();assert.ok(mobileComposer.y+mobileComposer.height<=431);
  await phone.close();
  await page.setViewportSize({width:1440,height:1000});await page.waitForTimeout(100);
  if(process.env.EVIDENCE_DIR)await page.screenshot({path:path.join(process.env.EVIDENCE_DIR,'artwork-desktop.png')});
  // Saved server theme wins over conflicting browser cache before first paint.
  for(const theme of ['light','dark','system']){
   await post({theme,skin:'ares'});
   for(const os of ['light','dark']){
    const fresh=await browser.newContext({colorScheme:os});const p=await fresh.newPage();
    await p.addInitScript(()=>{localStorage.setItem('hermes-theme','dark');requestAnimationFrame(()=>window.paintAppearance={dark:document.documentElement.classList.contains('dark'),skin:document.documentElement.dataset.skin});});
    await p.goto(url+'/login');await p.waitForFunction(()=>window.paintAppearance);
    assert.deepEqual(await p.evaluate(()=>window.paintAppearance),{dark:theme==='dark'||theme==='system'&&os==='dark',skin:'ares'});
    assert.equal((await fresh.request.get(url+'/api/settings')).status(),401);
    if(process.env.EVIDENCE_DIR&&theme==='light'&&os==='light')await p.screenshot({path:path.join(process.env.EVIDENCE_DIR,'login-light.png')});
    await fresh.close();
   }
  }
  const noCsrf=await context.request.post(url+'/api/settings',{headers:{Origin:url},data:{welcome_artwork:'none'}});assert.equal(noCsrf.status(),403);
  const cannotDisable=await page.evaluate(async()=>{try{await api('/api/settings',{method:'POST',body:JSON.stringify({_clear_password:true})});return false;}catch{return true;}});assert.equal(cannotDisable,true);
  const oldCookies=await context.cookies();
  const rotated='  '+crypto.randomBytes(24).toString('hex')+'  ';
  await post({_set_password:rotated});
  for(const [candidate,status] of [[password,401],[rotated.trim(),401],[rotated,200]]){
   const loginContext=await browser.newContext();const r=await loginContext.request.post(url+'/api/auth/login',{data:{password:candidate}});assert.equal(r.status(),status);await loginContext.close();
  }
  // Existing signed-in sessions survive password changes in the maintained baseline.
  // Preserve that policy; logout must still revoke the exact current session.
  await page.evaluate(()=>api('/api/auth/logout',{method:'POST',body:'{}'}));
  const stale=await browser.newContext();await stale.addCookies(oldCookies);assert.equal((await stale.request.get(url+'/api/settings')).status(),401);await stale.close();
  assert.deepEqual(errors,[]);
  console.log('PASS full HTTP: protected API, generated-password login, real CSRF writes, persisted modes/heights/glow/whole-group desktop-mobile offsets, short-screen clamps/restoration, narrow save preservation, invalid rejection, desktop/mobile geometry and six authoritative login initial-paint cases; password spaces, signed-in optional reentry, disable-auth refusal and old-session revocation on logout');
 }finally{if(browser)await browser.close();server.stdin.end('\n');await new Promise(resolve=>{if(server.exitCode!==null)return resolve();server.once('exit',resolve);setTimeout(()=>{server.kill();resolve();},5000).unref();});}
})().catch(e=>{console.error(e);process.exitCode=1;});
