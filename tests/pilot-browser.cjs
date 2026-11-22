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

async function respond(page, weakSkills) {
  const seen = [];
  for (;;) {
    await page.locator('#prompt').waitFor();
    const question = await page.locator('#prompt').innerText();
    const key = keys[question], right = !weakSkills.includes(key.name);
    const options = page.getByRole('radio');
    if (await options.count()) {
      const values = await options.evaluateAll(items => items.map(i => i.value));
      await options.nth(values.findIndex(value => (value === key.expected_answer) === right)).check();
    } else {
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
  const context = await browser.newContext({reducedMotion:'reduce'});
  try {
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror',error => errors.push(error.message));
    await page.goto(origin);
    await page.locator('.discipline-card').filter({hasText:discipline}).click();
    await page.locator('.topic-map-node').filter({hasText:topic}).click();
    await page.locator('#topic-test-link').click();
    await page.locator('#graph button').first().waitFor();
    const email = randomUUID()+'@example.invalid', password = randomUUID();
    await page.getByLabel('Почта').fill(email);
    await page.getByLabel('Пароль').fill(password);
    await page.getByLabel('Псевдоним').fill('Учебный профиль');
    await page.getByRole('button',{name:'Создать профиль'}).click();
    await page.locator('#start').click();
    const questions = await respond(page,nextWeak ? [weak, nextWeak] : [weak]);
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
    if (weak === 'Вычислять ошибку управления') {
      assert.match(await page.locator('#step-path').innerText(), /Понимать отрицательную обратную связь/);
      if (!nextWeak && process.env.REMI_PREVIEW_DIR) await page.locator('#next-box').screenshot({
        path: require('node:path').join(process.env.REMI_PREVIEW_DIR, 'tau-before.png')
      });
    }
    await page.locator('#next-skill').click();
    const link = page.locator('#materials a').first();
    await link.waitFor();
    assert.match(await page.locator('#mode').innerText(),/MiniLM/);
    const section = await link.innerText();
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
    assert.deepEqual(errors,[]);
    console.log(weak,'→',section);
    return {questions,section};
  } finally { await context.close(); }
}
(async () => {
  const browser = await chromium.launch({executablePath:process.env.REMI_CHROME || undefined});
  try {
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
  } finally { await browser.close(); }
})().catch(error => {console.error(error);process.exitCode=1;});

