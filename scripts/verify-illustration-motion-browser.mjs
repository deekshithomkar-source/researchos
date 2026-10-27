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
  await call('Emulation.setDeviceMetricsOverride', {width:1440,height:1000,deviceScaleFactor:1,mobile:false});
  await call('Page.navigate', {url:'http://127.0.0.1:5173/'});
  await waitFor(`!!document.querySelector('.ros-art-scene')`);
  await evaluate(`document.querySelector('.ros-pillars').scrollIntoView({block:'center'})`);
  await waitFor(`document.querySelector('.ros-pillars svg').dataset.visible === 'true'`);
  assert.equal(await evaluate(`getComputedStyle(document.querySelector('.ros-art-scene')).animationName`),'ros-art-drift');
  assert.equal(await evaluate(`getComputedStyle(document.querySelector('.ros-art-search')).animationName`),'ros-art-explore');
  assert.equal(await evaluate(`getComputedStyle(document.querySelector('.ros-art-chart')).animationName`),'ros-art-chart-draw');
  await call('Emulation.setEmulatedMedia',{features:[{name:'prefers-reduced-motion',value:'reduce'}]});
  assert.equal(await evaluate(`getComputedStyle(document.querySelector('.ros-art-scene')).animationName`),'none');
  for (const width of [390,320]) {
    await call('Emulation.setDeviceMetricsOverride', {width,height:1000,deviceScaleFactor:1,mobile:false});
    assert.ok(await evaluate('document.documentElement.scrollWidth <= innerWidth'));
  }
  console.log('PASS viewport-triggered artwork, discovery/chart animation, reduced motion, mobile overflow');
} finally {
  socket?.close();
  browser.kill();
}
