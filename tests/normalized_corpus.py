#!/usr/bin/env python3
"""Exercise the production policy against data; execute no upstream PHP."""
import ast
import json
import re
import sys
sys.dont_write_bytecode = True
from pathlib import Path
from extract_normalized_corpus import extract, ROOT

script = (ROOT.parent / 'git-init').read_text()
embedded = script.split("<<'PYV'\n", 1)[1].split('\nPYV', 1)[0]
tree = ast.parse(embedded)
nodes = [node for node in tree.body if isinstance(node, (ast.ClassDef, ast.FunctionDef))
         and node.name in ('NormalizedVersionError', 'validate_normalized_version')]
assert len(nodes) == 2
namespace = {'re': re}
exec(compile(ast.Module(body=nodes, type_ignores=[]), '<production normalized policy>', 'exec'), namespace)
validate = namespace['validate_normalized_version']
error = namespace['NormalizedVersionError']
corpus = json.loads((ROOT / 'corpus/normalized-outputs.json').read_text())
assert corpus == extract(ROOT / 'corpus/VersionParserTest.php'), 'corpus is not reproducible'
for record in corpus['records']:
    try:
        validate(record['output'])
    except error:
        raise AssertionError('material corpus grammar gap: ' + record['provider'] + '/' + record['label']) from None
print('PASS: all', len(corpus['records']), 'upstream successful normalized outputs/branches')

# Input-only spellings are classified using the actual expected normalize
# output. A changed input is not automatically invalid as an output: dev-
# aliases and stability flags can themselves be arbitrary branch names.
examples = {
    'strips leading v': False,
    'expand shorthand/2': False,
    'semver metadata/3': False,
    'parses branches': False,
    'RC uppercase': False,
    'ignores aliases': True,
    'ignores stability/2': True,
    'parses arbitrary/2': False,
}
for label, accepted in examples.items():
    record = next(r for r in corpus['records'] if r['provider'] == 'successfulNormalizedVersions' and r['label'] == label)
    assert record['input'] != record['output']
    try:
        validate(record['input'])
        actual = True
    except error:
        actual = False
    assert actual == accepted, label
# Pinned normalize() explicitly returns the numeric base for lowercase stable
# (VersionParser.php lines 154-159); this pair is source-derived, not invented
# as an upstream provider row. Only its numeric output is canonical here.
assert corpus['stable_source']['input'] == '1.2.3.0-stable'
validate(corpus['stable_source']['output'])
for value in ('1.2.3.0-stable', '1.2.3.0-stable-dev'):
    try:
        validate(value)
    except error:
        continue
    raise AssertionError('stable input spelling accepted as numeric output')
validate('dev-feature-stable')
print('PASS: input-only spelling classification, including stable; arbitrary branches retained')
