const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const questions = require('../app/static/demo-data.js');
const engine = require('../app/static/demo-engine.js');

test('учебные вопросы доступны для пяти дисциплин и имеют допустимые ответы', () => {
  assert.equal(Object.keys(questions).length, 5);
  for (const items of Object.values(questions)) {
    assert.equal(items.length, 2);
    for (const item of items) {
      assert.ok(item.question && item.explanation);
      assert.ok(item.answer >= 0 && item.answer < item.options.length);
      assert.equal(new Set(item.options).size, item.options.length);
    }
  }
});

test('переход возможен после ответа, финал не создаёт оценку', () => {
  let state = engine.start(questions['Высшая математика']);
  assert.throws(() => engine.next(state));
  assert.throws(() => engine.answer(state, 99));
  state = engine.answer(state, 1);
  assert.equal(state.checked, true);
  assert.throws(() => engine.answer(state, 0));
  state = engine.next(state);
  assert.equal(state.index, 1);
  assert.equal(state.checked, false);
  state = engine.answer(state, 1);
  state = engine.next(state);
  assert.equal(state.finished, true);
  assert.equal('score' in state, false);
});

test('интерфейс проходит два вопроса и не отправляет ответы на сервер', async () => {
  class Element {
    constructor(tag = 'div') {
      this.tag = tag; this.children = []; this.listeners = {}; this.hidden = false;
      this.disabled = false; this.checked = false; this.textContent = ''; this.attributes = {};
      this.classList = { add() {}, remove() {}, toggle() {} };
    }
    append(...children) { this.children.push(...children); }
    replaceChildren(...children) { this.children = children; }
    addEventListener(name, handler) { this.listeners[name] = handler; }
    setAttribute(name, value) { this.attributes[name] = value; }
    scrollIntoView() {}
    focus() {}
    querySelector() {
      return elements['#demo-options'].children.map(label => label.children[0]).find(input => input.checked) || null;
    }
  }
  const ids = ['discipline-list', 'message', 'count', 'topics-section', 'topics-title', 'topics-message', 'topics-list', 'close-topics', 'start-demo', 'demo-availability', 'demo-section', 'demo-form', 'demo-options', 'check-answer', 'next-question', 'demo-finished', 'demo-progress', 'demo-question', 'demo-feedback', 'demo-discipline', 'restart-demo', 'close-demo'];
  const elements = Object.fromEntries(ids.map(id => [`#${id}`, new Element()]));
  const requests = [];
  const document = {
    querySelector(selector) { assert.ok(elements[selector], selector); return elements[selector]; },
    querySelectorAll(selector) { assert.equal(selector, '.discipline-card'); return elements['#discipline-list'].children; },
    createElement(tag) { return new Element(tag); },
  };
  const fetch = async url => {
    requests.push(url);
    if (url === '/api/disciplines') return { ok: true, json: async () => ({ disciplines: [{ discipline_id: 1, name: 'Высшая математика', topic_count: 1 }] }) };
    if (url === '/api/disciplines/1/topics') return { ok: true, json: async () => ({ topics: [{ name: 'Функции' }] }) };
    throw new Error(`Unexpected request: ${url}`);
  };
  const source = fs.readFileSync(path.join(__dirname, '../app/static/app.js'), 'utf8');
  vm.runInNewContext(source, { document, fetch, RemiDemoQuestions: questions, RemiDemoEngine: engine });
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(elements['#discipline-list'].children.length, 1);
  await elements['#discipline-list'].children[0].listeners.click();
  elements['#start-demo'].listeners.click();
  assert.equal(elements['#demo-section'].hidden, false);
  assert.equal(elements['#demo-progress'].textContent, 'ВОПРОС 1 ИЗ 2');
  let radio = elements['#demo-options'].children[1].children[0];
  radio.checked = true; radio.listeners.change();
  elements['#demo-form'].listeners.submit({ preventDefault() {} });
  assert.match(elements['#demo-feedback'].textContent, /^Верно\./);
  elements['#next-question'].listeners.click();
  assert.equal(elements['#demo-progress'].textContent, 'ВОПРОС 2 ИЗ 2');
  radio = elements['#demo-options'].children[1].children[0];
  radio.checked = true; radio.listeners.change();
  elements['#demo-form'].listeners.submit({ preventDefault() {} });
  assert.match(elements['#demo-feedback'].textContent, /^Не совсем\./);
  elements['#next-question'].listeners.click();
  assert.equal(elements['#demo-finished'].hidden, false);
  assert.deepEqual(requests, ['/api/disciplines', '/api/disciplines/1/topics']);
});
