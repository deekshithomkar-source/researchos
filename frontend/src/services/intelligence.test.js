import test from 'node:test';
import assert from 'node:assert/strict';
import { safeResourceUrl, resourceStatus, intelligenceTabs } from './intelligence.js';
test('resource links reject executable and malformed URLs', () => {
  assert.equal(safeResourceUrl('javascript:alert(1)'), null);
  assert.equal(safeResourceUrl('bad'), null);
  assert.equal(safeResourceUrl('https://ocw.mit.edu/'), 'https://ocw.mit.edu/');
});
test('provider failure is not described as an empty search', () => {
  assert.match(resourceStatus('provider_unavailable'), /unavailable/);
  assert.match(resourceStatus('no_verified_matches'), /No verified matches/);
});
test('all requested intelligence sections have unique identifiers', () => {
  assert.equal(new Set(intelligenceTabs.map(([id]) => id)).size, 7);
});

test('invalid metadata has its own empty-state explanation', () => {
  assert.match(resourceStatus('invalid_response'), /invalid metadata/);
  assert.doesNotMatch(resourceStatus('invalid_response'), /No verified matches/);
});
