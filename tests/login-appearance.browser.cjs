// Verify server-rendered login before the first animation frame, without cached state.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const fs=require('node:fs'), path=require('node:path'), assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..');
(async()=>{
 const browser=await chromium.launch({headless:true});
 try{
  const source=fs.readFileSync(path.join(root,'api/routes.py'),'utf8');
  const template=source.match(/_LOGIN_PAGE_HTML = """([\s\S]*?)"""/)[1];
  for(const theme of ['light','dark','system']) for(const os of ['light','dark']){
   const page=await browser.newPage({colorScheme:os});
   await page.route('http://fixture/**',async route=>{
    const name=new URL(route.request().url()).pathname;
    if(name.startsWith('/static/')){
     const file=path.join(root,name);
     if(fs.existsSync(file))return route.fulfill({body:fs.readFileSync(file),contentType:name.endsWith('.css')?'text/css':'application/javascript'});
     return route.fulfill({status:404,body:''});
    }
    const html=template.replace('{{APPEARANCE_THEME}}',theme).replace('{{APPEARANCE_SKIN}}','ares').replaceAll('{{WEBUI_VERSION}}','test');
    return route.fulfill({body:html,contentType:'text/html'});
   });
   await page.addInitScript(()=>{ requestAnimationFrame(()=>{window.firstPaintAppearance={dark:document.documentElement.classList.contains('dark'),skin:document.documentElement.dataset.skin,bg:getComputedStyle(document.body).backgroundColor};}); });
   await page.goto('http://fixture/login');
   await page.waitForFunction(()=>window.firstPaintAppearance);
   const first=await page.evaluate(()=>window.firstPaintAppearance);
   assert.equal(first.dark,theme==='dark'||theme==='system'&&os==='dark',`${theme}/${os}`);
   assert.equal(first.skin,'ares');
   assert.notEqual(first.bg,'rgba(0, 0, 0, 0)');
   if(theme==='system'){
    await page.emulateMedia({colorScheme:os==='dark'?'light':'dark'});
    await page.waitForTimeout(100);
    assert.equal(await page.evaluate(()=>document.documentElement.classList.contains('dark')),os!=='dark');
   }
   await page.close();
  }
  console.log('PASS login: six initial-paint light/dark/system+OS cases, palette, live System resolution');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
