#!/usr/bin/env python3
"""Build offline HTML reading pages for the project's supporting Markdown docs."""
from __future__ import annotations

import html
import hashlib
import json
import os
from pathlib import Path
import re
from urllib.parse import quote, unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
REPO = 'https://github.com/kkk-bot/HowToGetAlong'
SITE = 'https://kkk-bot.github.io/HowToGetAlong/'

# The ASCII Markdown copies are synchronized by tools/build.py before this runs.
PAGES = {
    'README.md': 'about.html',
    'docs/practice.md': 'docs/practice.html',
    'docs/verification.md': 'docs/verification.html',
    'docs/editorial-guide.md': 'docs/editorial-guide.html',
    'docs/使用指南.md': 'docs/usage.html',
    'docs/平台调研.md': 'docs/sources.html',
    'docs/孙子兵法学习笔记.md': 'docs/strategy-notes.html',
    'docs/访谈与博客学习笔记.md': 'docs/interview-notes.html',
    'docs/研究资料整理.md': 'docs/research-notes.html',
    'docs/平台素材收集-2026-10-04.md': 'docs/platform-notes.html',
    'docs/章节扩充资料-2026-10-04.md': 'docs/chapter-materials.html',
}
# Each historical record keeps its own content and URL, including in the ZIP.
PAGES.update({file.relative_to(ROOT).as_posix(): f'docs/history/{file.stem}.html'
              for file in sorted((ROOT / 'docs/核实记录').glob('*.md'))})
ALIASES = {
    'docs/交流复盘与场景练习.md': 'docs/practice.html',
    'docs/编写规范.md': 'docs/editorial-guide.html',
    'docs/Morris账号整理/学习笔记.md': 'docs/Morris账号整理/阅读笔记.html',
    '完整指南.md': '阅读全文.html',
}

CSS = '''
:root{--paper:#f5f5f8;--surface:#fff;--ink:#17161d;--purple:#654bff;--purple-dark:#4b34df;--purple-soft:#f0edff;--muted:#6f6d7a;--line:#e3e1ea;--teal:#237b70}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--paper);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;font-size:16px;line-height:1.9;overflow-wrap:anywhere}
header,main,footer{width:min(100%,880px);margin:auto;padding:0 28px}header{padding-top:22px}.top{display:flex;align-items:center;justify-content:space-between;gap:16px;padding-bottom:18px;border-bottom:1px solid var(--line);font-size:14px}.brand{font-weight:760;letter-spacing:.04em}.top nav{display:flex;gap:6px 16px;justify-content:flex-end;flex-wrap:wrap}a{color:var(--purple-dark);text-underline-offset:4px}a:focus-visible,summary:focus-visible{outline:3px solid #c7bfff;outline-offset:4px}.top a{text-decoration:none}.top nav a{color:var(--muted)}.top nav a:hover{color:var(--purple)}
main{padding-top:44px;padding-bottom:42px}h1{font-size:42px;line-height:1.28;letter-spacing:0;margin:0 0 22px}h2{font-size:24px;line-height:1.5;margin:44px 0 14px;padding-top:10px;border-top:1px solid var(--line);scroll-margin-top:20px}h3{font-size:19px;line-height:1.6;margin:30px 0 10px;scroll-margin-top:20px}h4,h5,h6{font-size:17px;margin:22px 0 8px;scroll-margin-top:20px}p{margin:0 0 18px}ul,ol{margin:0 0 22px;padding-left:1.5em}li{padding-left:.15em;margin:6px 0}li p{margin:8px 0}strong{font-weight:720}img{display:block;width:auto;max-width:100%;height:auto;margin:22px auto;border-radius:6px}blockquote{margin:20px 0;padding:8px 0 8px 16px;border-left:3px solid var(--purple);color:#504d5c;background:linear-gradient(90deg,var(--purple-soft),transparent)}blockquote p:last-child{margin-bottom:0}hr{border:0;border-top:1px solid var(--line);margin:32px 0}
.table-wrap{max-width:100%;overflow-x:auto;margin:18px 0 26px;background:var(--surface);border:1px solid var(--line);border-radius:8px;padding:0 12px}table{width:100%;border-collapse:collapse;font-size:15px;line-height:1.75}th,td{text-align:left;vertical-align:top;padding:11px 12px;border-bottom:1px solid var(--line);min-width:115px}th{font-weight:700;color:var(--purple-dark);background:var(--purple-soft)}td:first-child,th:first-child{padding-left:8px}code{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;font-size:.88em;background:#eeedf2;padding:2px 5px;border-radius:3px}pre{overflow-x:auto;padding:16px;background:#eeedf2;border-radius:6px;line-height:1.6}pre code{background:none;padding:0;white-space:pre;overflow-wrap:normal}.toc{margin:26px 0 34px;padding:18px 20px;background:var(--surface);border:1px solid var(--line);border-radius:8px;font-size:14px}.toc summary{color:var(--purple-dark);font-weight:720;cursor:pointer}.toc ul{display:flex;flex-wrap:wrap;gap:6px 20px;list-style:none;padding:0;margin:12px 0 0}.toc li{margin:0;padding:0}.toc a{text-decoration:none}
footer{border-top:1px solid var(--line);padding-top:20px;padding-bottom:30px;font-size:13px;color:var(--muted)}footer p{margin-bottom:8px}.footer-links{display:flex;flex-wrap:wrap;gap:8px 18px}
@media(max-width:600px){header,main,footer{padding-left:18px;padding-right:18px}.top{display:block}.top nav{justify-content:flex-start;margin-top:12px;font-size:14px;gap:6px 14px}main{padding-top:30px}h1{font-size:32px}h2{font-size:22px}h3{font-size:18px}th,td{padding:9px 10px}table{font-size:14px}.toc ul{display:block}.toc li{margin:8px 0}}
@media print{body{background:white;color:#111;font-size:11pt}header,.toc,.footer-links{display:none}main,footer{width:auto;max-width:none;padding:0}h1{font-size:24pt}h2{font-size:17pt;break-after:avoid}h3{font-size:14pt;break-after:avoid}a{color:inherit}.table-wrap{overflow:visible}pre{white-space:pre-wrap}img{max-height:80vh}footer{margin-top:25px}}
'''


