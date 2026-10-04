"""Generate the complete PDF from 完整指南.md (requires reportlab)."""
import argparse
import hashlib
import json
from pathlib import Path
import re
from xml.sax.saxutils import escape, quoteattr

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont, TTFError
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.platypus.tableofcontents import TableOfContents

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'downloads' / '低内耗社交指南.pdf'
DEFAULT_FONT = '/System/Library/Fonts/STHeiti Light.ttc'
DEFAULT_BOLD_FONT = '/System/Library/Fonts/STHeiti Medium.ttc'
INK = colors.HexColor('#17161d')
MUTED = colors.HexColor('#6f6d7a')
PURPLE = colors.HexColor('#654bff')
PURPLE_SOFT = colors.HexColor('#f0edff')
CHAPTER_RE = re.compile(r'^(\d+)\.\s+(.+)$')
ENTRY_RE = re.compile(r'^(\d+(?:\.\d+)?)\.\s+(.+)$')
SOURCE_RE = re.compile(r'^([SRPA]\d{2})\b[.：:、\s-]*(.*)$')
INLINE_RE = re.compile(r'\[([^\]]+)\]\(([^)]+)\)|\*\*(.+?)\*\*|`([^`]+)`')


def entry_key(number):
    return 'entry-' + number.replace('.', '-')


def discover_targets(lines):
    """Only numbered chapters and their ### headings are guide entries."""
    entries, sources = set(), set()
    chapter_number = None
    in_sources = False
    for line in lines:
        line = line.strip()
        if line.startswith('# '):
            title = line[2:]
            match = CHAPTER_RE.match(title)
            chapter_number = match.group(1) if match else None
            in_sources = title == '来源索引'
        elif line.startswith('### ') and chapter_number is not None:
            match = ENTRY_RE.match(line[4:])
            if match:
                number = match.group(1)
                entries.add(number if '.' in number else chapter_number + '.' + number)
        elif line.startswith(('## ', '### ')) and in_sources:
            match = SOURCE_RE.match(line.lstrip('# '))
            if match:
                sources.add(match.group(1))
    return entries, sources


def markup(text, entries=(), sources=(), link_entries=False):
    """Keep Markdown links, emphasis, and verified internal references."""
    def plain(part):
        pattern = r'(?<![\w.])(\d+\.\d+)(?![\w.])|\b([SRPA]\d{2})\b'
        rendered, position = [], 0
        for match in re.finditer(pattern, part):
            rendered.append(escape(part[position:match.start()]))
            number, source = match.groups()
            label = match.group(0)
            if number and link_entries and number in entries:
                target = entry_key(number)
            elif source and source in sources:
                target = 'source-' + source
            else:
                target = None
            rendered.append('<link underline="0" href="#' + target + '">' + label + '</link>'
                            if target else escape(label))
            position = match.end()
        rendered.append(escape(part[position:]))
        return ''.join(rendered)

    rendered, position = [], 0
    for match in INLINE_RE.finditer(text):
        rendered.append(plain(text[position:match.start()]))
        label, href, bold, code = match.groups()
        if label is not None:
            if href.startswith(('https://', 'http://', 'mailto:')):
                destination = href
            elif href.startswith('#'):
                destination = href
            else:
                destination = None
            # Link labels must not contain nested links.
            clean_label = escape(label.replace('**', '').replace('`', ''))
            rendered.append('<link underline="0" href=' + quoteattr(destination) + '>' +
                            clean_label + '</link>' if destination else clean_label)
        elif bold is not None:
            rendered.append('<b>' + plain(bold) + '</b>')
        else:
            rendered.append(escape(code))
        position = match.end()
    rendered.append(plain(text[position:]))
    return ''.join(rendered)


