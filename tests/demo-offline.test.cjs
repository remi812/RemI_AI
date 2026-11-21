const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const demoPath = path.join(__dirname, '../demo/index.html');
const html = fs.readFileSync(demoPath, 'utf8');

function inlineScripts(source) {
  const scripts = [];
  const regex = /<script\b[^>]*>([\s\S]*?)<\/script>/gi;
  let match;
  while ((match = regex.exec(source)) !== null) {
    if (match[1].trim()) scripts.push(match[1]);
  }
  return scripts;
}

test('демо-файл автономен: стили и JavaScript встроены, нет сетевых запросов', () => {
  assert.doesNotMatch(html, /<script\b[^>]*\bsrc\s*=/i, 'не должно быть внешних скриптов');
  assert.doesNotMatch(html, /<link\b[^>]*\bhref\s*=/i, 'не должно быть внешних стилей');
  assert.doesNotMatch(html, /\bfetch\s*\(/, 'не должно быть сетевых запросов');
  assert.doesNotMatch(html, /XMLHttpRequest/, 'не должно быть XHR-запросов');
  assert.doesNotMatch(html, /<script\b[^>]*src\s*=|<img\b[^>]*src\s*=/i, 'демо не должно загружать внешние ресурсы автоматически');
  assert.match(html, /<style>/i, 'стили должны быть встроены');
});

test('демо содержит четыре дисциплины, примеры тем и ключевые элементы', () => {
  for (const name of [
    'Высшая математика',
    'Дифференциальные уравнения',
    'Основы программирования',
    'Моделирование систем',
    'Теория автоматического управления'
  ]) {
    assert.match(html, new RegExp(name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')), `отсутствует дисциплина ${name}`);
  }
  for (const topic of ['Функции', 'Производные', 'Переменные', 'Циклы', 'Математические модели', 'Обратная связь']) {
    assert.match(html, new RegExp(topic.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')), `отсутствует тема ${topic}`);
  }
  for (const id of [
    'discipline-list', 'topics-list', 'demo-form', 'demo-options',
    'demo-feedback', 'demo-progress', 'demo-finished', 'start-demo'
  ]) {
    assert.match(html, new RegExp(`id="${id}"`), `отсутствует элемент ${id}`);
  }
  assert.match(html, /демонстрационные данные/i);
  assert.match(html, /не сохраняются/i);
  assert.match(html, /не являются реальной оценкой/i);
  assert.match(html, /дальнейш/i);
});

test('встроенный JavaScript компилируется и работает без сети', async () => {
  const scripts = inlineScripts(html);
  assert.ok(scripts.length >= 2, 'должно быть несколько встроенных скриптов');

  for (const code of scripts) {
    new vm.Script(code, { filename: 'demo/index.html' });
  }

  class Element {
    constructor(tag = 'div') {
      this.tag = tag;
      this.children = [];
      this.listeners = {};
      this.hidden = false;
      this.disabled = false;
      this.checked = false;
      this.textContent = '';
      this.attributes = {};
      this.style = {};
      this.classList = { add() {}, remove() {}, toggle() {} };
    }
    append(...children) { this.children.push(...children); }
    replaceChildren(...children) { this.children = children; }
    addEventListener(name, handler) { this.listeners[name] = handler; }
    setAttribute(name, value) { this.attributes[name] = value; }
    scrollIntoView() {}
    focus() {}
    querySelector(selector) {
      if (selector === 'input[name="demo-answer"]:checked' || selector.includes('demo-answer')) {
        return (elements['#demo-options'].children || []).flatMap(label => label.children || [])
          .find(input => input && input.checked) || null;
      }
      const id = selector.replace(/^#/, '');
      return elements[`#${id}`] || null;
    }
    querySelectorAll(selector) {
      if (selector === '.discipline-card') return elements['#discipline-list'].children;
      return [];
    }
  }

  const ids = [
    'discipline-list', 'message', 'count', 'topics-section', 'topics-title',
    'topics-message', 'topics-list', 'resource-list', 'close-topics', 'start-demo', 'demo-availability',
    'demo-section', 'demo-form', 'demo-options', 'check-answer', 'next-question',
    'demo-finished', 'demo-progress', 'demo-question', 'demo-feedback', 'demo-result', 'demo-review',
    'demo-discipline', 'restart-demo', 'close-demo', 'next-steps-current', 'show-map',
    'map-section', 'path-map', 'map-goal', 'node-details', 'node-title'
  ];
  const elements = Object.fromEntries(ids.map(id => [`#${id}`, new Element()]));
  const document = {
    querySelector(selector) {
      assert.ok(elements[selector], selector);
      return elements[selector];
    },
    querySelectorAll(selector) {
      if (selector === '.discipline-card') return elements['#discipline-list'].children;
      return [];
    },
    createElement(tag) { return new Element(tag); },
    createElementNS(namespace, tag) { return new Element(tag); }
  };

  const sandbox = { document, console };
  vm.createContext(sandbox);
  vm.runInContext(scripts.join('\n;\n'), sandbox);
  await new Promise(resolve => setImmediate(resolve));

  assert.equal(elements['#discipline-list'].children.length, 4, 'должно быть четыре карточки дисциплин');

  await elements['#discipline-list'].children[0].listeners.click();
  assert.equal(elements['#topics-section'].hidden, false, 'должны открыться темы');
  assert.ok(elements['#topics-list'].children.length >= 1, 'должен быть список тем');
  assert.equal(elements['#start-demo'].disabled, true, 'нельзя начать без цели');
  elements['#topics-list'].children[1].children[1].listeners.click();
  assert.equal(elements['#start-demo'].disabled, false);

  elements['#start-demo'].listeners.click();
  assert.equal(elements['#demo-section'].hidden, false, 'должен открыться учебный пример');
  assert.equal(elements['#demo-progress'].textContent, 'ВОПРОС 1 ИЗ 2');

  let radio = elements['#demo-options'].children[1].children[0];
  radio.checked = true;
  radio.listeners.change();
  elements['#demo-form'].listeners.submit({ preventDefault() {} });
  assert.equal(elements['#demo-feedback'].textContent, 'Верно.');

  elements['#next-question'].listeners.click();
  assert.equal(elements['#demo-progress'].textContent, 'ВОПРОС 2 ИЗ 2');

  radio = elements['#demo-options'].children[1].children[0];
  radio.checked = true;
  radio.listeners.change();
  elements['#demo-form'].listeners.submit({ preventDefault() {} });
  assert.equal(elements['#demo-feedback'].textContent, 'Неверно.');

  elements['#next-question'].listeners.click();
  assert.equal(elements['#demo-finished'].hidden, false);
  assert.equal(elements['#demo-result'].textContent, 'Верных ответов в примере: 1 из 2.');
  assert.match(elements['#demo-review'].textContent, /производная/);
  elements['#show-map'].listeners.click();
  assert.equal(elements['#map-section'].hidden, false);
  assert.match(elements['#map-goal'].textContent, /Производные/);
  const nodes = elements['#path-map'].children;
  assert.equal(nodes[0].tag, 'svg');
  assert.ok(nodes[0].children.length > 0, 'должны отображаться связи');
  assert.match(nodes[1].className, /review/);
  assert.match(nodes[2].className, /passed/);
  assert.equal(nodes[nodes.length - 1].disabled, true);
  nodes[2].listeners.click();
  assert.equal(elements['#node-details'].hidden, false);
  assert.equal(elements['#node-title'].textContent, 'Графики');
  assert.ok(elements['#resource-list'].children.length > 0);
  elements['#restart-demo'].listeners.click();
  assert.equal(elements['#demo-finished'].hidden, true);
  assert.equal(elements['#map-section'].hidden, true);
  assert.equal(elements['#demo-progress'].textContent, 'ВОПРОС 1 ИЗ 2');
});
