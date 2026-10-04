#!/usr/bin/env python3
"""Validate canonical Markdown; build an offline searchable page and Skill snapshot."""
from pathlib import Path
import json
import re
import shutil
import html
from sources import load_sources

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = ['判断关键', '行动前准备', '何时换办法', '遇到的情况', '先做什么', '可以怎么说', '分情境处理', '花掉什么', '可能换回什么', '例外与代价', '依据', '相关条目']

def read_entries():
    entries, chapters = [], []
    for file in sorted((ROOT / 'book').glob('[0-9][0-9]-*.md')):
        source = file.read_text(encoding='utf-8')
        chapter = int(file.name[:2])
        chapter_title = source.splitlines()[0].removeprefix('# ')
        chapters.append({'number': chapter, 'title': chapter_title, 'file': file.name})
        parts = re.split(r'^### (\d+)\. (.+)$', source, flags=re.M)
        numbers = []
        for i in range(1, len(parts), 3):
            number, title, body = int(parts[i]), parts[i + 1], parts[i + 2]
            numbers.append(number)
            pairs = re.findall(r'^- ([^：\n]+)：(.+)$', body, re.M)
            fields = dict(pairs)
            if len(pairs) != len(fields):
                raise ValueError(f'{file.name} 第{number}条字段重复')
            missing = set(REQUIRED) - fields.keys()
            if missing or not any(key.startswith('如果') for key in fields):
                raise ValueError(f'{file.name} 第{number}条字段不完整：{missing}')
            tag_match = re.search(r'<!-- 标签: (.+?) -->', body)
            if not tag_match:
                raise ValueError(f'{file.name} 第{number}条缺少标签')
            tags = {}
            for pair in tag_match[1].split():
                key, value = pair.split('=', 1)
                tags[key] = re.split('[,，]', value)
            if set(tags) != {'场景', '对象', '主题'}:
                raise ValueError(f'{file.name} 第{number}条标签不完整')
            for key, values in tags.items():
                if any(not value.strip() for value in values) or len(values) != len(set(values)):
                    raise ValueError(f'{file.name} 第{number}条{key}标签为空或重复')
            entries.append({'id': f'{chapter}.{number}', 'chapter': chapter,
                'chapterTitle': chapter_title, 'title': title, 'fields': fields,
                'tags': tags, 'source': f'book/{file.name}'})
        if numbers != list(range(1, len(numbers) + 1)):
            raise ValueError(f'{file.name} 条号不连续')
    if [c['number'] for c in chapters] != list(range(1, len(chapters) + 1)):
        raise ValueError('章节编号不连续')
    if not entries:
        raise ValueError('没有正文')
    ids = {entry['id'] for entry in entries}
    if len(ids) != len(entries):
        raise ValueError('条目编号重复')
    for entry in entries:
        if not entry['fields']['依据'].startswith('经验建议。'):
            raise ValueError(f'{entry["id"]} 增加新依据类型后须更新页面依据展示')
        for target in re.findall(r'\b\d+\.\d+\b', entry['fields']['相关条目']):
            if target not in ids:
                raise ValueError(f'{entry["id"]} 引用了不存在的条目 {target}')
    return entries, chapters

