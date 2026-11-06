const list = document.querySelector('#discipline-list');
const message = document.querySelector('#message');
const count = document.querySelector('#count');
const topicsSection = document.querySelector('#topics-section');
const topicsTitle = document.querySelector('#topics-title');
const topicsMessage = document.querySelector('#topics-message');
const topicsList = document.querySelector('#topics-list');
const patterns = ['∑', '∫', '{ }', '◈', '⌁'];
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
  topicsTitle.textContent = discipline.name;
  topicsList.replaceChildren();
  topicsMessage.textContent = 'Загружаем темы…';
  try {
    const result = await getJson(`/api/disciplines/${discipline.discipline_id}/topics`);
    if (request !== topicsRequest) return;
    topicsMessage.textContent = result.topics.length ? '' : 'Темы для этой дисциплины пока не добавлены.';
    for (const [index, topic] of result.topics.entries()) {
      const item = document.createElement('li');
      const number = document.createElement('span');
      const name = document.createElement('span');
      number.className = 'topic-number';
      number.textContent = String(index + 1).padStart(2, '0');
      name.textContent = topic.name;
      item.append(number, name);
      topicsList.append(item);
    }
  } catch {
    if (request !== topicsRequest) return;
    topicsMessage.textContent = 'Не получилось загрузить темы. Попробуй ещё раз.';
  }
  topicsSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

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
    feedback.textContent = `${isCorrect ? 'Верно.' : 'Не совсем.'} ${question.explanation}`;
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
