// Shared execution gate for every submitted study HTML, independent of subject.
const {chromium}=require(process.env.STUDY_PLAYWRIGHT_MODULE || 'playwright');
const fs=require('fs');
(async()=>{
  const {html}=JSON.parse(fs.readFileSync(0,'utf8'));
  const errors=[],blocked=[],checks=[],actions=[];
  if (!/<head(?:\s|>)/i.test(html)) {
    process.stdout.write(JSON.stringify({ok:false,errors:['Include an explicit head element for metadata and the validation policy.']}));return;
  }
  const browser=await chromium.launch({...(process.env.STUDY_CHROMIUM ? {executablePath:process.env.STUDY_CHROMIUM} : {}),headless:true});
  try {
    const context=await browser.newContext({viewport:{width:1280,height:900},reducedMotion:'reduce'});
    context.setDefaultTimeout(1500);
    await context.route('**/*',r=>{blocked.push(r.request().url().slice(0,180));return r.abort();});
    const page=await context.newPage();
    page.on('pageerror',e=>errors.push(e.message.slice(0,500)));
    page.on('console',msg=>{if(msg.type()==='error')errors.push(msg.text().slice(0,500));});
    const csp="default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data: blob:; font-src data:; media-src data: blob:; connect-src 'none'";
    const monitor=`<script>(()=>{const active=new Set(),start=globalThis.setInterval.bind(globalThis),stop=globalThis.clearInterval.bind(globalThis);globalThis.setInterval=(...args)=>{const id=start(...args);active.add(id);return id};globalThis.clearInterval=id=>{active.delete(id);return stop(id)};globalThis.__studyActiveIntervals=()=>active.size})();</script>`;
    const safe=html.replace(/<head([^>]*)>/i,(_,attrs)=>`<head${attrs}><meta http-equiv="Content-Security-Policy" content="${csp}">${monitor}`);
    await page.setContent('<iframe title="lesson" sandbox="allow-scripts" style="border:0;width:100%;height:800px"></iframe>');
    await page.locator('iframe').evaluate((el,src)=>el.srcdoc=src,safe);
    const frame=page.frameLocator('iframe');
    await frame.locator('body').waitFor();await page.waitForTimeout(300);
    const inspect=()=>frame.locator('body').evaluate(el=>{
      const visible=x=>x.getClientRects().length&&getComputedStyle(x).visibility!=='hidden';
      const name=x=>x.getAttribute('aria-label')?.trim()||
        (x.getAttribute('aria-labelledby')||'').split(/\s+/).map(id=>document.getElementById(id)?.textContent||'').join(' ').trim()||
        [...(x.labels||[])].map(l=>l.textContent).join(' ').trim()||
        (x.tagName==='BUTTON'?x.textContent.trim():'')||x.getAttribute('title')?.trim()||
        (['button','submit','reset'].includes(x.type)?x.value:'');
      const controls=[...document.querySelectorAll('button,input:not([type=hidden]),select,textarea')].filter(visible);
      return {text:el.innerText.trim().length,width:innerWidth,
        overflow:document.documentElement.scrollWidth>innerWidth+3,
        controls:controls.map(x=>({tag:x.tagName,type:x.type,id:x.id,label:name(x),disabled:x.disabled})),
        unlabeled:controls.filter(x=>!name(x)).length};
    });
    const desktop=await inspect();
    if(desktop.text<40)errors.push('The rendered lesson has insufficient visible explanatory text.');
    if(desktop.unlabeled)errors.push(`${desktop.unlabeled} visible controls lack accessible labels.`);
    const snapshot=()=>frame.locator('body').evaluate(el=>el.outerHTML+[...document.querySelectorAll('canvas')].map(c=>{try{return c.toDataURL()}catch{return ''}}).join(''));
    const initial=await snapshot();
    let changed=false;
    const exercise=async(label,kind,act,requireChange=true)=>{
      const before=await snapshot();
      try {
        await act();await page.waitForTimeout(160);
        const mutation=await snapshot()!==before;
        actions.push({label,kind,changed:mutation});changed ||= mutation;
        if(requireChange&&!mutation)errors.push(`Control "${label}" (${kind}) produced no rendered feedback or state change.`);
      }catch(e){errors.push(`Control "${label}" (${kind}) failed: ${e.message.slice(0,220)}`);}
    };
    const buttons=frame.locator('button,input[type=button],input[type=submit],input[type=reset]');
    if(await buttons.count()>20)errors.push('Split this lesson into smaller units: more than 20 action controls exceeds the execution check.');
    const deferred=[];
    for(let i=0;i<Math.min(await buttons.count(),20);i++){
      const b=buttons.nth(i);if(!(await b.isVisible()))continue;
      const label=(await b.getAttribute('aria-label'))||(await b.innerText())||(await b.getAttribute('value'))||`button ${i+1}`;
      if(/reset|previous|back|restart/i.test(label)){deferred.push({b,label});continue;}
      if(!(await b.isEnabled()))continue;
      await exercise(label,'click',()=>b.click({timeout:1500}));
    }
    const inputs=frame.locator('input:not([type=hidden]):not([type=button]):not([type=submit]):not([type=reset]),select,textarea');
    if(await inputs.count()>20)errors.push('Split this lesson into smaller units: more than 20 input controls exceeds the execution check.');
    for(let i=0;i<Math.min(await inputs.count(),20);i++){
      const c=inputs.nth(i);if(!(await c.isVisible())||!(await c.isEnabled()))continue;
      const info=await c.evaluate(x=>({tag:x.tagName,type:x.type,value:x.value,checked:x.checked,
        label:x.getAttribute('aria-label')||x.id||x.name||x.type,test:x.dataset.studyTestValue,
        step:x.step,min:x.min,max:x.max,options:x.tagName==='SELECT'?[...x.options].filter(o=>!o.disabled).map(o=>o.value):[]}));
      if(info.tag==='SELECT'){
        const value=info.options.find(v=>v!==info.value);
        if(value!==undefined)await exercise(info.label,'select',()=>c.selectOption(value));
      }else if(['checkbox','radio'].includes(info.type)){
        if(info.type==='radio'&&info.checked)continue;
        await exercise(info.label,info.type,()=>c.setChecked(!info.checked));
      }else if(info.type==='range'){
        const key=Number(info.value)>=Number(info.max||100)?'Home':'End';
        await exercise(info.label,'range keyboard',()=>c.press(key));
      }else if(['text','number','search','textarea'].includes(info.type)){
        let value=info.test||(info.type==='number'?String(Number(info.value||0)+(Number(info.step)||1)):'Example');
        if(info.max&&Number(value)>Number(info.max))value=info.min||'0';
        await exercise(info.label,'input',async()=>{await c.fill(value);await c.press('Enter');},false);
      }else {
        actions.push({label:info.label,kind:info.type,covered:false});
        errors.push(`Input type "${info.type}" has no automatic interaction check. Use a tested teaching control or add a scenario test before accepting it.`);
      }
    }
    // Return/reset controls are useful after another interaction changed state.
    for(const {b,label} of deferred){
      if(await b.isEnabled()){
        await exercise(label,'return/reset',()=>b.click({timeout:1500}),await snapshot()!==initial);
        if(/reset|restart/i.test(label)){
          const timers=await frame.locator('body').evaluate(()=>globalThis.__studyActiveIntervals());
          if(timers)errors.push(`Reset left ${timers} animation interval(s) running.`);
        }
      }
    }
    for(let i=0;i<Math.min(await buttons.count(),20);i++){
      const b=buttons.nth(i);if(!(await b.isVisible())||!(await b.isEnabled()))continue;
      const label=(await b.getAttribute('aria-label'))||(await b.innerText())||`button ${i+1}`;
      if(/reset|previous|back|restart/i.test(label))continue;
      await exercise(label,'keyboard Enter',()=>b.press('Enter'));break;
    }
    if(!changed)errors.push('No tested learner control changed the rendered lesson. Provide visible explanatory feedback.');
    for(const [label,width] of [['desktop',1280],['narrow desktop',900],['phone',390]]){
      await page.setViewportSize({width,height:900});await page.waitForTimeout(80);
      const view=await inspect();
      if(view.overflow)errors.push(`The document overflows horizontally at ${label} width (${width}px).`);
      checks.push({viewport:label,...view});
    }
    if(blocked.length)errors.push('The lesson attempted external requests; bundle dependencies and assets into the HTML.');
    process.stdout.write(JSON.stringify({ok:errors.length===0,errors:[...new Set(errors)],blocked,checks,actions,
      scope:'General runtime/interaction checks; source correctness and topic-specific expected results require scenario tests.'}));
  } finally {await browser.close();}
})().catch(e=>{process.stdout.write(JSON.stringify({ok:false,errors:['Browser validation failed: '+e.message]}));process.exitCode=1;});
