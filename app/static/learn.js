'use strict';
const $ = id => document.getElementById(id);
const slug = location.pathname.startsWith('/learn/') ? location.pathname.split('/').pop()
  : new URLSearchParams(location.search).get('pilot') || 'derivatives';
const api = '/api/learn/' + encodeURIComponent(slug);
const reasons = {sufficient:'Собрано достаточно ответов', exhausted:'Вы уже видели все доступные задания или для этого навыка ещё нет проверенных вопросов.',
  limit:'Достигнут лимит проверки', student:'Проверка завершена студентом'};
const labels = {mastered:'Предварительно освоено',possible_gap:'Вероятный пробел',needs_review:'Требует уточнения',not_assessed:'Не проверено'};
let pilot, account, progress, current, selected, path = [], reviews = [];
function element(tag, text) {
  const node = document.createElement(tag);
  node.textContent = text;
  return node;
}
async function request(url, body) {
  const response = await fetch(url, body === undefined ? {cache:'no-store'} :
    {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    const error = new Error(typeof data.detail === 'string' ? data.detail : 'Проверьте введённые данные.');
    error.status = response.status;
    throw error;
  }
  return response.json();
}
function action(fn) {
  return async event => {
    event?.preventDefault();
    const target = event?.submitter || event?.currentTarget;
    if (target) target.disabled = true;
    $('error').textContent = '';
    try { await fn(event); }
    catch (error) { $('error').textContent = error.message; $('error').focus(); }
    finally { if (target) target.disabled = false; }
  };
}
const nodeById = id => pilot.nodes.find(n => n.competency_id === id);
const goal = () => pilot.nodes.find(n => n.name === pilot.goal);
function notice(text) { $('notice').textContent = text; $('notice').hidden = !text; }
function map(node) {
  const states = {};
  for (const n of pilot.nodes) {
    const result = progress?.results[n.competency_id];
    if (result) states[n.name] = {...result,status:result.knowledge_status};
  }
  drawSkillMap($('graph'),pilot,node,states,actionNode);
}
async function actionNode(node,button,graph) {
  if (selected?.competency_id === node.competency_id) return;
  if (!matchMedia('(prefers-reduced-motion: reduce)').matches && graph.animate) {
    const rect = graph.getBoundingClientRect(), point = button.getBoundingClientRect();
    graph.style.transformOrigin = (point.left-rect.left+point.width/2)+'px '+(point.top-rect.top)+'px';
    await graph.animate([{transform:'scale(1)'},{transform:'scale(1.2)',opacity:0.3}],{duration:220}).finished;
  }
  await action(() => openNode(node))();
}
async function openNode(node, remember=true) {
  if (remember) path.push(selected);
  selected = node;
  $('next-box').hidden = true;
  map(node);
  $('back').hidden = false;
  $('detail').hidden = false;
  $('skill-title').textContent = node.name;
  $('skill-title').focus();
  $('skill-description').textContent = node.description;
  $('materials').replaceChildren();
  $('retake').hidden = true;
  $('mode').textContent = account ? 'Загружаем материалы…' : 'Войдите, чтобы получить рекомендации по своим ответам.';
  if (!account) return;
  try {
    const data = await request(api+'/skills/'+node.competency_id+'/materials');
    if (selected !== node) return;
    renderMaterials(data, $('materials'), $('mode'));
    const available = progress.availability;
    const studied = progress.history.some(s => !s.retake_skill && s.status !== 'in_progress');
    const fresh = available.remaining[node.competency_id].retake;
    $('retake').hidden = !available.available || !data.items.length || !studied || !fresh || !!current;
    if (studied && !fresh && available.available) $('mode').append(' Вы уже видели все повторные задания по этому навыку.');
  } catch {
    if (selected !== node) return;
    $('mode').textContent = 'Не удалось загрузить материалы.';
    const retry = element('button','Попробовать снова');
    retry.type = 'button'; retry.className = 'secondary-button';
    retry.onclick = action(() => openNode(node, false));
    $('materials').replaceChildren(retry);
  }
}
function renderMaterials(data, container, mode, limit = data.items.length) {
  mode.textContent = {semantic:'Подобрано по смыслу цели и навыка · MiniLM', links:'Подобрано по теме навыка. Смысловой поиск сейчас недоступен.',
    empty:'Подходящего одобренного материала для этого навыка пока нет.'}[data.mode];
  if (data.items.length === 1 && data.mode === 'semantic') mode.textContent = 'Единственный допущенный раздел по этому навыку.';
  container.replaceChildren();
  for (const item of data.items.slice(0, limit)) {
    const card = element('article',''); card.className = 'resource-card';
    const link = element('a',item.title); link.href = item.url; link.target = '_blank'; link.rel = 'noopener noreferrer';
    card.append(element('strong',item.course),link,element('p',item.access),element('p',item.reason)); container.append(card);
  }
}
function overview() {
  selected = null; path = [];
  $('back').hidden = $('detail').hidden = true;
  $('next-box').hidden = !progress?.history.some(s => s.status !== 'in_progress');
  map(goal());
}
$('back').onclick = action(async () => { const prior = path.pop(); if (prior) await openNode(prior,false); else { overview(); $('map-title').focus(); } });
$('next-skill').onclick = action(() => openNode(nodeById(progress.next)));
function showRetakeChange(history) {
  const finished = history.filter(s => s.status !== 'in_progress');
  const last = finished[0];
  $('change-box').hidden = !last?.retake_skill;
  if (!last?.retake_skill) return;
  const findSkill = session => session.estimates.find(e => e.competency_id === last.retake_skill);
  const after = findSkill(last);
  const before = finished.slice(1).map(findSkill).find(e => e?.total);
  const describe = e => labels[e.knowledge_status] + ' (' + e.correct + ' из ' + e.total + ')';
  $('change-skill').textContent = nodeById(last.retake_skill).name;
  if (after?.total) {
    $('change-result').textContent = (before ? describe(before) : 'Не проверено') + ' → ' + describe(after);
  } else {
    $('change-result').textContent = 'Новых ответов нет. ' + (before ? 'Сохранён результат: ' + describe(before) + '.' : 'Навык ещё не проверен.');
  }
}
async function showStudySteps(state) {
  const [first, ...later] = state.steps;
  $('step-list').replaceChildren();
  $('later-steps').hidden = later.length === 0;
  $('later-steps').open = false;
  for (const step of later) {
    const li = element('li','');
    const button = element('button',nodeById(step.skill).name + ' · ' + labels[step.status]);
    button.className = 'suggestion-button';
    button.onclick = action(() => openNode(nodeById(step.skill)));
    li.append(button); $('step-list').append(li);
  }
  $('step-heading').textContent = first ? 'Следующий шаг' : 'Маршрут пройден';
  $('next-text').textContent = first ? nodeById(first.skill).name : 'Ключевые навыки цели предварительно освоены.';
  $('next-skill').hidden = !first;
  $('step-path').hidden = !first || first.path.length < 2;
  $('step-path').textContent = first?.path.length > 1 ? 'Путь к цели: ' + first.path.map(id => nodeById(id).name).join(' → ') : '';
  $('step-mode').textContent = '';
  $('step-resources').replaceChildren();
  if (!first) return;
  $('step-mode').textContent = 'Подбираем раздел курса…';
  try {
    const data = await request(api+'/skills/'+first.skill+'/materials');
    if (progress === state) renderMaterials(data, $('step-resources'), $('step-mode'), 1);
  } catch (error) {
    if (progress === state) $('step-mode').textContent = 'Не удалось загрузить рекомендацию. Откройте подтему, чтобы попробовать ещё раз.';
  }
}
async function refresh() {
  progress = await request(api+'/progress');
  const history = progress.history;
  $('history-box').hidden = !history.length;
  $('history').replaceChildren();
  history.forEach(s => {
    const detail = element('details','');
    detail.append(element('summary',new Date(s.started_at).toLocaleString('ru-RU')+' · '+(s.skill || 'Начальная диагностика')+' · '+(reasons[s.stop_reason] || 'В процессе')));
    for (const e of s.estimates) detail.append(element('p',nodeById(e.competency_id).name+' · '+labels[e.knowledge_status]+' · '+e.correct+' из '+e.total));
    $('history').append(detail);
  });
  const completed = history.some(s => s.status !== 'in_progress');
  $('map-title').textContent = completed ? 'Твоя карта' : 'Предварительная карта';
  showRetakeChange(history);
  const active = history.find(s => s.status === 'in_progress');
  $('start').textContent = active ? 'Продолжить проверку' : completed ? 'Пройти новую диагностику' : 'Начать диагностику';
  const available = progress.availability;
  $('start').hidden = !active && (!available.available || !available.initial_remaining);
  if (!active && !available.available) notice('Доступен обзор карты. Диагностика ожидает допуска преподавателя.');
  else if (!active && !available.initial_remaining) notice('Вы уже видели все вступительные задания для этой цели.');
  overview();
  if (completed) await showStudySteps(progress);
}
function displayQuestion() {
  $('feedback').textContent = ''; $('continue').hidden = true; $('answer-form').hidden = false;
  const q = current.question;
  $('prompt').textContent = q.question_text; $('prompt').focus(); $('answers').replaceChildren();
  if (q.answer_type === 'choice') {
    for (const option of q.options_snapshot) {
      const label = element('label',''), input = document.createElement('input');
      input.type = 'radio'; input.name = 'value'; input.value = option; input.required = true;
      label.append(input,document.createTextNode(option)); $('answers').append(label);
    }
  } else {
    const input = document.createElement('input'); input.name = 'value'; input.required = true; input.maxLength = 256;
    input.setAttribute('aria-label',q.answer_type === 'numeric' ? 'Числовой ответ' : 'Короткий ответ');
    if (q.answer_type === 'numeric') input.inputMode = 'decimal';
    $('answers').append(input);
  }
}
async function continueSession() {
  if (current.done) {
    notice(reasons[current.reason]); current = null; $('quiz').hidden = true;
    $('map-section').hidden = $('actions').hidden = false;
    await refresh(); $('map-title').focus();
  } else { displayQuestion(); }
}
async function begin(skill) {
  current = await request(api+'/start',{skill});
  notice(''); $('quiz').hidden = false; $('actions').hidden = $('map-section').hidden = $('history-box').hidden = true;
  $('quiz-title').textContent = skill ? 'Проверка после изучения' : 'Начальная диагностика';
  $('stop').hidden = false;
  await continueSession();
}
$('start').onclick = action(() => begin(progress.history.find(s => s.status === 'in_progress')?.retake_skill || null));
$('retake').onclick = action(() => begin(selected.competency_id));
$('stop').onclick = action(async () => {current = await request('/api/learn/sessions/'+current.session_id+'/stop',{}); await continueSession();});
$('continue').onclick = action(continueSession);
$('answer-form').onsubmit = action(async () => {
  const value = new FormData($('answer-form')).get('value');
  try {
    const result = await request('/api/learn/sessions/'+current.session_id+'/answer',{version:current.question.question_version_id,value});
    current = result; $('feedback').textContent = result.correct ? 'Верно' : 'Неверно';
    $('answer-form').hidden = true; $('feedback').focus(); $('continue').hidden = false; $('stop').hidden = result.done;
    $('continue').textContent = result.done ? 'Открыть карту →' : 'Следующий вопрос →';
  } catch (error) {
    if (error.status === 409) { await refresh(); await begin(progress.history.find(s => s.status==='in_progress')?.retake_skill || null); }
    throw error;
  }
});
$('credentials').onsubmit = action(async event => {
  const data = Object.fromEntries(new FormData($('credentials')));
  if (event.submitter.value === 'register' && !data.alias.trim()) throw new Error('Введите псевдоним для регистрации.');
  await request('/api/account/'+event.submitter.value,data); $('credentials').reset(); await loadAccount();
});
$('logout').onclick = action(async () => {await request('/api/account/logout',{}); location.reload();});
async function loadAccount() {
  try { account = await request('/api/account/me'); }
  catch (error) { if (error.status !== 401) throw error; $('auth').hidden = !pilot.availability.available; overview(); return; }
  $('identity').textContent = account.alias; $('logout').hidden = false;
  $('auth').hidden = true; $('moderate').hidden = !account.moderator;
  await refresh();
  $('actions').hidden = false;
}
function showReview() {
  const row = reviews[$('review-list').selectedIndex];
  const detail = $('review-detail'); detail.replaceChildren(); if (!row) return;
  if (row.kind === 'questions') {
    detail.append(element('p',row.skill+' · '+(row.pilot_phase==='initial'?'Вступительный':'Повторный')+' · версия '+row.version_number),
      element('p',row.title),element('p',(row.options_snapshot||[]).join(' / ')),element('p','Ключ: '+row.expected_answer),element('p',row.evaluation_rules));
  } else {
    const a = element('a',row.title); a.href = row.url; a.target = '_blank'; a.rel = 'noopener noreferrer';
    detail.append(element('p',row.course),a,element('p',row.description),element('p',row.skills.join(' · ')),
      element('p',row.language+' · '+row.access_type+' · проверка ссылки '+row.link_checked_at.slice(0,10)));
  }
}
async function loadReviews(selectedIndex=0) {
  const data = await request('/api/review');
  reviews = Object.entries(data).flatMap(([kind,items]) => items.map(item => ({...item,kind})));
  $('review-list').replaceChildren(...reviews.map(item => element('option',
    ({pending:'Ожидает решения',approved:'Допущено',rejected:'Отклонено'}[item.status])+' · '+item.title)));
  $('review-list').selectedIndex = selectedIndex; showReview();
}
$('moderate').onclick = action(async () => { $('review').hidden = !$('review').hidden; if (!$('review').hidden) await loadReviews(); });
$('review-list').onchange = showReview;
for (const [decision,title] of Object.entries({approved:'Допустить',needs_review:'На уточнение',rejected:'Отклонить'})) {
  const button = element('button',title); button.className = 'secondary-button';
  button.onclick = action(async () => {
    const idx = $('review-list').selectedIndex, item = reviews[idx];
    await request('/api/review/'+item.kind+'/'+item.id,{decision,note:$('review-note').value});
    $('review-note').value = ''; await loadReviews(idx);
  });
  $('decisions').append(button);
}
for (const [approved,label] of [[true,'Допустить карту'],[false,'Отозвать допуск карты']]) {
  const button = element('button',label);
  button.className = 'secondary-button';
  button.onclick = action(async () => {
    await request('/api/review/graph/'+encodeURIComponent(slug)+'/decision',{fingerprint:pilot.availability.fingerprint,approved});
    location.reload();
  });
  $('graph-decisions').append(button);
}
$('retry-page').onclick = () => location.reload();
action(async () => {
  $('retry-page').hidden = false;
  pilot = await request(api+'/preview'); $('title').textContent = pilot.goal; document.title = pilot.topic+' · RemI AI';
  $('synthetic').hidden = !pilot.synthetic;
  for (const e of pilot.edges) $('edge-list').append(element('li',nodeById(e.prerequisite_id).name+' → '+nodeById(e.competency_id).name));
  $('map-section').hidden = false;
  if (!pilot.availability.available) notice('Доступен обзор карты. Диагностика ожидает допуска преподавателя.');
  await loadAccount();
  $('retry-page').hidden = true;
})();

