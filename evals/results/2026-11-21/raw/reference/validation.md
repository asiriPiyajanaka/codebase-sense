# Report artifact validation

Four reports are complete: checkout.md/.html, ledger.md/.html, click.md/.html, and flask.md/.html. Each audit contains its workflow findings, source references, architectural assessment, useful behavioral tests, skill/harness adaptations, exact test commands and results. No source or test was edited. No additional passing suite was rerun during artifact preparation.

## Saved executable probe source

- checkout-probe.py: exact-replay, changed payload, reward-insertion failure using in-memory SQLite.
- click-cleanup-probe.py: cleanup raises and the current Context remains set.
- click-parse-probe.py: parse failure leaves registered cleanup uncalled.
- flask-probe.py: code/scope precedence, trap with handler, handler failure and propagation.
- validate-reports.py: the structural HTML/Markdown check below.

Each probe's original exact heredoc command and output are preserved in its case Markdown report. The scripts were saved after those executions and were not rerun merely to save them.

## Initial structural check

Working directory: /Users/asiripiyajanaka/Workspace/Skills/codebase-sense

Exact command:

~~~sh
env PYTHONDONTWRITEBYTECODE=1 /private/tmp/codebase-sense-qa-91vasxy9/venv/bin/python - <<'PY'
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
PY
~~~

Exit code: 1. Exact output:

~~~text
Traceback (most recent call last):
  File "<stdin>", line 22, in <module>
AssertionError: ('checkout', [('svg', 'rect'), ('section', 'rect'), ('svg', 'rect'), ('section', 'rect'), ('div', 'rect'), ('article', 'rect'), ('main', 'rect'), ('body', 'rect'), ('html', 'rect')], ['html', 'body', 'main', 'article', 'div', 'section', 'svg', 'rect', 'rect', 'rect', 'rect', 'section', 'svg', 'rect', 'rect'])
~~~

The emitted SVG had unquoted numeric final attributes immediately followed by the self-closing slash; HTML parsing treated that slash as part of the attribute value. The report HTML was corrected by placing whitespace before self-closing slashes. This affected report artifacts only.

## Check after artifact correction

Exact command:

~~~sh
env PYTHONDONTWRITEBYTECODE=1 /private/tmp/codebase-sense-qa-91vasxy9/venv/bin/python /private/tmp/codebase-sense-qa-91vasxy9/jobs/reference/reports/validate-reports.py
~~~

Exit code: 0. Exact output:

~~~text
checkout: Markdown 9910 bytes; HTML 17243 bytes; structure and required sections OK
ledger: Markdown 9890 bytes; HTML 17247 bytes; structure and required sections OK
click: Markdown 15270 bytes; HTML 23364 bytes; structure and required sections OK
flask: Markdown 18809 bytes; HTML 26893 bytes; structure and required sections OK
~~~

HTML tags, required sections, code-fence pairing and diagram presence pass the structural check. No browser or window was opened, so this is structural verification rather than rendered visual inspection. Inline SVG and embedded CSS provide readable diagrams without CDN execution; CDN references required by the skill were never fetched.

## Outstanding validation limitation

Flask's initial selected run reported 1 failed, 217 passed, 2 skipped. tests/test_reqctx.py::test_bad_environ_raises_bad_request observed 404 instead of its expected 400. Its cause was not established and no source or dependency was changed. The narrower error-handler/blueprint/basic/signals set passed 206 tests. Both commands and outputs remain in flask.md. There are no blockers to reviewing the four completed audits.

