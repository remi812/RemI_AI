const list = document.querySelector('#discipline-list');
const message = document.querySelector('#message');
const count = document.querySelector('#count');
const topicsSection = document.querySelector('#topics-section');
const topicsTitle = document.querySelector('#topics-title');
const topicsMessage = document.querySelector('#topics-message');
const topicsList = document.querySelector('#topics-list');
const patterns = ['∑', '∫', '{ }', '◈', '⌁'];
const pilotTopics = {
  'Высшая математика': {'Производные':'derivatives'},
  'Основы программирования': {'Циклы':'programming', 'Переменные':'programming-variables', 'Типы данных':'programming-types', 'Условия':'programming-conditions'},
  'Моделирование систем': {'Математические модели':'modeling'},
  'Теория автоматического управления': {'Обратная связь':'control', 'Понятие системы управления':'control-system', 'Сигналы и элементы системы':'control-signals'},
};
const topicMapView = document.querySelector('#topic-map-view');
const topicPreview = document.querySelector('#topic-preview');
const previewGraph = document.querySelector('#topic-preview-graph');
let previewRequest = 0;
let topicsRequest = 0;
let selectedDiscipline = null;
let demoState = null;
const demoSection = document.querySelector('#demo-section');
const demoForm = document.querySelector('#demo-form');
const demoOptions = document.querySelector('#demo-options');
const checkAnswer = document.querySelector('#check-answer');
const nextQuestion = document.querySelector('#next-question');

function topicWord(number) {
  const last = number % 10;
  const lastTwo = number % 100;
  if (last === 1 && lastTwo !== 11) return 'тема';
  if (last >= 2 && last <= 4 && (lastTwo < 12 || lastTwo > 14)) return 'темы';
  return 'тем';
}

async function getJson(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error('Ошибка загрузки');
  return response.json();
}