def register_fonts(font_path, bold_font_path, lines):
    visible_text = '\n'.join(line for line in lines if not line.strip().startswith('<!--'))
    visible_text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', visible_text)
    for name, path in [('GuideChinese', font_path), ('GuideChineseBold', bold_font_path)]:
        path = Path(path).expanduser()
        if not path.is_file():
            raise ValueError('找不到中文字体：' + str(path) + '。请用 --font 与 --bold-font 指定 TTF/TTC 字体。')
        try:
            font = TTFont(name, str(path), subfontIndex=0)
        except (TTFError, OSError) as error:
            raise ValueError('无法读取中文 TrueType 字体：' + str(path) + '（' + str(error) + '）') from error
        missing = sorted({char for char in visible_text if not char.isspace() and
                          ord(char) not in font.face.charToGlyph})
        if missing:
            raise ValueError('字体 ' + path.name + ' 缺少字符：' + ''.join(missing[:20]) +
                             '。请改用覆盖这些字符的中文 TTF/TTC 字体。')
        pdfmetrics.registerFont(font)
    pdfmetrics.registerFontFamily('GuideChinese', normal='GuideChinese',
                                 bold='GuideChineseBold', italic='GuideChinese',
                                 boldItalic='GuideChineseBold')


def styles():
    body = ParagraphStyle('body', fontName='GuideChinese', fontSize=10.5,
                          leading=17, textColor=INK, spaceAfter=7, wordWrap='CJK')
    chapter = ParagraphStyle('chapter', parent=body, fontName='GuideChineseBold',
                             fontSize=20, leading=29, spaceAfter=18, keepWithNext=True)
    heading = ParagraphStyle('heading', parent=body, fontName='GuideChineseBold',
                             fontSize=14, leading=22, spaceBefore=14, spaceAfter=10,
                             keepWithNext=True)
    example = ParagraphStyle('example', parent=body, backColor=PURPLE_SOFT,
                             borderColor=PURPLE, borderWidth=0, borderPadding=9,
                             spaceBefore=4, spaceAfter=12)
    return body, chapter, heading, example


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont('GuideChinese', 9)
    canvas.setFillColor(MUTED)
    canvas.drawString(46, 27, '低内耗社交指南 · 未白实验室')
    canvas.drawRightString(A4[0] - 46, 27, str(doc.page))
    canvas.restoreState()


class GuideDoc(SimpleDocTemplate):
    def afterFlowable(self, flowable):
        key = getattr(flowable, '_guide_bookmark', None)
        if not key:
            return
        title = flowable.getPlainText()
        # Target the heading position instead of always returning to the page top.
        self.canv.bookmarkHorizontalAbsolute(key, self.frame._y + flowable.height)
        self.canv.addOutlineEntry(title, key, getattr(flowable, '_guide_outline_level', 0))
        if getattr(flowable, '_guide_toc', False):
            self.notify('TOCEntry', (0, title, self.page, key))


def bookmarked_paragraph(text, style, key, level=0, toc=False):
    paragraph = Paragraph(text, style)
    paragraph._guide_bookmark = key
    paragraph._guide_outline_level = level
    paragraph._guide_toc = toc
    return paragraph


