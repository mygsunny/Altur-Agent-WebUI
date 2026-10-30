// Delays transport, not settings values: every selection comes from the real server.
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path');
module.exports=async function(browser,url,context,post){
 for(const [width,height] of [[1440,1000],[430,600],[820,430]]) for(const mode of ['photo','none','original']){
  await post({welcome_artwork:mode,welcome_logo_glow:true});
  const freshBrowser=await browser.browserType().launch({headless:true});
  const cold=await freshBrowser.newContext({viewport:{width,height},isMobile:width!==1440,hasTouch:width!==1440,storageState:await context.storageState()});
  try{
   const page=await cold.newPage();
   await page.addInitScript(()=>{
    window.artworkFrames=[];
    const visible=e=>{if(!e)return false;const s=getComputedStyle(e);return !!e.getClientRects().length&&s.visibility==='visible'&&s.opacity!=='0';};
    function sample(){const host=document.querySelector('#emptyState'),logo=host?.querySelector('.empty-logo'),photo=host?.querySelector('.welcome-photo'),img=photo?.querySelector('img');
     if(host)window.artworkFrames.push({scroll:document.querySelector('#messages')?.scrollTop||0,documentScroll:document.scrollingElement.scrollTop,mode:host.dataset.artwork||null,logo:visible(logo),photo:visible(photo),decoded:!!img?.naturalWidth&&img.complete,heading:visible(host.querySelector('h2'))});
     requestAnimationFrame(sample);
    }requestAnimationFrame(sample);
   });
   for(const reload of [false,true]){
    let releaseSettings,releasePhoto;
    const settingsGate=new Promise(r=>releaseSettings=r),photoGate=new Promise(r=>releasePhoto=r);
    await page.route('**/api/settings',async route=>{if(route.request().method()==='GET')await settingsGate;await route.continue();});
    await page.route('**/static/images/welcome-feast.png',async route=>{await photoGate;await route.continue();});
    if(reload)await page.reload({waitUntil:'domcontentloaded'});else await page.goto(url+'/',{waitUntil:'domcontentloaded'});
    await page.waitForFunction(()=>window.artworkFrames.some(f=>f.heading));
    await page.waitForTimeout(150);
    let frames=await page.evaluate(()=>window.artworkFrames);
    if(process.env.EVIDENCE_DIR){fs.mkdirSync(process.env.EVIDENCE_DIR,{recursive:true});await page.screenshot({path:path.join(process.env.EVIDENCE_DIR,`startup-${width}-${mode}-${reload?'reload':'fresh'}.png`)});}
    // Release before asserting so a RED cannot strand the HTTP fixture.
    releaseSettings();
    try{
     assert.ok(frames.every(f=>!f.logo),`unresolved ${mode}/${width}: Original logo painted: ${JSON.stringify(frames.find(f=>f.logo))}`);
     await page.waitForFunction(mode=>document.querySelector('#emptyState').dataset.artwork===mode,mode);
     if(width!==1440){
      await page.evaluate(()=>newSession());
      assert.equal(await page.locator('#messages').evaluate(e=>e.scrollTop),0,'New chat stays at top with photo response still blocked');
     }
     await page.waitForTimeout(100);
     frames=await page.evaluate(()=>window.artworkFrames);
     assert.ok(frames.every(f=>!f.photo||f.decoded),'Photo/halo must wait for decoded pixels');
    }finally{releasePhoto();}
    if(mode==='photo')await page.locator('.welcome-photo img').evaluate(img=>img.decode());
    await page.waitForTimeout(100);
    assert.equal(await page.locator('.empty-logo').isVisible(),mode==='original');
    assert.equal(await page.locator('.welcome-photo').isVisible(),mode==='photo');
    frames=await page.evaluate(()=>window.artworkFrames);
    if(mode!=='original')assert.ok(frames.every(f=>!f.logo),'Original must never paint for photo/None');
    if(process.env.EVIDENCE_DIR)fs.writeFileSync(path.join(process.env.EVIDENCE_DIR,`frames-${width}-${mode}-${reload?'reload':'fresh'}.json`),JSON.stringify(frames));
    assert.ok(frames.every(f=>f.scroll===0&&f.documentScroll===0),`welcome startup scrolled ${width}/${height}: ${JSON.stringify(frames.find(f=>f.scroll||f.documentScroll))}`);
    // Exercise the real composer observer and the queued transcript retry seam.
    await page.evaluate(()=>{document.querySelector('#composerWrap').style.minHeight='180px';_repinMessagesAfterComposerResize();});
    await page.waitForTimeout(350);
    assert.equal(await page.locator('#messages').evaluate(e=>e.scrollTop),0,'composer resize must not bottom-pin welcome');
    await page.unrouteAll({behavior:'wait'});
    if(width!==1440){
     // User scrolling within the welcome is not a request to pin the tail.
     await page.locator('#messages').evaluate(e=>e.scrollTop=40);
     const manual=await page.locator('#messages').evaluate(e=>e.scrollTop);
     const authoritative=await page.evaluate(()=>api('/api/settings'));
     await page.evaluate(settings=>{applyWelcomeArtwork(settings,_profileSwitchGeneration);_repinMessagesAfterComposerResize();},authoritative);
     await page.waitForTimeout(350);
     assert.equal(await page.locator('#messages').evaluate(e=>e.scrollTop),manual,'later manual welcome scroll is retained');
     await page.evaluate(()=>newSession());
     await page.waitForTimeout(400);
     assert.equal(await page.locator('#messages').evaluate(e=>e.scrollTop),0,'explicit New chat resets welcome to top');
     assert.equal(await page.evaluate(()=>document.scrollingElement.scrollTop),0);
     // Real source scroll policy with a fixture transcript; no model/network call.
     const policy=await page.evaluate(async()=>{
      const host=document.querySelector('#emptyState'),inner=document.querySelector('#msgInner'),el=document.querySelector('#messages');
      host.style.display='none';inner.innerHTML='<div style="height:2500px">Fixture conversation</div>';
      _messageUserUnpinned=false;_scrollPinned=true;_setMessageScrollToBottom();
      await new Promise(r=>requestAnimationFrame(r));
      const bottom=el.scrollTop>0;
      _messageUserUnpinned=true;_scrollPinned=false;el.scrollTop=30;_repinMessagesAfterComposerResize();
      await new Promise(r=>requestAnimationFrame(r));const retained=el.scrollTop===30;
      // Queue an old transcript retry, then enter welcome before its next frame.
      _messageUserUnpinned=false;_scrollPinned=true;_setMessageScrollToBottom();
      inner.innerHTML='';host.style.display='';_resetEmptyWelcomeScroll();
      await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));
      return {bottom,retained,top:el.scrollTop};
     });
     assert.deepEqual(policy,{bottom:true,retained:true,top:0});
    }
   }
  }finally{await cold.close();await freshBrowser.close();}
 }
 console.log('PASS first paint: desktop/mobile × photo/None/Original × cold context/reload; delayed real settings and photo');
};
