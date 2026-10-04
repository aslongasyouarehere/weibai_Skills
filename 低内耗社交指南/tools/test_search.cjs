// Regression checks for search intent and URL state; no browser dependencies.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
const data = fs.readFileSync(path.join(root, 'index.html'), 'utf8')
  .match(/<script id="entries" type="application\/json">(.*?)<\/script>/s)[1];
const code = fs.readFileSync(path.join(__dirname, 'search.js'), 'utf8');

function page(url) {
  const elements = new Map();
  const cards = new Map();
  function element(id) {
    if (id.startsWith('entry-')) return cards.get(id) || null;
    if (!elements.has(id)) elements.set(id, {
      value: '', options: [{ value: '' }], handlers: {}, textContent: '',
      append(option) { this.options.push(option); },
      addEventListener(event, handler) { this.handlers[event] = handler; },
      set innerHTML(html) {
        this.html = html;
        if (id === 'list') {
          cards.clear();
          for (const match of html.matchAll(/<article class="card" id="([^"]+)"/g)) {
            const details = { open: false };
            cards.set(match[1], { details, querySelector: () => details, scrollIntoView() {} });
          }
        }
      },
      get innerHTML() { return this.html; }
    });
    return elements.get(id);
  }
  element('entries').textContent = data;
  const location = { href: url, get hash() { return new URL(this.href).hash; } };
  const windowHandlers = {};
  const history = [url];
  let cursor = 0;
  const context = vm.createContext({
    document: { getElementById: element, createElement: () => ({}) },
    location, URL, history: {
      replaceState(_, __, href) { history[cursor] = location.href = href; },
      pushState(_, __, href) {
        history.splice(cursor + 1);
        history.push(href);
        cursor++;
        location.href = href;
      }
    },
    window: { addEventListener(event, handler) { windowHandlers[event] = handler; } }
  });
  vm.runInContext(code, context);
  return { element, location, cards,
    run: expression => vm.runInContext(expression, context),
    query(value) { element('query').value = value; element('search-submit').handlers.click(); },
    reference(id, modifiers = {}) {
      let prevented = false;
      const link = { dataset: { ref: id } };
      element('list').handlers.click({
        target: { closest: () => link }, button: 0, ...modifiers,
        preventDefault() { prevented = true; }
      });
      return prevented;
    },
    back() {
      assert(cursor > 0, 'Related-entry navigation must create a history entry');
      location.href = history[--cursor];
      windowHandlers.popstate();
    },
    forward() {
      assert(cursor < history.length - 1);
      location.href = history[++cursor];
      windowHandlers.popstate();
    },
    ids() { return [...cards.keys()]; }
  };
}