async function showTopics(discipline, button) {
  const request = ++topicsRequest;
  selectedDiscipline = discipline;
  demoState = null;
  demoSection.hidden = true;
  document.querySelector('#start-demo').disabled = !RemiDemoQuestions[discipline.name];
  document.querySelector('#demo-availability').textContent = RemiDemoQuestions[discipline.name]
    ? 'Посмотри, как может выглядеть тест по этой дисциплине.'
    : 'Для этой дисциплины пример пока не подготовлен.';
  document.querySelectorAll('.discipline-card').forEach(card => {
    card.classList.remove('selected');
    card.setAttribute('aria-pressed', 'false');
  });
  button.classList.add('selected');
  button.setAttribute('aria-pressed', 'true');
  topicsSection.hidden = false;
  previewRequest++;
  topicMapView.hidden = false;
  topicPreview.hidden = true;
  topicsTitle.textContent = discipline.name;
  topicsList.replaceChildren();
  const resources = document.querySelector('#resource-list');
  resources.textContent = 'Загружаем материалы…';
  getJson(`/api/disciplines/${discipline.discipline_id}/resources`).then(result => {
    if (request !== topicsRequest) return;
    resources.replaceChildren();
    for (const resource of result.resources) {
      const item = document.createElement('article');
      item.className = 'resource-card';
      const title = document.createElement(resource.link_status === 'unconfirmed' ? 'strong' : 'a');
      title.textContent = resource.title;
      if (resource.link_status !== 'unconfirmed' && /^https:\/\//.test(resource.url)) {
        title.href = resource.url;
        title.target = '_blank';
        title.rel = 'noopener noreferrer';
      }
      const meta = document.createElement('p');
      meta.textContent = `${resource.kind} · ${resource.provider}${resource.link_status === 'unconfirmed' ? ' · ссылка проверяется' : resource.link_status === 'title_only' ? ' · условия доступа уточняются' : ''}`;
      const description = document.createElement('p');
      description.textContent = resource.description || '';
      item.append(title, meta, description);
      resources.append(item);
    }
    if (!result.resources.length) resources.textContent = 'Материалы пока не добавлены.';
  }).catch(() => { if (request === topicsRequest) resources.textContent = 'Не удалось загрузить материалы.'; });
  topicsMessage.textContent = 'Загружаем темы…';
  try {
    const result = await getJson(`/api/disciplines/${discipline.discipline_id}/topics`);
    if (request !== topicsRequest) return;
    topicsMessage.textContent = result.topics.length ? '' : 'Темы для этой дисциплины пока не добавлены.';
    drawTopicsMap(result.topics, discipline);

  } catch {
    if (request !== topicsRequest) return;
    topicsMessage.textContent = 'Не получилось загрузить темы. Попробуй ещё раз.';
  }
  topicsSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function drawTopicsMap(topics, discipline) {
  topicsList.replaceChildren();
  if (!topics.length) return;
  const columns = Math.min(4, topics.length);
  const rows = Math.ceil(topics.length / columns);
  const width = Math.max(660, columns * 220);
  const height = rows * 126 + 155;
  topicsList.style.minWidth = `${width}px`;
  topicsList.style.height = `${height}px`;
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('viewBox', `0 0 1000 ${height}`);
  svg.setAttribute('preserveAspectRatio', 'none');
  svg.setAttribute('aria-hidden', 'true');
  const positions = topics.map((topic, index) => {
    const row = Math.floor(index / columns);
    const rowCount = Math.min(columns, topics.length - row * columns);
    return { x: ((index % columns) + .5) * 1000 / rowCount, y: 55 + row * 126 };
  });
  for (const point of positions) {
    const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    const bottom = height - 55, middle = (point.y + bottom) / 2;
    path.setAttribute('d', `M ${point.x} ${point.y} C ${point.x} ${middle}, 500 ${middle}, 500 ${bottom}`);
    svg.append(path);
  }
  topicsList.append(svg);
  topics.forEach((topic, index) => {
    const slug = pilotTopics[discipline.name]?.[topic.name];
    const button = document.createElement('button');
    button.type = 'button';
    button.className = `topic-map-node ${slug ? 'available' : 'pending'}`;
    button.style.left = `${positions[index].x / 10}%`;
    button.style.top = `${positions[index].y}px`;
    const title = document.createElement('strong'); title.textContent = topic.name;
    const note = document.createElement('small'); note.textContent = slug ? 'Открыть карту ↗' : 'Маршрут готовится';
    button.append(title, note);
    button.addEventListener('click', () => openTopic(topic, slug, button, discipline));
    topicsList.append(button);
  });
  const root = document.createElement('div'); root.className = 'topic-map-root';
  root.style.top = `${height - 55}px`;
  const rootLabel = document.createElement('small'); rootLabel.textContent = 'ДИСЦИПЛИНА';
  const rootName = document.createElement('strong'); rootName.textContent = discipline.name;
  root.append(rootLabel, rootName); topicsList.append(root);
}

async function openTopic(topic, slug, button, discipline) {
  const request = ++previewRequest;
  const rect = topicsList.getBoundingClientRect(), target = button.getBoundingClientRect();
  const reduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (!reduced && topicsList.animate) {
    topicsList.style.transformOrigin = `${target.left + target.width / 2 - rect.left}px ${target.top + target.height / 2 - rect.top}px`;
    const animation = topicsList.animate([{transform:'scale(1)', opacity:1}, {transform:'scale(1.6)', opacity:0}], {duration:380, easing:'ease-in', fill:'forwards'});
    try { await animation.finished; } catch {}
    animation.cancel();
  }
  if (request !== previewRequest || selectedDiscipline !== discipline) return;
  topicMapView.hidden = true;
  topicPreview.hidden = false;
  document.querySelector('#topic-preview-title').textContent = topic.name;
  const message = document.querySelector('#topic-preview-message');
  const testLink = document.querySelector('#topic-test-link');
  const scroll = document.querySelector('#topic-preview-scroll');
  const back = document.querySelector('#preview-back');
  back.hidden = true; scroll.hidden = true; testLink.hidden = true;
  previewGraph.replaceChildren();
  if (!slug) {
    message.textContent = 'Карту и тест для этой темы ещё готовим.';
  } else {
    message.textContent = 'Загружаем карту темы…';
    const adaptive = slug !== 'modeling';
    testLink.href = adaptive ? `/learn/${slug}` : `/pilot/derivatives?pilot=${encodeURIComponent(slug)}`;
    testLink.textContent = `Пройти начальный тест: ${topic.name} →`;
    try {
      const pilot = await getJson(adaptive ? `/api/learn/${slug}/preview` : `/api/pilot/${encodeURIComponent(slug)}`);
      if (request !== previewRequest) return;
      const goal = pilot.nodes.find(node => node.name === pilot.goal);
      if (!goal) throw new Error('Цель не найдена');
      const history = [];
      function show(node) {
        renderPreview(pilot, node, selected => { history.push(node); show(selected); });
        document.querySelector('#topic-preview-title').textContent = node.name;
        back.hidden = !history.length;
        message.textContent = 'Это предварительная карта основ. Нажми на узел, чтобы приблизиться ещё глубже.';
      }
      back.onclick = () => { const previous = history.pop(); if (previous) show(previous); };
      show(goal);
      scroll.hidden = false; testLink.hidden = slug === 'modeling';
      if (slug === 'modeling') message.textContent = 'Обзорная карта моделирования. Выберите узел, чтобы изучить связи.';
    } catch {
      if (request !== previewRequest) return;
      message.textContent = 'Не удалось загрузить карту темы. Попробуй открыть её позже.';
    }
  }
  topicPreview.classList.remove('topic-reveal');
  void topicPreview.offsetWidth;
  topicPreview.classList.add('topic-reveal');
  topicPreview.focus({preventScroll:true});
  topicPreview.scrollIntoView({behavior: reduced ? 'auto' : 'smooth', block:'nearest'});
}

function renderPreview(pilot, goal, selectNode) {
  const layout = RemiMapLayout.layout(pilot.nodes, pilot.edges, goal.competency_id, 132, 55);
  previewGraph.style.height = `${layout.height}px`; previewGraph.style.minWidth = `${layout.width}px`;
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('viewBox', `0 0 1000 ${layout.height}`); svg.setAttribute('preserveAspectRatio', 'none'); svg.setAttribute('aria-hidden', 'true');
  for (const edge of layout.edges) {
    const a = layout.points.get(edge.prerequisite_id), b = layout.points.get(edge.competency_id), middle = (a.y + b.y) / 2;
    const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    path.setAttribute('d', `M ${a.x} ${a.y} C ${a.x} ${middle}, ${b.x} ${middle}, ${b.x} ${b.y}`); svg.append(path);
  }
  previewGraph.replaceChildren(svg);
  for (const node of layout.nodes) {
    const button = document.createElement('button'); button.type = 'button';
    const isGoal = node.competency_id === goal.competency_id;
    button.className = `preview-node${isGoal ? ' preview-goal' : ''}`;
    const coords = layout.points.get(node.competency_id); button.style.left = `${coords.x / 10}%`; button.style.top = `${coords.y}px`;
    button.textContent = node.name;
    if (isGoal) { button.setAttribute('aria-label', `${node.name} — текущая цель`); }
    else button.addEventListener('click', async () => {
      const reduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      if (!reduced && previewGraph.animate) {
        const rect = previewGraph.getBoundingClientRect(), target = button.getBoundingClientRect();
        previewGraph.style.transformOrigin = `${target.left + target.width / 2 - rect.left}px ${target.top + target.height / 2 - rect.top}px`;
        const animation = previewGraph.animate([{transform:'scale(1)', opacity:1}, {transform:'scale(1.6)', opacity:0}], {duration:350, easing:'ease-in', fill:'forwards'});
        try { await animation.finished; } catch {} animation.cancel();
      }
      if (!topicPreview.hidden) selectNode(node);
    });
    previewGraph.append(button);
  }
}

document.querySelector('#topic-back').addEventListener('click', () => {
  previewRequest++; topicPreview.hidden = true; topicMapView.hidden = false;
});

function renderDiscipline(discipline, index) {
  const card = document.createElement('button');
  card.className = `discipline-card color-${index % patterns.length}`;
  card.type = 'button';
  card.setAttribute('aria-pressed', 'false');

  const top = document.createElement('span');
  top.className = 'card-top';
  const symbol = document.createElement('span');
  symbol.className = 'card-symbol';
  symbol.textContent = patterns[index % patterns.length];
  symbol.setAttribute('aria-hidden', 'true');
  const arrow = document.createElement('span');
  arrow.className = 'card-arrow';
  arrow.textContent = '↗';
  arrow.setAttribute('aria-hidden', 'true');
  top.append(symbol, arrow);

  const title = document.createElement('span');
  title.className = 'card-title';
  title.textContent = discipline.name;
  const description = document.createElement('span');
  description.className = 'card-description';
  description.textContent = discipline.description || 'Изучи основные темы и понятия.';
  const bottom = document.createElement('span');
  bottom.className = 'card-bottom';
  bottom.textContent = `${discipline.topic_count} ${topicWord(discipline.topic_count)}`;

  card.append(top, title, description, bottom);
  card.addEventListener('click', () => showTopics(discipline, card));
  return card;
}

async function loadDisciplines() {
  try {
    const result = await getJson('/api/disciplines');
    list.replaceChildren(...result.disciplines.map(renderDiscipline));
    message.textContent = result.disciplines.length ? '' : 'Дисциплины пока не добавлены.';
    message.hidden = result.disciplines.length > 0;
    count.textContent = `${result.disciplines.length} В КАТАЛОГЕ`;
  } catch {
    message.textContent = 'Не удалось загрузить дисциплины. Убедись, что база данных доступна, и обнови страницу.';
    message.classList.add('error');
    count.textContent = 'НЕТ СОЕДИНЕНИЯ';
  }
}

document.querySelector('#close-topics').addEventListener('click', () => {
  topicsRequest++;
  previewRequest++;
  selectedDiscipline = null;
  demoState = null;
  demoSection.hidden = true;
  topicsSection.hidden = true;
  document.querySelectorAll('.discipline-card').forEach(card => {
    card.classList.remove('selected');
    card.setAttribute('aria-pressed', 'false');
  });
});

function renderDemo() {
  const finished = document.querySelector('#demo-finished');
  const progress = document.querySelector('#demo-progress');
  demoForm.hidden = demoState.finished;
  finished.hidden = !demoState.finished;
  if (demoState.finished) {
    progress.textContent = '';
    return;
  }
  const question = demoState.questions[demoState.index];
  progress.textContent = `ВОПРОС ${demoState.index + 1} ИЗ ${demoState.questions.length}`;
  document.querySelector('#demo-question').textContent = question.question;
  demoOptions.replaceChildren();
  for (const [index, text] of question.options.entries()) {
    const label = document.createElement('label');
    label.className = 'demo-option';
    const input = document.createElement('input');
    input.type = 'radio';
    input.name = 'demo-answer';
    input.value = String(index);
    input.disabled = demoState.checked;
    input.checked = demoState.chosen === index;
    input.addEventListener('change', () => { checkAnswer.disabled = false; });
    const caption = document.createElement('span');
    caption.textContent = text;
    label.append(input, caption);
    demoOptions.append(label);
  }
  const feedback = document.querySelector('#demo-feedback');
  feedback.hidden = !demoState.checked;
  if (demoState.checked) {
    const isCorrect = demoState.chosen === question.answer;
    feedback.textContent = isCorrect ? 'Верно.' : 'Неверно.';
    feedback.classList.toggle('incorrect', !isCorrect);
  }
  checkAnswer.hidden = demoState.checked;
  checkAnswer.disabled = true;
  nextQuestion.hidden = !demoState.checked;
  nextQuestion.textContent = demoState.index + 1 === demoState.questions.length ? 'Завершить пример' : 'Следующий вопрос →';
}

function startDemo() {
  const questions = selectedDiscipline && RemiDemoQuestions[selectedDiscipline.name];
  if (!questions) return;
  demoState = RemiDemoEngine.start(questions);
  document.querySelector('#demo-discipline').textContent = selectedDiscipline.name;
  demoSection.hidden = false;
  renderDemo();
  demoSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
  demoSection.focus({ preventScroll: true });
}

document.querySelector('#start-demo').addEventListener('click', startDemo);
document.querySelector('#restart-demo').addEventListener('click', startDemo);
document.querySelector('#close-demo').addEventListener('click', () => {
  demoSection.hidden = true;
  demoState = null;
  document.querySelector('#start-demo').focus();
});
demoForm.addEventListener('submit', event => {
  event.preventDefault();
  const chosen = demoForm.querySelector('input[name="demo-answer"]:checked');
  if (!chosen || !demoState || demoState.checked) return;
  demoState = RemiDemoEngine.answer(demoState, Number(chosen.value));
  renderDemo();
  document.querySelector('#demo-feedback').focus();
});
nextQuestion.addEventListener('click', () => {
  if (!demoState || !demoState.checked) return;
  demoState = RemiDemoEngine.next(demoState);
  renderDemo();
  if (demoState.finished) document.querySelector('#restart-demo').focus();
  else document.querySelector('#demo-question').focus();
});

loadDisciplines();
