const list = document.querySelector('#discipline-list');
const message = document.querySelector('#message');
const count = document.querySelector('#count');
const topicsSection = document.querySelector('#topics-section');
const topicsTitle = document.querySelector('#topics-title');
const topicsMessage = document.querySelector('#topics-message');
const topicsList = document.querySelector('#topics-list');
const patterns = ['∑', '∫', '{ }', '◈', '⌁'];
let topicsRequest = 0;

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
  topicsSection.hidden = true;
  document.querySelectorAll('.discipline-card').forEach(card => {
    card.classList.remove('selected');
    card.setAttribute('aria-pressed', 'false');
  });
});

loadDisciplines();
