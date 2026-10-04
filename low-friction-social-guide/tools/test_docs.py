"""Check that history links preserve the named source rather than the latest record."""
import hashlib
from urllib.parse import unquote, urlsplit

from build_docs import ROOT, PAGES, rewrite_url


def main():
    records = sorted((ROOT / 'docs/核实记录').glob('*.md'))
    for record in records:
        target = rewrite_url(f'核实记录/{record.name}', 'docs/章节扩充资料-2026-10-04.md',
                             'docs/chapter-materials.html')
        assert target != 'verification.html', f'History must not point at the latest record: {record.name}'
        output = ROOT / 'docs' / unquote(urlsplit(target).path)
        assert output == ROOT / PAGES[record.relative_to(ROOT).as_posix()], record.name
        page = output.read_text(encoding='utf-8')
        digest = hashlib.sha256(record.read_bytes()).hexdigest()
        assert f'name="source-sha256" content="{digest}"' in page, record.name
    assert rewrite_url('核实记录/v1.15说明.md#整合范围', 'docs/研究资料整理.md',
                       'docs/research-notes.html') == 'history/v1.15说明.html#整合范围'
    print(f'Document regression checks passed: {len(records)} distinct history records and source fingerprints.')


if __name__ == '__main__':
    main()
