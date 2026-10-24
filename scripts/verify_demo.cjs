// Local browser checks for the generated offline archive; never visits data providers.
const path=require('path');
const fs=require('fs');
const {pathToFileURL}=require('url');
const runtime=process.env.CODEX_DELIVERY_NODE_MODULES;
if(!runtime)throw new Error('Set CODEX_DELIVERY_NODE_MODULES to the bundled Node package directory');
const {chromium}=require(path.join(runtime,'playwright'));
const root=path.resolve(__dirname,'..');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try{
  const page=await browser.newPage({viewport:{width:1365,height:1024}});
  const errors=[];const requests=[];
  page.on('pageerror',e=>errors.push(String(e)));
  page.on('request',r=>{if(/^https?:/.test(r.url()))requests.push(r.url());});
  await page.goto(pathToFileURL(path.join(root,'demo/index.html')).href);
  await page.waitForSelector('#rawBars .prob');
  if(await page.locator('#match option').count()!==380)throw new Error('Expected all 380 matches');
  if(await page.locator('#model option').count()!==16)throw new Error('Expected 16 registered models');
  if(await page.locator('#rawBars .prob').count()!==3)throw new Error('Missing probability class');
  if(await page.locator('#actual').isVisible())throw new Error('Outcome should be hidden initially');
  await page.check('#showActual');if(!await page.locator('#actual').isVisible())throw new Error('Reveal outcome failed');
  await page.selectOption('#team','Arsenal');
  if(await page.locator('#match option').count()!==38)throw new Error('Team filter must include home and away');
  if(await page.locator('#actual').isVisible())throw new Error('Outcome must reset after filtering');
  await page.selectOption('#model','full__frequency');
  if(await page.locator('#calPanel').isVisible())throw new Error('Frequency baseline must not invent calibration');
  await page.fill('#date','2024-08-16');await page.locator('#date').dispatchEvent('change');
  if(!await page.locator('#empty').isVisible())throw new Error('Empty filter state missing');
  await page.click('#reset');
  if(await page.locator('#match option').count()!==380)throw new Error('Reset failed');
  await page.selectOption('#model','common__xgboost__A_plus_P_plus_F');
  if(!await page.locator('#calPanel').isVisible())throw new Error('Temperature display missing');
  const qa=path.join(root,'.qa');fs.mkdirSync(qa,{recursive:true});
  await page.screenshot({path:path.join(qa,'demo-desktop.png'),fullPage:true});
  await page.setViewportSize({width:390,height:844});
  await page.screenshot({path:path.join(qa,'demo-mobile.png'),fullPage:true});
  const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth);
  if(overflow)throw new Error('Mobile horizontal overflow');
  if(errors.length||requests.length)throw new Error(JSON.stringify({errors,requests}));
  fs.writeFileSync(path.join(root,'reports/delivery/demo_verification.json'),JSON.stringify({
    browser:'Microsoft Edge headless',matches:380,registered_models:16,team_filter:38,
    outcomes_hidden_and_reveal_works:true,empty_state_and_reset_passed:true,
    raw_and_temperature_display_passed:true,mobile_has_no_horizontal_overflow:true,
    javascript_errors:errors,external_network_requests:requests
  },null,2)+'\n');
  process.stdout.write('Offline demo browser checks passed on desktop and mobile.\n');
 }finally{await browser.close();}
})().catch(e=>{process.stderr.write(e.stack+'\n');process.exitCode=1;});
