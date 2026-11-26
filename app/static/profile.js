'use strict';
const get = id => document.getElementById(id);
async function api(path, body) {
  const response = await fetch('/api/account/'+path, body === undefined ? {cache:'no-store'} :
    {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  const result = await response.json();
  if (!response.ok) throw Object.assign(new Error(result.detail || 'Не удалось выполнить запрос.'),{status:response.status});
  return result;
}
function say(text) { get('status').textContent = text; get('status').focus(); }
function handle(callback) {
  return async event => {
    event?.preventDefault();
    const control = event?.submitter || event?.currentTarget;
    if (control) control.disabled = true;
    try { await callback(); }
    catch (error) { say(error.message); get('retry').hidden = false; }
    finally { if (control) control.disabled = false; }
  };
}
async function load() {
  get('retry').hidden = true;
  const info = await api('support');
  get('data-notice').textContent = info.data_notice || '';
  get('data-notice').hidden = !info.data_notice;
  if (info.email) {
    const link = document.createElement('a');
    link.href = 'mailto:'+info.email; link.textContent = info.email;
    get('support').replaceChildren('Вопросы о доступе и удалении данных: ',link);
  }
  let account;
  try { account = await api('me'); }
  catch (error) { if (error.status !== 401) throw error; get('login').hidden = false; return; }
  get('login').hidden = true;
  const routes = await api('routes');
  get('routes').replaceChildren(...routes.map(route => {
    const li = document.createElement('li'), link = document.createElement('a');
    link.href = '/learn/'+encodeURIComponent(route.slug); link.textContent = route.title; li.append(link); return li;
  }));
  get('empty').hidden = !!routes.length; get('alias').textContent = account.alias;
  get('dashboard').hidden = false;
}
for (const [id,path] of [['credentials','login'],['request-code','recovery'],['reset','recovery/finish']]) {
  get(id).onsubmit = handle(async () => {
    const result = await api(path,Object.fromEntries(new FormData(get(id))));
    get(id).reset(); say(result.message || 'Вы вошли в профиль.');
    if (path === 'login') await load();
  });
}
get('logout').onclick = handle(async () => {await api('logout',{}); location.reload();});
get('retry').onclick = handle(load);
handle(load)();
