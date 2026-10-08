#!/usr/bin/env python3
"""Isolated dependency policy regressions; no project Git mutations."""
import copy
import json
import os
import stat
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'git-init'
MANIFEST = {'devDependencies': {'example': '1.2.3'}}
LOCK = {'lockfileVersion': 3, 'packages': {
    '': copy.deepcopy(MANIFEST),
    'node_modules/example': {'version': '1.2.3',
        'resolved': 'https://registry.example.test/example.tgz',
        'integrity': 'sha512-' + 'A' * 86 + '=='}}}


def snapshot(directory):
    result = {}
    def visit(parent):
        mode = parent.stat().st_mode
        # Read an intentionally unreadable fixture, then restore its permissions.
        parent.chmod(stat.S_IMODE(mode) | 0o700)
        try:
            for path in parent.iterdir():
                key = str(path.relative_to(directory))
                if path.is_symlink():
                    result[key] = ('link', os.readlink(path))
                elif path.is_dir():
                    result[key] = ('directory', stat.S_IMODE(path.stat().st_mode))
                    visit(path)
                elif path.is_file():
                    result[key] = path.read_bytes()
        finally:
            parent.chmod(stat.S_IMODE(mode))
    visit(directory)
    return result


def main():
    with tempfile.TemporaryDirectory(prefix='git-init-dependencies-') as temporary:
        base = Path(temporary)
        env = dict(os.environ, GIT_CONFIG_GLOBAL=str(base / 'global'),
                   GIT_CONFIG_SYSTEM='/dev/null', GIT_CONFIG_NOSYSTEM='1')
        (base / 'global').touch()
        def case(label, change=lambda d: None, expected=4):
            d = base / label
            d.mkdir()
            def git(*args):
                subprocess.run(['git', '-C', str(d), *args], env=env,
                               check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            git('init', '-q', '-b', 'main')
            git('config', 'user.name', 'Fixture')
            git('config', 'user.email', 'fixture@example.test')
            (d / '.gitignore').write_text('node_modules/\n')
            (d / 'package.json').write_text(json.dumps(MANIFEST))
            (d / 'package-lock.json').write_text(json.dumps(LOCK))
            (d / 'node_modules/example').mkdir(parents=True)
            (d / 'node_modules/example/cli.js').write_text('safe\n')
            (d / 'node_modules/.bin').mkdir()
            (d / 'node_modules/.bin/example').symlink_to('../example/cli.js')
            git('add', '.gitignore')
            git('commit', '-qm', 'test(fixture): baseline', '--no-verify')
            change(d)
            if label == 'not-ignored':
                git('add', '.gitignore')
                git('commit', '-qm', 'test(fixture): ignore policy', '--no-verify')
            case_env = dict(env)
            if label == 'find-partial-failure':
                tools = d / '.git/tools'
                tools.mkdir()
                wrapper = tools / 'find'
                wrapper.write_text('#!/bin/bash\n' + shutil.which('find') + ' "$@"\nfor arg in "$@"; do [[ $arg == -print0 ]] && exit 1; done\nexit 0\n')
                wrapper.chmod(0o755)
                case_env['PATH'] = str(tools) + os.pathsep + env['PATH']
            before = snapshot(d)
            for mode in ('--check', '--dry-run', '--init'):
                out = subprocess.run([str(SCRIPT), mode], cwd=d, env=case_env,
                                     text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                assert out.returncode == expected, f'{label} {mode}: {out.returncode}\n{out.stdout}'
                assert 'fixtureSensitiveValue' not in out.stdout, out.stdout
                if expected:
                    assert snapshot(d) == before, f'{label}: mutation'
            print('PASS:', label)
        def lock_change(d, mutate):
            value = copy.deepcopy(LOCK)
            mutate(value)
            (d / 'package-lock.json').write_text(json.dumps(value))
        def metadata(d, key, value):
            lock_change(d, lambda lock: lock['packages']['node_modules/example'].__setitem__(key, value))
        def ignored_content(d):
            (d / 'node_modules/example/content.js').write_bytes(b'\x00' + b'x' * 1048577 + b'\ntoken=fixtureSensitiveValue\n')
        case('valid-internal-bin-and-content', ignored_content, 0)
        case('not-ignored', lambda d: (d / '.gitignore').write_text(''))
        case('tracked', lambda d: subprocess.run(['git', '-C', str(d), 'add', '-f', 'node_modules/example/cli.js'], env=env, check=True))
        case('root-file', lambda d: (subprocess.run(['rm', '-r', str(d / 'node_modules')], check=True), (d / 'node_modules').write_text('file')))
        case('root-link', lambda d: ((d / 'node_modules').rename(d / 'deps'), (d / 'node_modules').symlink_to('deps')))
        for filename in ('.env', '.env.local', '.envrc', '.env-prod', '.environment', '.ENVRC', 'credentials.json', 'secret.txt', 'private-key', 'id_rsa', 'cert.pem', 'cert.key', 'cert.p12', 'db.sqlite', 'dump.sql', 'SECRET.txt'):
            case('filename-' + filename, lambda d, name=filename: (d / 'node_modules/example' / name).write_text('safe'))
        case('high-risk-directory', lambda d: (d / 'node_modules/example/.env').mkdir())
        case('non-bin-link', lambda d: (d / 'node_modules/example/link').symlink_to('cli.js'))
        case('external-bin', lambda d: (d / 'node_modules/.bin/external').symlink_to('/etc/passwd'))
        case('project-external-bin', lambda d: (d / 'node_modules/.bin/external').symlink_to('../../package.json'))
        case('broken-bin', lambda d: (d / 'node_modules/.bin/broken').symlink_to('../missing'))
        case('cycle-bin', lambda d: (d / 'node_modules/.bin/cycle').symlink_to('cycle'))
        case('directory-bin', lambda d: (d / 'node_modules/.bin/directory').symlink_to('../example'))
        case('bin-directory-link', lambda d: (subprocess.run(['rm', '-r', str(d / 'node_modules/.bin')], check=True), (d / 'node_modules/.bin').symlink_to('example')))
        case('missing-lock', lambda d: (d / 'package-lock.json').unlink())
        case('malformed-lock', lambda d: (d / 'package-lock.json').write_text('{'))
        case('duplicate-lock-key', lambda d: (d / 'package-lock.json').write_text('{"packages":{},"packages":{}}'))
        case('lock-root-list', lambda d: (d / 'package-lock.json').write_text('[]'))
        case('missing-packages', lambda d: lock_change(d, lambda lock: lock.pop('packages')))
        case('unsupported-lock', lambda d: lock_change(d, lambda lock: lock.__setitem__('lockfileVersion', 1)))
        case('root-mismatch', lambda d: lock_change(d, lambda lock: lock['packages'][''].__setitem__('devDependencies', {})))
        case('version-mismatch', lambda d: metadata(d, 'version', '1.2.4'))
        case('range-direct-version', lambda d: (d / 'package.json').write_text(json.dumps({'devDependencies': {'example': '^1.2.3'}})))
        case('missing-direct', lambda d: lock_change(d, lambda lock: lock['packages'].pop('node_modules/example')))
        for url in ('https://' + 'user:fixtureSensitiveValue@example.test/p', 'https://user%40example.test/p', 'https://example.test/p?token=fixtureSensitiveValue', 'https://example.test/p#fixtureSensitiveValue', 'file:../example', 'http://example.test/p'):
            case('url-' + str(len(list(base.iterdir()))), lambda d, value=url: metadata(d, 'resolved', value))
        for value in ('', 'sha512-invalid', 'sha1-' + 'A' * 28, 'sha512-YQ==', None):
            case('integrity-' + str(len(list(base.iterdir()))), lambda d, value=value: metadata(d, 'integrity', value))
        case('lock-link-entry', lambda d: metadata(d, 'link', True))
        case('find-partial-failure')
        case('generic-source-secret', lambda d: (d / 'source.js').write_text('token=fixtureSensitiveValue\n'))
        case('nested-dependencies-still-scanned', lambda d: ((d / 'nested/node_modules').mkdir(parents=True), (d / 'nested/node_modules/file').write_bytes(b'\x00')))
        for filename in ('.envrc', '.env-prod', '.environment'):
            case('generic-' + filename, lambda d, name=filename: (d / name).write_text('safe'))
        def transitive(d):
            path = d / 'node_modules/example/node_modules/transitive'
            path.mkdir(parents=True)
            return path
        case('root-transitive-content-policy', lambda d: (transitive(d) / 'code.js').write_bytes(b'\x00token=fixtureSensitiveValue'), 0)
        case('root-transitive-envrc', lambda d: (transitive(d) / '.envrc').write_text('token=fixtureSensitiveValue'))
        def unreadable(d, name):
            path = d / name
            path.mkdir(parents=True)
            (path / 'file').write_text('safe')
            path.chmod(0)
        assert os.geteuid() != 0, 'Permission regressions require an unprivileged user'
        for name in ('node_modules/example/unreadable', 'sub/node_modules', 'source/unreadable'):
            case('permission-' + name.replace('/', '-'), lambda d, path=name: unreadable(d, path))
        def version(d, value, direct=True):
            lock = copy.deepcopy(LOCK)
            lock['packages']['node_modules/example']['version'] = value
            if direct:
                manifest = {'devDependencies': {'example': value}}
                (d / 'package.json').write_text(json.dumps(manifest))
                lock['packages'][''] = manifest
            else:
                lock['packages']['node_modules/transitive'] = dict(lock['packages']['node_modules/example'])
                lock['packages']['node_modules/example']['version'] = '1.2.3'
            (d / 'package-lock.json').write_text(json.dumps(lock))
        for index, value in enumerate(('01.2.3', '1.02.3', '1.2.03', '1.2.3-01', '1.2.3-alpha.01', '1.2.3-alpha..beta', '1.2.3-', '1.2.3+', '1.2.3+build..x', '１.2.3', '1.2.3\n')):
            case('invalid-semver-' + str(index), lambda d, v=value: version(d, v))
            case('invalid-transitive-semver-' + str(index), lambda d, v=value: version(d, v, False))
        for index, value in enumerate(('0.0.0', '1.2.3-alpha.0', '1.2.3-0alpha.01a', '1.2.3+001.build', '1.2.3-alpha-beta+build.01')):
            case('valid-semver-' + str(index), lambda d, v=value: version(d, v), 0)
        for index, port in enumerate(('notaport', '65536', '-1', '', '0')):
            case('invalid-port-' + str(index), lambda d, p=port: metadata(d, 'resolved', 'https://registry.example.test:' + p + '/pkg.tgz'))
        case('valid-port', lambda d: metadata(d, 'resolved', 'https://registry.example.test:8443/pkg.tgz'), 0)
        case('generic-source-link', lambda d: (d / 'link').symlink_to('package.json'))
        case('valid-v2', lambda d: lock_change(d, lambda lock: lock.__setitem__('lockfileVersion', 2)), 0)
        assert (base / 'global').read_bytes() == b''


if __name__ == '__main__':
    main()
