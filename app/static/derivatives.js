const message = document.querySelector('#pilot-message');
const quiz = document.querySelector('#quiz');
const form = document.querySelector('#quiz-form');
const questionList = document.querySelector('#questions');
const mapSection = document.querySelector('#map-section');
let pilot;
const pilotSlug = new URLSearchParams(window.location.search).get('pilot') || 'derivatives';
const pilotBase = `/api/pilot/${encodeURIComponent(pilotSlug)}`;
let mapResults = null;
let selectedNode = null;
let mapPath = [];
let transitioning = false;
let retakeQuestions = [];
const storageMessage = document.querySelector('#storage-message');
const savedMapLink = document.querySelector('#saved-map-link');

function storage() {
  try { return window.localStorage; } catch { return null; }
}

function saveProgress() {
  const saved = RemiPilotProgress.save(storage(), pilot, mapResults);
  storageMessage.textContent = saved
    ? 'Карта сохранена в этом браузере. На другом устройстве её не будет.'
    : 'Не удалось сохранить карту в браузере. Она доступна до закрытия страницы.';
  savedMapLink.hidden = !saved;
  return saved;
}

async function readJson(url, options) {
  const response = await fetch(url, options);
  const body = await response.json();
  if (!response.ok) throw new Error(body.detail || 'Не удалось выполнить запрос.');
  return body;
}

function showQuestions() {
  questionList.replaceChildren();
  for (const [index, question] of pilot.questions.entries()) {
    const group = document.createElement('fieldset');
    group.className = 'pilot-question';
    const title = document.createElement('legend');
    title.textContent = `${index + 1}. ${question.text}`;
    group.append(title);
    for (const [optionIndex, option] of question.options.entries()) {
      const label = document.createElement('label');
      const input = document.createElement('input');
      input.type = 'radio';
      input.name = `question-${index}`;
      input.value = String(optionIndex);
      const text = document.createElement('span');
      text.textContent = option;
      label.append(input, text);
      group.append(label);
    }
    const feedback = document.createElement('p');
    feedback.className = 'answer-feedback';
    feedback.hidden = true;
    group.append(feedback);
    questionList.append(group);
  }
}

