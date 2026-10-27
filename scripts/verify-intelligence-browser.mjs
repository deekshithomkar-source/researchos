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
  await fill('#topic', 'Artificial Intelligence in Healthcare');
  await clickText('5');
  await clickText('Run research');
  await waitFor(`!!document.querySelector('progress')`);
  console.log('PASS research submission -> visible progress');
  await waitFor(`document.body.innerText.includes('Download MD')`);
  const saved = await evaluate(`import('/src/services/api.js').then(async api => {
    const history = await api.getHistory();
    return await api.getResearchById(history[0].research_id);
  })`);
  assert.equal(saved.status, 'completed');
  assert.equal(saved.sources.length, 5);
  assert.ok(saved.provider_diagnostics.length);
  assert.ok(saved.report && saved.findings.length);
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
  }
  await clickText('Internships');
  assert.ok(await evaluate(`document.body.innerText.includes('not vacancies')`));
  console.log('PASS all intelligence tabs; suggested roles separated from listings');
  await clickText('Sources');
  await waitFor(`document.querySelectorAll('.source-card').length > 0 || document.body.innerText.includes('Source catalog')`);
  const screenshot = await call('Page.captureScreenshot', { format: 'png' });
  writeFileSync('.tmp/retrieval-browser.png', Buffer.from(screenshot.data, 'base64'));

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
