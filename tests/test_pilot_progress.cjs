const test = require('node:test');
const assert = require('node:assert/strict');
const progress = require('../app/static/pilot-progress.js');

function memory() {
  const records = new Map();
  return { setItem: (key, value) => records.set(key, value),
    getItem: key => records.get(key) || null, removeItem: key => records.delete(key) };
}
const pilot = {goal:'b', nodes:[{competency_id:1,name:'a'}, {competency_id:2,name:'b'}],
  edges:[{prerequisite_id:1, competency_id:2}]};
const results = {a:{correct:1,total:2,status:'needs_review'}, b:{correct:2,total:2,status:'preliminary_correct'}};

test('результат сохраняется, восстанавливается и удаляется', () => {
  const store = memory();
  assert.equal(progress.save(store, pilot, results), true);
  assert.deepEqual(progress.load(store, pilot).results, results);
  const updated = {...results, a:{correct:2,total:2,status:'preliminary_correct'}};
  assert.equal(progress.save(store, pilot, updated), true);
  assert.deepEqual(progress.load(store, pilot).results, updated);
  assert.equal(progress.clear(store), true);
  assert.equal(progress.load(store, pilot), null);
});

test('изменение связей, неверный результат и недоступное хранилище обрабатываются безопасно', () => {
  const store = memory();
  assert.equal(progress.save(store, pilot, results), true);
  assert.equal(progress.load(store, {...pilot, edges:[]}), null);
  assert.equal(progress.save(store, pilot, {...results, a:{correct:1,total:2,status:'preliminary_correct'}}), false);
  assert.deepEqual(progress.load(store, pilot).results, results);
  assert.equal(progress.save(null, pilot, results), false);
  assert.equal(progress.load(null, pilot), null);
  assert.equal(progress.clear(null), false);
});

test('прогресс разных учебных маршрутов не перезаписывается', () => {
  const store = memory();
  const other = {...pilot, slug:'programming'};
  assert.equal(progress.save(store, pilot, results), true);
  const changed = {...results, a:{correct:2,total:2,status:'preliminary_correct'}};
  assert.equal(progress.save(store, other, changed), true);
  assert.deepEqual(progress.load(store, pilot).results, results);
  assert.deepEqual(progress.load(store, other).results, changed);
  progress.clear(store, other);
  assert.equal(progress.load(store, other), null);
  assert.deepEqual(progress.load(store, pilot).results, results);
});
