import {test,expect} from '@playwright/test';
import fs from 'node:fs';
test.setTimeout(60000);
test.use({launchOptions:{args:['--use-fake-ui-for-media-stream','--use-fake-device-for-media-stream']},permissions:['microphone']});
const trial=process.env.COWORK_TRIAL_DIR||'../.cowork-local';
const base=fs.readFileSync(trial+'/url','utf8').trim();
const url=base+'/static/cowork/index.html';
for(const fail of [false,true])test(`Listen stays disabled during delayed ${fail?'failed':'successful'} document switch`,async({page})=>{
 await page.goto(url);await page.waitForFunction(()=>!!window.cowork?.adapter);
 const previous=await page.evaluate(()=>window.cowork.id);let entered=false,release;
 await page.route('**/api/cowork/document?id=*',async route=>{if(entered){await route.continue();return;}entered=true;await new Promise(r=>release=r);if(fail)await route.fulfill({status:500,json:{error:'Delayed switch failed'}});else await route.continue();});
 await page.evaluate(()=>{window.micCalls=0;navigator.mediaDevices.getUserMedia=async()=>{window.micCalls++;throw Error('test permission denied')};document.getElementById('new-doc').click()});
 await expect.poll(()=>entered).toBeTruthy();await expect(page.locator('#listen')).toBeDisabled();
 await page.evaluate(()=>document.getElementById('listen').onclick());expect(await page.evaluate(()=>window.micCalls)).toBe(0);
 // Only the first request is held; successful open re-reads after claim.
 release();
 await expect(page.locator('#listen')).toBeEnabled({timeout:30000});
 if(fail)expect(await page.evaluate(()=>window.cowork.id)).toBe(previous);else expect(await page.evaluate(()=>window.cowork.id)).not.toBe(previous);
 await page.locator('#listen').click();expect(await page.evaluate(()=>window.micCalls)).toBe(1);
});
test.beforeEach(async({context,page})=>{
 const response=await context.request.post(base+'/api/auth/login',{data:{password:fs.readFileSync(trial+'/password','utf8')},headers:{Origin:base}});
 expect(response.ok()).toBeTruthy();
 const go=page.goto.bind(page);page.goto=async(...args)=>{const response=await go(...args);if(String(args[0]).includes('/static/cowork/'))await expect(page.locator('#apply')).toBeEnabled({timeout:30000});return response;};
});
test('shell lazily embeds editor and retains model when closed',async({page})=>{
 await page.goto(base);await page.screenshot({path:'../.cowork-local/shell-before.png',fullPage:true});
 await page.getByRole('button',{name:'Open Co-work spreadsheet and document editor'}).click();
 const frame=page.frameLocator('iframe[title="Spreadsheet and document co-work"]');await expect(frame.locator('.tiptap')).toBeVisible();
 await expect(frame.locator('#apply')).toBeEnabled({timeout:30000});
 await frame.locator('.tiptap').fill('Retained synthetic work');await page.screenshot({path:'../.cowork-local/shell-after.png',fullPage:true});
 await page.getByRole('button',{name:'Close Co-work',exact:true}).click();await expect(page.locator('dialog[aria-label="Co-work editor"]')).not.toBeVisible();
 await page.getByRole('button',{name:'Open Co-work spreadsheet and document editor'}).click();await expect(frame.locator('.tiptap')).toContainText('Retained synthetic work');
});