def relative(target: str, output: str) -> str:
    """Produce a browser-relative URL from a path relative to the project root."""
    return Path(os.path.relpath(ROOT / target, (ROOT / output).parent)).as_posix()


def rewrite_url(url: str, source: str, output: str) -> str:
    url = html.unescape(url.strip())
    parts = urlsplit(url)
    if parts.scheme and parts.scheme not in {'https', 'http', 'mailto'}:
        return '#'
    if not parts.path and parts.fragment:
        return url
    # Public reading links are also usable when the ZIP is opened offline.
    if url.startswith(SITE):
        local = unquote(parts.path.removeprefix('/HowToGetAlong/')) or 'index.html'
    elif url.startswith(REPO + '/blob/main/'):
        local = unquote(parts.path.removeprefix('/kkk-bot/HowToGetAlong/blob/main/'))
    elif parts.scheme or parts.netloc:
        return url
    else:
        resolved = ((ROOT / source).parent / unquote(parts.path)).resolve()
        try:
            local = resolved.relative_to(ROOT).as_posix()
        except ValueError:
            return '#'
    mapped = PAGES.get(local) or ALIASES.get(local)
    fragment = parts.fragment
    if local.startswith('book/') and local.endswith('.md'):
        chapter = re.match(r'book/(\d+)-', local)
        if chapter:
            mapped, fragment = '阅读全文.html', f'chapter-{int(chapter[1])}'
    if mapped:
        result = relative(mapped, output)
    elif local.endswith('.md'):
        result = relative(local, output)
    else:
        result = relative(local, output)
    if parts.query:
        result += '?' + parts.query
    if fragment:
        result += '#' + fragment
    return result