def build(input_path=ROOT / '完整指南.md', output_path=OUT,
          font_path=DEFAULT_FONT, bold_font_path=DEFAULT_BOLD_FONT):
    input_path, output_path = Path(input_path), Path(output_path)
    lines = input_path.read_text(encoding='utf-8').splitlines()
    register_fonts(font_path, bold_font_path, lines)
    entries, sources = discover_targets(lines)
    body, chapter, heading, example = styles()
    meta = json.loads((ROOT / 'project.json').read_text(encoding='utf-8'))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cover_eyebrow = ParagraphStyle('cover-eyebrow', parent=body, fontName='GuideChineseBold',
                                   fontSize=10, leading=14, textColor=PURPLE, spaceAfter=20)
    cover_title = ParagraphStyle('cover-title', parent=body, fontName='GuideChineseBold',
                                 fontSize=38, leading=50, textColor=INK, spaceAfter=20)
    cover_lead = ParagraphStyle('cover-lead', parent=body, fontSize=15, leading=25,
                                textColor=INK, spaceAfter=28)
    cover_meta = ParagraphStyle('cover-meta', parent=body, fontSize=10, leading=17,
                                textColor=MUTED, spaceAfter=8)
    story = [
        Spacer(1, 58),
        Paragraph('WEIBAI LAB / LOW-FRICTION SOCIAL GUIDE', cover_eyebrow),
        Paragraph('<font color="#654bff">低内耗</font><br/>社交指南', cover_title),
        Paragraph(escape(meta['positioning']), cover_lead),
        Spacer(1, 14),
        Paragraph(f'10 章 · 67 个真实场景 · V{escape(meta["version"])}', cover_meta),
        Paragraph('先看清关系，再决定怎么说、怎么做。', cover_meta),
        Spacer(1, 150),
        Paragraph('未白实验室', cover_meta),
    ]
    first_title, in_body, in_sources = True, False, False
    chapter_number, chapter_index = None, 0
    for line in lines:
        line = line.strip()
        if not line or line.startswith('<!--'):
            continue
        if line.startswith('# '):
            if first_title:
                first_title = False
                continue
            if not in_body:
                story.extend([PageBreak(), Paragraph('目录', chapter)])
                toc = TableOfContents()
                toc.levelStyles = [ParagraphStyle('toc', parent=body, leading=24, spaceAfter=8)]
                toc.dotsMinLevel = 0
                story.append(toc)
            story.append(PageBreak())
            in_body = True
            title = line[2:]
            match = CHAPTER_RE.match(title)
            chapter_number = match.group(1) if match else None
            in_sources = title == '来源索引'
            key = 'chapter-' + str(chapter_index)
            chapter_index += 1
            story.append(bookmarked_paragraph(markup(title), chapter, key, toc=True))
        elif line.startswith(('## ', '### ')):
            title = line.lstrip('# ')
            entry_match = ENTRY_RE.match(title) if line.startswith('### ') and chapter_number else None
            source_match = SOURCE_RE.match(title) if in_sources else None
            if entry_match:
                number, label = entry_match.groups()
                number = number if '.' in number else chapter_number + '.' + number
                story.append(bookmarked_paragraph(markup(number + ' ' + label), heading,
                                                   entry_key(number), level=1))
            elif source_match:
                story.append(bookmarked_paragraph(markup(title), heading,
                                                   'source-' + source_match.group(1), level=1))
            else:
                story.append(Paragraph(markup(title), heading))
        else:
            text = line[2:] if line.startswith('- ') else line
            style = example if text.startswith(('可以怎么说：', '原创示例：')) else body
            related = text.startswith('相关条目：')
            rendered = markup(text, entries, sources, link_entries=related or in_sources)
            if in_body:
                if '：' in text and line.startswith('- '):
                    label, content = text.split('：', 1)
                    rendered = '<b>' + markup(label + '：') + '</b>' + \
                        markup(content, entries, sources, link_entries=related or in_sources)
            if text.startswith('可以怎么说：'):
                rendered = re.sub(r'(（示例仅供参考，请根据事实情况调整。）)(?=.)', r'\1<br/><br/>', rendered)
            story.append(Paragraph(rendered, style))
    GuideDoc(str(output_path), pagesize=A4, rightMargin=46, leftMargin=46,
             topMargin=45, bottomMargin=49, title=meta['name'], author='未白实验室',
             subject='Source SHA256: ' + hashlib.sha256(input_path.read_bytes()).hexdigest(),
             pageCompression=1).multiBuild(story, onFirstPage=footer, onLaterPages=footer)
    return output_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--font', default=DEFAULT_FONT,
                        help='Path to a Chinese TrueType font (TTF or TTC); embedded in the PDF')
    parser.add_argument('--bold-font', default=DEFAULT_BOLD_FONT,
                        help='Path to the bold Chinese TrueType font; embedded in the PDF')
    parser.add_argument('--input', type=Path, default=ROOT / '完整指南.md',
                        help='Markdown source path (defaults to 完整指南.md)')
    parser.add_argument('--output', type=Path, default=OUT,
                        help='PDF output path (defaults to downloads/低内耗社交指南.pdf)')
    args = parser.parse_args()
    try:
        output = build(args.input, args.output, args.font, args.bold_font)
    except (ValueError, FileNotFoundError) as error:
        parser.error(str(error))
    print(output)


if __name__ == '__main__':
    main()