test('same-ID Reopen retains native history and writable ownership',async({page})=>{
 await page.goto(url);const doc=page.locator('.tiptap');await doc.fill('Keep own history');
 await page.evaluate(()=>{window.originalAdapter=window.cowork.adapter});await page.locator('#reopen').click();
 await expect(page.locator('#status')).toContainText('Ready');expect(await page.evaluate(()=>window.cowork.adapter===window.originalAdapter)).toBeTruthy();
 await page.locator('#undo').click();await expect(doc).not.toContainText('Keep own history');
});
test('double Enable while permission is pending cannot leave a microphone after Pause',async({page})=>{
 await page.goto(url);await page.waitForFunction(()=>!!window.cowork?.adapter);
 await page.evaluate(()=>{
  const native=navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);window.acquisitions=0;window.tracks=[];
  navigator.mediaDevices.getUserMedia=async options=>{window.acquisitions++;await new Promise(r=>{window.allowMic=r});const stream=await native(options);window.tracks.push(...stream.getTracks());return stream};
  document.getElementById('listen').click();document.getElementById('listen').click();
 });
 expect(await page.evaluate(()=>window.acquisitions)).toBe(1);await page.locator('#pause').click();await page.evaluate(()=>window.allowMic());
 await expect.poll(()=>page.evaluate(()=>window.tracks.length)).toBe(1);await expect.poll(()=>page.evaluate(()=>window.tracks.every(t=>t.readyState==='ended'))).toBeTruthy();
});
test('native document human + targeted AI + shared undo and tables',async({page})=>{
 await page.goto(url); await page.getByRole('button',{name:'New document',exact:true}).click();
 const doc=page.locator('.tiptap'); await doc.click(); await page.keyboard.type('Human paragraph');
 await expect(doc).toContainText('Human paragraph');
 await page.evaluate(()=>window.cowork.adapter.apply({type:'document.replace',find:'Human paragraph',text:'AI paragraph'}));
 await expect(doc).toContainText('AI paragraph');
 await page.getByPlaceholder('Ask AI to edit…').focus(); await page.keyboard.press('Meta+z');
 await expect(doc).toContainText('Human paragraph');
 await page.getByRole('button',{name:'Redo',exact:true}).click(); await expect(doc).toContainText('AI paragraph');
 await page.evaluate(()=>window.cowork.adapter.apply({type:'document.table',rows:[['Name','Count'],['Synthetic','2']]}));
 await expect(doc.locator('table')).toContainText('Synthetic');
 await page.getByRole('button',{name:'Undo',exact:true}).click(); await expect(doc.locator('table')).toHaveCount(0);
});
test('native spreadsheet formulas, targeted interleavings and undo',async({page})=>{
 await page.goto(url); await page.getByRole('button',{name:'New spreadsheet',exact:true}).click();
 await page.waitForFunction(()=>window.cowork?.kind==='sheet');
 await expect(page.locator('#apply')).toBeEnabled({timeout:30000});
 const result=await page.evaluate(()=>{
  const a=window.cowork.adapter, s=a.context().sheet_id;
  a.apply({type:'sheet.set',sheet_id:s,range:'A1:B1',values:[[2,3]]});
  a.apply({type:'sheet.set',sheet_id:s,range:'A1',values:[[7]]});
  a.apply({type:'sheet.set',sheet_id:s,range:'C1',values:[['=SUM(A1:B1)']]});
  const before=a.snapshot(); a.undo(); const undone=a.snapshot(); a.redo();
  return {before,undone,redone:a.snapshot()};
 });
 const cells=s=>Object.values(s.sheets)[0].cellData;
 expect(cells(result.before)['0']['0'].v).toBe(7);
 expect(cells(result.before)['0']['1'].v).toBe(3);
 expect(cells(result.before)['0']['2'].f).toBe('=SUM(A1:B1)');
 expect(cells(result.undone)['0']['2']?.f).toBeFalsy();
 expect(cells(result.redone)['0']['2'].f).toBe('=SUM(A1:B1)');
 await expect.poll(()=>page.evaluate(()=>window.cowork.adapter.book.getActiveSheet().getRange('C1').getValues()[0][0])).toBe(10);
 await page.screenshot({path:'../.cowork-local/spreadsheet.png',fullPage:true});
 await page.mouse.click(90,312);await page.keyboard.type('Manual');await page.keyboard.press('Enter');
 await expect.poll(()=>page.evaluate(()=>window.cowork.adapter.book.getActiveSheet().getRange('A1').getValues()[0][0])).toBe('Manual');
 await page.evaluate(()=>{const a=window.cowork.adapter;a.apply({type:'sheet.set',sheet_id:a.context().sheet_id,range:'A1',values:[['AI after manual']]})});
 await page.getByRole('button',{name:'Undo',exact:true}).click();
 await expect.poll(()=>page.evaluate(()=>window.cowork.adapter.book.getActiveSheet().getRange('A1').getValues()[0][0])).toBe('Manual');
});

