// Run with node; PLAYWRIGHT_MODULE may select an existing installation.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const root = path.resolve(__dirname, '..');
(async () => {
  const browser = await chromium.launch({headless: true});
  try {
    const page = await browser.newPage({viewport:{width:1440,height:1000}});
    const html = fs.readFileSync(path.join(root,'static/index.html'),'utf8');
    const empty = html.match(/<div class="empty-state" id="emptyState">([\s\S]*?)<\/div>\s*<\/div>/)[0];
    await page.setContent(`<style>${fs.readFileSync(path.join(root,'static/style.css'),'utf8')}</style><main style="height:800px;display:flex;flex-direction:column;width:100%">${empty}<div class="composer-wrap" style="height:100px">Composer</div></main>`);
    await page.addScriptTag({path:path.join(root,'static/welcome-artwork.js')});
    await page.evaluate(() => applyWelcomeArtwork({welcome_artwork:'photo',welcome_artwork_height_desktop:240,welcome_artwork_height_mobile:160}));
    const height = () => page.locator('.welcome-photo img').evaluate(e=>e.getBoundingClientRect().height);
    assert.equal(await height(),240);
    await page.setViewportSize({width:900,height:1000});
    await page.waitForTimeout(80); assert.equal(await height(),240);
    for (const width of [430,320]) {
      await page.setViewportSize({width,height:1000});
      await page.waitForTimeout(80); assert.equal(await height(),160);
    }
    await page.setViewportSize({width:320,height:300});
    await page.waitForTimeout(80); assert.ok(await height()<160);
    await page.setViewportSize({width:320,height:1000});
    await page.waitForTimeout(80); assert.equal(await height(),160);
    assert.match(await page.locator('.welcome-photo').evaluate(e=>getComputedStyle(e).maskImage),/linear-gradient/);
    await page.evaluate(() => applyWelcomeArtwork({welcome_artwork:'none'}));
    assert.equal(await page.locator('.empty-logo').isVisible(),false);
    assert.equal(await page.locator('.welcome-photo').isVisible(),false);
    assert.equal(await page.locator('#emptyState h2').isVisible(),true);
    await page.evaluate(() => applyWelcomeArtwork({welcome_artwork:'original'}));
    assert.equal(await page.locator('.empty-logo').isVisible(),true);
    // A delayed response from Profile A must not overwrite Profile B's UI.
    await page.addScriptTag({content:'let _profileSwitchGeneration = 0;'});
    await page.evaluate(async () => {
      const control = document.createElement('select'); control.id='settingsWelcomeArtwork';
      control.innerHTML='<option value="photo">Photo</option><option value="none">None</option>';
      const status=document.createElement('span');status.id='welcomeArtworkStatus';
      document.body.append(control,status);
      applyWelcomeArtwork({welcome_artwork:'photo'});
      control.value='none';
      let finish;window.api=()=>new Promise(resolve=>finish=resolve);
      const saving=saveWelcomeArtwork(control);
      window.eval('_profileSwitchGeneration++');
      applyWelcomeArtwork({welcome_artwork:'original'});
      finish({welcome_artwork:'none'});await saving;
    });
    assert.equal(await page.locator('#emptyState').getAttribute('data-artwork'),'original');
    const panels=fs.readFileSync(path.join(root,'static/panels.js'),'utf8');
    const loadFunction=panels.slice(panels.indexOf('async function loadSettingsPanel()'),panels.indexOf('\nfunction ',panels.indexOf('async function loadSettingsPanel()')));
    await page.addScriptTag({content:'let _tabOrderSaveQueue=Promise.resolve(); window.$=id=>document.getElementById(id); window.checkWebUIVersionSkew=()=>{}; window.showToast=()=>{}; window.t=k=>k;\n'+loadFunction});
    await page.evaluate(async()=>{
      let finish;window.api=()=>new Promise(resolve=>finish=resolve);
      const loading=loadSettingsPanel();
      await Promise.resolve();
      window.eval('_profileSwitchGeneration++');
      applyWelcomeArtwork({welcome_artwork:'photo'});
      finish({welcome_artwork:'none'});
      await loading;
    });
    assert.equal(await page.locator('#emptyState').getAttribute('data-artwork'),'photo','Delayed actual loadSettingsPanel must not replace Profile B artwork');
    assert.equal(await page.locator('#settingsWelcomeArtwork').inputValue(),'photo','Delayed actual loadSettingsPanel must not replace Profile B control');
    await page.evaluate(()=>applyWelcomeArtwork({welcome_artwork:'none'},0));
    assert.equal(await page.locator('#settingsWelcomeArtwork').inputValue(),'photo','Renderer must reject an explicitly stale owner');
    const queueFunction=panels.slice(panels.indexOf('function _enqueueSettingsPost('),panels.indexOf('// Ownership token for the shared preferences'));
    await page.addScriptTag({content:'let releaseSettingsQueue; let _settingsPanelPostQueue=new Promise(resolve=>releaseSettingsQueue=resolve);\n'+queueFunction});
    await page.evaluate(async()=>{
      let posts=0;window.api=async()=>{posts++;return {welcome_artwork:'none'};};
      applyWelcomeArtwork({welcome_artwork:'photo'});
      const control=document.getElementById('settingsWelcomeArtwork');control.value='none';
      const saving=saveWelcomeArtwork(control);
      window.eval('_profileSwitchGeneration++');
      applyWelcomeArtwork({welcome_artwork:'original'});
      window.eval('releaseSettingsQueue()');await saving;
      window.queuedArtworkPosts=posts;
    });
    assert.equal(await page.evaluate(()=>window.queuedArtworkPosts),0,'A queued Profile A save must not be sent after switching profiles');
    await page.setViewportSize({width:1440,height:1000});
    await page.evaluate(()=>{
      applyWelcomeArtwork({welcome_artwork:'original',welcome_offset_desktop:-300});
      Object.defineProperty(visualViewport,'offsetTop',{configurable:true,value:150});
      visualViewport.dispatchEvent(new Event('scroll'));
    });
    assert.ok(await page.locator('.welcome-group').evaluate(e=>e.getBoundingClientRect().top)>=158,'Keyboard visual-viewport panning must re-clamp the group');
    console.log('PASS artwork: modes, independent heights, desktop/mobile width-only resize, vertical shrink/restore, alpha mask, stale-profile response and queued-write guards, keyboard viewport panning');
  } finally { await browser.close(); }
})().catch(e=>{ console.error(e); process.exitCode=1; });
