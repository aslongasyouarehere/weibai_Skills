'use strict';

const entries = JSON.parse(document.getElementById('entries').textContent);
const $ = id => document.getElementById(id);
const escape = value => String(value).replace(/[&<>"']/g, char => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
}[char]));
const normalize = value => String(value).normalize('NFKC').toLocaleLowerCase();
const filterIds = ['query', 'chapter', 'topic', 'person'];
let allExpanded = false;

function options(id, values) {
  for (const [value, label] of values) {
    const option = document.createElement('option');
    option.value = value;
    option.textContent = label;
    $(id).append(option);
  }
}
options('chapter', [...new Map(entries.map(entry => [entry.chapter, entry.chapterTitle])).entries()]);
for (const [id, key] of [['topic', '主题'], ['person', '对象']]) {
  options(id, [...new Set(entries.flatMap(entry => entry.tags[key]))].sort().map(tag => [tag, tag]));
}

// A small, inspectable phrase dictionary, rather than splitting every Chinese
// character. Specific phrases such as “借钱不还” are consumed before “借钱”.
const concepts = [
  { aliases: ['别人把照片发朋友圈', '发合照', '合照', '朋友圈照片', '发布照片', '聊天截图', '转发截图', '转发聊天记录', '公开聊天记录', '线上隐私'], matches: ['发布合照', '合照', '聊天截图', '线上隐私'] },
  { aliases: ['看到别人被冒犯', '旁观者', '朋友被羞辱', '群里有人被欺负', '网络围攻', '群聊骚扰'], matches: ['旁观者', '看到别人被冒犯', '骚扰'] },
  { aliases: ['offer催我答复', '申请延长offer回复期限', '延长offer回复期限', 'offer回复期限', '谈薪', '谈工资', '协商offer', 'offer协商', '申请延长回复期限', '回复期限'], matches: ['协商 offer', '回复期限'] },
  { aliases: ['敬酒词', '敬酒话术', '敬酒', '祝酒词', '祝酒', '举杯'], matches: ['敬酒', '敬酒词', '祝福'] },
  { aliases: ['借钱不还', '借钱没还', '欠钱不还', '借了不还', '不还钱', '没还钱', '还钱', '还款', '催还', '催款', '催债', '讨债'], matches: ['没还钱', '还款', '催还', '还钱'] },
  { aliases: ['借钱', '借款'], matches: ['借钱', '借款'] },
  { aliases: ['送礼物', '送礼', '随礼', '伴手礼', '随手礼', '礼物', '礼金', '红包', '赠礼'], matches: ['送礼', '随礼', '礼物', '赠礼'] },
  { aliases: ['婉拒', '拒绝', '回绝', '不想答应', '说不'], matches: ['拒绝'] },
  { aliases: ['没回消息', '消息不回', '不回消息', '没回复', '不回复', '未回复', '已读不回'], matches: ['没回复', '没有回复', '未回复', '没有回应'] },
  { aliases: ['不想喝酒', '不喝酒', '拒酒', '劝酒'], matches: ['不喝酒', '拒酒'] },
  { aliases: ['请客吃饭', '聚餐', '饭局', '组局', '酒局'], matches: ['聚餐', '饭局'] },
  { aliases: ['聊天冷场', '接话', '聊天', '闲聊', '冷场'], matches: ['聊天', '话题'] },
  { aliases: ['被夸', '被夸奖', '被夸赞', '被别人夸奖', '被别人夸赞', '被表扬', '接夸', '怎么回复夸奖', '夸我工作做得好', '夸我做得好', '夸我表现好', '夸我', '别人夸我'], matches: ['被夸赞', '接夸'] },
  { aliases: ['赞美', '夸赞', '夸人', '夸奖', '表扬'], matches: ['夸赞', '赞美'] },
  { aliases: ['求人帮忙', '求助', '求人'], matches: ['求助'] },
  { aliases: ['帮忙', '帮助'], matches: ['帮忙', '帮助'] },
  { aliases: ['表达感谢', '感谢', '道谢', '答谢'], matches: ['感谢'] },
  { aliases: ['道歉', '认错', '犯错', '做错'], matches: ['道歉', '犯错'] },
  { aliases: ['内推', '推荐工作', '托人推荐'], matches: ['托人推荐', '简历'] },
  { aliases: ['离职', '辞职', '辞工'], matches: ['离职', '离开岗位'] },
  { aliases: ['入职', '新人', '新工作'], matches: ['入职', '刚进入团队'] },
  { aliases: ['面试', '应聘'], matches: ['面试'] },
  { aliases: ['工资', '薪资', '薪酬', '待遇', 'offer'], matches: ['待遇', '入职条件'] },
  { aliases: ['催婚', '催生', '催问感情', '催问生育'], matches: ['感情或生育', '催问'] },
  { aliases: ['隐私', '私事'], matches: ['隐私'] },
  { aliases: ['分手', '结束关系', '结束亲密关系'], matches: ['结束亲密关系', '结束关系'] },
  { aliases: ['吵架', '争吵', '冲突'], matches: ['冲突', '分歧'] },
  { aliases: ['误会', '修复关系'], matches: ['误会', '修复'] },
  { aliases: ['开玩笑', '玩笑', '冒犯'], matches: ['玩笑', '冒犯'] },
  { aliases: ['被批评', '批评', '挨骂'], matches: ['批评'] },
  { aliases: ['借东西', '借物', '借用物品', '拿我的东西', '用我的东西', '擅自用我的东西'], matches: ['借物', '物品', '使用你的东西'] },
  { aliases: ['临时让我加班', '突然让我加班', '临时加班'], matches: ['临时任务', '临时加任务'] },
  { aliases: ['aa制', 'aa', '垫钱', '垫款', '代付'], matches: ['aa', '垫款', '垫钱'] },
  { aliases: ['分工', '小组作业', '团队合作'], matches: ['分工', '合作'] },
  { aliases: ['返工', '重做', '要求不清', '模糊要求'], matches: ['返工', '模糊要求'] },
  { aliases: ['开会', '会议'], matches: ['会议'] },
  { aliases: ['汇报', '报告进展'], matches: ['汇报'] },
  { aliases: ['署名', '抢功', '功劳', '成果归属'], matches: ['署名', '成果归属', '贡献'] },
  { aliases: ['倾听', '安慰', '烦恼'], matches: ['倾听', '烦恼'] },
  { aliases: ['边界', '界限'], matches: ['边界', '限制'] },
  { aliases: ['做客', '拜访'], matches: ['做客'] },
  { aliases: ['接待', '招待'], matches: ['接待'] },
  { aliases: ['联系', '联络'], matches: ['联系'] },
  { aliases: ['迟到', '迟到取消'], matches: ['迟到'] },
  { aliases: ['分摊', '共同花钱'], matches: ['分摊', '共同花钱'] },
  { aliases: ['父母', '爸妈', '爸爸妈妈', '家长'], matches: ['父母', '亲人', '家人'] },
  { aliases: ['领导', '老板', '上司'], matches: ['领导', '负责人'] },
  { aliases: ['伴侣', '男朋友', '女朋友', '对象'], matches: ['伴侣', '亲密关系'] }
];
// Exact tags support compound questions like “怎么拒绝朋友借钱”.
const coveredAliases = new Set(concepts.flatMap(concept => concept.aliases.map(normalize)));
for (const tag of new Set(entries.flatMap(entry => Object.values(entry.tags).flat()))) {
  if (!coveredAliases.has(normalize(tag))) concepts.push({ aliases: [tag], matches: [tag] });
}
const phraseIndex = concepts.flatMap((concept, index) => concept.aliases.map(alias => {
  const phrase = normalize(alias).replace(/\s+/gu, '');
  // Match a known phrase across spaces, without discarding unknown words.
  const pattern = new RegExp([...phrase].map(char => char.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('\\s*'), 'gu');
  return { phrase, pattern, index };
})).sort((a, b) => b.phrase.length - a.phrase.length);

const searchIndex = entries.map((entry, position) => ({
  entry, position,
  title: normalize(entry.title),
  tags: Object.values(entry.tags).flat().map(normalize),
  scene: normalize(entry.fields['遇到的情况']),
  // Cross-references and source notes should not pull unrelated cards into results.
  body: normalize(Object.entries(entry.fields).filter(([key]) => !['相关条目', '依据'].includes(key)).map(([, value]) => value).join(' '))
}));

function questionCore(query) {
  return normalize(query).trim()
    .replace(/^(?:请问|请教一下|我想知道|我想问|帮我看看|帮我|我应该|我该|应该|到底|该|可以|要|想|我)(?:\s*)/u, '')
    .replace(/^(?:怎么才能|怎么样|怎么|如何|怎样)(?:\s*)/u, '')
    .replace(/(?:该怎么办|怎么办|怎么处理|怎么说|怎么做|如何处理|怎么回复|如何回复|怎么回应|如何回应|怎么回答|如何回答|好不好|可以吗|合适吗|[呢吗啊呀吧])(?:\s*)$/u, '')
    .trim();
}

function queryGroups(query) {
  const core = questionCore(query);
  if (!core) return [];
  const groups = [];
  const conceptIds = new Set();
  let rest = core;
  for (const { pattern, index } of phraseIndex) {
    pattern.lastIndex = 0;
    if (!pattern.test(rest)) continue;
    if (!conceptIds.has(index)) {
      conceptIds.add(index);
      groups.push(concepts[index].matches.map(normalize));
    }
    rest = rest.replace(pattern, ' ');
  }
  // Remove only complete grammatical remnants. Unknown phrases stay required,
  // so “送礼火星矿石” does not silently become “送礼”.
  for (const remainder of rest.split(/[\s，。！？、；：,.;!?]+/u).filter(Boolean)) {
    const significant = remainder
      .replace(/^(?:请问|怎么才能|怎么样|怎么|如何|怎样|应该|该|我想|我|你|对方|别人|有人|给|向|跟|和|与|的|要|想|不想)+/u, '')
      .replace(/(?:怎么办|怎么处理|怎么说|怎么做|如何处理|怎么回复|如何回复|怎么回应|如何回应|怎么回答|如何回答|的时候|的时候该|时|的|了|呢|吗|啊|呀|吧|该)+$/u, '');
    if (significant) groups.push([significant]);
  }
  return groups;
}

function entryNumber(query) {
  const match = normalize(query).trim().match(/^(?:#?entry[-\s]*|条目\s*|第\s*)?(\d+\.\d+)(?:\s*条)?$/u);
  return match ? match[1] : '';
}

function groupScore(indexed, terms) {
  let score = 0;
  for (const term of terms) {
    if (indexed.title.includes(term)) score = Math.max(score, 100);
    if (indexed.tags.some(tag => tag === term)) score = Math.max(score, 80);
    else if (indexed.tags.some(tag => tag.includes(term))) score = Math.max(score, 65);
    if (indexed.scene.includes(term)) score = Math.max(score, 40);
    if (indexed.body.includes(term)) score = Math.max(score, 10);
  }
  return score;
}

function filtered() {
  const query = $('query').value.trim();
  const number = entryNumber(query);
  const groups = number ? [] : queryGroups(query);
  const core = questionCore(query);
  return searchIndex.filter(({ entry }) =>
    (!number || entry.id === number) &&
    (!$('chapter').value || String(entry.chapter) === $('chapter').value) &&
    (!$('topic').value || entry.tags['主题'].includes($('topic').value)) &&
    (!$('person').value || entry.tags['对象'].includes($('person').value))
  ).map(indexed => {
    const scores = groups.map(group => groupScore(indexed, group));
    const matched = scores.every(score => score > 0);
    const exactBonus = core && indexed.title.includes(core) ? 120 :
      core && indexed.tags.includes(core) ? 100 :
      core && indexed.scene.includes(core) ? 30 : 0;
    return { ...indexed, matched, score: scores.reduce((sum, score) => sum + score, 0) + exactBonus };
  }).filter(item => item.matched).sort((a, b) => b.score - a.score || a.position - b.position).map(item => item.entry);
}

function saveFilters(clearAnchor = false) {
  const url = new URL(location.href);
  // A new search must not retain an old card jump: on reload that jump would
  // clear the new filters to reveal the old card.
  if (clearAnchor && url.hash.startsWith('#entry-')) url.hash = '';
  for (const [id, parameter] of [['query', 'q'], ['chapter', 'chapter'], ['topic', 'topic'], ['person', 'person']]) {
    const value = $(id).value.trim();
    if (value) url.searchParams.set(parameter, value);
    else url.searchParams.delete(parameter);
  }
  if (url.href !== location.href) {
    // Local files and restricted embedded browsers can disallow history changes;
    // filtering still works when the address cannot be changed.
    try { history.replaceState(null, '', url.href); } catch (_) {}
  }
}

function restoreFilters() {
  const params = new URL(location.href).searchParams;
  $('query').value = (params.get('q') || '').slice(0, 200);
  $('top-query').value = $('query').value;
  for (const id of ['chapter', 'topic', 'person']) {
    const value = params.get(id) || '';
    $(id).value = [...$(id).options].some(option => String(option.value) === value) ? value : '';
  }
}

function render(save = true, clearAnchor = false) {
  const shown = filtered();
  $('count').textContent = `找到 ${shown.length} 条 / 共 ${entries.length} 条 · 依据：经验建议`;
  const showChapterHeadings = !$('query').value.trim() && !$('topic').value && !$('person').value;
  $('list').innerHTML = shown.length ? shown.map((entry, index) => {
    const fields = entry.fields;
    const followUps = Object.entries(fields).filter(([key]) => key.startsWith('如果'));
    const detailGroup = (title, keys) => {
      const rows = keys.flatMap(key => key === '跟进' ? followUps : fields[key] ? [[key, fields[key]]] : []);
      return rows.length ? `<section class="detail-group"><h3>${escape(title)}</h3><dl>${rows.map(([key, value]) => `<dt>${escape(key)}</dt><dd>${escape(value)}</dd>`).join('')}</dl></section>` : '';
    };
    const targets = [...fields['相关条目'].matchAll(/(\d+\.\d+)（([^）]+)）/g)].map(match => `<a href="#entry-${match[1]}" data-ref="${match[1]}">${escape(match[1] + ' ' + match[2])}</a>`).join('');
    const startsChapter = showChapterHeadings && (index === 0 || shown[index - 1].chapter !== entry.chapter);
    const chapterTitle = entry.chapterTitle.replace(/^\d+\.\s*/, '');
    const chapterCount = entries.filter(item => item.chapter === entry.chapter).length;
    const heading = startsChapter ? `<header class="chapter-heading" id="chapter-${entry.chapter}"><h2>${entry.chapter}. ${escape(chapterTitle)}</h2><span>${chapterCount} 条</span></header>` : '';
    return `${heading}<article class="card" id="entry-${entry.id}"><div class="cardhead"><span>第 ${entry.chapter} 章 · 第 ${entry.id.split('.')[1]} 条</span><span>经验建议</span></div><h2>${escape(entry.title)}</h2><p class="scene">${escape(fields['遇到的情况'])}</p><p class="judgment"><strong>一句话判断</strong>${escape(fields['判断关键'])}</p><p class="action"><strong>第一步</strong>${escape(fields['先做什么'])}</p><p class="example-label">表达参考</p><blockquote>${escape(fields['可以怎么说']).replaceAll('（示例仅供参考，请根据事实情况调整。）', '（示例仅供参考，请根据事实情况调整。）<br><br>').replace(/(<br><br>)$/, '')}</blockquote><div class="chips">${entry.tags['主题'].map(tag => `<span class="chip">${escape(tag)}</span>`).join('')}</div><details ${allExpanded ? 'open' : ''}><summary>查看完整决策依据与回应分支</summary>${detailGroup('行动前准备', ['行动前准备'])}${detailGroup('根据关系与条件调整', ['分情境处理'])}${detailGroup('回应后怎么办', ['跟进', '何时换办法'])}<section class="detail-group"><h3>可能收益与代价</h3><div class="costs"><section><strong>可能换回什么</strong><span>${escape(fields['可能换回什么'])}</span></section><section><strong>花掉什么</strong><span>${escape(fields['花掉什么'])}</span></section></div></section>${detailGroup('例外、依据与边界', ['例外与代价', '依据'])}<div class="refs">相关条目：${targets}</div><div class="source"><a href="阅读全文.html#chapter-${entry.chapter}">阅读本章正文 ↗</a></div></details></article>`;
  }).join('') : '<div class="empty">没有找到相近条目。可以试试更具体的关键词，或清除筛选。</div>';
  $('expand').textContent = allExpanded ? '收起全部细节' : '展开全部细节';
  if (save) saveFilters(clearAnchor);
}

function applyFilters() { render(true, true); }
function reset(clearAnchor = true) {
  for (const id of filterIds) $(id).value = '';
  $('top-query').value = '';
  render(true, clearAnchor);
}
$('query').maxLength = 200;
$('top-query').maxLength = 200;
$('query').addEventListener('input', event => {
  $('top-query').value = event.target.value;
  if (!event.isComposing) applyFilters();
});
$('query').addEventListener('compositionend', event => {
  $('top-query').value = event.target.value;
  applyFilters();
});
$('top-query').addEventListener('input', event => {
  $('query').value = event.target.value;
  if (!event.isComposing) applyFilters();
});
$('top-query').addEventListener('compositionend', event => {
  $('query').value = event.target.value;
  applyFilters();
});
for (const id of ['chapter', 'topic', 'person']) $(id).addEventListener('change', applyFilters);
$('search-submit').addEventListener('click', applyFilters);
$('top-search-submit').addEventListener('click', applyFilters);
$('query').addEventListener('keydown', event => {
  if (event.key === 'Enter' && !event.isComposing) { event.preventDefault(); applyFilters(); }
});
$('top-query').addEventListener('keydown', event => {
  if (event.key === 'Enter' && !event.isComposing) { event.preventDefault(); applyFilters(); }
});
$('reset').addEventListener('click', () => reset());
$('expand').addEventListener('click', () => { allExpanded = !allExpanded; render(); });

function decisionCheck() {
  const goal = $('decision-goal').value.trim();
  const power = $('decision-power').value;
  const agreement = $('decision-agreement').value;
  const stakes = $('decision-stakes').value;
  const fallback = $('decision-fallback').value.trim();
  const missing = [];
  if (!goal) missing.push('核心目标');
  if (!power) missing.push('关系与权力');
  if (!agreement) missing.push('已有约定');
  if (!stakes) missing.push('现实后果');
  if (!fallback) missing.push('替代方案');
  const lines = [];
  if (goal) lines.push(`当前目标：${goal}`);
  if (missing.length) lines.push(`还值得确认：${missing.join('、')}。`);
  if (power.includes('评价、资源或机会')) lines.push('对方掌握关键资源：先核对事实与可用支持，不只优化语气。');
  if (agreement.includes('模糊') || agreement.includes('不清楚')) lines.push('约定不清：第一步优先确认范围、期限、责任或公开边界。');
  if (stakes.includes('安全、隐私、合同或正式纪律')) lines.push('现实风险较高：不要只靠一句话处理，先核对适用规则或求助渠道。');
  else if (stakes.includes('时间、金钱、学业或工作')) lines.push('存在现实成本：表达前写清可承担范围和停止条件。');
  if (fallback) lines.push(`备选动作：${fallback}`);
  lines.push('下一步：在下方搜索最接近的场景，比较第一步、回应分支与代价。');
  $('decision-output').textContent = lines.join('\n');
  $('decision-output').hidden = false;
}

function clearDecision() {
  for (const id of ['decision-goal', 'decision-power', 'decision-agreement', 'decision-stakes', 'decision-fallback']) $(id).value = '';
  $('decision-output').textContent = '';
  $('decision-output').hidden = true;
}

$('decision-check').addEventListener('click', decisionCheck);
$('decision-clear').addEventListener('click', clearDecision);

function jump(id) {
  if (!entries.some(entry => entry.id === id)) return;
  let card = $('entry-' + id);
  if (!card) { reset(false); card = $('entry-' + id); }
  card.querySelector('details').open = true;
  card.scrollIntoView({ behavior: 'smooth', block: 'start' });
}
function jumpFromHash() {
  if (location.hash.startsWith('#entry-')) jump(location.hash.slice(7));
}
$('list').addEventListener('click', event => {
  const link = event.target.closest('a[data-ref]');
  if (!link) return;
  // Modified clicks belong to the browser (new tab/window, download, etc.).
  if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
  event.preventDefault();
  const id = link.dataset.ref;
  if (!entries.some(entry => entry.id === id)) return;
  const url = new URL(location.href);
  url.hash = 'entry-' + id;
  // Keep the current query and filters in the previous history entry. If jump()
  // reveals a card outside the results, reset() updates only the new entry.
  try {
    if (url.href !== location.href) history.pushState(null, '', url.href);
  } catch (_) { location.hash = url.hash; }
  jump(id);
});
window.addEventListener('hashchange', jumpFromHash);
window.addEventListener('popstate', () => { restoreFilters(); render(false); jumpFromHash(); });
restoreFilters();
render();
jumpFromHash();