def inline(text: str, source: str, output: str) -> str:
    """Escape text, then render this project's inline Markdown without raw HTML."""
    tokens: list[str] = []

    def token(value: str) -> str:
        tokens.append(value)
        return f'\x00{len(tokens)-1}\x00'

    text = re.sub(r'`([^`]+)`', lambda m: token('<code>' + html.escape(m[1]) + '</code>'), text)

    def image(match: re.Match) -> str:
        alt, url = match[1], match[2]
        return token('<img src="' + html.escape(rewrite_url(url, source, output), quote=True)
                     + '" alt="' + html.escape(alt, quote=True) + '" loading="lazy">')

    text = re.sub(r'!\[([^\]]*)\]\(([^\s]+?)\)', image, text)

    def link(match: re.Match) -> str:
        label, url = match[1], match[2]
        return token('<a href="' + html.escape(rewrite_url(url, source, output), quote=True)
                     + '">' + inline(label, source, output) + '</a>')

    text = re.sub(r'\[([^\]]+)\]\(([^\s]+?)\)', link, text)
    text = html.escape(text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'<em>\1</em>', text)
    text = re.sub(r'\x00(\d+)\x00', lambda m: tokens[int(m[1])], text)
    return text


def slug(text: str) -> str:
    plain = re.sub(r'!?\[([^\]]+)\]\([^)]+\)', r'\1', text)
    plain = plain.replace('`', '').replace('*', '').strip().lower()
    return re.sub(r'[^\w\u4e00-\u9fff -]', '', plain).replace(' ', '-') or 'section'


def table_cells(line: str) -> list[str]:
    # A protected \| in a cell stays text rather than starting another column.
    return [cell.strip().replace('\x01', '|')
            for cell in line.strip().strip('|').replace('\\|', '\x01').split('|')]


def render_markdown(markdown: str, source: str, output: str) -> tuple[str, list[tuple[str, str]]]:
    lines = markdown.splitlines()
    rendered: list[str] = []
    headings: list[tuple[str, str]] = []
    ids: dict[str, int] = {}
    i = 0

    def is_table_separator(line: str) -> bool:
        cells = table_cells(line)
        return len(cells) > 1 and all(re.fullmatch(r':?-{3,}:?', cell) for cell in cells)

    def starts_block(index: int) -> bool:
        line = lines[index]
        return (not line.strip() or bool(re.match(r'^(?:#{1,6}\s|```|~~~|>\s?|\s*(?:[-+*]|\d+[.)])\s+)', line))
                or bool(re.fullmatch(r'\s*(?:-{3,}|\*{3,}|_{3,})\s*', line))
                or (index + 1 < len(lines) and '|' in line and is_table_separator(lines[index + 1])))

    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        fence = re.match(r'^(?:```|~~~)(.*)$', line)
        if fence:
            marker = line[:3]
            code = []
            i += 1
            while i < len(lines) and not lines[i].startswith(marker):
                code.append(lines[i])
                i += 1
            rendered.append('<pre><code>' + html.escape('\n'.join(code)) + '</code></pre>')
            i += 1
            continue
        heading = re.match(r'^(#{1,6})\s+(.+?)\s*#*$', line)
        if heading:
            level, text = len(heading[1]), heading[2]
            base = slug(text)
            suffix = ids.get(base, 0)
            ids[base] = suffix + 1
            ident = base + (f'-{suffix}' if suffix else '')
            rendered.append(f'<h{level} id="{html.escape(ident, quote=True)}">'
                            + inline(text, source, output) + f'</h{level}>')
            if level == 2:
                headings.append((ident, text))
            i += 1
            continue
        if re.fullmatch(r'\s*(?:-{3,}|\*{3,}|_{3,})\s*', line):
            rendered.append('<hr>')
            i += 1
            continue
        if i + 1 < len(lines) and '|' in line and is_table_separator(lines[i + 1]):
            headers = table_cells(line)
            alignment = table_cells(lines[i + 1])
            rows = []
            i += 2
            while i < len(lines) and lines[i].strip() and '|' in lines[i]:
                rows.append(table_cells(lines[i]))
                i += 1
            rendered.append('<div class="table-wrap"><table><thead><tr>'
                            + ''.join('<th scope="col">' + inline(cell, source, output) + '</th>' for cell in headers)
                            + '</tr></thead><tbody>')
            for row in rows:
                rendered.append('<tr>')
                for col, cell in enumerate(row):
                    align = alignment[col] if col < len(alignment) else ''
                    style = ' style="text-align:center"' if align.startswith(':') and align.endswith(':') else ''
                    rendered.append('<td' + style + '>' + inline(cell, source, output) + '</td>')
                rendered.append('</tr>')
            rendered.append('</tbody></table></div>')
            continue
        item = re.match(r'^\s*([-+*]|\d+[.)])\s+(.+)$', line)
        if item:
            ordered = item[1][0].isdigit()
            tag = 'ol' if ordered else 'ul'
            start = int(re.match(r'\d+', item[1])[0]) if ordered else 1
            rendered.append(f'<{tag}' + (f' start="{start}"' if ordered and start != 1 else '') + '>')
            while i < len(lines):
                current = re.match(r'^\s*([-+*]|\d+[.)])\s+(.+)$', lines[i])
                if not current or current[1][0].isdigit() != ordered:
                    break
                content = current[2]
                i += 1
                while i < len(lines) and lines[i].strip() and lines[i].startswith('  ') and not starts_block(i):
                    content += ' ' + lines[i].strip()
                    i += 1
                rendered.append('<li>' + inline(content, source, output) + '</li>')
            rendered.append(f'</{tag}>')
            continue
        if line.startswith('>'):
            quote_lines = []
            while i < len(lines) and lines[i].startswith('>'):
                quote_lines.append(re.sub(r'^>\s?', '', lines[i]))
                i += 1
            quote_body, _ = render_markdown('\n'.join(quote_lines), source, output)
            rendered.append('<blockquote>' + quote_body + '</blockquote>')
            continue
        paragraph = [line.strip()]
        i += 1
        while i < len(lines) and not starts_block(i):
            paragraph.append(lines[i].strip())
            i += 1
        rendered.append('<p>' + inline(' '.join(paragraph), source, output) + '</p>')
    return '\n'.join(rendered), headings


