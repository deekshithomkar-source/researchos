import test from 'node:test';
import assert from 'node:assert/strict';
import { sectionData } from '../src/services/result-mapping.js';

test('every tab maps only to its corresponding module', () => {
  const keys = ['overview','research_questions','papers','sources','research_gaps','datasets','skills','courses','projects','internships','career_paths','next_steps','report'];
  const modules = Object.fromEntries(keys.map(key => [key, { marker: key }]));
  for (const key of keys) assert.equal(sectionData(modules,key), modules[key]);
  assert.notEqual(sectionData(modules,'papers'), sectionData(modules,'sources'));
});
test('missing modules never borrow overview or source content', () => {
  assert.deepEqual(sectionData({overview: {summary:'not a dataset'}, sources:[{title:'not a course'}]},'datasets'), []);
  assert.deepEqual(sectionData(null,'courses'), []);
});
