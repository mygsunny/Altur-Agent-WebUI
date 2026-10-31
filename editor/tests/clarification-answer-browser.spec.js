import {test,expect} from '@playwright/test';
import fs from 'node:fs';
import crypto from 'node:crypto';
import {execFileSync} from 'node:child_process';
// Optional immutable baseline bundle proves the UI regression without changing
// the active served tree or any documents.
test.beforeEach(async({page})=>{
 const revision=process.env.COWORK_UI_BASELINE;if(!revision)return;
 const html=execFileSync('git',['show',revision+':static/cowork/index.html'],{encoding:'utf8'});
 const asset=html.match(/src="\/static\/cowork\/([^\"]+\.js)"/)[1];
 const body=execFileSync('git',['show',revision+':static/cowork/'+asset],{maxBuffer:5*1024*1024});
 await page.route('**/assets/index-*.js',route=>route.fulfill({body,contentType:'text/javascript'}));
});
test.use({browserName:'firefox'});
const trial=process.env.COWORK_TRIAL_DIR||'../.cowork-local';
const base=fs.readFileSync(trial+'/url','utf8').trim();
for(const action of ['stop','switch','dismiss','disconnect'])test('detached Answer cannot apply after '+action,async({page,context})=>{
 await context.request.post(base+'/api/auth/login',{data:{password:fs.readFileSync(trial+'/password','utf8')},headers:{Origin:base}});let calls=0;await page.route('**/api/cowork/intent',route=>{const b=route.request().postDataJSON();calls++;return route.fulfill({json:{...b,clarification:'Which?'}});});
 await page.goto(base+'/static/cowork/index.html?id=answer-stale-'+crypto.randomUUID());await expect(page.locator('#apply')).toBeEnabled({timeout:30000});await page.locator('#request').fill('A');await page.locator('#apply').click();await page.getByRole('textbox',{name:'Clarification answer'}).fill('stale answer');await page.getByRole('button',{name:'Answer',exact:true}).evaluate(button=>window.staleAnswer=button);
 if(action==='disconnect')await page.evaluate(()=>window.dispatchEvent(new Event('offline')));else if(action==='stop')await page.locator('#stop').click();else if(action==='dismiss')await page.getByRole('button',{name:'Dismiss',exact:true}).click();else await page.locator('#new-doc').click();
 await page.evaluate(()=>staleAnswer.click());await page.waitForTimeout(150);expect(calls).toBe(1);await expect(page.getByRole('textbox',{name:'Clarification answer'})).toHaveCount(0);
});
test('Answer error retains usable reply, rapid clicks dedupe, Stop rejects detached reply',async({page,context})=>{
 test.setTimeout(45000);await context.request.post(base+'/api/auth/login',{data:{password:fs.readFileSync(trial+'/password','utf8')},headers:{Origin:base}});
 const calls=[];await page.route('**/api/cowork/intent',async route=>{const b=route.request().postDataJSON();calls.push(b);await new Promise(r=>setTimeout(r,100));if(calls.length===2)return route.fulfill({status:500,json:{error:'fixture answer failure'}});await route.fulfill({json:{document_id:b.document_id,utterance_id:b.utterance_id,...(calls.length===1?{clarification:'Which text?'}:{operations:[{type:'document.append',text:'resolved'}]})}});});
 await page.goto(base+'/static/cowork/index.html?id=answer-retry-fixture-'+crypto.randomUUID());await expect(page.locator('#apply')).toBeEnabled({timeout:30000});await page.locator('#request').fill('A');await page.locator('#apply').click();
 const reply=page.getByRole('textbox',{name:'Clarification answer'});await reply.fill('retained answer');await page.getByRole('button',{name:'Answer',exact:true}).evaluate(button=>{button.click();button.click();});
 await expect(page.locator('#command-queue')).toContainText('fixture answer failure');await expect(reply).toHaveValue('retained answer');expect(calls.length).toBe(2);
 await page.getByRole('button',{name:'Answer',exact:true}).evaluate(button=>{window.detachedReply=button;button.click();button.click();});await expect(page.locator('.tiptap')).toContainText('resolved');expect(calls.length).toBe(3);
 await page.locator('#pause').click();await page.evaluate(()=>detachedReply.click());expect(calls.length).toBe(3);await expect(page.locator('#command-queue li')).toHaveCount(0);
});
test('Answer UI resumes same command before waiting B and supports reclarification',async({page,context})=>{
 test.setTimeout(45000);expect((await context.request.post(base+'/api/auth/login',{data:{password:fs.readFileSync(trial+'/password','utf8')},headers:{Origin:base}})).ok()).toBeTruthy();
 const calls=[];let releaseFirst;const firstGate=new Promise(resolve=>releaseFirst=resolve);await page.route('**/api/cowork/intent',async route=>{const b=route.request().postDataJSON();calls.push(b);if(calls.length===1)await firstGate;await new Promise(r=>setTimeout(r,100));await route.fulfill({json:{document_id:b.document_id,utterance_id:b.utterance_id,...(calls.length<=2?{clarification:calls.length===1?'Which text?':'Which paragraph?'}:{operations:[{type:'document.append',text:b.text==='B'?'result B':'result A'}]})}});});
 await page.goto(base+'/static/cowork/index.html?id=answer-fixture-'+crypto.randomUUID());await expect(page.locator('#apply')).toBeEnabled({timeout:30000});
 await page.locator('#request').fill('A');await page.locator('#apply').click();await page.locator('#request').fill('B');await page.locator('#apply').click();releaseFirst();
 const reply=page.getByRole('textbox',{name:'Clarification answer'});await reply.fill('hello');await reply.focus();await expect(page.locator('#command-queue')).toContainText('Voice replies to this clarification');
 await page.getByRole('button',{name:'Answer',exact:true}).click();await expect(page.locator('#command-queue')).toContainText('Which paragraph?');await expect(page.locator('#command-queue li')).toHaveCount(2);
 await page.route('**/api/transcribe',route=>route.fulfill({json:{text:'last paragraph'}}));
 await page.evaluate(()=>{window.audioFixture=new AudioContext();const dest=audioFixture.createMediaStreamDestination(),osc=audioFixture.createOscillator();window.voiceGain=audioFixture.createGain();voiceGain.gain.value=.2;osc.connect(voiceGain);voiceGain.connect(dest);osc.start();navigator.mediaDevices.getUserMedia=async()=>{await audioFixture.resume();return dest.stream;};});
 await page.locator('#listen').click();await reply.focus();await page.waitForTimeout(650);await page.evaluate(()=>voiceGain.gain.value=0);
 await expect(reply).toHaveValue('last paragraph',{timeout:10000});expect(calls.length).toBe(2);
 await page.getByRole('button',{name:'Answer',exact:true}).click();await expect(page.locator('.tiptap')).toContainText('result B');
 expect(calls.map(x=>x.utterance_id)).toEqual([calls[0].utterance_id,calls[0].utterance_id,calls[0].utterance_id,calls[3].utterance_id]);expect(calls[2].text).toContain('hello');expect(calls[2].text).toContain('last paragraph');await expect(page.locator('#command-queue li')).toHaveCount(0);
 expect(await page.locator('.tiptap').innerText()).toMatch(/result A\s+result B/);await page.locator('#undo').click();await expect(page.locator('.tiptap')).not.toContainText('result B');await expect(page.locator('.tiptap')).toContainText('result A');await page.locator('#redo').click();await expect(page.locator('.tiptap')).toContainText('result B');
});
