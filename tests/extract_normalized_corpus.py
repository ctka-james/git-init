#!/usr/bin/env python3
"""Read pinned PHP literal providers; never execute PHP or upstream tests."""
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SHA256 = '3ad4d38753436d3508eb120b220f8f343f0308d13d4d8867921246aa125d6005'
COMMIT = '198166618906cb2de69b95d7d47e5fa8aa1b2b95'
PROVIDERS = ('successfulNormalizedVersions', 'successfulNormalizedBranches')


def extract(source):
    raw = source.read_bytes()
    if hashlib.sha256(raw).hexdigest() != SHA256:
        raise ValueError('pinned upstream source SHA-256 mismatch')
    text = raw.decode('utf-8')
    # The pinned providers contain only one labelled pair of single-quoted PHP
    # strings per active line. Fail closed on any unrecognized active syntax.
    literal = r"'((?:[^'\\]|\\.)*)'"
    row = re.compile(r'\s*' + literal + r'\s*=>\s*array\(' + literal + r',\s*' + literal + r'\),\s*')
    def decode(value):
        return value.replace("\\'", "'").replace('\\\\', '\\')
    records = []
    for provider in PROVIDERS:
        match = re.search(r'public static function ' + provider + r'\(\)\s*\{\s*return array\((.*?)\n\s*\);\s*\}', text, re.S)
        if not match:
            raise ValueError('missing provider: ' + provider)
        count = 0
        for line in match[1].splitlines():
            if not line.strip() or line.lstrip().startswith('//'):
                continue
            item = row.fullmatch(line)
            if not item:
                raise ValueError('unsupported provider syntax: ' + provider)
            label, input_value, output = map(decode, item.groups())
            records.append(dict(provider=provider, label=label, input=input_value, output=output))
            count += 1
        if not count:
            raise ValueError('empty provider: ' + provider)
    parser = source.with_name('VersionParser.php').read_bytes()
    parser_sha = '63311ae28a20ca266fb0d9599cbb39c60aed64f69aadc59052b34b9b32043e17'
    if hashlib.sha256(parser).hexdigest() != parser_sha:
        raise ValueError('pinned upstream parser SHA-256 mismatch')
    outputs = {record['output'] for record in records}
    # Changed input spelling alone is not evidence of an invalid output. In
    # particular dev- aliases/flags can also be literal branch names. Preserve
    # the facts for classification; do not generate blanket rejection rules.
    return dict(source=dict(package='composer/semver', version='3.4.4', commit=COMMIT,
                            path='tests/VersionParserTest.php', sha256=SHA256,
                            url=f'https://raw.githubusercontent.com/composer/semver/{COMMIT}/tests/VersionParserTest.php'),
                method='Static complete labelled literal-pair extraction from both successful providers; comments excluded; no PHP execution.',
                counts={p: sum(r['provider'] == p for r in records) for p in PROVIDERS},
                stable_source=dict(path='src/VersionParser.php', sha256=parser_sha,
                                   url=f'https://raw.githubusercontent.com/composer/semver/{COMMIT}/src/VersionParser.php',
                                   lines='154-159', input='1.2.3.0-stable', output='1.2.3.0',
                                   method='Read normalize(): lowercase stable returns numeric base; source-derived pair, not a provider fixture.'),
                records=records,
                changed_inputs=[r for r in records if r['input'] != r['output'] and r['input'] not in outputs])


if __name__ == '__main__':
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'corpus/VersionParserTest.php'
    rendered = json.dumps(extract(source), ensure_ascii=False, indent=2) + '\n'
    target = ROOT / 'corpus/normalized-outputs.json'
    if '--check' in sys.argv[2:]:
        if target.read_text() != rendered:
            raise SystemExit('corpus differs from reproducible extraction')
        print('PASS: reproducible pinned corpus')
    else:
        target.write_text(rendered)
