import {test,expect,chromium,firefox,webkit} from '@playwright/test';
import fs from 'node:fs';
const base=process.env.COWORK_LAN_URL;
test.skip(!base,'Set COWORK_LAN_URL to the actual LAN trial, and COWORK_PASSWORD_FILE to its private password file');
for(const [name,engine] of Object.entries({chromium,firefox,webkit}))test(name+' LAN visible document, configured Apply, sustained sheet typing and autosave',async()=>{
 test.setTimeout(150000);const browser=await engine.launch();
 try{
  const context=await browser.newContext({viewport:{width:1440,height:1000}});
  const login=await context.request.post(base+'/api/auth/login',{data:{password:fs.readFileSync(process.env.COWORK_PASSWORD_FILE,'utf8')},headers:{Origin:base}});expect(login.status()).toBe(200);
  const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.addInitScript(()=>{window.inputLags=[];document.addEventListener('keydown',()=>{const t=performance.now();requestAnimationFrame(()=>window.inputLags.push(performance.now()-t))},true)});
  const start=Date.now();await page.goto(base+'/static/cowork/index.html');await expect(page.locator('#voice-status')).toContainText('trusted HTTPS');await expect(page.locator('#apply')).toBeEnabled({timeout:40000});
  const pageBox=await page.locator('.tiptap').boundingBox();expect(pageBox.width).toBeGreaterThan(500);expect(pageBox.height).toBeGreaterThan(350);
  await expect(page.locator('.tiptap')).toHaveAttribute('data-placeholder',/Start typing/);
  // Firefox returns the unevaluated attr() expression for computed content.
  expect(await page.locator('.tiptap').evaluate(e=>getComputedStyle(e,'::before').content)).toMatch(/Start typing|attr\(data-placeholder\)/);
  await page.screenshot({path:test.info().outputPath(name+'-document.png')});
  await page.locator('.tiptap').click({position:{x:100,y:100}});await expect(page.locator('.tiptap')).toBeFocused();
  await page.keyboard.type('Synthetic visible page typing',{delay:20});await expect(page.locator('.tiptap')).toContainText('Synthetic visible page typing');
  const docReadyMs=Date.now()-start;
  await page.locator('#listen').click();await expect(page.locator('#status')).toContainText('HTTPS');
  await page.locator('#request').fill('Append a paragraph containing exactly "Synthetic configured model check".');
  const infer=page.waitForResponse(r=>r.url().endsWith('/api/cowork/intent'));const applyStart=Date.now();await page.locator('#apply').click();expect((await infer).status()).toBe(200);
  await expect(page.locator('.tiptap')).toContainText('Synthetic configured model check',{timeout:40000});const applyMs=Date.now()-applyStart;
  await page.locator('#new-sheet').click();await page.waitForFunction(()=>window.cowork.kind==='sheet');await expect(page.locator('#apply')).toBeEnabled({timeout:40000});
  await expect.poll(()=>page.locator('#editor canvas').evaluateAll(es=>es.some(e=>{const r=e.getBoundingClientRect();return r.width>500&&r.height>200})),{timeout:10000}).toBe(true);
  const grid=await page.locator('#editor canvas').evaluateAll(es=>es.find(e=>e.getBoundingClientRect().width>500).getBoundingClientRect().toJSON());
  await page.mouse.dblclick(grid.x+90,grid.y+32);const text='Synthetic sustained keyboard input '.repeat(8);const typingStart=Date.now();await page.keyboard.type(text,{delay:20});await page.keyboard.press('Enter');const typingMs=Date.now()-typingStart;expect(typingMs).toBeLessThan(13000);
  await expect.poll(()=>page.evaluate(()=>window.cowork.adapter.book.getActiveSheet().getRange('A1').getValues()[0][0])).toBe(text);
  // Native keyboard commits create a font color style; the first Office export
  // must not revoke the writer grant and strand all subsequent input.
  await page.waitForTimeout(6000);await expect(page.locator('#apply')).toBeEnabled();expect(await page.locator('#editor').evaluate(e=>e.inert)).toBe(false);
  await page.mouse.dblclick(grid.x+180,grid.y+32);await page.keyboard.type('second committed edit',{delay:20});await page.keyboard.press('Enter');
  await expect.poll(()=>page.evaluate(()=>window.cowork.adapter.book.getActiveSheet().getRange('B1').getValues()[0][0])).toBe('second committed edit');
  await page.locator('#undo').click();await expect.poll(()=>page.evaluate(()=>window.cowork.adapter.book.getActiveSheet().getRange('B1').getValues()[0][0]??null)).toBe(null);
  await page.locator('#redo').click();await expect.poll(()=>page.evaluate(()=>window.cowork.adapter.book.getActiveSheet().getRange('B1').getValues()[0][0])).toBe('second committed edit');
  const id=await page.evaluate(()=>window.cowork.id);
  await expect.poll(async()=>JSON.stringify(await(await context.request.get(base+'/api/cowork/document?id='+id)).json()),{timeout:10000}).toContain('second committed edit');
  const lags=await page.evaluate(()=>window.inputLags);lags.sort((a,b)=>a-b);expect(lags[Math.floor(lags.length*.95)]).toBeLessThan(150);
  expect(errors).toEqual([]);console.log(JSON.stringify({browser:name,docReadyMs,applyMs,typingMs,inputP95:lags[Math.floor(lags.length*.95)],inputMax:lags.at(-1),pageBox}));
 }finally{await browser.close();}
});
