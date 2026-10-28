// Isolated presentation test: no backend, credentials, sessions or network.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const root = path.resolve(__dirname, '..');
(async () => {
 const browser = await chromium.launch({headless:true});
 const page = await browser.newPage();
 await page.route('**/*', r => r.abort());
 const html = fs.readFileSync(path.join(root,'static/index.html'),'utf8');
 const css = fs.readFileSync(path.join(root,'static/style.css'),'utf8');
 const sidebar = html.match(/<aside class="sidebar">([\s\S]*?)<\/aside>/)[0].replace(/<script\b[^>]*>[\s\S]*?<\/script>/g,'');
 const out = path.join(root,'evidence/sidebar-new-chat'); fs.mkdirSync(out,{recursive:true});
 const results=[];
 for(const width of [1280,390]) for(const dark of [false,true]) {
  await page.setViewportSize({width,height:800});
  await page.setContent(`<!doctype html><html class="${dark?'dark':''}"><head><style>${css}</style></head><body><div class="layout">${sidebar}</div></body></html>`);
  await page.evaluate(() => {
   window.$ = id => document.getElementById(id);
   window.activationCount=0;
   $('btnNewChat').onclick=()=>window.activationCount++;
   document.body.classList.add('sidebar-open');
   document.querySelector('.sidebar').style.cssText='display:flex;position:relative;transform:none;visibility:visible;left:0;top:0;height:100vh;width:280px;z-index:100;pointer-events:auto;';
   $('sessionList').innerHTML='<div class="session-date-header">Today</div><div class="session-item"><span class="session-title">Example conversation</span></div>';
  });
  const button=page.locator('#btnSidebarNewChat');
  await button.click(); await button.focus(); await page.keyboard.press('Enter'); await page.keyboard.press('Space');
  assert.equal(await page.evaluate(()=>window.activationCount),3,'click, Enter, Space each delegate once');
  const metrics=await page.evaluate(()=>{
   const b=$('btnSidebarNewChat'), svg=b.querySelector('svg'), label=b.querySelector('span'), date=document.querySelector('.session-date-header');
   const br=b.getBoundingClientRect(), sr=svg.getBoundingClientRect(),lr=label.getBoundingClientRect(),dr=date.getBoundingClientRect();
   return {buttonLeft:br.left,iconLeft:sr.left,dateContentLeft:dr.left+parseFloat(getComputedStyle(date).paddingLeft),centerDelta:Math.abs(sr.y+sr.height/2-lr.y-lr.height/2),aboveToday:br.bottom<=dr.top,height:br.height,background:getComputedStyle(b).backgroundColor,iconColor:getComputedStyle(svg).color};
  });
  assert(metrics.aboveToday);assert(metrics.centerDelta<1);assert.equal(metrics.iconLeft,metrics.dateContentLeft);assert(metrics.height>=(width<768?44:40));
  await page.screenshot({path:path.join(out,`${width}-${dark?'dark':'light'}.png`)});
  results.push({width,dark,...metrics,activations:3});
 }
 fs.writeFileSync(path.join(out,'results.json'),JSON.stringify(results,null,2));
 console.log(JSON.stringify(results,null,2));await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
