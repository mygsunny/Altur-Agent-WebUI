import {test,expect} from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
import {Document,Packer,Paragraph,TextRun} from 'docx';
import ExcelJS from 'exceljs';
const trial=path.resolve(process.env.COWORK_TRIAL_DIR||'../.cowork-local/sync-trial');
const base=fs.readFileSync(trial+'/url','utf8').trim();
const shared=trial+'/shared';fs.mkdirSync(shared,{recursive:true});
fs.writeFileSync(trial+'/state/cowork-office-roots.json',JSON.stringify({default:shared}));
test.beforeEach(async({context})=>{expect((await context.request.post(base+'/api/auth/login',{data:{password:fs.readFileSync(trial+'/password','utf8')},headers:{Origin:base}})).ok()).toBeTruthy();});
for(const kind of ['document','sheet'])test(kind+' synthetic filesystem roundtrip resets native Undo without feedback',async({page})=>{
 await page.goto(base+'/static/cowork/index.html');await page.waitForFunction(()=>window.cowork?.adapter);
 if(kind==='sheet'){await page.locator('#new-sheet').click();await page.waitForFunction(()=>window.cowork?.kind==='sheet');}
 const id=await page.evaluate(()=>window.cowork.id),filename=shared+'/'+id+(kind==='sheet'?'.xlsx':'.docx');
 await expect.poll(()=>fs.existsSync(filename),{timeout:30000}).toBeTruthy();
 let bytes;
 if(kind==='document')bytes=await Packer.toBuffer(new Document({sections:[{children:[new Paragraph('External synthetic arrival')]}]}));
 else{const wb=new ExcelJS.Workbook();wb.addWorksheet('External').getCell('A1').value='External synthetic arrival';bytes=await wb.xlsx.writeBuffer();}
 fs.writeFileSync(filename+'.incoming',bytes);fs.renameSync(filename+'.incoming',filename);
 await expect(page.getByRole('button',{name:'Import external Office version'})).toBeVisible({timeout:30000});
 await page.getByRole('button',{name:'Import external Office version'}).click();
 await expect.poll(async()=>page.evaluate(()=>JSON.stringify(window.cowork.adapter.snapshot())),{timeout:30000}).toContain('External synthetic arrival');
 await page.locator('#undo').click();
 expect(await page.evaluate(()=>JSON.stringify(window.cowork.adapter.snapshot()))).toContain('External synthetic arrival');
 await page.waitForTimeout(5500);expect(fs.readFileSync(filename).equals(Buffer.from(bytes))).toBeTruthy();
});
test('upload retains exact original bytes and external/local conflict requires explicit import',async({page})=>{
 await page.goto(base+'/static/cowork/index.html');await page.waitForFunction(()=>window.cowork?.adapter);
 const original=await Packer.toBuffer(new Document({sections:[{children:[new Paragraph('Original upload')]}]}));
 page.on('dialog',d=>d.accept());
 await page.locator('#import').setInputFiles({name:'original.docx',mimeType:'application/vnd.openxmlformats-officedocument.wordprocessingml.document',buffer:original});
 await expect(page.locator('.tiptap')).toContainText('Original upload');
 const id=await page.evaluate(()=>window.cowork.id),filename=shared+'/'+id+'.docx';
 await expect.poll(()=>fs.existsSync(filename)&&fs.readFileSync(filename).equals(original)).toBeTruthy();
 const external=await Packer.toBuffer(new Document({sections:[{children:[new Paragraph('Remote conflict copy')]}]}));
 fs.writeFileSync(filename,external);await page.locator('.tiptap').fill('Local conflict copy');
 await expect(page.getByRole('button',{name:'Import external Office version'})).toBeVisible({timeout:20000});
 await expect(page.locator('.tiptap')).toContainText('Local conflict copy');expect(fs.readFileSync(filename).equals(external)).toBeTruthy();
 await page.getByRole('button',{name:'Import external Office version'}).click();
 await expect(page.locator('.tiptap')).toContainText('Remote conflict copy');
 const backups=trial+'/state/cowork/default/office-backups/'+id;
 const natives=trial+'/state/cowork/default/native-backups/'+id;
 expect(fs.readdirSync(natives).some(n=>fs.readFileSync(natives+'/'+n,'utf8').includes('Local conflict copy'))).toBeTruthy();
 expect(fs.readdirSync(backups).some(n=>fs.readFileSync(backups+'/'+n).equals(original))).toBeTruthy();
});
test('unsupported external formatting is never silently overwritten',async({page})=>{
 await page.goto(base+'/static/cowork/index.html');await page.waitForFunction(()=>window.cowork?.adapter);
 const id=await page.evaluate(()=>window.cowork.id),filename=shared+'/'+id+'.docx';
 await expect.poll(()=>fs.existsSync(filename)).toBeTruthy();
 const bytes=await Packer.toBuffer(new Document({sections:[{children:[new Paragraph({children:[new TextRun({text:'Unsupported bold original',bold:true})]})]}]}));
 fs.writeFileSync(filename,bytes);
 await expect(page.locator('#status')).toContainText('Unsupported Office/native',{timeout:15000});
 await page.locator('.tiptap').fill('Local retained');await page.waitForTimeout(5500);
 expect(fs.readFileSync(filename).equals(bytes)).toBeTruthy();
 await expect(page.locator('.tiptap')).toContainText('Local retained');
});

