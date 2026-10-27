import { spawn } from 'node:child_process';
import { resolve } from 'node:path';
import assert from 'node:assert/strict';
import { writeFileSync } from 'node:fs';

const browser = spawn('C:/Program Files/Google/Chrome/Application/chrome.exe', [
  '--headless=new', '--remote-debugging-port=9227',
  `--user-data-dir=${resolve('.tmp/auth-review-chrome')}`, '--no-first-run', 'about:blank',
], { windowsHide: true, stdio: 'ignore' });
const sleep = ms => new Promise(r => setTimeout(r, ms));
let socket;
try {
  let tabs;
  for (let i = 0; i < 40; i++) {
    try { tabs = await (await fetch('http://127.0.0.1:9227/json')).json(); break; }
    catch { await sleep(250); }
  }
  assert.ok(tabs, 'Chrome debugging connection');
  socket = new WebSocket(tabs.find(t => t.type === 'page').webSocketDebuggerUrl);
  await new Promise((ok, fail) => { socket.onopen = ok; socket.onerror = fail; });
  let id = 0;
  const pending = new Map();
  socket.onmessage = ({ data }) => {
    const result = JSON.parse(data);
    if (pending.has(result.id)) {
      const { ok, fail } = pending.get(result.id);
      pending.delete(result.id);
      result.error ? fail(new Error(JSON.stringify(result.error))) : ok(result.result);
    }
  };
  const call = (method, params = {}) => new Promise((ok, fail) => {
    const messageId = ++id;
    pending.set(messageId, { ok, fail });
    socket.send(JSON.stringify({ id: messageId, method, params }));
  });
  const evaluate = async expression => {
    const result = await call('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true });
    if (result.exceptionDetails) throw new Error(JSON.stringify(result.exceptionDetails));
    return result.result?.value;
  };
  const waitFor = async expression => {
    for (let i = 0; i < 480; i++) {
      if (await evaluate(expression)) return;
      await sleep(250);
    }
    throw new Error(`Browser check timed out: ${expression}; ${await evaluate('document.body.innerText')}`);
  };
  const fill = (selector, value) => evaluate(`(() => {
    const field = document.querySelector(${JSON.stringify(selector)});
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(field, ${JSON.stringify(value)});
    field.dispatchEvent(new Event('input', { bubbles: true }));
  })()`);
  const clickText = text => evaluate(`Array.from(document.querySelectorAll('button')).find(b => b.textContent.trim() === ${JSON.stringify(text)}).click()`);
  await call('Page.enable');
  const viewport = async width => { await call('Emulation.setDeviceMetricsOverride', {width, height: 1000, deviceScaleFactor: 1, mobile: false}); await sleep(350); };
  const noOverflow = async () => assert.ok(await evaluate('document.documentElement.scrollWidth <= innerWidth'), 'no horizontal page overflow');
  const screenshotAt = async (name, width) => { await viewport(width); await noOverflow(); if (name === 'results') await evaluate(`document.getElementById('research-results').scrollIntoView({block:'start'})`); const shot = await call('Page.captureScreenshot', {format: 'png'}); writeFileSync(`.tmp/ui-${name}-${width}.png`, Buffer.from(shot.data,'base64')); };
  await viewport(1440);
  await call('Page.navigate', {url:'http://127.0.0.1:5173/'});
  await waitFor(`!!document.querySelector('.ros-hero')`);
  for (const width of [1440, 780, 390, 320]) await screenshotAt('landing', width);
  await evaluate(`document.querySelector('.ros-menu-button').click()`);
  assert.ok(await evaluate(`document.querySelector('#landing-navigation').classList.contains('is-open')`));
  await evaluate(`document.querySelector('#landing-navigation a').click()`);
  assert.ok(await evaluate(`!document.querySelector('#landing-navigation').classList.contains('is-open')`));
  await clickText('Research gaps');
  assert.ok(await evaluate(`document.querySelector('.ros-preview-empty').innerText.includes('limitations')`));
  await call('Page.navigate', {url:'http://127.0.0.1:5173/auth?mode=signin'});
  await waitFor(`!!document.querySelector('input[type="email"]')`);
  assert.equal(await evaluate(`document.querySelectorAll('input[type="text"]').length`), 0);
  console.log('PASS landing responsive widths, navigation, interactive demo and sign-in CTA');
  await call('Page.navigate', {url:'http://127.0.0.1:5173/'});
  await waitFor(`!!document.querySelector('.ros-feature-trigger')`);
  for (const width of [1440, 390, 320]) {
    await viewport(width);
    await evaluate(`document.querySelector('.ros-feature-trigger').focus(); document.querySelector('.ros-feature-trigger').click()`);
    await waitFor(`!!document.querySelector('dialog[open]')`);
    assert.ok(await evaluate(`document.querySelector('dialog').contains(document.activeElement)`));
    assert.equal(await evaluate(`document.body.style.overflow`), 'hidden');
    await evaluate(`document.querySelector('dialog a').focus()`);
    await call('Input.dispatchKeyEvent', {type:'keyDown', key:'Tab',code:'Tab'});
    await sleep(100);
    assert.ok(await evaluate(`document.querySelector('dialog').contains(document.activeElement)`));
    await noOverflow();
    await sleep(300);
    const shot = await call('Page.captureScreenshot', {format:'png'});
    writeFileSync(`.tmp/motion-dialog-${width}.png`, Buffer.from(shot.data,'base64'));
    await call('Input.dispatchKeyEvent', {type:'keyDown',key:'Escape',code:'Escape'});
    await waitFor(`!document.querySelector('dialog')`);
    assert.ok(await evaluate(`document.activeElement.classList.contains('ros-feature-trigger')`));
    assert.notEqual(await evaluate(`document.body.style.overflow`), 'hidden');
  }
  await evaluate(`document.querySelectorAll('.ros-workflow-controls button')[1].click()`);
  assert.ok(await evaluate(`document.querySelector('.ros-stage-copy').innerText.includes('evidence')`));
  await call('Emulation.setEmulatedMedia', {features:[{name:'prefers-reduced-motion',value:'reduce'}]});
  assert.equal(await evaluate(`getComputedStyle(document.querySelector('.ros-floating')).animationName`), 'none');
  await call('Emulation.setEmulatedMedia', {features:[]});
  console.log('PASS modal focus trap, Escape, restoration, mobile sizing, stage switching and reduced motion');
  await viewport(1440);
  const email = `browser-review-${Date.now()}@example.com`;
  const password = `Review-only-${crypto.randomUUID()}`;
  await call('Page.navigate', { url: 'http://127.0.0.1:5173/auth' });
  await waitFor(`!!document.querySelector('input[type="email"]')`);
  await fill('input[type="text"]', 'Browser Review');
  await fill('input[type="email"]', email);
  await fill('input[type="password"]', password);
  await evaluate(`document.querySelector('button[type="submit"]').click()`);
  await waitFor(`location.pathname === '/dashboard' && document.body.innerText.includes('Sign out') && document.body.innerText.includes('API online')`);
  console.log('PASS signup -> authenticated dashboard');
  const status = await evaluate(`fetch('http://127.0.0.1:8000/api/auth/me', {credentials:'include'}).then(r => r.status)`);
  assert.equal(status, 200);
  console.log('PASS browser session cookie -> /auth/me 200');
  for (const width of [1440, 780, 390, 320]) await screenshotAt('dashboard', width);
  await evaluate(`document.querySelector('[aria-label="Open workspace navigation"]').click()`);
  assert.ok(await evaluate(`document.querySelector('[role="dialog"]')?.contains(document.activeElement)`));
  await call('Input.dispatchKeyEvent', {type:'keyDown',key:'Tab',code:'Tab',modifiers:8});
  assert.ok(await evaluate(`document.querySelector('[role="dialog"]')?.contains(document.activeElement)`));
  await call('Input.dispatchKeyEvent', {type:'keyDown',key:'Escape',code:'Escape'});
  await sleep(150);
  assert.ok(await evaluate(`document.activeElement.getAttribute('aria-label') === 'Open workspace navigation'`));
  await viewport(1440);
  await evaluate(`document.querySelector('[aria-label="Collapse sidebar"]').click()`);
  await sleep(250);
  assert.ok(await evaluate(`document.querySelector('.ros-app').classList.contains('is-collapsed')`));
  await evaluate(`document.querySelector('[aria-label="Expand sidebar"]').click()`);
  console.log('PASS dashboard responsive widths, sidebar collapse, mobile focus containment and Escape');
  await fill('#topic' , 'Artificial Intelligence in Healthcare');
  await evaluate(`(() => {
    for (const [selector, value] of [['#academic-level','PhD'],['#report-type','project_proposal']]) {
      const field = document.querySelector(selector);
      Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, 'value').set.call(field, value);
      field.dispatchEvent(new Event('change', {bubbles:true}));
    }
  })()`);
  await clickText('IEEE');
  await clickText('5');
  await clickText('Run research');
  await waitFor(`!!document.querySelector('progress')`);
  console.log('PASS research submission -> visible progress');
  await waitFor(`document.body.innerText.includes('Download MD')`);
  assert.ok(await evaluate(`document.querySelector('.ros-toast-region').innerText.includes('Research saved')`));
  console.log('PASS saved confirmation only after completed research response');
  const saved = await evaluate(`import('/src/services/api.js').then(async api => {
    const history = await api.getHistory();
    return await api.getResearchById(history[0].research_id);
  })`);
  assert.equal(saved.status, 'completed');
  assert.equal(saved.modules.overview.academic_level, 'PhD');
  assert.equal(saved.modules.report.output_type, 'project_proposal');
  assert.equal(saved.modules.report.citation_style, 'ieee');
  assert.ok(saved.modules.report.sections.some(s => s.name === 'Evaluation protocol'));
  await clickText('Research Papers');
  await waitFor(`!!document.querySelector('.paper-citation')`);
  const paperText = await evaluate(`document.querySelector('[data-result-section="papers"]').innerText`);
  assert.ok(paperText.includes('IEEE: [1]'));
  await clickText('Sources');
  const sourceText = await evaluate(`document.querySelector('[data-result-section="sources"]').innerText`);
  assert.notEqual(paperText, sourceText);
  assert.ok(sourceText.includes('Provider record:'));
  assert.ok(!sourceText.includes('IEEE:'));
  console.log('PASS PhD/proposal/IEEE input flow and distinct paper/provenance rendering');
  assert.equal(saved.sources.length, 5);
  assert.ok(saved.provider_diagnostics.length);
  assert.ok(saved.report);
  assert.ok(saved.intent && saved.citations.length === saved.sources.length);
  assert.ok(saved.report_sections.length >= 8);
  assert.ok(Array.isArray(saved.evidence) && Array.isArray(saved.gaps));
  for (const passage of saved.evidence) {
    const paper = saved.sources.find(p => p.id === passage.paper_id);
    assert.equal(paper.abstract.slice(passage.start, passage.end), passage.text);
  }
  console.log('PASS additive analysis fields, citations, report sections and exact evidence offsets');
  console.log('PASS live retrieval -> completed report and 5 saved sources');
  await clickText('Datasets');
  await waitFor(`document.body.innerText.includes('Coverage and limitations')`);
  const intelligence = await evaluate(`import('/src/services/api.js').then(api => api.getIntelligence('${saved.research_id}'))`);
  assert.equal(intelligence.research_id, saved.research_id);
  assert.ok(intelligence.projects.length && intelligence.roadmap.length === 4);
  console.log('PASS browser -> enrichment API -> persisted recommendations', JSON.stringify(Object.fromEntries(Object.entries(intelligence.resources).map(([key,value]) => [key, {status:value.status, count:value.items.length}]))));
  for (const label of ['Skills','Courses','Projects','Internships','Career Paths','Next Steps']) {
    await clickText(label);
    await waitFor(`!!document.querySelector('.intelligence-section')`);
    const contents = await evaluate(`document.querySelector('.intelligence-section').innerText`);
    assert.ok(contents.length > 50, label + ' renders its own data');
  }
  await clickText('Internships');
  assert.ok(await evaluate(`document.body.innerText.includes('not vacancies')`));
  console.log('PASS all intelligence tabs; suggested roles separated from listings');
  await clickText('Sources');
  await waitFor(`document.querySelectorAll('.source-card').length > 0 || document.body.innerText.includes('Source catalog')`);
  const screenshot = await call('Page.captureScreenshot', { format: 'png' });
  writeFileSync('.tmp/retrieval-browser.png', Buffer.from(screenshot.data, 'base64'));

  await evaluate(`document.querySelector('[role="tab"][aria-selected="true"]').focus()`);
  await call('Input.dispatchKeyEvent', {type:'keyDown',key:'ArrowRight',code:'ArrowRight'});
  await sleep(150);
  assert.equal(await evaluate(`document.activeElement.getAttribute('aria-selected')`), 'true');
  await clickText('Sources');
  for (const width of [1440, 780, 390, 320]) await screenshotAt('results', width);
  console.log('PASS result keyboard navigation and no page overflow at all four viewport sizes');
  await viewport(1440);
  await call('Page.reload');
  await waitFor(`location.pathname === '/dashboard' && document.body.innerText.includes('Sign out') && document.body.innerText.includes('API online')`);
  console.log('PASS dashboard survives refresh');
  await waitFor(`!!document.querySelector('.history-item')`);
  await evaluate(`document.querySelector('.history-item').click()`);
  await waitFor(`document.body.innerText.includes('Download MD')`);
  await clickText('Skills');
  await waitFor(`document.body.innerText.includes('Learning roadmap')`);
  console.log('PASS reload -> persisted intelligence and roadmap');

  await clickText('Sign out');
  await waitFor(`location.pathname === '/auth' && !!document.querySelector('input[type="email"]')`);
  await clickText('Sign in');
  await fill('input[type="email"]', email);
  await fill('input[type="password"]', password);
  await evaluate(`document.querySelector('button[type="submit"]').click()`);
  await waitFor(`location.pathname === '/dashboard' && document.body.innerText.includes('Sign out') && document.body.innerText.includes('API online')`);
  console.log('PASS sign-in -> authenticated dashboard');
  await clickText('Sign out');
  await waitFor(`location.pathname === '/auth'`);
  console.log('PASS signout; review account and successful research retained');
} finally {
  socket?.close();
  browser.kill();
}