def build_page(source: str, output: str, project_name: str, reference_note: str) -> None:
    source_path = ROOT / source
    markdown = source_path.read_text(encoding='utf-8')
    first = re.search(r'^#\s+(.+)$', markdown, re.M)
    title = first[1] if first else project_name
    body, headings = render_markdown(markdown, source, output)
    if len(headings) >= 3:
        contents = '<details class="toc"><summary>本页目录</summary><ul>'
        contents += ''.join('<li><a href="#' + html.escape(ident, quote=True) + '">'
                            + inline(label, source, output) + '</a></li>' for ident, label in headings)
        contents += '</ul></details>'
        body = re.sub(r'(</h1>)', r'\1' + contents, body, count=1)
    nav = ''.join('<a href="' + html.escape(relative(target, output), quote=True) + '">' + label + '</a>'
                  for target, label in [('index.html', '阅读与检索'), ('阅读全文.html', '连续阅读'),
                                        ('docs/practice.html', '练习'), ('about.html', '项目说明')])
    source_url = relative(source, output)
    document = ('<!doctype html>\n<html lang="zh-CN"><head><meta charset="utf-8">'
                '<meta name="viewport" content="width=device-width,initial-scale=1">'
                '<meta name="source-sha256" content="' + hashlib.sha256(source_path.read_bytes()).hexdigest() + '">'
                '<meta name="description" content="' + html.escape(project_name + ' · ' + title, quote=True) + '">'
                '<title>' + html.escape(title) + ' · ' + html.escape(project_name) + '</title>'
                '<style>' + CSS + '</style></head><body>'
                '<header><div class="top"><a class="brand" href="' + html.escape(relative('index.html', output), quote=True)
                + '">' + html.escape(project_name) + '</a><nav aria-label="站点导航">' + nav + '</nav></div></header>'
                '<main>' + body + '</main><footer><p>根据自己的关系与条件选择做法。示例可以调整，经验建议未验证效果。</p>'
                '<p>' + html.escape(reference_note) + '</p>'
                '<p class="footer-links">' + nav + '<a href="' + html.escape(source_url, quote=True)
                + '">查看 Markdown 源文档</a></p></footer></body></html>\n')
    (ROOT / output).parent.mkdir(parents=True, exist_ok=True)
    (ROOT / output).write_text(document, encoding='utf-8')


def main() -> None:
    meta = json.loads((ROOT / 'project.json').read_text(encoding='utf-8'))
    project_name = meta['name']
    for source, output in PAGES.items():
        if not (ROOT / source).is_file():
            raise FileNotFoundError(f'缺少源文档 {source}；请先运行 tools/build.py')
        build_page(source, output, project_name, meta['reference_note'])
    print(f'已生成 {len(PAGES)} 个静态文档阅读页。')


if __name__ == '__main__':
    main()
