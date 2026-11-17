// Explicit opt-in real-service check. Audio must be synthetic append + silence + undo + silence.
// COWORK_TRIAL_DIR=/absolute/isolated-trial COWORK_SYNTHETIC_WAV=/absolute/synthetic.wav node tests/voice-live.mjs
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {chromium} from '@playwright/test';
const dir=process.env.COWORK_TRIAL_DIR,wav=process.env.COWORK_SYNTHETIC_WAV&&fs.realpathSync(process.env.COWORK_SYNTHETIC_WAV);
if(!dir||!wav)throw Error('Explicit isolated trial directory and synthetic audio required');
const base=fs.readFileSync(dir+'/url','utf8').trim(),evidence=[];
const browser=await chromium.launch({headless:true,args:['--use-fake-ui-for-media-stream','--use-fake-device-for-media-stream','--use-file-for-fake-audio-capture='+wav+'%noloop']});
const context=await browser.newContext({permissions:['microphone']});
const login=await context.request.post(base+'/api/auth/login',{data:{password:fs.readFileSync(dir+'/password','utf8')},headers:{Origin:base}});assert(login.ok());
const page=await context.newPage();
page.on('response',async r=>{if(r.url().includes('/api/cowork/intent')||r.url().endsWith('/api/transcribe'))evidence.push({url:r.url(),status:r.status(),body:await r.json()});});
try{
 await page.goto(base+'/static/cowork/index.html');await page.waitForFunction(()=>!!window.cowork?.adapter);await page.locator('#apply').waitFor({state:'visible'});await page.waitForFunction(()=>!document.getElementById('apply').disabled,{},{timeout:30000});
 await page.locator('.tiptap').fill('Human paragraph.');await page.locator('#listen').click();
 await page.waitForFunction(()=>document.querySelector('.tiptap')?.textContent.includes('trial is working'),{},{timeout:180000});
 await page.waitForFunction(()=>!document.querySelector('.tiptap')?.textContent.includes('trial is working'),{},{timeout:180000});
 assert.equal(await page.locator('.tiptap').innerText(),'Human paragraph.');assert.match(await page.locator('#listen').innerText(),/Listening/);
 await page.locator('#pause').click();
 for(const text of ['请添加一段文字,测试成功。','请添加一段文字：“测试成功。”','请添加一段文字 Hello World 测试成功']){
  const before=await page.locator('.tiptap').innerText();await page.evaluate(async text=>await window.cowork.controller.submit(text),text);
  const status=await page.locator('#status').innerText(),after=await page.locator('.tiptap').innerText();
  assert(!after.includes(text),'Instruction must not become inserted content');
  assert(after!==before||/clarif|明确|\?|？/i.test(status),'Apply intended content or ask clarification');
  evidence.push({input:text,status,document:after});
 }
}finally{fs.writeFileSync(dir+'/voice-live-evidence.json',JSON.stringify(evidence,null,2));await browser.close();}
console.log('Real sequential STT/model append + spoken native undo and bilingual checks passed');
