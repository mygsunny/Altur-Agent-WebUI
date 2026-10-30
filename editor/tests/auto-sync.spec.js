import {test,expect} from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
import {Document,Packer,Paragraph} from 'docx';
import JSZip from 'jszip';
test.setTimeout(60000);
const trial=path.resolve(process.env.COWORK_TRIAL_DIR||'../.cowork-local/oneowner-live');
const base=fs.readFileSync(trial+'/url','utf8').trim(),shared=trial+'/shared';
test.beforeEach(async({context})=>{expect((await context.request.post(base+'/api/auth/login',{data:{password:fs.readFileSync(trial+'/password','utf8')},headers:{Origin:base}})).ok()).toBeTruthy();});
async function open(page){await page.goto(base+'/static/cowork/index.html');await page.waitForFunction(()=>window.cowork?.adapter);await expect(page.locator('#apply')).toBeEnabled({timeout:30000});return await page.evaluate(()=>window.cowork.id);}
async function arrival(id,text){const bytes=await Packer.toBuffer(new Document({sections:[{children:[new Paragraph(text)]}]}));const file=shared+'/'+id+'.docx';fs.writeFileSync(file+'.incoming',bytes);fs.renameSync(file+'.incoming',file);return bytes;}
test('disconnect freezes writers; delayed arriving Office reloads automatically before writers resume',async({page,context})=>{
 const id=await open(page),file=shared+'/'+id+'.docx';
 const original=fs.readFileSync(file);
 await context.setOffline(true);await expect(page.locator('#apply')).toBeDisabled({timeout:6000});
 expect(await page.locator('#editor').evaluate(e=>e.inert)).toBeTruthy();
 await page.evaluate(()=>window.cowork.controller.submit('Append a paragraph that says must not execute offline.'));
 expect(fs.readFileSync(file).equals(original)).toBeTruthy();
 await context.setOffline(false);
 await page.waitForTimeout(1000);await expect(page.locator('#apply')).toBeDisabled();
 // Connection and iCloud delivery are deliberately separate events.
 await page.waitForTimeout(7000);await arrival(id,'Delayed synthetic Office arrival');
 await expect(page.locator('.tiptap')).toContainText('Delayed synthetic Office arrival',{timeout:30000});
 await expect(page.locator('#apply')).toBeEnabled({timeout:15000});
 await page.locator('#undo').click();await expect(page.locator('.tiptap')).toContainText('Delayed synthetic Office arrival');
});
test('WebUI autosave updates SAME file with backups; late cloud arrival after a new edit preserves both and asks once',async({page})=>{
 const id=await open(page),file=shared+'/'+id+'.docx';
 await page.locator('.tiptap').fill('WebUI synthetic draft');
 await expect.poll(async()=>{const z=await JSZip.loadAsync(fs.readFileSync(file));return z.file('word/document.xml').async('string')},{timeout:30000}).toContain('WebUI synthetic draft');
 const external=await arrival(id,'Later remote copy');
 await expect(page.getByRole('button',{name:'Use arriving Office version (draft preserved)'})).toBeVisible({timeout:30000});
 await expect(page.locator('.tiptap')).toContainText('WebUI synthetic draft');expect(fs.readFileSync(file).equals(external)).toBeTruthy();
 const natives=trial+'/state/cowork/default/native-backups/'+id;
 expect(fs.readdirSync(natives).some(n=>fs.readFileSync(natives+'/'+n,'utf8').includes('WebUI synthetic draft'))).toBeTruthy();
 await page.getByRole('button',{name:'Use arriving Office version (draft preserved)'}).click();
 await expect(page.locator('.tiptap')).toContainText('Later remote copy');await expect(page.locator('#apply')).toBeEnabled();
});
test('last-moment native edit during external status read is a preserved conflict',async({page})=>{
 const id=await open(page);let entered=false,release,once=false;
 await page.route('**/api/cowork/sync',async route=>{const b=route.request().postDataJSON();if(!once&&b.action==='owner-status'){
  once=true;await arrival(id,'External status race');const response=await route.fetch();entered=true;await new Promise(r=>release=r);await route.fulfill({response});return;
 }await route.continue();});
 await expect.poll(()=>entered,{timeout:15000}).toBeTruthy();await page.locator('.tiptap').fill('Last moment native draft');release();
 await expect(page.getByRole('button',{name:'Use arriving Office version (draft preserved)'})).toBeVisible({timeout:15000});
 await expect(page.locator('.tiptap')).toContainText('Last moment native draft');
});
for(const dropped of ['accept','native-save'])test('automatic reconciliation survives dropped '+dropped+' without repeating replacement',async({page})=>{
 const id=await open(page);let once=false;
 await page.route('**/api/cowork/**',async route=>{let b;try{b=route.request().postDataJSON()}catch{};
  if(!once&&b&&((dropped==='accept'&&b.action==='accept')||(dropped==='native-save'&&b.office_import))){once=true;await route.fetch();await route.abort('failed');return;}await route.continue();});
 await arrival(id,'Durable automatic import');await expect(page.locator('.tiptap')).toContainText('Durable automatic import',{timeout:30000});
 await page.evaluate(()=>window.imported=window.cowork.adapter);await expect(page.locator('#apply')).toBeEnabled({timeout:15000});
 expect(once).toBeTruthy();await page.evaluate(()=>window.cowork.officeSync.tick());expect(await page.evaluate(()=>window.imported===window.cowork.adapter)).toBeTruthy();
});
