#!/usr/bin/env python3
"""Build and validate the site, Markdown, Skill snapshot and complete PDF together."""
import argparse
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote, urlsplit

from build import ROOT, read_entries
from sources import load_sources
from build_docs import PAGES as DOC_SOURCES

PAGES = ['index.html', '阅读全文.html', 'about.html', 'downloads/html.html', 'docs/usage.html',
         'docs/practice.html', 'docs/verification.html', 'docs/editorial-guide.html',
         'docs/sources.html', 'docs/strategy-notes.html', 'docs/interview-notes.html',
         'docs/research-notes.html', 'docs/platform-notes.html', 'docs/chapter-materials.html']
PAGES = list(dict.fromkeys([*PAGES, *DOC_SOURCES.values()]))


class Links(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.ids, self.links = set(), []
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get('id'):
            self.ids.add(attrs['id'])
        if tag == 'a' and attrs.get('href'):
            self.links.append(attrs['href'])
        elif tag == 'img' and attrs.get('src'):
            self.links.append(attrs['src'])


def validate():
    from pypdf import PdfReader
    entries, chapters = read_entries()
    snapshots = ROOT / 'skills/low-friction-social-guide/references'
    meta = json.loads((ROOT / 'project.json').read_text(encoding='utf-8'))
    build_revision = meta.get('build_revision', meta['version'])
    if build_revision != '1.17':
        current_record = ROOT / f'docs/核实记录/v{build_revision}说明.md'
        if current_record.read_bytes() != (snapshots / f'v{build_revision}整合记录.md').read_bytes():
            raise ValueError('Skill 当前核实记录快照过期')
    for chapter in chapters:
        source = ROOT / 'book' / chapter['file']
        if source.read_bytes() != (snapshots / 'book' / chapter['file']).read_bytes():
            raise ValueError(f'Skill 正文快照过期：{source.name}')
    for original, snapshot in [('docs/交流复盘与场景练习.md', '交流复盘与场景练习.md'),
                               ('docs/编写规范.md', '编写规范.md'),
                               ('docs/研究资料整理.md', '研究资料整理.md'),
                               ('docs/平台素材收集-2026-10-04.md', '平台素材收集-2026-10-04.md'),
                               ('docs/章节扩充资料-2026-10-04.md', '章节扩充资料-2026-10-04.md'),
                               ('docs/核实记录/v1.15说明.md', 'v1.15整合记录.md'),
                               ('docs/核实记录/v1.16说明.md', 'v1.16整合记录.md'),
                               ('docs/核实记录/v1.17说明.md', 'v1.17整合记录.md')]:
        expected = (ROOT / original).read_text(encoding='utf-8')
        if snapshot == '章节扩充资料-2026-10-04.md':
            expected = expected.replace('核实记录/v1.17说明.md', 'v1.17整合记录.md')
        elif snapshot == '平台素材收集-2026-10-04.md':
            expected = expected.replace('核实记录/v1.16说明.md', 'v1.16整合记录.md')
        elif snapshot == 'v1.17整合记录.md':
            expected = expected.replace('../章节扩充资料-2026-10-04.md', '章节扩充资料-2026-10-04.md').replace('../../阅读全文.html', '目录.md')
        elif snapshot == '研究资料整理.md':
            expected = expected.replace('核实记录/v1.15说明.md', 'v1.15整合记录.md').replace('](editorial-guide.md)', '](编写规范.md)')
        elif snapshot == 'v1.15整合记录.md':
            expected = expected.replace('../研究资料整理.md', '研究资料整理.md')
        elif snapshot == 'v1.16整合记录.md':
            expected = expected.replace('../平台素材收集-2026-10-04.md', '平台素材收集-2026-10-04.md')
        if expected != (snapshots / snapshot).read_text(encoding='utf-8'):
            raise ValueError(f'Skill 文档快照过期：{snapshot}')
    for file in [ROOT / 'README.md', *(ROOT / 'skills/low-friction-social-guide').rglob('*.md')]:
        for link in re.findall(r'\]\(([^\s)]+)\)', file.read_text(encoding='utf-8')):
            url = urlsplit(link)
            if url.scheme or url.netloc or not url.path:
                continue
            target = (file.parent / unquote(url.path)).resolve()
            if not target.is_relative_to(ROOT) or not target.exists():
                raise ValueError(f'Markdown 链接缺失：{file.relative_to(ROOT)} → {link}')
    source = ROOT / '完整指南.md'
    full = source.read_text(encoding='utf-8')
    for chapter in chapters:
        if (ROOT / 'book' / chapter['file']).read_text(encoding='utf-8').strip() not in full:
            raise ValueError(f'完整 Markdown 正文过期：{chapter["file"]}')
    if (ROOT / 'docs/交流复盘与场景练习.md').read_text(encoding='utf-8').strip() not in full:
        raise ValueError('完整 Markdown 练习过期')
    for entry in entries:
        if f'### {entry["id"].split(".")[1]}. {entry["title"]}' not in full:
            raise ValueError(f'完整 Markdown 缺少条目：{entry["id"]}')
    index = (ROOT / 'index.html').read_text(encoding='utf-8')
    data = re.search(r'<script id="entries" type="application/json">(.*?)</script>', index, re.S)
    if not data or json.loads(data[1]) != entries:
        raise ValueError('检索页正文数据与 book/ 不一致')
    if (ROOT / 'tools/search.js').read_text(encoding='utf-8') not in index:
        raise ValueError('检索页脚本过期')

    parsed = {}
    for original, output in DOC_SOURCES.items():
        digest = hashlib.sha256((ROOT / original).read_bytes()).hexdigest()
        if f'name="source-sha256" content="{digest}"' not in (ROOT / output).read_text(encoding='utf-8'):
            raise ValueError(f'文档阅读页过期：{output}')
    for name in PAGES:
        file = ROOT / name
        parsed[file] = Links(file.read_text(encoding='utf-8'))
    for file, page in list(parsed.items()):
        for link in page.links:
            url = urlsplit(link)
            if url.scheme or url.netloc:
                continue
            target = (file.parent / unquote(url.path)).resolve() if url.path else file
            if not target.is_relative_to(ROOT):
                raise ValueError(f'网页链接超出项目：{file.name} → {link}')
            if not target.exists():
                raise ValueError(f'网页链接缺失：{file.name} → {link}')
            if url.fragment and target.suffix == '.html':
                if target not in parsed:
                    parsed[target] = Links(target.read_text(encoding='utf-8'))
                # Search cards are rendered by the inline JavaScript.
                dynamic = target == ROOT / 'index.html' and unquote(url.fragment) in {
                    f'entry-{entry["id"]}' for entry in entries}
                if unquote(url.fragment) not in parsed[target].ids and not dynamic:
                    raise ValueError(f'网页锚点缺失：{file.name} → {link}')

    pdf = PdfReader(ROOT / 'downloads/低内耗社交指南.pdf')
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    if digest not in (pdf.metadata.subject or ''):
        raise ValueError('PDF 正文指纹不一致，请重新生成')
    contents_text = pdf.pages[1].extract_text()
    if '目录' not in contents_text:
        raise ValueError('PDF 目录页缺少目录标题')
    outline_titles = []
    def visit(items):
        for item in items:
            if isinstance(item, list):
                visit(item)
            else:
                outline_titles.append(item.title)
                if pdf.get_destination_page_number(item) is None:
                    raise ValueError(f'PDF 书签没有有效页面：{item.title}')
    visit(pdf.outline)
    for entry in entries:
        if f'{entry["id"]} {entry["title"]}' not in outline_titles:
            raise ValueError(f'PDF 缺少条目书签：{entry["id"]}')
    sources = load_sources()
    referenced = set(re.findall(r'\b[SRPA]\d{2}\b', full))
    outline_sources = {match[1] for title in outline_titles
                       if (match := re.match(r'^([SRPA]\d{2})\b', title))}
    if referenced - outline_sources:
        raise ValueError(f'PDF 缺少来源书签：{sorted(referenced - outline_sources)}')
    uris = set()
    for page in pdf.pages:
        for ref in page.get('/Annots', []):
            annotation = ref.get_object()
            action = annotation.get('/A', {})
            if action.get('/S') == '/URI':
                uris.add(action.get('/URI'))
    for item in sources:
        if item['id'] in referenced and item['url'] not in uris:
            raise ValueError(f'PDF 缺少来源外链：{item["id"]}')
    print(f'校验通过：{len(entries)} 条正文、Skill 快照、{len(PAGES)} 个网页入口、'
          f'{len(pdf.pages)} 页 PDF、条目书签及 {len(referenced)} 个来源链接。')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Only validate existing outputs')
    parser.add_argument('--font', help='Chinese TrueType font used for PDF')
    parser.add_argument('--bold-font', help='Bold Chinese TrueType font used for PDF')
    args = parser.parse_args()
    try:
        import reportlab  # noqa: F401
        import pypdf  # noqa: F401
    except ImportError as error:
        parser.error(f'缺少 {error.name}；请先安装 reportlab 和 pypdf')
    if not args.check:
        fonts = []
        for option, value in [('--font', args.font), ('--bold-font', args.bold_font)]:
            if value:
                fonts.extend([option, value])
        for script, options in [('build.py', []), ('build_docs.py', []), ('build_pdf.py', fonts)]:
            subprocess.run([sys.executable, str(ROOT / 'tools' / script), *options], check=True)
    validate()


if __name__ == '__main__':
    main()