function showDetail(node, outcome = null) {
  selectedNode = node;
  retakeQuestions = [];
  document.querySelector('#retake-form').hidden = true;
  document.querySelector('#retake-questions').replaceChildren();
  document.querySelector('#retake-error').textContent = '';
  document.querySelector('#retake-message').textContent = outcome || '';
  document.querySelector('#retake-start').hidden = false;
  const detail = document.querySelector('#detail');
  document.querySelector('.map-overflow').hidden = true;
  document.querySelector('#study-next').hidden = true;
  detail.classList.remove('depth-enter');
  document.querySelector('#detail-title').textContent = node.name;
  document.querySelector('#detail-description').textContent = node.description || node.topic;
  const inner = document.querySelector('#inner-map');
  renderGraph(inner, node, mapResults);
  document.querySelector('#inner-map-note').textContent =
    pilot.edges.some(edge => edge.competency_id === node.competency_id)
      ? 'Основы этой темы расположены выше. Нажми на любую, чтобы открыть её карту.'
      : 'Для этой темы более глубокие связи пока не добавлены.';
  document.querySelector('#back-to-map').textContent = mapPath.length
    ? '← Назад к предыдущей теме' : '← К общей карте';
  const container = document.querySelector('#detail-resources');
  container.replaceChildren();
  const resources = pilot.resources.filter(item => item.competency_id === node.competency_id);
  for (const resource of resources) {
    const card = document.createElement('article');
    card.className = 'resource-card';
    const link = document.createElement('a');
    link.textContent = resource.title;
    link.href = resource.url;
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    const note = document.createElement('p');
    note.textContent = `${resource.provider || 'Источник'} · ${resource.review_status === 'approved' ? 'одобрен' : 'ожидает проверки преподавателем'}${resource.check_note ? ` · ${resource.check_note}` : ''}`;
    card.append(link, note);
    container.append(card);
  }
  if (!resources.length) container.textContent = 'Связанных материалов пока нет.';
  detail.hidden = false;
  detail.classList.add('depth-enter');
  detail.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// Each level uses the same tree: prerequisites above, the selected goal below.
function renderGraph(graph, goal, results) {
  graph.replaceChildren();
  const layout = RemiMapLayout.layout(pilot.nodes, pilot.edges, goal.competency_id);
  graph.style.height = `${layout.height}px`;
  graph.style.minWidth = `${layout.width}px`;
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('viewBox', `0 0 1000 ${layout.height}`);
  svg.setAttribute('preserveAspectRatio', 'none');
  svg.setAttribute('aria-hidden', 'true');
  for (const edge of layout.edges) {
    const from = layout.points.get(edge.prerequisite_id), to = layout.points.get(edge.competency_id);
    const line = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    const middle = (from.y + to.y) / 2;
    line.setAttribute('d', `M ${from.x} ${from.y} C ${from.x} ${middle}, ${to.x} ${middle}, ${to.x} ${to.y}`);
    svg.append(line);
  }
  graph.append(svg);
  const labels = {preliminary_correct:'Предварительно верно', needs_review:'Требует уточнения', not_assessed:'Не проверено'};
  for (const node of layout.nodes) {
    const point = layout.points.get(node.competency_id);
    const result = results[node.name] || {status:'not_assessed', correct:0, total:0};
    const button = document.createElement('button');
    button.type = 'button';
    button.className = `graph-node ${result.status}${node.competency_id === goal.competency_id ? ' goal' : ''}`;
    button.style.left = `${point.x / 10}%`;
    button.style.top = `${point.y}px`;
    const name = document.createElement('strong'); name.textContent = node.name;
    const status = document.createElement('small');
    status.textContent = `${labels[result.status]}${result.total ? ` · ${result.correct} из ${result.total}` : ''}`;
    button.append(name, status);
    button.addEventListener('click', () => enterNode(node, button, graph));
    graph.append(button);
  }
}

async function enterNode(node, button, graph) {
  if (transitioning || (selectedNode && selectedNode.competency_id === node.competency_id)) return;
  transitioning = true;
  const previous = selectedNode;
  const rect = graph.getBoundingClientRect();
  const target = button.getBoundingClientRect();
  const reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (!reduceMotion && graph.animate) {
    const animation = graph.animate([
      {transform: 'scale(1)', opacity: 1},
      {transform: 'scale(1.65)', opacity: 0}
    ], {duration: 330, easing: 'ease-in', fill: 'forwards'});
    graph.style.transformOrigin = `${target.left + target.width / 2 - rect.left}px ${target.top + target.height / 2 - rect.top}px`;
    try { await animation.finished; } catch { /* Navigation can cancel the animation. */ }
    animation.cancel();
  }
  if (!mapResults || mapSection.hidden || selectedNode !== previous) { transitioning = false; return; }
  if (previous) mapPath.push(previous);
  showDetail(node);
  transitioning = false;
}

function drawStudySuggestions(results) {
  const container = document.querySelector('#study-suggestions');
  container.replaceChildren();
  const review = pilot.nodes.filter(node => results[node.name]?.status === 'needs_review');
  const unknown = pilot.nodes.filter(node => results[node.name]?.status === 'not_assessed');
  const complete = pilot.nodes.filter(node => results[node.name]?.status === 'preliminary_correct');
  document.querySelector('#study-summary').textContent =
    `Предварительно верно: ${complete.length} · требует уточнения: ${review.length} · не проверено: ${unknown.length}.`;
  // Put foundational nodes first: a suggestion never assumes mastery of prerequisites.
  const depth = new Map();
  function level(id, seen = new Set()) {
    if (depth.has(id)) return depth.get(id);
    if (seen.has(id)) return 0;
    const next = new Set(seen); next.add(id);
    const parents = pilot.edges.filter(edge => edge.competency_id === id);
    const result = parents.length ? 1 + Math.max(...parents.map(edge => level(edge.prerequisite_id, next))) : 0;
    depth.set(id, result); return result;
  }
  const candidates = [...review, ...unknown].sort((a,b) => level(a.competency_id) - level(b.competency_id));
  if (!candidates.length) {
    const note = document.createElement('p');
    note.textContent = 'Все навыки предварительно проверены. Можно открыть любую тему, изучить материалы и проверить себя ещё раз.';
    container.append(note);
    return;
  }
  const intro = document.createElement('p');
  intro.textContent = 'Начни с основ: открой тему, изучи материалы и затем проверь себя.';
  container.append(intro);
  for (const node of candidates.slice(0, 3)) {
    const button = document.createElement('button'); button.type = 'button';
    button.className = 'suggestion-button';
    const title = document.createElement('strong'); title.textContent = node.name;
    const state = document.createElement('span');
    state.textContent = results[node.name].status === 'needs_review' ? 'Требует уточнения →' : 'Пока не проверено →';
    button.append(title, state);
    button.addEventListener('click', () => { mapPath = []; showDetail(node); });
    container.append(button);
  }
}

function drawGraph(results) {
  const goal = pilot.nodes.find(node => node.name === pilot.goal);
  if (!goal) throw new Error('Цель карты не найдена. Нужна проверка данных.');
  document.querySelector('#detail').hidden = true;
  document.querySelector('.map-overflow').hidden = false;
  document.querySelector('#study-next').hidden = false;
  drawStudySuggestions(results);
  selectedNode = null;
  mapPath = [];
  renderGraph(document.querySelector('#graph'), goal, results);
}

document.querySelector('#back-to-map').addEventListener('click', () => {
  if (transitioning) return;
  if (mapPath.length) {
    const parent = mapPath.pop();
    showDetail(parent);
  } else {
    selectedNode = null;
    document.querySelector('#detail').hidden = true;
    document.querySelector('.map-overflow').hidden = false;
    document.querySelector('#study-next').hidden = false;
    mapSection.focus({preventScroll:true});
  }
});

form.addEventListener('submit', async event => {
  event.preventDefault();
  const error = document.querySelector('#quiz-error');
  const answers = {};
  for (const [index, question] of pilot.questions.entries()) {
    const selected = form.querySelector(`input[name="question-${index}"]:checked`);
    if (!selected) { error.textContent = 'Ответь на все вопросы, чтобы открыть карту.'; return; }
    answers[question.id] = Number(selected.value);
  }
  try {
    error.textContent = '';
    const result = await readJson(`${pilotBase}/check`, {
      method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({answers})
    });
    for (const [index, question] of pilot.questions.entries()) {
      const feedback = questionList.children[index].querySelector('.answer-feedback');
      feedback.textContent = result.feedback[question.id] ? 'Верно.' : 'Неверно.';
      feedback.hidden = false;
    }
    mapResults = result.results;
    drawGraph(mapResults);
    saveProgress();
    mapSection.hidden = false;
    mapSection.scrollIntoView({behavior:'smooth', block:'start'});
    mapSection.focus({preventScroll:true});
  } catch (failure) { error.textContent = failure.message; }
});

form.addEventListener('change', () => {
  if (!mapSection.hidden) {
    mapSection.hidden = true;
    selectedNode = null;
    mapResults = null;
    savedMapLink.hidden = true;
    storageMessage.textContent = 'Новый тест ещё не завершён; предыдущий сохранённый результат пока остаётся в браузере.';
    for (const feedback of questionList.querySelectorAll('.answer-feedback')) feedback.hidden = true;
  }
});

document.querySelector('#restart').addEventListener('click', () => {
  form.reset();
  selectedNode = null;
  mapResults = null;
  for (const feedback of questionList.querySelectorAll('.answer-feedback')) feedback.hidden = true;
  mapSection.hidden = true;
  savedMapLink.hidden = true;
  storageMessage.textContent = 'Предыдущий результат останется в браузере, пока ты не завершишь новый тест или не удалишь его.';
  quiz.scrollIntoView({behavior:'smooth', block:'start'});
});

document.querySelector('#retake-start').addEventListener('click', async () => {
  const node = selectedNode;
  if (!node || !mapResults) return;
  const message = document.querySelector('#retake-message');
  message.textContent = 'Загружаем вопросы…';
  try {
    const data = await readJson(`${pilotBase}/retake/${node.competency_id}`);
    if (selectedNode !== node || mapSection.hidden) return;
    retakeQuestions = data.questions;
    const container = document.querySelector('#retake-questions');
    container.replaceChildren();
    for (const [index, question] of retakeQuestions.entries()) {
      const group = document.createElement('fieldset');
      group.className = 'pilot-question';
      const title = document.createElement('legend');
      title.textContent = `${index + 1}. ${question.text}`;
      group.append(title);
      for (const [optionIndex, option] of question.options.entries()) {
        const label = document.createElement('label');
        const input = document.createElement('input');
        input.type = 'radio'; input.name = `retake-${index}`; input.value = String(optionIndex);
        const text = document.createElement('span'); text.textContent = option;
        label.append(input, text); group.append(label);
      }
      container.append(group);
    }
    document.querySelector('#retake-form').hidden = false;
    document.querySelector('#retake-start').hidden = true;
    message.textContent = 'Ответь на новые учебные вопросы. Результат сохранится только в этом браузере.';
  } catch (error) { if (selectedNode === node) message.textContent = error.message; }
});

document.querySelector('#retake-form').addEventListener('submit', async event => {
  event.preventDefault();
  const node = selectedNode;
  const activeResults = mapResults;
  if (!node || !activeResults || !retakeQuestions.length) return;
  const answers = {};
  const error = document.querySelector('#retake-error');
  for (const [index, question] of retakeQuestions.entries()) {
    const selected = event.currentTarget.querySelector(`input[name="retake-${index}"]:checked`);
    if (!selected) { error.textContent = 'Ответь на оба вопроса.'; return; }
    answers[question.id] = Number(selected.value);
  }
  const submit = document.querySelector('#retake-submit');
  submit.disabled = true;
  try {
    error.textContent = '';
    const response = await readJson(`${pilotBase}/retake`, {
      method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({competency_id:node.competency_id, answers})
    });
    if (selectedNode !== node || mapResults !== activeResults || mapSection.hidden) return;
    const result = response.results[node.name];
    const previous = activeResults[node.name];
    mapResults = {...mapResults, [node.name]:result};
    const previousPath = mapPath.slice();
    drawGraph(mapResults);
    mapPath = previousPath;
    const saved = saveProgress();
    const labels = retakeQuestions.map((question, index) => `${index + 1}: ${response.feedback[question.id] ? 'верно' : 'неверно'}`).join(' · ');
    const comparison = previous && previous.total ? `Было: ${previous.correct} из ${previous.total}. ` : '';
    const next = result.status === 'preliminary_correct' ? 'Оба ответа верны; это предварительный результат.' : 'Посмотри материалы ещё раз и повтори проверку.';
    showDetail(node, `${comparison}Теперь: ${result.correct} из ${result.total}. ${labels}. ${next} ${saved ? 'Карта сохранена в этом браузере.' : 'Карта обновлена, но сохранить её не удалось.'}`);
  } catch (failure) { if (selectedNode === node) error.textContent = failure.message; }
  finally { submit.disabled = false; }
});

document.querySelector('#clear-progress').addEventListener('click', () => {
  const cleared = RemiPilotProgress.clear(storage(), pilot);
  if (!cleared) {
    storageMessage.textContent = 'Не удалось удалить сохранённый результат из браузера.';
    return;
  }
  mapResults = null;
  selectedNode = null;
  mapSection.hidden = true;
  savedMapLink.hidden = true;
  form.reset();
  for (const feedback of questionList.querySelectorAll('.answer-feedback')) feedback.hidden = true;
  storageMessage.textContent = 'Сохранённый результат удалён. Можно пройти тест заново.';
  quiz.scrollIntoView({behavior:'smooth', block:'start'});
});

readJson(pilotBase).then(data => {
  pilot = data;
  pilot.slug = data.slug || pilotSlug;
  document.querySelector('#pilot-breadcrumb').textContent = `${pilot.discipline || 'Высшая математика'} / ${pilot.topic || 'Производные'}`;
  document.querySelector('#pilot-title').textContent = `Путь к цели: ${pilot.topic || 'Производные'}`;
  document.title = `${pilot.topic || 'Производные'} — RemI AI`;
  if (!pilot.questions.length) throw new Error('Для этой карты пока нет учебных вопросов.');
  showQuestions();
  message.textContent = '';
  message.hidden = true;
  quiz.hidden = false;
  const saved = RemiPilotProgress.load(storage(), pilot);
  if (saved) {
    drawGraph(saved.results);
    mapResults = saved.results;
    mapSection.hidden = false;
    savedMapLink.hidden = false;
    storageMessage.textContent = 'Восстановлена карта, сохранённая в этом браузере.';
  }
}).catch(error => { message.textContent = error.message; });
