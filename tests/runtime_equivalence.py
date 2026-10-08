#!/usr/bin/env python3
"""Capture actual fixture arguments and scanner grep argv without running harness setup."""
import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / 'tests/runtime-equivalence-baseline.json'


def capture():
    inputs = {}
    tree = ast.parse((ROOT / 'tests/dependencies.py').read_text())
    loop = next(n for n in ast.walk(tree) if isinstance(n, ast.For)
                and isinstance(n.target, ast.Name) and n.target.id == 'url')
    calls = []
    def case(label, change):
        change(None)
    exec(compile(ast.Module(body=[loop], type_ignores=[]), '<fixture>', 'exec'),
         {'case': case, 'metadata': lambda d, key, value: calls.append(value),
          'base': Path('/tmp')})
    inputs['dependencies URL metadata'] = [v.encode().hex() for v in calls]
    tree = ast.parse((ROOT / 'tests/preflight.py').read_text())
    call = next(n for n in ast.walk(tree) if isinstance(n, ast.Call)
                and isinstance(n.func, ast.Name) and n.func.id == 'git'
                and any(isinstance(a, ast.Constant) and a.value == 'private' for a in n.args))
    calls = []
    exec(compile(ast.Expression(call), '<fixture>', 'eval'),
         {'git': lambda *args, **kwargs: calls.append(args[-1]), 'remotes': None, 'env': {}})
    inputs['preflight remote'] = [v.encode().hex() for v in calls]
    lines = (ROOT / 'tests/run.sh').read_text().splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith('d=$(newdir remote)'))
    end = next(i for i in range(start, len(lines)) if 'remote add origin' in lines[i])
    line = '\n'.join(lines[start:end + 1])
    result = subprocess.run(['bash', '-c', 'newdir() { :; }; setup_repo() { :; }; '
                             'git() { printf "%s\\0" "$@"; }; ' + line],
                            check=True, stdout=subprocess.PIPE)
    inputs['run.sh remote'] = [result.stdout.split(b'\0')[-2].hex()]
    source = (ROOT / 'git-init').read_text()
    function = source[source.index('scan_file() {'):source.index('\n}\n', source.index('scan_file() {')) + 3]
    with tempfile.TemporaryDirectory(prefix='runtime-equivalence-') as temporary:
        directory = Path(temporary)
        fixture = directory / 'input'
        fixture.write_bytes(b'token=' + b'abcdefgh\n')
        argv = directory / 'argv'
        script = ('issue() { :; }; EXIT_RISK=4; TARGET_DIR=/tmp; '
                  'grep() { printf "%s\\0" "$@" >> "$ARGV"; printf "\\0" >> "$ARGV"; command grep "$@"; };\n'
                  + function + '\nscan_file "$INPUT" input\n')
        subprocess.run(['bash', '-c', script], check=True,
                       env=dict(os.environ, ARGV=str(argv), INPUT=str(fixture)), stdout=subprocess.PIPE)
        commands = [c.split(b'\0') for c in argv.read_bytes().split(b'\0\0') if c]
        token_calls = [c for c in commands if c[0] == b'-Ein'][:2]
        assert len(token_calls) == 2
        patterns = [c[-3] for c in token_calls]
        assert patterns[0] == patterns[1]
        flags = [c[:-3] for c in token_calls]
        matches = []
        rows = [b'token=' + b'abcdefgh', b'TOKEN: abcdefgh', b'api-key = abcdefgh',
                b'authorization' + b':BearerABC', b'x ' + b'token=' + b'abcdefgh # comment',
                b'token=short', b'xtoken=abcdefgh', b'token=#abcdefgh', b'ordinary source',
                b'password = 12345678\nsecret=abcdefgh', b'authorization' + b': abcdefg']
        for row in rows:
            for options in flags:
                out = subprocess.run(['grep', *[v.decode() for v in options], patterns[0].decode()],
                                     input=row + b'\n', stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                matches.append({'input': row.hex(), 'flags': [v.decode() for v in options],
                                'rc': out.returncode, 'stdout': out.stdout.hex(), 'stderr': out.stderr.hex()})
    return {'fixture_bytes_hex': inputs, 'regex_bytes_hex': patterns[0].hex(),
            'grep_flags': [[v.decode() for v in f] for f in flags], 'matches': matches}


def main():
    actual = capture()
    if '--record' in sys.argv:
        GOLDEN.write_text(json.dumps(actual, indent=2) + '\n')
        print('BASELINE: captured runtime fixture bytes, regex bytes, grep flags and matches')
    else:
        assert actual == json.loads(GOLDEN.read_text()), 'runtime bytes/flags/matches changed'
        print('PASS: exact runtime fixture bytes, regex bytes, grep flags and matches')
    if '--remediated' in sys.argv:
        source = (ROOT / 'git-init').read_text()
        function = source[source.index('scan_file() {'):source.index('\n}\n', source.index('scan_file() {')) + 3]
        risks = []
        for path in ('git-init', 'tests/dependencies.py', 'tests/preflight.py', 'tests/run.sh', 'tests/runtime_equivalence.py'):
            script = 'issue() { printf "RISK\\n"; }; EXIT_RISK=4; TARGET_DIR="$PWD";\n' + function + '\nscan_file "$1" "$1"'
            result = subprocess.run(['bash', '-c', script, 'scan', str(ROOT / path)],
                                    check=True, stdout=subprocess.PIPE)
            if result.stdout:
                risks.append(path)
        assert not risks, f'static representation still raises risks: {risks}'
        print('PASS: all four static source risks absent under unchanged scanner')
    print('baseline sha256:', hashlib.sha256(GOLDEN.read_bytes()).hexdigest())


if __name__ == '__main__':
    main()