test('HTTP snapshots reject CSRF, stale revision and profile confusion',async({page,playwright})=>{
 await page.goto(url);await page.waitForFunction(()=>!!window.cowork?.adapter);
 const result=await page.evaluate(async()=>{
  const html=await fetch('/').then(r=>r.text()),csrf=JSON.parse(html.match(/csrfToken:("(?:[^"\\]|\\.)*")/)[1]);
  const send=async(body,token=csrf)=>{const r=await fetch('/api/cowork/document',{method:'POST',headers:{'Content-Type':'application/json','X-Hermes-CSRF-Token':token},body:JSON.stringify(body)});return {status:r.status,body:await r.json()}};
  const document_id=crypto.randomUUID(),owner=crypto.randomUUID(),payload={profile:'default',owner,document_id,kind:'document',revision:0,snapshot:{type:'doc',content:[]}};
  await fetch('/api/cowork/claim',{method:'POST',headers:{'Content-Type':'application/json','X-Hermes-CSRF-Token':csrf},body:JSON.stringify({profile:'default',owner,document_id})});
  const badToken=await send(payload,'bad'),first=await send(payload),stale=await send(payload);
  const foreign=await send({...payload,profile:'foreign',revision:1});
  const second=await send({...payload,revision:1,snapshot:{type:'doc',content:[{type:'paragraph'}]}});
  const read=await fetch('/api/cowork/document?id='+document_id).then(r=>r.json());
  const prior=await fetch('/api/cowork/document?id='+document_id+'&previous=1').then(r=>r.json());
  return {badToken,first,stale,foreign,second,read,prior};
 });
 expect(result.badToken.status).toBe(403);expect(result.first.status).toBe(200);expect(result.stale.status).toBe(409);expect(result.foreign.status).toBe(409);expect(result.second.status).toBe(200);
 expect(result.read.document.revision).toBe(2);expect(result.prior.document.revision).toBe(1);
 const anon=await playwright.request.newContext();expect((await anon.get(base+'/api/cowork/document?id=test')).status()).toBe(401);await anon.dispose();
});

test('open re-reads latest snapshot after server ownership claim',async({page,context})=>{
 const html=await (await context.request.get(base)).text(),csrf=JSON.parse(html.match(/csrfToken:("(?:[^"\\]|\\.)*")/)[1]);
 const document_id='claim-race-'+Date.now(),owner='owner-'+Date.now(),headers={'X-Hermes-CSRF-Token':csrf,Origin:base};
 expect((await context.request.post(base+'/api/cowork/claim',{headers,data:{document_id,owner,profile:'default'}})).ok()).toBeTruthy();
 const snapshot={type:'doc',content:[{type:'paragraph',content:[{type:'text',text:'Latest committed before claim'}]}]};
 expect((await context.request.post(base+'/api/cowork/document',{headers,data:{document_id,owner,profile:'default',revision:0,kind:'document',snapshot}})).ok()).toBeTruthy();
 await page.addInitScript(({key,owner})=>sessionStorage.setItem(key,owner),{key:'cowork-owner:default:'+document_id,owner});
 let first=true;await page.route('**/api/cowork/document?id='+document_id,route=>{if(first){first=false;return route.fulfill({json:{profile:'default',document:{document_id,kind:'document',revision:0,snapshot:{type:'doc',content:[{type:'paragraph'}]}}}})}return route.continue()});
 await page.goto(url+'?id='+document_id);await expect(page.locator('.tiptap')).toContainText('Latest committed before claim');
});

test('autosave/reload preserves content; second writable tab is refused',async({page,context})=>{
 await page.goto(url);const doc=page.locator('.tiptap');await doc.fill('Synthetic persistence');await page.getByRole('button',{name:'Save',exact:true}).click();
 await expect(page.locator('#save-status')).toContainText('Saved revision');
 const current=page.url(),second=await context.newPage();await second.goto(current);await expect(second.locator('#status')).toContainText('already has a writable browser tab');await expect(second.locator('.tiptap')).toHaveCount(0);await second.close();
 await page.reload();await expect(page.locator('.tiptap')).toContainText('Synthetic persistence');
});

test('final transcript dispatch uses real endpoint, partial and duplicate events do not',async({page})=>{
 await page.goto(url);await page.waitForFunction(()=>!!window.cowork?.adapter);
 let count=0;page.on('request',r=>{if(r.url().endsWith('/api/cowork/intent'))count++});
 await page.evaluate(()=>window.cowork.controller.transcript('set A1 to five','synthetic-final-1',false));expect(count).toBe(0);
 await page.evaluate(()=>window.cowork.controller.transcript('set A1 to five','synthetic-final-1',true));expect(count).toBe(1);
 await page.evaluate(()=>window.cowork.controller.transcript('set A1 to five','synthetic-final-1',true));expect(count).toBe(1);
 await expect(page.locator('#status')).not.toContainText('Inferring intent');
 await expect(page.locator('.tiptap')).not.toContainText('set A1 to five');
});

test('narrow and dark layouts retain usable controls',async({page})=>{
 await page.setViewportSize({width:390,height:844});await page.goto(url);await expect(page.locator('.tiptap')).toBeVisible();
 await page.getByRole('button',{name:'Light / dark'}).click();await expect(page.locator('html')).toHaveClass('dark');
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
 await page.screenshot({path:'../.cowork-local/narrow-dark.png',fullPage:true});
 await page.setViewportSize({width:1440,height:1000});await page.screenshot({path:'../.cowork-local/desktop-dark.png',fullPage:true});
});

test('synthetic microphone pause discards and releases tracks',async({page})=>{
 await page.goto(url);await page.waitForFunction(()=>!!window.cowork?.adapter);
 let count=0;page.on('request',r=>{if(r.url().endsWith('/api/transcribe'))count++});
 await page.evaluate(()=>{const native=navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);navigator.mediaDevices.getUserMedia=async options=>{const stream=await native(options);window.voiceTracks=stream.getTracks();return stream;};});
 await page.locator('#listen').click();await expect(page.locator('#listen')).toContainText('Listening');
 await page.locator('#pause').click();await expect(page.locator('#listen')).toHaveText('Enable voice');expect(count).toBe(0);
 expect(await page.evaluate(()=>window.voiceTracks.every(t=>t.readyState==='ended'))).toBeTruthy();
});

test('simulated model schema: finalized Chinese undo shares native history; Stop cancels late response',async({page})=>{
 await page.goto(url);const doc=page.locator('.tiptap');await doc.fill('Human work');
 await page.route('**/api/cowork/intent',async route=>{const body=route.request().postDataJSON();await route.fulfill({json:{document_id:body.document_id,utterance_id:body.utterance_id,operations:[{type:'undo'}]}})});
 await page.getByPlaceholder('Ask AI to edit…').focus();
 await page.evaluate(()=>window.cowork.controller.transcript('撤销','simulated-undo',true));await expect(doc).not.toContainText('Human work');
 await page.getByRole('button',{name:'Redo',exact:true}).click();await expect(doc).toContainText('Human work');
 await page.unroute('**/api/cowork/intent');let held;
 await page.route('**/api/cowork/intent',async route=>{held=route;await new Promise(r=>{held.release=r});});
 await page.evaluate(()=>{window.pending=window.cowork.controller.submit('replace Human with late','late-response')});
 await expect.poll(()=>!!held).toBeTruthy();await doc.fill('Human edited during inference');await page.getByRole('button',{name:'Stop AI',exact:true}).click();
 held.release();await held.fulfill({json:{document_id:await page.evaluate(()=>window.cowork.id),utterance_id:'late-response',operations:[{type:'document.replace',find:'Human edited during inference',text:'Wrong late edit'}]}}).catch(()=>{});
 await expect(doc).toContainText('Human edited during inference');
});

test('genuine XLSX UI exchange preserves values and formulas',async({page})=>{
 const {sheetToXlsx,xlsxToSheet}=await import('../src/exchange.js');
 const bytes=await sheetToXlsx({id:'synthetic',name:'Synthetic',sheetOrder:['s'],sheets:{s:{id:'s',name:'Data',cellData:{0:{0:{v:4},1:{v:'中文'},2:{f:'=A1*2'}}}}}});
 await page.goto(url);await page.waitForFunction(()=>!!window.cowork?.adapter);page.on('dialog',d=>d.accept(d.type()==='prompt'?'office':undefined));
 await page.locator('#import').setInputFiles({name:'synthetic.xlsx',mimeType:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',buffer:Buffer.from(bytes)});await page.waitForFunction(()=>window.cowork.kind==='sheet');
 const pending=page.waitForEvent('download');await page.getByRole('button',{name:'Export',exact:true}).click();const download=await pending;await download.saveAs('../.cowork-local/roundtrip.xlsx');
 const result=await xlsxToSheet(fs.readFileSync('../.cowork-local/roundtrip.xlsx'));const cells=Object.values(result.sheets)[0].cellData;
 expect(cells[0][0].v).toBe(4);expect(cells[0][1].v).toBe('中文');expect(cells[0][2].f).toBe('=A1*2');
});

test('DOCX upload rejects sync-unsupported tables, plain paragraph roundtrip remains supported',async({page})=>{
 const {documentToDocx}=await import('../src/exchange.js');const mammoth=await import('mammoth');
 const p=text=>({type:'paragraph',content:[{type:'text',text}]});
 const bytes=await documentToDocx({type:'doc',content:[p('Roundtrip 中文'),{type:'table',content:[{type:'tableRow',content:[{type:'tableCell',content:[p('Table cell')]}]}]}]});
 await page.goto(url);await page.waitForFunction(()=>!!window.cowork?.adapter);page.on('dialog',d=>d.accept(d.type()==='prompt'?'office':undefined));
 await page.locator('#import').setInputFiles({name:'synthetic.docx',mimeType:'application/vnd.openxmlformats-officedocument.wordprocessingml.document',buffer:Buffer.from(bytes)});
 await expect(page.locator('#status')).toContainText('Unsupported Office/native');await expect(page.locator('.tiptap')).not.toContainText('Table cell');
 const {Document,Packer,Paragraph}=await import('docx');
 const plain=await Packer.toBuffer(new Document({sections:[{children:[new Paragraph('Roundtrip 中文')]}]}));
 await page.locator('#import').setInputFiles({name:'plain.docx',mimeType:'application/vnd.openxmlformats-officedocument.wordprocessingml.document',buffer:Buffer.from(plain)});
 await expect(page.locator('.tiptap')).toContainText('Roundtrip 中文');
 const pending=page.waitForEvent('download');await page.getByRole('button',{name:'Export',exact:true}).click();const download=await pending;
 await download.saveAs('../.cowork-local/roundtrip.docx');const text=await mammoth.default.extractRawText({buffer:fs.readFileSync('../.cowork-local/roundtrip.docx')});expect(text.value).toContain('Roundtrip 中文');expect(text.value).not.toContain('Table cell');
});
