"""Встраивает подготовленный каталог в автономную демонстрационную страницу."""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
page = root / 'demo' / 'index.html'
html = page.read_text(encoding='utf-8')
old = "  { discipline_id: 2, name: 'Дифференциальные уравнения', description: 'Модели изменения систем', detail_level: 'overview', topic_count: 1, topics: ['Введение в дифференциальные уравнения'] },\n"
html = html.replace(old, '')
html = html.replace("topic_count: 3, topics: ['Функции', 'Производные', 'Интегралы']", "topic_count: 4, topics: ['Функции', 'Производные', 'Интегралы', 'Дифференциальные уравнения']")
html = html.replace('Вся демонстрация работает без интернета, сервера и базы.', 'Каталог и пробный тест работают без базы; для внешних материалов нужен интернет.')
resource_html = '<div class="resources"><h3>Курсы и материалы</h3><p class="resource-note">Демонстрационная подборка. Для перехода на внешние сайты нужен интернет. Условия доступа и качество требуют проверки; неподтверждённые ссылки скрыты.</p><div id="resource-list" class="resource-list" aria-live="polite"></div></div>'
if 'id="resource-list"' not in html:
    html = html.replace('<ul id="topics-list" class="topics-list"></ul>', '<ul id="topics-list" class="topics-list"></ul>\n        ' + resource_html)
callout = '<div class="demo-callout"><div><strong>Хочешь попробовать?</strong><p id="demo-availability">Посмотри, как может выглядеть тест по этой дисциплине.</p></div><button id="start-demo" class="primary-button" type="button">Начать пример <span aria-hidden="true">↗</span></button></div>'
html = html.replace(resource_html + '\n        ' + callout, callout + '\n        ' + resource_html)
style = '''.resources { margin-top: 26px; border-top: 1px solid #e8eee6; padding-top: 15px; }
.resources h3 { color: #203b2a; margin-bottom: 6px; }
.resource-note { color: #718174; font-size: 12px; line-height: 1.5; }
.resource-list { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 240px), 1fr)); gap: 10px; margin-top: 14px; }
.resource-card { border: 1px solid #e5ece2; border-radius: 12px; padding: 15px; background: #fbfcfa; }
.resource-card a, .resource-card strong { color: #285d3c; font-weight: 700; font-size: 14px; }
.resource-card p { color: #718174; font-size: 12px; line-height: 1.5; margin: 8px 0 0; }
'''
if '.resource-card {' not in html:
    html = html.replace('  </style>', style + '  </style>')
data = json.dumps(json.loads((root / 'database' / 'course_catalog.json').read_text(encoding='utf-8')), ensure_ascii=False).replace('</', '<\\/')
start = '<!-- resource data start -->'
end = '<!-- resource data end -->'
block = start + '\n  <script>globalThis.RemiResources = ' + data + ';</script>\n  ' + end
if start in html:
    first = html.index(start)
    last = html.index(end, first) + len(end)
    html = html[:first] + block + html[last:]
else:
    html = html.replace('  <script>\nglobalThis.RemiDemoDisciplines', '  ' + block + '\n  <script>\nglobalThis.RemiDemoDisciplines')
code = '''  const resources = document.querySelector('#resource-list');
  resources.replaceChildren();
  for (const resource of globalThis.RemiResources.filter(item => item.discipline === discipline.name)) {
    const item = document.createElement('article');
    item.className = 'resource-card';
    const title = document.createElement(resource.link_status === 'unconfirmed' ? 'strong' : 'a');
    title.textContent = resource.title;
    if (resource.link_status !== 'unconfirmed' && /^https:\\/\\//.test(resource.url)) {
      title.href = resource.url;
      title.target = '_blank';
      title.rel = 'noopener noreferrer';
    }
    const meta = document.createElement('p');
    meta.textContent = `${resource.kind} · ${resource.provider}${resource.link_status === 'unconfirmed' ? ' · ссылка проверяется' : resource.link_status === 'title_only' ? ' · условия доступа уточняются' : ''}`;
    const description = document.createElement('p');
    description.textContent = resource.description;
    item.append(title, meta, description);
    resources.append(item);
  }
'''
if "const resources = document.querySelector('#resource-list');" not in html:
    html = html.replace("  topicsList.replaceChildren();\n  topicsMessage.textContent", "  topicsList.replaceChildren();\n" + code + "  topicsMessage.textContent")
page.write_text(html, encoding='utf-8')
