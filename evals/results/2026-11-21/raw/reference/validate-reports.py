from pathlib import Path
from html.parser import HTMLParser
root = Path('/private/tmp/codebase-sense-qa-91vasxy9/jobs/reference/reports')
class Check(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.errors = []
    def handle_starttag(self, tag, attrs):
        if tag not in {'meta', 'link', 'img', 'br', 'hr', 'input', 'source', 'wbr', 'area', 'base', 'col', 'embed', 'param', 'track'}:
            self.stack.append(tag)
    def handle_endtag(self, tag):
        if not self.stack or self.stack[-1] != tag:
            self.errors.append((tag, self.stack[-1] if self.stack else None))
        else:
            self.stack.pop()
for case in ('checkout', 'ledger', 'click', 'flask'):
    md = (root / f'{case}.md').read_text()
    html = (root / f'{case}.html').read_text()
    parser = Check()
    parser.feed(html)
    assert not parser.errors and not parser.stack, (case, parser.errors, parser.stack)
    assert sum(line.startswith('~~~') for line in md.splitlines()) % 2 == 0
    assert '## Top recommendation' in md and '## Skill and harness adaptation' in md
    assert 'Before' in html and 'After' in html and '<svg' in html
    assert 'PYTHONDONTWRITEBYTECODE=1' in md
    print(f'{case}: Markdown {len(md.encode())} bytes; HTML {len(html.encode())} bytes; structure and required sections OK')

