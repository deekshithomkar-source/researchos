import assert from 'node:assert/strict';
import test from 'node:test';
import { resolveApiRoot } from '../src/services/api-url.js';

test('local authentication stays same-site for either loopback hostname', () => {
  assert.equal(resolveApiRoot('http://localhost:8000', 'http://127.0.0.1:5173/auth', true), 'http://127.0.0.1:8000');
  assert.equal(resolveApiRoot('http://127.0.0.1:8000/api/', 'http://localhost:5173/auth', true), 'http://localhost:8000');
});

test('default API uses the website hostname', () => {
  assert.equal(resolveApiRoot(undefined, 'http://127.0.0.1:5173/dashboard', true), 'http://127.0.0.1:8000');
});

test('explicit remote and production API configuration is preserved', () => {
  assert.equal(resolveApiRoot('https://api.example.com/api/', 'http://localhost:5173/auth', true), 'https://api.example.com');
  assert.equal(resolveApiRoot('http://localhost:8000', 'http://127.0.0.1:5173/auth', false), 'http://localhost:8000');
});
