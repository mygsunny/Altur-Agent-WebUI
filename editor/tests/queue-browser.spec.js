import {test,expect} from '@playwright/test';
import fs from 'node:fs';
import crypto from 'node:crypto';
test.use({browserName:'firefox'});
for(const barrier of ['authentication','ownership','disconnect'])test(`Firefox session barrier ${barrier}`,async({page,context})=>{
 test.setTimeout(60000);const base=origins[0];await context.request.post(base+'/api/auth/login',{data:{password:fs.readFileSync(trial+'/password','utf8')},headers:{Origin:base}});
 let calls=0;await page.route('**/api/cowork/intent',async route=>{calls++;if(barrier==='disconnect')await route.abort('connectionfailed');else await route.fulfill({status:barrier==='authentication'?401:409,json:{error:'Session barrier'}});});
 await page.goto(base+'/static/cowork/index.html?id=queue-barrier-'+crypto.randomUUID());await expect(page.locator('#apply')).toBeEnabled({timeout:30000});
 await page.evaluate(()=>{window.cowork.controller.submit('first','a');window.cowork.controller.submit('second','b');});
 await expect(page.locator('#command-queue')).toContainText('Paused');expect(calls).toBe(1);expect(await page.evaluate(()=>window.cowork.controller.pauseReason)).toBe(barrier);await page.locator('#stop').click();
});
const trial=process.env.COWORK_TRIAL_DIR||'../.cowork-local';
const origins=(process.env.COWORK_TEST_ORIGINS||fs.readFileSync(trial+'/url','utf8').trim()).split(',');
for(const base of origins)for(const failure of ['invalid','timeout'])test(`Firefox ${base} FIFO ${failure} fixture`,async({page,context})=>{
 test.setTimeout(60000);
 const login=await context.request.post(base+'/api/auth/login',{data:{password:fs.readFileSync(trial+'/password','utf8')},headers:{Origin:base}});expect(login.ok()).toBeTruthy();
 const fixture='queue-fixture-'+crypto.randomUUID(),calls=[];
 await page.route('**/api/cowork/intent',async route=>{const b=route.request().postDataJSON();calls.push(b.text);if(b.text==='bad'){if(failure==='timeout')await new Promise(r=>setTimeout(r,300));await route.fulfill({json:{document_id:b.document_id,utterance_id:b.utterance_id,operations:[]}}).catch(()=>{});return;}await new Promise(r=>setTimeout(r,25));await route.fulfill({json:{document_id:b.document_id,utterance_id:b.utterance_id,operations:[{type:'document.append',text:'result '+b.text}]}});});
 await page.goto(base+'/static/cowork/index.html?id='+fixture);await expect(page.locator('#apply')).toBeEnabled({timeout:30000});
 await page.evaluate(mode=>{const c=window.cowork.controller;c.inferenceTimeout=mode==='timeout'?100:2000;c.submit('first','a');c.transcript('bad','b',true);c.submit('third','c');c.transcript('bad duplicate','b',true);},failure);
 await expect(page.locator('#command-queue')).toContainText('Running');await expect(page.locator('#command-queue')).toContainText('Waiting');
 await expect(page.locator('.tiptap')).toContainText('result third');expect(calls).toEqual(['first','bad','third']);
 await expect(page.locator('#command-queue li')).toHaveCount(1);await expect(page.locator('#command-queue')).toContainText('Failed');await expect(page.getByRole('button',{name:'Retry',exact:true})).toBeVisible();
 await page.waitForTimeout(350);expect(await page.locator('.tiptap').innerText()).not.toContain('bad');await page.getByRole('button',{name:'Dismiss',exact:true}).click();await expect(page.locator('#command-queue li')).toHaveCount(0);
 console.log(JSON.stringify({base,failure,fixture,calls,timing:'mock intent 25ms; timeout 100ms; late reply 300ms; actual Firefox/server/editor'}));
});
