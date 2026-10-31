import {test,expect} from '@playwright/test';
import fs from 'node:fs';
import crypto from 'node:crypto';
test.use({browserName:'firefox'});
const trial=process.env.COWORK_TRIAL_DIR||'../.cowork-local';
const origins=(process.env.COWORK_TEST_ORIGINS||fs.readFileSync(trial+'/url','utf8').trim()).split(',');
for(const base of origins)test(`Firefox ${base} dismiss clarification resumes only waiting commands`,async({page,context})=>{
 test.setTimeout(45000);expect((await context.request.post(base+'/api/auth/login',{data:{password:fs.readFileSync(trial+'/password','utf8')},headers:{Origin:base}})).ok()).toBeTruthy();
 const calls=[];await page.route('**/api/cowork/intent',async route=>{const b=route.request().postDataJSON();calls.push(b.text);await new Promise(r=>setTimeout(r,50));await route.fulfill({json:{document_id:b.document_id,utterance_id:b.utterance_id,...(['A','C'].includes(b.text)?{clarification:'Which target?'}:{operations:[{type:'document.append',text:'result '+b.text}]})}});});
 await page.goto(base+'/static/cowork/index.html?id=clarification-fixture-'+crypto.randomUUID());await expect(page.locator('#apply')).toBeEnabled({timeout:30000});
 await page.evaluate(()=>{const c=window.cowork.controller;c.submit('A','a');c.submit('B','b');c.submit('C','c');c.submit('D','d');});
 await expect(page.locator('#command-queue')).toContainText('Clarification');await expect(page.locator('#command-queue')).toContainText('Paused');expect(calls).toEqual(['A']);
 await page.getByRole('button',{name:'Dismiss',exact:true}).click();await expect(page.locator('.tiptap')).toContainText('result B',{timeout:3000});
 await expect(page.locator('#command-queue')).toContainText('Clarification');expect(calls).toEqual(['A','B','C']);await page.getByRole('button',{name:'Dismiss',exact:true}).click();await expect(page.locator('.tiptap')).toContainText('result D');
 await page.locator('#request').fill('E');await page.locator('#apply').click();await expect(page.locator('.tiptap')).toContainText('result E');expect(calls).toEqual(['A','B','C','D','E']);expect(await page.locator('.tiptap').innerText()).not.toMatch(/result [AC]/);await expect(page.locator('#command-queue li')).toHaveCount(0);
});
