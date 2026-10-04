"""Load the project's traceable opinion, research, and practical sources."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def load_sources():
    items = []
    for name in ['docs/Morris账号整理/来源与条目.json', 'docs/访谈与博客来源.json', 'docs/研究资料来源.json', 'docs/平台素材来源.json', 'docs/章节扩充来源.json']:
        items.extend(json.loads((ROOT / name).read_text(encoding='utf-8'))['sources'])
    ids = [item['id'] for item in items]
    if len(ids) != len(set(ids)):
        raise ValueError('来源编号重复')
    return items
