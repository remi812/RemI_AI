/* Run after pilot_acceptance.py against the same dedicated local demo DB. */
const { chromium } = require('playwright');
const { execFileSync } = require('node:child_process');
const { randomUUID } = require('node:crypto');
const assert = require('node:assert/strict');

if (!process.env.PGDATABASE?.endsWith('_demo')) throw new Error('Dedicated demo database required');
const sql = `from app.pilot_db import open_database
import json
with open_database() as db:
    rows = db.execute('SELECT v.question_text,v.expected_answer,c.name FROM approved_pilot_questions v JOIN competencies c USING(competency_id)').fetchall()
    print(json.dumps({q['question_text']:q for q in rows}))`;
const keys = JSON.parse(execFileSync('python',['-c',sql],{encoding:'utf8'}));
const origin = 'http://127.0.0.1:' + (process.env.REMI_HTTP_PORT || '8019');
const inputKinds = new Set();

async function respond(page, weakSkills) {
  const seen = [];
  for (;;) {
    await page.locator('#prompt').waitFor();
    const question = await page.locator('#prompt').innerText();
    const key = keys[question], right = !weakSkills.includes(key.name);
    const options = page.getByRole('radio');
    if (await options.count()) {
      inputKinds.add('choice');
      const values = await options.evaluateAll(items => items.map(i => i.value));
      await options.nth(values.findIndex(value => (value === key.expected_answer) === right)).check();
    } else {
      inputKinds.add(await page.locator('#answers input').getAttribute('aria-label'));
      await page.locator('#answers input').fill(right ? key.expected_answer.split('|')[0] : '999');
    }
    seen.push(question);
    await page.locator('#answer-form button').click();
    await page.locator('#continue').waitFor();
    assert.equal(await page.locator('#feedback').innerText(),right?'Верно':'Неверно');
    const done = (await page.locator('#continue').innerText()).includes('карту');
    await page.locator('#continue').click();
    if (done) break;
    await page.locator('#answer-form').waitFor();
  }
  await page.locator('#history-box').waitFor();
  return seen;
}
async function student(browser, discipline, topic, weak, nextWeak) {
  const options = {reducedMotion:'reduce',viewport:{width:390,height:844}};
  const live = nextWeak && process.env.REMI_SHOW_PROFILE;
  const context = live ? await chromium.launchPersistentContext(live,{
    ...options,headless:false,executablePath:process.env.REMI_CHROME
  }) : await browser.newContext(options);
  try {
    const page = await context.newPage();
    const errors = [];
    await page.route(origin+'/api/**', async route => {
      const response = await route.fetch();
      if (response.ok()) {
        try {
          const data = await response.json();
          const privateField = /"(?:expected_answer|correct_answer|correct_index|evaluation_rules|options_snapshot_key|password_hash)"\s*:/;
          assert.doesNotMatch(JSON.stringify(data),privateField);
          if (data.question) assert.deepEqual(Object.keys(data.question).sort(),
            ['answer_type','options_snapshot','question_text','question_version_id']);
        } catch (error) { errors.push(error.message); }
      }
      await route.fulfill({response});
    });
    page.on('pageerror',error => errors.push(error.message));
    await page.goto(origin);
    await page.locator('.discipline-card').filter({hasText:discipline}).click();
    await page.locator('.topic-map-node').filter({has:page.getByText(topic,{exact:true})}).click();
    const previewGoal = page.locator('.preview-goal');
    await previewGoal.waitFor();
    const goalName = await previewGoal.innerText();
    const children = page.locator('.preview-node:not(.preview-goal)');
    if (await children.count()) {
      const name = await children.first().innerText();
      await children.first().click();
      assert.equal(await previewGoal.innerText(),name);
      await page.locator('#preview-back').click();
      assert.equal(await previewGoal.innerText(),goalName);
    }
    await page.locator('#topic-test-link').click();
    await page.locator('#graph button').first().waitFor();
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),'Профиль выходит за экран');
    const email = randomUUID()+'@example.invalid', password = randomUUID();
    await page.getByLabel('Почта').fill(email);
    await page.getByLabel('Пароль').fill(password);
    await page.getByLabel('Псевдоним').fill('Учебный профиль');
    await page.getByRole('button',{name:'Создать профиль'}).click();
    await page.locator('#start').click();
    await page.locator('#prompt').waitFor();
    const firstPrompt = await page.locator('#prompt').innerText();
    await page.reload();
    await page.getByRole('button',{name:'Продолжить проверку'}).click();
    await page.locator('#prompt').waitFor();
    assert.equal(await page.locator('#prompt').innerText(),firstPrompt);
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'Узкий экран: горизонтальное переполнение');
    const questions = await respond(page,nextWeak ? [weak, nextWeak] : [weak]);
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),'Карта выходит за экран');
    const nextName = await page.locator('#next-text').innerText();
    if (nextWeak === nextName) [weak, nextWeak] = [nextWeak, weak];
    assert.equal(nextName,weak);
    if (nextWeak) {
      await page.locator('#later-steps summary').click();
      await page.locator('#step-list button').filter({hasText:nextWeak}).click();
      assert.equal(await page.locator('#skill-title').innerText(),nextWeak);
      await page.locator('#back').click();
    }
    const recommendation = page.locator('#step-resources a').first();
    await recommendation.waitFor();
    const firstSection = await recommendation.innerText();
    assert.match(await page.locator('#step-resources').innerText(), /0 из 2/);
    if (weak === 'Вычислять ошибку управления' && topic === 'Обратная связь') {
      assert.match(await page.locator('#step-path').innerText(), /Понимать отрицательную обратную связь/);
      if (!nextWeak && process.env.REMI_PREVIEW_DIR) await page.locator('#next-box').screenshot({
        path: require('node:path').join(process.env.REMI_PREVIEW_DIR, 'tau-before.png')
      });
    }
    if (nextWeak) {
      await page.locator('#graph button').filter({hasText:'Распознавать математическую модель'}).click();
      await page.locator('#materials a').filter({hasText:'Решение задач с помощью линейных уравнений'}).waitFor();
      await page.locator('#back').click();
      await page.route('**/skills/*/materials', route => route.fulfill({
        json:{mode:'empty',items:[]}
      }),{times:1});
      await page.locator('#graph button').filter({hasText:'Распознавать математическую модель'}).click();
      await page.getByText('Подходящего одобренного материала для этого навыка пока нет.',{exact:true}).waitFor();
      assert.equal(await page.locator('#materials a').count(),0);
      await page.locator('#back').click();
      await page.route('**/skills/*/materials', route => route.fulfill({status:503,body:'{}'}),{times:1});
      await page.locator('#next-skill').click();
      await page.getByText('Не удалось загрузить материалы.',{exact:true}).waitFor();
      await page.getByRole('button',{name:'Попробовать снова'}).click();
    } else await page.locator('#next-skill').click();
    const link = page.locator('#materials a').first();
    await link.waitFor();
    assert.match(await page.locator('#mode').innerText(),/MiniLM|Единственный допущенный раздел/);
    const section = await link.innerText();
    if (weak === 'Различать разомкнутую и замкнутую системы') {
      assert.deepEqual(await page.locator('#materials a').allTextContents(),[
        'Введение перед первой лекцией','1.2.1. Принцип разомкнутого управления'
      ]);
    }
    assert.equal(section, firstSection);
    assert.match(await page.locator('#materials').innerText(),/0 из 2/);
    await page.locator('#retake').click();
    const fresh = await respond(page,[]);
    assert.ok(fresh.length >= 2);
    assert.ok(fresh.every(q => !questions.includes(q)));
    assert.notEqual(await page.locator('#next-text').innerText(),weak);
    assert.match(await page.locator('#change-result').innerText(),
      /Вероятный пробел \(0 из 2\) → Предварительно освоено \(2 из 2\)/);
    if (nextWeak) {
      assert.equal(await page.locator('#next-text').innerText(),nextWeak);
      await page.locator('#step-resources a').first().waitFor();
      assert.notEqual(await page.locator('#step-resources a').first().innerText(),firstSection);
      if (process.env.REMI_PREVIEW_DIR) await page.locator('#next-box').screenshot({
        path: require('node:path').join(process.env.REMI_PREVIEW_DIR, 'tau-next-step.png')
      });
    }
    if (!nextWeak && weak === 'Вычислять ошибку управления' && process.env.REMI_PREVIEW_DIR)
      await page.locator('#next-box').screenshot({path: require('node:path').join(process.env.REMI_PREVIEW_DIR, 'tau-after.png')});
    assert.equal(await page.locator('#graph button.mastered').filter({hasText:weak}).count(),1);
    await page.locator('#logout').click();
    await page.getByLabel('Почта').fill(email);
    await page.getByLabel('Пароль').fill(password);
    await page.getByRole('button',{name:'Войти',exact:true}).click();
    await page.locator('#history-box').waitFor();
    assert.equal(await page.locator('#history details').count(),2);
    assert.equal(await page.locator('#change-skill').innerText(), weak);
    await page.locator('#history details').first().click();
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),'История выходит за экран');
    assert.ok(!(await page.evaluate(() => performance.getEntriesByType('resource').some(r => r.name.includes('/demo-data.js')))));
    assert.deepEqual(errors,[]);
    console.log(weak,'→',section);
    return {questions,section};
  } finally {
    for (const page of context.pages()) await page.unrouteAll({behavior:'wait'});
    await context.close();
  }
}
async function verifyFallback(browser, port) {
  const page = await browser.newPage({viewport:{width:390,height:844},reducedMotion:'reduce'});
  try {
    await page.goto('http://127.0.0.1:'+Number(port)+'/learn/control');
    await page.getByLabel('Почта').fill(randomUUID()+'@example.invalid');
    await page.getByLabel('Пароль').fill(randomUUID());
    await page.getByLabel('Псевдоним').fill('Проверка без модели');
    await page.getByRole('button',{name:'Создать профиль'}).click();
    await page.locator('#start').waitFor();
    await page.locator('#graph button').filter({hasText:'Различать разомкнутую и замкнутую системы'}).click();
    await page.getByText('Подобрано по теме навыка. Смысловой поиск сейчас недоступен.',{exact:true}).waitFor();
    const titles = await page.locator('#materials a').allTextContents();
    assert.deepEqual(titles,['1.2.1. Принцип разомкнутого управления','Введение перед первой лекцией']);
    console.log('Отдельный сервер без модели: подпись и обе ссылки проверены.');
  } finally { await page.close(); }
}
(async () => {
  const browser = await chromium.launch({executablePath:process.env.REMI_CHROME || undefined});
  try {
    if (process.env.REMI_EMPTY_ONLY === '1') {
      assert.deepEqual(Object.keys(keys),[]);
      const page = await browser.newPage({viewport:{width:390,height:844}});
      await page.goto(origin+'/learn/control');
      await page.getByText(/Доступен обзор карты/).waitFor();
      assert.equal(await page.locator('#auth').isVisible(),false);
      assert.equal(await page.locator('#start').isVisible(),false);
      assert.equal(await page.locator('#map-title').isVisible(),true);
      console.log('Проверен доступный обзор до допуска.');
      return;
    }
    if (process.env.REMI_FALLBACK_PORT) await verifyFallback(browser,process.env.REMI_FALLBACK_PORT);
    const a = await student(browser,'Теория автоматического управления','Обратная связь','Вычислять ошибку управления');
    const b = await student(browser,'Теория автоматического управления','Обратная связь','Различать разомкнутую и замкнутую системы');
    assert.notEqual(a.questions[1],b.questions[1]);
    assert.notEqual(a.section,b.section);
    const math = await student(browser,'Высшая математика','Производные','Вычислять производную многочлена');
    assert.equal(math.section,'Как найти производную? Правило суммы');
    const python = await student(browser,'Основы программирования','Циклы','Определять число повторений цикла');
    assert.equal(python.section,'Цикл for. Функция range');
    await student(browser,'Теория автоматического управления','Обратная связь',
      'Вычислять ошибку управления','Различать разомкнутую и замкнутую системы');
    const catalog = await browser.newPage();
    const disciplines = (await (await catalog.request.get(origin+'/api/disciplines')).json()).disciplines;
    let detailed = 0, overview = 0;
    for (const discipline of disciplines) {
      const {topics} = await (await catalog.request.get(origin+'/api/disciplines/'+discipline.discipline_id+'/topics')).json();
      for (const topic of topics) {
        assert.ok(topic.slug,topic.name);
        if (topic.slug === 'modeling') {
          await catalog.goto(origin);
          await catalog.locator('.discipline-card').filter({hasText:discipline.name}).click();
          await catalog.locator('.topic-map-node').filter({hasText:topic.name}).click();
          await catalog.locator('#modeling-overview').waitFor();
          assert.ok(await catalog.locator('#modeling-materials a').count() >= 1);
          assert.equal(await catalog.locator('#modeling-overview a[href^="/learn/"]').count(),3);
          assert.equal(await catalog.locator('#topic-test-link').isVisible(),false);
          await catalog.locator('.preview-node:not(.preview-goal)').first().click();
          await catalog.locator('#preview-back').click();
          assert.equal(await catalog.locator('.preview-goal').innerText(),'Распознавать математическую модель');
          overview++;
          continue;
        }
        if (!['control','derivatives','programming'].includes(topic.slug)) {
          const preview = await (await catalog.request.get(origin+'/api/learn/'+topic.slug+'/preview')).json();
          await student(browser,discipline.name,topic.name,preview.goal);
        }
        detailed++;
      }
    }
    assert.equal(detailed,19); assert.equal(overview,1);
    assert.deepEqual([...inputKinds].sort(), ['choice','Короткий ответ','Числовой ответ'].sort());
    await catalog.close();
    console.log('Все 19 подробных тем и обзор моделирования пройдены.');
  } finally { await browser.close(); }
})().catch(error => {console.error(error);process.exitCode=1;});