const site = 'https://example.test/guide/index.html';
const search = page(site);
search.element('decision-goal').value = '拒绝继续代做，同时保留正常合作';
search.element('decision-power').value = '对方掌握评价、资源或机会';
search.element('decision-agreement').value = '只有口头或模糊约定';
search.element('decision-stakes').value = '可能影响时间、金钱、学业或工作';
search.element('decision-fallback').value = '缩小范围或请负责人确认';
search.element('decision-check').handlers.click();
assert.match(search.element('decision-output').textContent, /当前目标：拒绝继续代做/);
assert.match(search.element('decision-output').textContent, /对方掌握关键资源/);
assert.match(search.element('decision-output').textContent, /约定不清/);
assert.match(search.element('decision-output').textContent, /存在现实成本/);
search.element('decision-clear').handlers.click();
assert.equal(search.element('decision-output').textContent, '');
for (const entry of JSON.parse(data)) {
  search.query(entry.id);
  assert.deepEqual(search.ids(), ['entry-' + entry.id], 'Find the exact entry by number: ' + entry.id);
  search.query(entry.title);
  assert(search.ids().includes('entry-' + entry.id), 'Find an entry by its full title: ' + entry.id);
}
for (const query of ['条目 5.7', '第5.7条', '５．７', '#entry-5.7']) {
  search.query(query);
  assert.deepEqual(search.ids(), ['entry-5.7'], query);
}
search.query('99.1');
assert.equal(search.cards.size, 0, 'Unknown entry numbers must not search unrelated body text');
search.element('chapter').value = '4';
search.query('5.7');
assert.equal(search.cards.size, 0, 'Entry-number search must respect selected filters');
search.element('chapter').value = '';
for (const [query, target] of [
  ['offer 催我答复', 'entry-10.7'], ['申请延长 offer 回复期限', 'entry-10.7'],
  ['被别人夸奖时，要如何回复', 'entry-7.10'], ['领导夸我工作做得好怎么回复', 'entry-7.10'],
  ['转发截图', 'entry-5.7'], ['老板临时让我加班', 'entry-3.1'],
  ['室友拿我的东西', 'entry-1.4']
]) {
  search.query(query);
  assert.equal(search.ids()[0], target, query);
}
search.query('怎么样送礼');
assert(search.ids().includes('entry-4.4'), 'Longer question prefixes must not leave a stray character');
for (const query of ['被夸奖怎么回复', '别人夸我如何回应', '老师夸我怎么回复']) {
  search.query(query);
  assert.equal(search.ids()[0], 'entry-7.10', query);
}
for (const [query, target] of [
  ['别人把照片发朋友圈怎么办', 'entry-5.7'], ['怎么发合照', 'entry-5.7'],
  ['转发聊天记录', 'entry-5.7'], ['群里有人被欺负怎么办', 'entry-5.8'],
  ['看到别人被冒犯怎么办', 'entry-5.8'], ['offer催我答复', 'entry-10.7'],
  ['怎么谈薪', 'entry-10.7'], ['延长offer回复期限', 'entry-10.7']
]) {
  search.query(query);
  assert.equal(search.ids()[0], target, query);
}
search.query('送礼火星矿石');
assert.equal(search.cards.size, 0, 'Unknown content must not become a broad gift search');
search.query('offer 催我答复 火星矿石');
assert.equal(search.cards.size, 0, 'Space-tolerant matching must preserve unknown words');
search.query('怎么送礼');
assert(search.ids().includes('entry-4.4'));
search.element('chapter').value = '7';
search.element('chapter').handlers.change();
assert(search.ids().every(id => id.startsWith('entry-7.')));

const jumped = page(site + '#entry-4.1');
assert(jumped.cards.get('entry-4.1').details.open);
jumped.query('送礼');
assert.equal(new URL(jumped.location.href).hash, '');
const refreshed = page(jumped.location.href);
assert.equal(refreshed.element('query').value, '送礼');
assert.deepEqual(refreshed.ids(), jumped.ids());

const deepLink = page(site + '?q=送礼#entry-3.1');
assert(deepLink.cards.get('entry-3.1').details.open);
assert.equal(new URL(deepLink.location.href).hash, '#entry-3.1');
deepLink.element('reset').handlers.click();
assert.equal(new URL(deepLink.location.href).hash, '');
assert.equal(new URL(deepLink.location.href).search, '');
assert.equal(deepLink.cards.size, JSON.parse(data).length);

const offline = page('file:///tmp/index.html#entry-4.1');
offline.query('借钱不还');
assert(offline.ids().includes('entry-4.2'));
assert.equal(new URL(offline.location.href).hash, '');

const references = page(site + '?q=借钱不还&chapter=4');
const priorResults = references.ids();
for (const modifiers of [{ metaKey: true }, { ctrlKey: true }, { shiftKey: true }, { altKey: true }, { button: 1 }]) {
  assert.equal(references.reference('5.3', modifiers), false, 'Preserve native modified-link behavior');
  assert.deepEqual(references.ids(), priorResults);
  assert.equal(new URL(references.location.href).hash, '');
}
assert(references.reference('5.3'));
assert(references.cards.get('entry-5.3').details.open);
references.back();
assert.equal(references.element('query').value, '借钱不还');
assert.equal(references.element('chapter').value, '4');
assert.deepEqual(references.ids(), priorResults);
references.forward();
assert(references.cards.get('entry-5.3').details.open);
assert.equal(new URL(references.location.href).hash, '#entry-5.3');
console.log('Search regression checks passed: intent, filters, refresh, jumps, reset, offline URL, modified links and back/forward.');

const newRelated = page(site + '?q=发合照&chapter=5');
assert(newRelated.ids().includes('entry-5.7'));
assert(newRelated.reference('5.8'));
assert(newRelated.cards.get('entry-5.8').details.open);
newRelated.back();
assert(newRelated.ids().includes('entry-5.7'));
assert.equal(newRelated.element('query').value, '发合照');
