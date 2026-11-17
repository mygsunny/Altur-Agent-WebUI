import {test,expect,firefox} from '@playwright/test';import fs from 'node:fs';
const base=process.env.COWORK_LOOPBACK_URL;test.skip(!base,'Set COWORK_LOOPBACK_URL to the secure-context localhost trial');
test('Firefox actual recorder captures Opus from synthetic audio and UI releases session',async()=>{
 test.setTimeout(60000);const browser=await firefox.launch();try{const context=await browser.newContext();
 await context.request.post(base+'/api/auth/login',{data:{password:fs.readFileSync(process.env.COWORK_PASSWORD_FILE,'utf8')},headers:{Origin:base}});
 const page=await context.newPage();await page.goto(base+'/static/cowork/index.html');await expect(page.locator('#apply')).toBeEnabled({timeout:40000});
 // Synthetic audio stream, not a fake MediaRecorder or a claim about hardware.
 await page.evaluate(()=>{window.audioFixture=new AudioContext();const dest=audioFixture.createMediaStreamDestination();const oscillator=audioFixture.createOscillator();oscillator.connect(dest);oscillator.start();window.fixtureStream=dest.stream;navigator.mediaDevices.getUserMedia=async()=>{await audioFixture.resume();return fixtureStream};const Native=MediaRecorder;window.recorded=[];window.createdRecorders=[];window.MediaRecorder=class extends Native{constructor(stream,options){super(stream,options);createdRecorders.push(this);this.addEventListener('dataavailable',e=>recorded.push({size:e.data.size,type:e.data.type}))}};});
 await page.locator('#listen').click();await expect(page.locator('#status')).toContainText('Microphone ON');
 await page.waitForTimeout(1400);expect(await page.evaluate(()=>createdRecorders[0].state)).toBe('recording');expect(await page.evaluate(()=>createdRecorders[0].mimeType)).toMatch(/audio\/(webm|ogg).*opus/);
 await page.locator('#pause').click();await expect.poll(()=>page.evaluate(()=>recorded.some(x=>x.size>0))).toBe(true);
 expect(await page.evaluate(()=>fixtureStream.getTracks().every(t=>t.readyState==='ended'))).toBe(true);console.log('Firefox real synthetic recorder',await page.evaluate(()=>recorded));await page.evaluate(()=>audioFixture.close());
 }finally{await browser.close();}
});
