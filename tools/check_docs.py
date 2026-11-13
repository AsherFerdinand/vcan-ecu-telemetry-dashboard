"""Check repository Markdown file/heading links and case-only document collisions.

External sites are not contacted. This supports an offline documentation review;
it does not claim to render Mermaid, badges or native-platform shell commands.
"""
from collections import Counter
import html
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


def prose(path):
    return re.sub(r'```.*?```', '', path.read_text(encoding='utf-8'), flags=re.S)


def anchors(path):
    counts = Counter()
    result = set()
    for title in re.findall(r'^#{1,6}\s+(.+?)\s*#*$', prose(path), re.M):
        title = re.sub(r'<[^>]+>', '', html.unescape(title)).lower()
        slug = re.sub(r'[^\w\- ]', '', title).replace(' ', '-')
        result.add(slug if counts[slug] == 0 else f'{slug}-{counts[slug]}')
        counts[slug] += 1
    return result


def main():
    documents = [ROOT / 'README.md', *sorted((ROOT / 'docs').rglob('*.md')), ROOT / 'data/README.md']
    errors = []
    folded = {}
    checked = 0
    for document in documents:
        name = str(document.relative_to(ROOT))
        if name.casefold() in folded:
            errors.append(f'Case-only document collision: {name}, {folded[name.casefold()]}')
        folded[name.casefold()] = name
        for target in re.findall(r'!?\[[^\]]*\]\(([^\s)]+)(?:\s+"[^"]*")?\)', prose(document)):
            target = target.strip('<>')
            url = urlsplit(target)
            if url.scheme or url.netloc:
                continue
            path = (document.parent / unquote(url.path)).resolve() if url.path else document
            checked += 1
            if not path.exists():
                errors.append(f'{name}: missing target {target}')
            elif url.fragment and path.suffix.lower() == '.md' and unquote(url.fragment) not in anchors(path):
                errors.append(f'{name}: missing heading {target}')
    if errors:
        raise SystemExit('\n'.join(errors))
    print(f'PASS: {checked} local links/headings in {len(documents)} Markdown documents; no case-only document collisions.')


if __name__ == '__main__':
    main()