for(const dropped of ['accept','native-save'])test('dropped '+dropped+' response reconciles without repeated native replacement',async({page})=>{
 await page.goto(base+'/static/cowork/index.html');await page.waitForFunction(()=>window.cowork?.adapter);
 const id=await page.evaluate(()=>window.cowork.id),filename=shared+'/'+id+'.docx';
 await expect.poll(()=>fs.existsSync(filename)).toBeTruthy();
 const external=await Packer.toBuffer(new Document({sections:[{children:[new Paragraph('Durable external import')]}]}));
 fs.writeFileSync(filename,external);
 await expect(page.getByRole('button',{name:'Import external Office version'})).toBeVisible({timeout:15000});
 let droppedOnce=false;
 await page.route('**/api/cowork/**',async route=>{
  const body=route.request().postDataJSON();
  if(!droppedOnce&&body&&((dropped==='accept'&&body.action==='accept')||(dropped==='native-save'&&body.office_import))){
   droppedOnce=true;await route.fetch();await route.abort('failed');return;
  }
  await route.continue();
 });
 await page.getByRole('button',{name:'Import external Office version'}).click();
 await expect(page.locator('.tiptap')).toContainText('Durable external import');
 await page.evaluate(()=>{window.importedAdapter=window.cowork.adapter});
 await page.evaluate(()=>window.cowork.officeSync.tick());
 expect(droppedOnce).toBeTruthy();
 expect(await page.evaluate(()=>window.importedAdapter===window.cowork.adapter)).toBeTruthy();
 await expect(page.getByRole('button',{name:'Import external Office version'})).toBeHidden();
 expect(fs.readFileSync(filename).equals(external)).toBeTruthy();
 await page.reload();await page.waitForFunction(()=>window.cowork?.adapter);
 await expect(page.locator('.tiptap')).toContainText('Durable external import');
 await page.evaluate(()=>window.cowork.officeSync.tick());
 await expect(page.getByRole('button',{name:'Import external Office version'})).toBeHidden();
});

test('native edits publish a distinct generation and never rewrite watched Office input',async({page})=>{
 await page.goto(base+'/static/cowork/index.html');await page.waitForFunction(()=>window.cowork?.adapter);
 const id=await page.evaluate(()=>window.cowork.id),input=shared+'/'+id+'.docx';
 await expect.poll(()=>fs.existsSync(input)).toBeTruthy();const original=fs.readFileSync(input);
 await page.locator('.tiptap').fill('New native generation');
 const generations=()=>fs.readdirSync(shared).filter(n=>n.startsWith(id+'.export-'));
 await expect.poll(()=>generations().length,{timeout:15000}).toBeGreaterThan(0);
 expect(fs.readFileSync(input).equals(original)).toBeTruthy();
 const {default:JSZip}=await import('jszip');
 const output=generations()[0],z=await JSZip.loadAsync(fs.readFileSync(shared+'/'+output));
 expect(await z.file('word/document.xml').async('string')).toContain('New native generation');
 await page.evaluate(()=>window.cowork.officeSync.tick());
 await expect(page.locator('body')).toContainText(output);
 await expect(page.getByRole('button',{name:'Import external Office version'})).toBeHidden();
});