PAGE = r'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>__NAME__</title>
<meta name="description" content="面向大学生和初入职场者的场景决策指南。先判断目标、关系与风险，再选择动作并根据反馈调整。">
<style>
:root{--ink:#242329;--muted:#777581;--purple:#5d58d6;--purple-dark:#4541b8;--purple-soft:#f2f1ff;--paper:#fff;--side:#f6f6f8;--surface:#fff;--line:#e4e3e8;--teal:#237b70;--top:52px;--side-width:270px}*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--paper);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;line-height:1.8}a{color:var(--purple-dark);text-underline-offset:4px}button,input,select{font:inherit}button,select{cursor:pointer}.appbar{position:fixed;z-index:30;inset:0 0 auto 0;height:var(--top);display:grid;grid-template-columns:var(--side-width) minmax(280px,520px) 1fr;align-items:center;gap:24px;padding:0 14px;background:#fff;border-bottom:1px solid var(--line)}.brand{display:flex;align-items:center;gap:9px;font-weight:720;color:var(--ink);text-decoration:none;white-space:nowrap}.mark{display:inline-grid;place-items:center;width:23px;height:23px;border-radius:5px;background:var(--purple);color:#fff;font-size:15px}.top-search{position:relative}.top-search input{width:100%;height:36px;padding:6px 42px 6px 36px;border:0;border-radius:8px;background:#f5f5f7;color:var(--ink)}.top-search::before{content:'⌕';position:absolute;left:13px;top:2px;color:var(--muted);font-size:21px}.top-search button{position:absolute;right:4px;top:4px;height:28px;padding:0 10px;background:transparent;color:var(--muted)}.navlinks{display:flex;justify-content:flex-end;gap:16px;white-space:nowrap;font-size:13px}.navlinks a{color:var(--muted);text-decoration:none}.navlinks a:hover{color:var(--purple)}.menu-button{display:none}.sidebar{position:fixed;z-index:20;left:0;top:var(--top);bottom:0;width:var(--side-width);padding:24px 16px 30px;background:var(--side);border-right:1px solid var(--line);overflow-y:auto}.side-title{margin:0 4px 10px;font-size:14px;font-weight:720}.chapter-nav{display:grid;gap:2px}.chapter-nav a{display:grid;grid-template-columns:1fr auto;gap:10px;padding:8px 9px;color:#55535d;text-decoration:none;font-size:13px;line-height:1.55;border-radius:6px}.chapter-nav a:hover{background:#ebeaf1;color:var(--purple-dark)}.chapter-nav a:first-child{color:var(--purple-dark);font-weight:700;border-bottom:1px solid var(--line);border-radius:0;margin-bottom:6px}.chapter-count{color:#97959f;font-variant-numeric:tabular-nums}.reader{width:min(100% - var(--side-width),980px);margin-left:max(var(--side-width),calc((100% - 980px + var(--side-width))/2));padding:calc(var(--top) + 36px) 42px 64px}.intro{padding-bottom:26px;border-bottom:1px solid var(--line)}.intro h1{font-size:36px;line-height:1.25;letter-spacing:0;margin:0 0 8px}.lead{font-size:16px;color:var(--muted);margin:0 0 14px}.stats{display:flex;gap:8px 24px;flex-wrap:wrap;color:#96949d;font-size:12px}.note{font-size:12px;color:var(--muted);margin:15px 0 0;max-width:820px}.decision-shell{margin:22px 0;border:1px solid var(--line);border-radius:7px;background:#fff}.decision-shell>summary{padding:12px 16px;font-size:13px;color:#55535d;font-weight:680;cursor:pointer}.decision{padding:6px 18px 20px;border-top:1px solid var(--line);background:var(--purple-soft)}.decision h2{font-size:20px;margin:14px 0 4px}.decision-intro{font-size:13px;color:var(--muted);margin:0 0 14px}.decision-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}.decision-grid label{font-size:13px;color:var(--muted)}.decision-grid input,.decision-grid select{display:block;width:100%;margin:5px 0 0;padding:9px 11px;border:1px solid #cbc8d5;border-radius:5px;background:white}.decision-actions{display:flex;gap:10px;margin-top:14px}.decision-actions button:first-child{background:var(--purple);color:#fff}.decision-output{margin:14px 0 0;padding:12px 14px;background:white;border-left:3px solid var(--teal);font-size:13px;white-space:pre-line}.toolbar{display:flex;justify-content:space-between;gap:14px;align-items:center;margin:20px 0 8px}.filters{display:flex;gap:8px;flex-wrap:wrap}.filters label{font-size:12px;color:var(--muted)}select{margin-left:5px;padding:6px 8px;border:1px solid var(--line);border-radius:5px;background:#fff;color:var(--ink);max-width:220px}button{border:0;background:var(--purple-soft);color:var(--purple-dark);border-radius:5px;padding:7px 11px;font-size:12px}.search-actions{display:flex;gap:8px}.resultline{display:flex;align-items:center;justify-content:space-between;gap:12px;color:var(--muted);font-size:12px;margin:10px 0 20px}.chapter-heading{display:flex;align-items:end;justify-content:space-between;gap:18px;padding:26px 0 14px;border-top:1px solid var(--line);scroll-margin-top:70px}.chapter-heading h2{font-size:25px;line-height:1.4;margin:0}.chapter-heading span{font-size:12px;color:#aaa8b0;white-space:nowrap}#list{display:block}.card{padding:24px 0 28px;border-top:1px solid #efeff2;scroll-margin-top:68px}.chapter-heading+.card{border-top:0;padding-top:8px}.cardhead{font-size:11px;color:#9a98a2;display:flex;justify-content:space-between;gap:8px}.card h2{font-size:21px;line-height:1.5;margin:8px 0}.card .scene{color:var(--muted);font-size:14px;margin:0 0 14px}.judgment,.action{font-size:14px;margin:0 0 15px}.judgment strong,.action strong,.example-label{display:inline;color:var(--ink);font-weight:720;margin-right:8px}.example-label{font-size:14px}blockquote{background:#f7f7f9;border-left:3px solid var(--purple);margin:8px 0 12px;padding:10px 13px;font-size:14px}.chips{display:flex;gap:6px;flex-wrap:wrap;margin:10px 0}.chip{font-size:11px;background:#f1f0f4;color:var(--muted);padding:2px 8px;border-radius:20px}summary{font-size:13px;color:var(--purple-dark);cursor:pointer;padding:8px 0}dl{font-size:13px;margin:10px 0}dt{color:var(--ink);font-weight:680;margin-top:16px}dd{margin:3px 0;color:#55525f;overflow-wrap:anywhere}.detail-group{margin:16px 0 0;padding-top:2px;border-top:1px solid var(--line)}.detail-group h3{font-size:14px;color:var(--purple-dark);margin:12px 0 4px}.detail-group dl{margin:0}.costs{display:grid;grid-template-columns:1fr 1fr;gap:10px}.costs section{background:#f6f6f8;padding:10px 12px}.costs strong{display:block;color:var(--purple-dark);font-size:13px}.costs span{font-size:13px;color:#55525f}.refs{margin-top:16px;padding-top:12px;border-top:1px solid var(--line);font-size:12px}.refs a{display:inline-block;margin-right:12px}.source{font-size:12px;color:var(--muted);margin-top:10px}.empty{padding:48px;text-align:center;border:1px dashed #bbb7c8}.guide{margin-top:42px;padding-top:24px;border-top:1px solid var(--line)}.guide h2{font-size:22px}.guide p{font-size:13px;color:var(--muted)}footer{margin-top:34px;padding-top:20px;border-top:1px solid var(--line);font-size:12px;color:var(--muted)}.card:target{background:#fcfbff;box-shadow:0 0 0 10px #fcfbff}noscript{display:block;padding:20px;background:#fff1db}input:focus,select:focus,button:focus-visible,summary:focus-visible,a:focus-visible{outline:3px solid #c7bfff;outline-offset:3px}#nav-toggle{position:fixed;opacity:0;pointer-events:none}.nav-scrim{display:none}@media(max-width:850px){:root{--side-width:260px}.appbar{grid-template-columns:auto 1fr auto;gap:10px;padding:0 12px}.menu-button{display:grid;place-items:center;width:30px;height:30px;font-size:20px;cursor:pointer}.appbar .brand .brand-text{display:none}.navlinks a:not(:last-child){display:none}.sidebar{transform:translateX(-100%);transition:transform .18s ease}.nav-scrim{display:block;position:fixed;z-index:15;inset:var(--top) 0 0;background:rgba(20,18,30,.25);opacity:0;pointer-events:none;transition:opacity .18s}.reader{width:100%;margin-left:0;padding:calc(var(--top) + 28px) 22px 54px}#nav-toggle:checked~.sidebar{transform:translateX(0)}#nav-toggle:checked~.nav-scrim{opacity:1;pointer-events:auto}.intro h1{font-size:32px}}@media(max-width:600px){.reader{padding-left:18px;padding-right:18px}.top-search input{padding-left:31px}.top-search::before{left:10px}.navlinks{font-size:11px}.toolbar{align-items:flex-start}.filters{display:grid;grid-template-columns:1fr 1fr;width:100%}.filters label{display:flex;align-items:center;justify-content:space-between}.filters select{width:72%;max-width:none}.search-actions{flex-direction:column}.decision-grid,.costs{grid-template-columns:1fr}.chapter-heading h2{font-size:22px}.card h2{font-size:19px}}@media print{.appbar,.sidebar,.nav-scrim,.toolbar,.decision-shell,#expand{display:none}.reader{width:auto;margin:0;padding:0}.card{break-inside:avoid}.card:target{box-shadow:none}}
.card{margin:0 0 16px;padding:20px 22px 18px;background:#f8f8fa;border:1px solid #dedde4;border-radius:12px}.chapter-heading+.card{border:1px solid #dedde4;padding:20px 22px 18px}.card:target{background:#fbfaff;box-shadow:0 0 0 3px #d9d5ff}.card .judgment{margin:14px 0;padding:11px 14px;background:#e9e7ff;border-left:3px solid var(--purple);border-radius:0 6px 6px 0}.card .judgment strong{display:block;margin:0 0 2px;color:var(--purple-dark)}.card blockquote{background:#fff;border-color:#8b84ec;border-radius:0 6px 6px 0}.card details{margin-top:14px;border-top:1px solid var(--line)}.card details>summary{padding-top:12px}.card .chips{margin-bottom:14px}.card .chip{background:#ececf1}.card .source{margin-bottom:2px}
@media(max-width:850px){.appbar{grid-template-columns:auto auto minmax(0,1fr) auto}}
@media(max-width:600px){.card,.chapter-heading+.card{padding:17px 16px 15px;border-radius:10px}}
</style></head><body>
<input id="nav-toggle" type="checkbox" aria-hidden="true"><header class="appbar"><label class="menu-button" for="nav-toggle" aria-label="打开章节目录">☰</label><a class="brand" href="index.html"><span class="mark" aria-hidden="true">✓</span><span class="brand-text">__NAME__</span></a><div class="top-search"><input id="query" type="search" placeholder="搜索场景" autocomplete="off" aria-label="搜索场景"><button id="search-submit" type="button" aria-label="开始搜索">搜索</button></div><nav class="navlinks"><a href="阅读全文.html">连续阅读</a><a href="downloads/低内耗社交指南.pdf" download>下载 PDF</a><a href="about.html">项目说明</a></nav></header><label class="nav-scrim" for="nav-toggle" aria-hidden="true"></label><aside class="sidebar"><p class="side-title">章节</p><nav class="chapter-nav" aria-label="章节目录">__CHAPTER_NAV__</nav></aside>
<main class="reader" id="results"><section class="intro"><h1>__NAME__</h1><p class="lead">__POSITIONING__</p><div class="stats"><span>__CHAPTERS__ 章</span><span>__COUNT__ 个场景</span><span>V__VERSION__</span><span>支持离线检索</span></div><p class="note">每条包含判断、准备、做法、表达示例、代价与调整信号。示例可以调整，对方也有拒绝的空间。</p><p class="note"><strong>免责声明：仅供参考。</strong> __DISCLAIMER__</p></section><details class="decision-shell"><summary>先做一张 30 秒决策卡</summary><section class="decision" aria-labelledby="decision-title"><h2 id="decision-title">30 秒决策检查</h2><p class="decision-intro">这里不会替你评分，也不会保存输入，只整理会改变选择的事实。</p><div class="decision-grid"><label for="decision-goal">这次最想推进什么？<input id="decision-goal" type="text" maxlength="160" placeholder="例如：拒绝继续代做，同时保留正常合作"></label><label for="decision-power">关系与权力<select id="decision-power"><option value="">请选择</option><option>双方大致平等</option><option>对方掌握评价、资源或机会</option><option>我掌握主要资源或决定权</option><option>暂时不清楚</option></select></label><label for="decision-agreement">已有约定<select id="decision-agreement"><option value="">请选择</option><option>已有明确约定</option><option>只有口头或模糊约定</option><option>没有约定</option><option>暂时不清楚</option></select></label><label for="decision-stakes">现实后果<select id="decision-stakes"><option value="">请选择</option><option>主要是短暂尴尬或失望</option><option>可能影响时间、金钱、学业或工作</option><option>涉及安全、隐私、合同或正式纪律</option><option>暂时不清楚</option></select></label><label for="decision-fallback">如果对方不配合，我还有什么选择？<input id="decision-fallback" type="text" maxlength="160" placeholder="例如：缩小范围、换负责人、暂停参与"></label></div><div class="decision-actions"><button id="decision-check" type="button">生成检查结果</button><button id="decision-clear" type="button">清除</button></div><p id="decision-output" class="decision-output" role="status" aria-live="polite" hidden></p></section></details><section class="toolbar" aria-label="筛选场景"><div class="filters"><label for="chapter">章节<select id="chapter"><option value="">全部章节</option></select></label><label for="topic">主题<select id="topic"><option value="">全部主题</option></select></label><label for="person">对象<select id="person"><option value="">全部对象</option></select></label></div><div class="search-actions"><button id="reset" type="button">清除筛选</button></div></section><div class="resultline"><span id="count" role="status" aria-live="polite"></span><button id="expand" type="button">展开全部细节</button></div><noscript>阅读页需要启用 JavaScript。也可以直接打开 <a href="阅读全文.html">连续阅读版</a> 阅读全部正文。</noscript><section id="list" aria-label="建议条目"></section><section class="guide"><h2>怎么用这份指南</h2><p>想练习一次交流？<a href="docs/practice.html">打开决策卡、反馈卡与场景练习</a>。</p><p>先整理目标、关系、已有约定、现实后果与替代方案，再找相近场景。先看“一句话判断”“第一步”和“表达参考”，需要时再展开完整依据与回应分支。</p><p><a href="docs/editorial-guide.html">编写与纠错规范</a> · <a href="docs/sources.html">选题来源与限制</a> · <a href="docs/research-notes.html">研究资料</a> · <a href="docs/platform-notes.html">平台素材</a></p></section><footer>V__VERSION__ · __DATE__ · __CHAPTERS__ 章 __COUNT__ 条 · 根据自己的情况选择，不用全部做到。<br>__REFERENCE_NOTE__</footer></main>
<script id="entries" type="application/json">__DATA__</script>
<script>__SEARCH_SCRIPT__
</script></body></html>'''

# Keep the reader shell compact above, then layer the public-facing landing
# modules here so the original hero and tools remain explicit and editable.
PAGE = PAGE.replace(
    '--purple:#5d58d6;--purple-dark:#4541b8;--purple-soft:#f2f1ff;',
    '--purple:#654bff;--purple-dark:#4b34df;--purple-soft:#f0edff;',
)
PAGE = PAGE.replace(
    '<div class="top-search"><input id="query" type="search" placeholder="搜索场景" autocomplete="off" aria-label="搜索场景"><button id="search-submit" type="button" aria-label="开始搜索">搜索</button></div><nav class="navlinks"><a href="阅读全文.html">连续阅读</a><a href="downloads/低内耗社交指南.pdf" download>下载 PDF</a><a href="about.html">项目说明</a></nav>',
    '<div class="top-search"><input id="top-query" type="search" placeholder="搜索场景" autocomplete="off" aria-label="搜索场景"><button id="top-search-submit" type="button" aria-label="开始搜索">搜索</button></div><nav class="navlinks"><a href="阅读全文.html">阅读全文 ↗</a><a href="downloads/低内耗社交指南.pdf" download>下载 PDF</a><a href="docs/practice.html">场景练习</a><a href="about.html">项目说明 ↗</a></nav>',
)
PAGE = PAGE.replace(
    '<section class="intro"><h1>__NAME__</h1><p class="lead">__POSITIONING__</p><div class="stats"><span>__CHAPTERS__ 章</span><span>__COUNT__ 个场景</span><span>V__VERSION__</span><span>支持离线检索</span></div><p class="note">每条包含判断、准备、做法、表达示例、代价与调整信号。示例可以调整，对方也有拒绝的空间。</p><p class="note"><strong>免责声明：仅供参考。</strong> __DISCLAIMER__</p></section>',
    '<section class="intro"><div class="eyebrow">LOW-FRICTION SOCIAL GUIDE</div><h1><span>低内耗</span>社交指南</h1><p class="lead">__POSITIONING__</p><div class="hero-actions"><a class="primary-link" href="#finder">查找我的场景 →</a><a class="secondary-link" href="阅读全文.html">浏览全部内容</a></div><div class="stats"><span>__CHAPTERS__ 章</span><span>__COUNT__ 个场景</span><span>V__VERSION__</span><span>支持离线检索</span></div><p class="note">每条包含判断、准备、做法、表达示例、代价与调整信号。示例可以调整，对方也有拒绝的空间。</p><p class="note"><strong>免责声明：仅供参考。</strong> __DISCLAIMER__</p></section>',
)
PAGE = PAGE.replace(
    '<details class="decision-shell"><summary>先做一张 30 秒决策卡</summary>',
    '<details class="decision-shell" open><summary>先判断，再行动</summary>',
)
PAGE = PAGE.replace(
    '<section class="toolbar" aria-label="筛选场景"><div class="filters"><label for="chapter">章节<select id="chapter"><option value="">全部章节</option></select></label><label for="topic">主题<select id="topic"><option value="">全部主题</option></select></label><label for="person">对象<select id="person"><option value="">全部对象</option></select></label></div><div class="search-actions"><button id="reset" type="button">清除筛选</button></div></section>',
    '<section id="finder" class="finder-panel" aria-labelledby="finder-title"><div class="section-kicker">按问题找答案</div><h2 id="finder-title">你遇到了什么？</h2><label class="query-label" for="query">描述具体场景</label><input id="query" type="search" maxlength="200" placeholder="试试：内推、借钱、送礼、被批评、离职……" autocomplete="off"><div class="toolbar" aria-label="筛选场景"><div class="filters"><label for="chapter">章节<select id="chapter"><option value="">全部章节</option></select></label><label for="topic">主题<select id="topic"><option value="">全部主题</option></select></label><label for="person">对象<select id="person"><option value="">全部对象</option></select></label></div><div class="search-actions"><button id="search-submit" type="button">搜索</button><button id="reset" type="button">清除筛选</button></div></div></section>',
)

PAGE_STYLE_ADDITIONS = r'''
.intro{padding:34px 0 32px}
.eyebrow{color:var(--purple);font-size:12px;font-weight:760;letter-spacing:.16em}
.intro h1{font-size:58px;line-height:1.08;margin:15px 0 18px}
.intro h1 span{color:var(--purple)}
.intro .lead{font-size:18px;color:#3f3d47;margin-bottom:26px}
.hero-actions{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:24px}
.hero-actions a{display:inline-flex;align-items:center;justify-content:center;min-height:46px;padding:9px 20px;border-radius:999px;text-decoration:none;font-size:14px;font-weight:720}
.primary-link{background:var(--purple);color:#fff}
.primary-link:hover{background:var(--purple-dark);color:#fff}
.secondary-link{border:1px solid var(--line);background:#fff;color:var(--ink)}
.decision-shell{overflow:hidden;border-color:#d8d3ff;background:var(--purple-soft)}
.decision-shell>summary{padding:14px 18px;color:var(--purple-dark)}
.decision-shell[open]>summary{border-bottom:1px solid #d8d3ff}
.decision{border-top:0;padding:10px 22px 22px}
.finder-panel{margin:22px 0;padding:22px 24px 18px;border:1px solid var(--line);border-radius:10px;background:#fff;scroll-margin-top:68px}
.section-kicker{color:var(--purple);font-size:12px;font-weight:720}
.finder-panel h2{font-size:22px;line-height:1.4;margin:6px 0 10px}
.query-label{display:block;color:var(--muted);font-size:12px;margin-bottom:5px}
.finder-panel>input{display:block;width:100%;height:48px;padding:9px 14px;border:1px solid #cbc8d5;border-radius:6px;background:#fff;color:var(--ink)}
.finder-panel .toolbar{margin:12px 0 0;align-items:flex-end}
.finder-panel .search-actions button:first-child{background:var(--purple);color:#fff}
.chapter-nav>a:first-child{color:var(--purple-dark);font-weight:700;border-bottom:1px solid var(--line);border-radius:0;margin-bottom:6px}
.chapter-group{border-bottom:1px solid #e9e8ed}
.chapter-group>summary{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:8px;align-items:start;padding:9px;color:#55535d;font-size:13px;line-height:1.55;list-style:none}
.chapter-group>summary::-webkit-details-marker{display:none}
.chapter-group>summary::after{content:'›';grid-column:3;color:#9a98a2;font-size:17px;line-height:1.2;transform:rotate(0deg);transition:transform .15s ease}
.chapter-group[open]>summary::after{transform:rotate(90deg)}
.chapter-group>summary:hover{background:#ebeaf1;color:var(--purple-dark)}
.chapter-subnav{display:grid;padding:0 0 8px 13px}
.chapter-subnav a,.chapter-subnav a:first-child{display:grid;grid-template-columns:30px minmax(0,1fr);gap:5px;padding:5px 9px;color:#66636d;font-weight:400;font-size:12px;line-height:1.45;border:0;border-radius:5px;margin:0;text-decoration:none}
.chapter-subnav a:hover{background:#ebeaf1;color:var(--purple-dark)}
.entry-number{color:#aaa7b0;font-variant-numeric:tabular-nums}
.entry-title{display:-webkit-box;overflow:hidden;-webkit-box-orient:vertical;-webkit-line-clamp:2}
@media(max-width:1050px){.navlinks{gap:11px;font-size:12px}.appbar{gap:14px}}
@media(max-width:850px){.navlinks{display:none}.intro h1{font-size:48px}}
@media(max-width:600px){.intro{padding-top:18px}.intro h1{font-size:40px}.intro .lead{font-size:16px}.finder-panel{padding:18px 16px}.finder-panel .toolbar{display:block}.finder-panel .filters{margin-bottom:12px}.finder-panel .search-actions{flex-direction:row}}
'''
PAGE = PAGE.replace('</style>', PAGE_STYLE_ADDITIONS + '</style>', 1)

def main():
    entries, chapters = read_entries()
    meta = json.loads((ROOT / 'project.json').read_text(encoding='utf-8'))
    data = json.dumps(entries, ensure_ascii=False).replace('<', '\\u003c')
    chapter_counts = {chapter['number']: sum(entry['chapter'] == chapter['number'] for entry in entries)
                      for chapter in chapters}
    chapter_nav = (f'<a href="index.html#results"><span>全部章节</span>'
                   f'<span class="chapter-count">{len(entries)}</span></a>')
    for chapter_index, chapter in enumerate(chapters):
        title = re.sub(r'^\d+\.\s*', '', chapter['title'])
        number = chapter['number']
        chapter_entries = [entry for entry in entries if entry['chapter'] == number]
        subnav = ''.join(
            f'<a href="index.html#entry-{entry["id"]}"><span class="entry-number">{entry["id"]}</span>'
            f'<span class="entry-title">{html.escape(entry["title"])}</span></a>'
            for entry in chapter_entries
        )
        chapter_nav += (
            f'<details class="chapter-group"{" open" if chapter_index == 0 else ""}>'
            f'<summary><span>{number}. {html.escape(title)}</span>'
            f'<span class="chapter-count">{chapter_counts[number]}</span></summary>'
            f'<div class="chapter-subnav">{subnav}</div></details>'
        )
    page = PAGE.replace('__DATA__', data).replace('__COUNT__', str(len(entries))).replace('__CHAPTERS__', str(len(chapters)))
    page = page.replace('__NAME__', html.escape(meta['name']))
    page = page.replace('__POSITIONING__', html.escape(meta['positioning']))
    page = page.replace('__VERSION__', html.escape(meta['version']))
    page = page.replace('__DATE__', html.escape(meta['date']))
    page = page.replace('__DISCLAIMER__', html.escape(meta['disclaimer']))
    page = page.replace('__CHAPTER_NAV__', chapter_nav)
    page = page.replace('__REFERENCE_NOTE__', html.escape(meta['reference_note']))
    page = page.replace('__SEARCH_SCRIPT__', (ROOT / 'tools/search.js').read_text(encoding='utf-8'))
    (ROOT / 'index.html').write_text(page, encoding='utf-8')
    download_page = f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>下载 HTML · {html.escape(meta['name'])}</title><style>:root{{--purple:#654bff;--ink:#17161d;--muted:#6f6d7a;--paper:#f5f5f8;--line:#e3e1ea}}*{{box-sizing:border-box}}body{{max-width:700px;margin:64px auto;padding:0 24px;background:var(--paper);color:var(--ink);font:16px/1.9 -apple-system,"PingFang SC",sans-serif}}a{{color:#4b34df}}.download{{display:inline-block;padding:11px 22px;background:var(--purple);color:white;border-radius:999px;text-decoration:none;font-weight:700}}.reference{{margin-top:48px;padding-top:18px;border-top:1px solid var(--line);color:var(--muted);font-size:13px}}</style></head><body><p style="color:#654bff;font-size:12px;font-weight:700;letter-spacing:.12em">LOW-FRICTION SOCIAL GUIDE</p><h1>下载 HTML 检索页</h1><p>下载的是项目文件夹里的 index.html。保存后，用浏览器打开即可离线搜索和查看全部条目。</p><p><a id="download" class="download" href="../index.html" download="index.html">下载 index.html</a></p><p>正在开始下载。如果浏览器没有自动下载，请点击上面的按钮。</p><p>其他阅读页和资料需要配套文件。需要完整离线使用，请保留整个项目文件夹。</p><p><a href="../index.html">返回检索页</a></p><p class="reference">{html.escape(meta['reference_note'])}</p><script>document.getElementById('download').click();</script></body></html>'''
    (ROOT / 'downloads').mkdir(exist_ok=True)
    (ROOT / 'downloads/html.html').write_text(download_page, encoding='utf-8')
    refs = ROOT / 'skills/low-friction-social-guide/references'
    target = refs / 'book'
    target.mkdir(parents=True, exist_ok=True)
    for old in target.glob('*.md'):
        old.unlink()
    for chapter in chapters:
        shutil.copyfile(ROOT / 'book' / chapter['file'], target / chapter['file'])
    toc = f'# 正文目录\n\n版本：V{meta["version"]}；快照日期：{meta["date"]}；全部为经验建议。\n\n'
    toc += '**免责声明：仅供参考。** ' + meta['disclaimer'] + '\n\n'
    toc += '\n'.join(f'- [{c["title"]}](book/{c["file"]})' for c in chapters) + '\n'
    practice = (ROOT / 'docs/交流复盘与场景练习.md').read_text(encoding='utf-8')
    shutil.copyfile(ROOT / 'docs/交流复盘与场景练习.md', refs / '交流复盘与场景练习.md')
    toc += '\n- [附录：交流复盘与场景练习](交流复盘与场景练习.md)\n'
    toc += '\n- [Morris 来源笔记](Morris账号公开内容学习笔记.md)\n- [v1.4 整合记录](v1.4整合记录.md)\n'
    (refs / '目录.md').write_text(toc, encoding='utf-8')
    (refs / 'Morris账号公开内容学习笔记.md').write_text((ROOT / 'docs/Morris账号整理/学习笔记.md').read_text(encoding='utf-8'), encoding='utf-8')
    (refs / 'v1.4整合记录.md').write_text((ROOT / 'docs/核实记录/v1.4说明.md').read_text(encoding='utf-8').replace('../Morris账号整理/学习笔记.md', 'Morris账号公开内容学习笔记.md'), encoding='utf-8')
    shutil.copyfile(ROOT / 'docs/访谈与博客学习笔记.md', refs / '访谈与博客学习笔记.md')
    (refs / '访谈与博客学习笔记.md').write_text((refs / '访谈与博客学习笔记.md').read_text(encoding='utf-8').replace('核实记录/v1.6说明.md', 'v1.6整合记录.md'), encoding='utf-8')
    (refs / 'v1.6整合记录.md').write_text((ROOT / 'docs/核实记录/v1.6说明.md').read_text(encoding='utf-8').replace('../访谈与博客学习笔记.md', '访谈与博客学习笔记.md'), encoding='utf-8')
    with (refs / '目录.md').open('a', encoding='utf-8') as stream:
        stream.write('\n- [访谈与博客学习笔记](访谈与博客学习笔记.md)\n- [v1.6 整合记录](v1.6整合记录.md)\n')
    shutil.copyfile(ROOT / 'docs/核实记录/v1.7说明.md', refs / 'v1.7整合记录.md')
    with (refs / '目录.md').open('a', encoding='utf-8') as stream:
        stream.write('\n- [v1.7 敬酒表达整合记录](v1.7整合记录.md)\n')
    shutil.copyfile(ROOT / 'docs/核实记录/v1.8说明.md', refs / 'v1.8整合记录.md')
    with (refs / '目录.md').open('a', encoding='utf-8') as stream:
        stream.write('\n- [v1.8 场面话整合记录](v1.8整合记录.md)\n')
    shutil.copyfile(ROOT / 'docs/核实记录/v1.9说明.md', refs / 'v1.9整合记录.md')
    with (refs / '目录.md').open('a', encoding='utf-8') as stream:
        stream.write('\n- [v1.9 表达顺序整合记录](v1.9整合记录.md)\n')
    shutil.copyfile(ROOT / 'docs/核实记录/v1.10说明.md', refs / 'v1.10整合记录.md')
    with (refs / '目录.md').open('a', encoding='utf-8') as stream:
        stream.write('\n- [v1.10 社交摘要整合记录](v1.10整合记录.md)\n')
    shutil.copyfile(ROOT / 'docs/核实记录/v1.11说明.md', refs / 'v1.11整合记录.md')
    with (refs / '目录.md').open('a', encoding='utf-8') as stream:
        stream.write('\n- [v1.11 识人技巧整合记录](v1.11整合记录.md)\n')
    shutil.copyfile(ROOT / 'docs/核实记录/v1.12说明.md', refs / 'v1.12整合记录.md')
    with (refs / '目录.md').open('a', encoding='utf-8') as stream:
        stream.write('\n- [v1.12 平和回应整合记录](v1.12整合记录.md)\n')
    shutil.copyfile(ROOT / 'docs/核实记录/v1.13说明.md', refs / 'v1.13整合记录.md')
    with (refs / '目录.md').open('a', encoding='utf-8') as stream:
        stream.write('\n- [v1.13 回应夸奖新增记录](v1.13整合记录.md)\n')
    shutil.copyfile(ROOT / 'docs/核实记录/v1.14说明.md', refs / 'v1.14整合记录.md')
    with (refs / '目录.md').open('a', encoding='utf-8') as stream:
        stream.write('\n- [v1.14 十章情境深化记录](v1.14整合记录.md)\n')
    shutil.copyfile(ROOT / 'docs/核实记录/v1.14.1说明.md', refs / 'v1.14.1整合记录.md')
    with (refs / '目录.md').open('a', encoding='utf-8') as stream:
        stream.write('\n- [v1.14.1 检索与跳转修复记录](v1.14.1整合记录.md)\n')
    shutil.copyfile(ROOT / 'docs/编写规范.md', refs / '编写规范.md')
    (refs / '研究资料整理.md').write_text((ROOT / 'docs/研究资料整理.md').read_text(encoding='utf-8').replace('核实记录/v1.15说明.md', 'v1.15整合记录.md').replace('](editorial-guide.md)', '](编写规范.md)'), encoding='utf-8')
    (refs / 'v1.15整合记录.md').write_text((ROOT / 'docs/核实记录/v1.15说明.md').read_text(encoding='utf-8').replace('../研究资料整理.md', '研究资料整理.md'), encoding='utf-8')
    with (refs / '目录.md').open('a', encoding='utf-8') as stream:
        stream.write('\n- [编写与纠错规范](编写规范.md)\n- [论文与文章资料笔记](研究资料整理.md)\n- [v1.15 论文与文章整合记录](v1.15整合记录.md)\n')
    (refs / '平台素材收集-2026-10-04.md').write_text((ROOT / 'docs/平台素材收集-2026-10-04.md').read_text(encoding='utf-8').replace('核实记录/v1.16说明.md', 'v1.16整合记录.md'), encoding='utf-8')
    (refs / '章节扩充资料-2026-10-04.md').write_text((ROOT / 'docs/章节扩充资料-2026-10-04.md').read_text(encoding='utf-8').replace('核实记录/v1.17说明.md', 'v1.17整合记录.md'), encoding='utf-8')
    with (refs / '目录.md').open('a', encoding='utf-8') as stream:
        stream.write('\n- [短视频与网络文章候选素材](平台素材收集-2026-10-04.md)\n')
    (refs / 'v1.16整合记录.md').write_text((ROOT / 'docs/核实记录/v1.16说明.md').read_text(encoding='utf-8').replace('../平台素材收集-2026-10-04.md', '平台素材收集-2026-10-04.md'), encoding='utf-8')
    with (refs / '目录.md').open('a', encoding='utf-8') as stream:
        stream.write('\n- [v1.16 平台素材整合记录](v1.16整合记录.md)\n')
    (refs / 'v1.17整合记录.md').write_text((ROOT / 'docs/核实记录/v1.17说明.md').read_text(encoding='utf-8').replace('../章节扩充资料-2026-10-04.md', '章节扩充资料-2026-10-04.md').replace('../../阅读全文.html', '目录.md'), encoding='utf-8')
    with (refs / '目录.md').open('a', encoding='utf-8') as stream:
        stream.write('\n- [章节扩充资料](章节扩充资料-2026-10-04.md)\n- [v1.17 章节扩充整合记录](v1.17整合记录.md)\n')
    build_revision = meta.get('build_revision', meta['version'])
    if build_revision != '1.17':
        current_record = ROOT / f'docs/核实记录/v{build_revision}说明.md'
        current_snapshot = f'v{build_revision}整合记录.md'
        shutil.copyfile(current_record, refs / current_snapshot)
        with (refs / '目录.md').open('a', encoding='utf-8') as stream:
            stream.write(f'\n- [内部构建 v{build_revision} 记录]({current_snapshot})\n')
    full = f'# {meta["name"]}\n\n{meta["positioning"]}\n\nV{meta["version"]} · {meta["date"]} · {len(chapters)} 章 {len(entries)} 条\n\n'
    full += '先确认事实、目标、关系与风险，再做准备、选择行动，最后根据真实反馈调整。判断框架受《孙子兵法》的权衡、准备与因情境调整思路启发，生活建议仍是本项目的经验建议，未验证效果。\n\n'
    full += '**免责声明：仅供参考。** ' + meta['disclaimer'] + '\n\n'
    full += '本版全部为经验建议。示例表达可以调整，效果取决于关系和环境；涉及具体制度请查适用规则。\n\n'
    full += '\n\n'.join((ROOT / 'book' / c['file']).read_text(encoding='utf-8') for c in chapters)
    full += '\n\n' + practice
    sources = load_sources()
    referenced = set(re.findall(r'\b[SRPA]\d{2}\b', full))
    selected_sources = [item for item in sources if item['id'] in referenced]
    if referenced - {item['id'] for item in selected_sources}:
        raise ValueError('正文来源编号缺少索引')
    source_index = '# 来源索引\n\n以下来源编号对应正文中的选题、实践借鉴与有限研究背景。S 为原帖、R 为访谈、博客与平台配文、P 为论文或更正、A 为机构文章或通知。论文的对象、结论与局限见配套资料笔记；来源不证明整条建议或具体话术有效，取得状态与核实日期逐项记录。\n\n'
    for item in selected_sources:
        source_index += f'## {item["id"]}. {item["title"]}\n\n' + (item.get('citation', '') + '\n\n' if item.get('citation') else '') + f'来源日期：{item["date"]} · {item["status"]}。\n\n[查看来源]({item["url"]})\n\n'
    full += '\n\n' + source_index
    full += '\n# 参考说明\n\n' + meta['reference_note'] + '\n'
    (refs / '来源索引.md').write_text(source_index, encoding='utf-8')
    with (refs / '目录.md').open('a', encoding='utf-8') as stream:
        stream.write('\n- [来源索引](来源索引.md)\n')
    (ROOT / '完整指南.md').write_text(full.rstrip() + '\n', encoding='utf-8')
    body = '<h1>' + html.escape(meta['name']) + '</h1><p>' + html.escape(meta['positioning']) + '</p>'
    body += f'<p class="muted">V{meta["version"]} · {meta["date"]} · {len(chapters)} 章 {len(entries)} 条 · 全部为经验建议</p>'
    body += '<p><strong>免责声明：仅供参考。</strong> ' + html.escape(meta['disclaimer']) + '</p>'
    body += '<p>示例表达可以调整，效果取决于关系和环境。完整阅读情境、代价和例外后再决定；具体制度请查适用规则。</p>'
    body += '<p>先判断目标与条件，再做准备、选择行动，根据反馈调整。框架受《孙子兵法》启发，古文不是这些生活建议有效的证明。<a href="docs/strategy-notes.html">查看来源与转译边界</a>。</p>'
    body += '<p><a href="docs/Morris账号整理/阅读笔记.html">Morris 来源笔记</a> · <a href="docs/interview-notes.html">访谈与博客笔记</a> · <a href="docs/research-notes.html">论文与文章资料</a> · <a href="docs/verification.html">查看本次整合记录</a>；正文补充仍为经验建议。</p>'
    body += '<nav><a href="index.html">返回检索页</a> · <a href="downloads/低内耗社交指南.pdf" download>下载 PDF</a> · <a href="完整指南.md" download>下载完整正文</a> · <a href="docs/practice.html">场景练习</a> · <button onclick="window.print()">打印 / 保存为 PDF</button></nav><h2>目录</h2><ol>'
    body += ''.join(f'<li><a href="#chapter-{c["number"]}">{html.escape(c["title"])}</a></li>' for c in chapters) + '</ol><p><a href="#practice">附录：交流复盘与场景练习</a> · <a href="#sources">来源索引</a></p>'
    for chapter in chapters:
        body += f'<h2 class="chapter" id="chapter-{chapter["number"]}">{html.escape(chapter["title"])}</h2>'
        for entry in [e for e in entries if e['chapter'] == chapter['number']]:
            body += f'<article id="entry-{entry["id"]}"><h3>{entry["id"]} {html.escape(entry["title"])}</h3><dl>'
            for key, value in entry['fields'].items():
                escaped = html.escape(value)
                if key == '相关条目':
                    escaped = re.sub(r'(\d+\.\d+)（([^）]+)）', r'<a href="#entry-\1">\1（\2）</a>', escaped)
                elif key == '可以怎么说':
                    escaped = re.sub(r'(（示例仅供参考，请根据事实情况调整。）)(?=.)', r'\1<br><br>', escaped)
                elif key == '依据':
                    escaped = re.sub(r'\b([SRPA]\d{2})\b', r'<a href="#source-\1">\1</a>', escaped)
                body += '<dt>' + html.escape(key) + '</dt><dd' + (' class="example"' if key == '可以怎么说' else '') + '>' + escaped + '</dd>'
            body += '</dl></article>'
    body += '<section id="practice" class="chapter">'
    for block in practice.strip().split('\n\n'):
        block = block.strip()
        if block.startswith('# '):
            body += '<h2>' + html.escape(block[2:]) + '</h2>'
        elif block.startswith('## '):
            body += '<h3>' + html.escape(block[3:]) + '</h3>'
        elif all(line.startswith('- ') for line in block.splitlines()):
            body += '<ul>' + ''.join('<li>' + html.escape(line[2:]) + '</li>' for line in block.splitlines()) + '</ul>'
        elif block.startswith('原创示例：'):
            body += '<h4>表达示例</h4><p class="example">' + html.escape(block.removeprefix('原创示例：')) + '</p>'
        else:
            body += '<p>' + html.escape(block).replace('\n', '<br>') + '</p>'
    body += '</section><section id="sources" class="chapter"><h2>来源索引</h2><p>S 为原帖，R 为访谈、博客与平台配文，P 为论文、评论或更正，A 为机构文章或通知。来源提供选题、实践借鉴或限定范围的研究背景，不验证整条建议或具体话术。</p>'
    for item in selected_sources:
        body += '<h3 id="source-' + item['id'] + '">' + html.escape(item['id'] + ' ' + item['title']) + '</h3><p>' + html.escape((item.get('citation', '') + ' · ' if item.get('citation') else '') + item['date'] + ' · ' + item['status']) + ' · <a href="' + html.escape(item['url'], quote=True) + '">查看来源</a></p>'
    body += '</section><section id="reference" class="chapter"><h2>参考说明</h2><p>' + html.escape(meta['reference_note']) + '</p></section>'
    css = ':root{--ink:#17161d;--muted:#6f6d7a;--purple:#654bff;--purple-dark:#4b34df;--purple-soft:#f0edff;--paper:#f5f5f8;--surface:#fff;--line:#e3e1ea}*{box-sizing:border-box}html{scroll-behavior:smooth}body{max-width:880px;margin:0 auto;padding:42px 26px 70px;background:var(--paper);color:var(--ink);font:16px/1.9 -apple-system,"PingFang SC",sans-serif;overflow-wrap:anywhere}h1{font-size:42px;line-height:1.25;letter-spacing:0;margin:0 0 18px}h2{margin-top:54px;padding-top:16px;border-top:1px solid var(--line)}h3{font-size:22px;line-height:1.5;margin-top:34px}h4{font-size:16px;color:var(--purple-dark);margin:20px 0 8px}a{color:var(--purple-dark);text-underline-offset:4px}nav{display:flex;gap:8px 16px;flex-wrap:wrap;margin:28px 0;padding:16px 0;border-top:1px solid var(--line);border-bottom:1px solid var(--line)}nav,button{font:inherit}button{cursor:pointer;border:0;border-radius:6px;background:var(--purple-soft);color:var(--purple-dark);padding:4px 9px}article{background:var(--surface);border:1px solid var(--line);border-radius:8px;padding:22px 24px;margin:24px 0;scroll-margin-top:20px}article h3{margin-top:0}dt{font-size:16px;color:var(--purple-dark);font-weight:680;margin-top:22px}dd{margin:8px 0 0;color:#55525f;overflow-wrap:anywhere}.example{background:var(--purple-soft);border-left:3px solid var(--purple);border-radius:0 6px 6px 0;padding:10px 13px;max-width:100%}#practice p,#practice ul{margin:12px 0}#practice .example{margin-top:8px}.muted{color:var(--muted)}@media(max-width:600px){body{padding:28px 16px 54px}h1{font-size:32px}h2{font-size:24px}h3{font-size:20px}article{padding:18px}.example{padding:9px 11px}}@media print{body{background:white;margin:0;font-size:11pt}nav{display:none}.chapter{break-before:page}article{border:0;padding:0}.chapter,h3,dt{break-after:avoid}dd{orphans:3;widows:3}a{color:inherit;text-decoration:none}}'
    (ROOT / '阅读全文.html').write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>' + html.escape(meta['name']) + ' · 完整阅读</title><style>' + css + '</style><body>' + body + '</body></html>', encoding='utf-8')
    # ASCII-path copies keep GitHub entry points accessible; Chinese files remain the source.
    for source, destination in {
        '交流复盘与场景练习.md': 'practice.md',
        '编写规范.md': 'editorial-guide.md',
        f'核实记录/v{build_revision}说明.md': 'verification.md',
    }.items():
        text = (ROOT / 'docs' / source).read_text(encoding='utf-8')
        if '/' in source:
            text = text.replace('](../', '](./')
        (ROOT / 'docs' / destination).write_text(text, encoding='utf-8')
    print(f'已检查 {len(chapters)} 章 {len(entries)} 条及交叉引用；生成检索页、连续阅读页、完整正文，同步 Skill 正文快照。')

if __name__ == '__main__':
    main()
