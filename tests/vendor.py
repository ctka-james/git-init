#!/usr/bin/env python3
"""Composer fixtures never execute PHP or mutate the project repository."""
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path
sys.dont_write_bytecode = True
from dependencies import snapshot as dependency_snapshot, SCRIPT

def snapshot(directory):
    result = dependency_snapshot(directory)
    for parent, dirs, files in os.walk(directory, followlinks=False):
        for name in files:
            path = Path(parent) / name
            mode = path.lstat().st_mode
            if not (stat.S_ISREG(mode) or stat.S_ISLNK(mode)):
                result[str(path.relative_to(directory))] = ("special", mode)
    return result

PACKAGE = {'name': 'example/library', 'version': 'v1.2.3', 'type': 'library',
           'dist': {'type': 'zip', 'url': 'https://example.test/library.zip', 'reference': 'abc'}}
PHP = """<?php return array (
 'root' => array ('name' => 'fixture/project'),
 'versions' => array (
  'fixture/project' => array ('pretty_version' => 'dev-main', 'install_path' => __DIR__ . '/../..'),
  'example/library' => array ('pretty_version' => 'v1.2.3', 'version' => '1.2.3.0', 'reference' => 'abc', 'install_path' => __DIR__ . '/../example/library', 'dev_requirement' => false),
 ),
);
"""

def main():
    with tempfile.TemporaryDirectory(prefix='git-init-vendor-') as temporary:
        base = Path(temporary)
        env = dict(os.environ, GIT_CONFIG_GLOBAL=str(base / 'global'), GIT_CONFIG_SYSTEM='/dev/null', GIT_CONFIG_NOSYSTEM='1')
        (base / 'global').touch()
        def case(label, change=lambda d, git: None, expected=4, category=None):
            d = base / label; d.mkdir()
            def git(*args):
                subprocess.run(['git', '-C', str(d), *args], env=env, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            git('init', '-q', '-b', 'main'); git('config', 'user.name', 'Fixture'); git('config', 'user.email', 'fixture@example.test')
            (d / '.gitignore').write_text('vendor/\n')
            (d / 'composer.lock').write_text(json.dumps({'packages': [PACKAGE], 'packages-dev': []}))
            (d / 'vendor/composer').mkdir(parents=True)
            (d / 'vendor/example/library').mkdir(parents=True)
            item = dict(PACKAGE, **{'install-path': '../example/library', 'version_normalized': '1.2.3.0'})
            (d / 'vendor/composer/installed.json').write_text(json.dumps({'packages': [item], 'dev': True}))
            (d / 'vendor/composer/installed.php').write_text(PHP)
            (d / 'vendor/example/library/code.php').write_bytes(b'\x00token=fixtureSensitiveValue\n' + b'x' * 1048577)
            git('add', '.gitignore'); git('commit', '-qm', 'test(fixture): baseline', '--no-verify')
            change(d, git); before = snapshot(d); failures = []
            for mode in ('--check', '--dry-run', '--init'):
                out = subprocess.run([str(SCRIPT), mode], cwd=d, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                if out.returncode != expected:
                    failures.append(f'{label} {mode}: expected {expected}, got {out.returncode}\n{out.stdout}')
                    continue
                if category is not None:
                    assert re.findall(r'^RISK: (vendor Composer .*?)（內容已遮蔽）$', out.stdout, re.M) == [category], f'{label} {mode}: missing category\n{out.stdout}'
                    assert 'vendor Composer metadata invalid' not in out.stdout, f'{label} {mode}: generic metadata failure'
                    if category == 'vendor Composer normalized version invalid':
                        for filename in ('composer.lock', 'vendor/composer/installed.json'):
                            for item in json.loads((d / filename).read_text())['packages']:
                                value = item.get('version_normalized')
                                if isinstance(value, str) and value:
                                    assert value not in out.stdout, f'{label} {mode}: normalized value leak'

                    for value in ('123456789', '98765.4321', 'referenceSensitiveValue', 'validSourceReferenceValue', 'abc', 'bad normalized version', 'normalizedSensitiveValue'):
                        assert value not in out.stdout, f'{label} {mode}: metadata leak'
                assert 'fixtureSensitiveValue' not in out.stdout
                if expected or mode != '--init': assert snapshot(d) == before, label + ': mutation'
            assert not failures, '\n'.join(failures)
            print('PASS:', label)
        case('valid', expected=0)
        case('not-ignored', lambda d,g: ((d / '.gitignore').write_text(''), g('add', '.gitignore'), g('commit', '-qm', 'test(fixture): ignore', '--no-verify')))
        case('staged', lambda d,g: g('add', '-f', 'vendor/composer/installed.php'))
        case('tracked', lambda d,g: (g('add', '-f', 'vendor/composer/installed.php'), g('commit', '-qm', 'test(fixture): tracked', '--no-verify')))
        case('non-git', lambda d,g: shutil.rmtree(d / '.git'))
        case('root-file', lambda d,g: (shutil.rmtree(d / 'vendor'), (d / 'vendor').write_text('safe')))
        case('root-link', lambda d,g: ((d / 'vendor').rename(d / 'deps'), (d / 'vendor').symlink_to('deps')))
        for target in ('code.php', '/etc/passwd', '../../../composer.lock', 'missing', 'link'):
            case('link-' + str(len(list(base.iterdir()))), lambda d,g,t=target: (d / 'vendor/example/library/link').symlink_to(t))
        for name in ('.envrc', 'SECRET.txt', 'key.pem'):
            case('filename-' + name, lambda d,g,n=name: (d / 'vendor/example/library' / n).write_text('safe'))
        case('fifo', lambda d,g: os.mkfifo(d / 'vendor/fifo'))
        def unreadable(d,g):
            (d / 'vendor/unreadable').mkdir(); (d / 'vendor/unreadable').chmod(0)
        assert os.geteuid() != 0
        case('traversal', unreadable)
        case('php-mismatch', lambda d,g: (d / 'vendor/composer/installed.php').write_text(PHP.replace('v1.2.3', 'v1.2.4')))
        case('path-escape', lambda d,g: (d / 'vendor/composer/installed.php').write_text(PHP.replace('/../example/library', '/../..')))
        case('executable-php', lambda d,g: (d / 'vendor/composer/installed.php').write_text("<?php file_put_contents('executed', 'yes'); return [];"))
        case('json-mismatch', lambda d,g: (d / 'vendor/composer/installed.json').write_text('{"packages":[],"dev":true}'))
        case('normalized-mismatch', lambda d,g: (d / 'vendor/composer/installed.php').write_text(PHP.replace('1.2.3.0', '1.2.4.0')))
        def metadata(d, filename, change):
            path = d / filename
            data = json.loads(path.read_text())
            change(data['packages'][0])
            path.write_text(json.dumps(data))
        def locked_normalized(d, g, json_version='1.2.3.0', php_version='1.2.3.0'):
            metadata(d, 'composer.lock', lambda p: p.update(version_normalized='1.2.3.0'))
            metadata(d, 'vendor/composer/installed.json', lambda p: p.update(version_normalized=json_version) if json_version is not None else p.pop('version_normalized'))
            (d / 'vendor/composer/installed.php').write_text(PHP.replace('1.2.3.0', php_version))
        def coordinated_normalized(d, g, value, php_value=None, omit=()):
            for filename in ('composer.lock', 'vendor/composer/installed.json'):
                metadata(d, filename, lambda p: p.update(version_normalized=value) if filename not in omit else p.pop('version_normalized', None))
            literal = php_value if php_value is not None else "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"
            (d / 'vendor/composer/installed.php').write_text(PHP.replace("'1.2.3.0'", literal))
        category = 'vendor Composer normalized version invalid'
        for label, value in (
            ('stable-output', '1.2.3.0-stable'),
            ('spaces', 'bad normalized version'), ('arbitrary', 'normalizedSensitiveValue'),
            ('empty', ''), ('short', '1.2.3'), ('leading-v', 'v1.2.3.0'),
            ('build', '1.2.3.0+build'), ('unknown-stability', '1.2.3.0-meh'),
            ('shorthand', '1.2.3.0-b1'), ('lowercase-rc', '1.2.3.0-rc1'),
            ('too-many-parts', '1.2.3.0.0'), ('bad-calver', '2023013.0.0'),
            ('wildcard', '1.x-dev'), ('control', '1.2.3.0\n'),
        ):
            case('normalized-coordinated-invalid-' + label, lambda d,g,v=value: coordinated_normalized(d,g,v), category=category)
        for label, value, literal in (
            ('null', None, 'null'), ('integer', 123456789, '123456789'),
            ('float', 98765.4321, '98765.4321'), ('true', True, 'true'), ('false', False, 'false'),
            ('list', ['normalizedSensitiveValue'], "array ('normalizedSensitiveValue')"),
            ('object', {'value': 'normalizedSensitiveValue'}, "array ('value' => 'normalizedSensitiveValue')"),
        ):
            case('normalized-coordinated-type-' + label, lambda d,g,v=value,p=literal: coordinated_normalized(d,g,v,p), category=category)
        # Optional JSON fields must not leave installed PHP's version unchecked.
        for label, omit in (('no-lock', ('composer.lock',)), ('php-only', ('composer.lock', 'vendor/composer/installed.json'))):
            case('normalized-invalid-' + label, lambda d,g,o=omit: coordinated_normalized(d,g,'normalizedSensitiveValue',omit=o), category=category)
        for filename in ('composer.lock', 'vendor/composer/installed.json'):
            case('normalized-invalid-only-' + filename.replace('/', '-'),
                 lambda d,g,f=filename: metadata(d,f,lambda p: p.update(version_normalized='normalizedSensitiveValue')), category=category)
        for label, value, literal in (
            ('null', None, 'null'), ('integer', 123456789, '123456789'),
            ('true', True, 'true'), ('false', False, 'false'),
            ('list', [], 'array ()'), ('object', {}, "array ('value' => 'normalizedSensitiveValue')"),
        ):
            case('normalized-php-only-type-' + label,
                 lambda d,g,v=value,p=literal: coordinated_normalized(d,g,v,p,omit=('composer.lock', 'vendor/composer/installed.json')), category=category)
        def uninstalled_dev(d, g):
            path = d / 'composer.lock'
            data = json.loads(path.read_text())
            data['packages-dev'] = [dict(PACKAGE, name='example/dev', version_normalized='normalizedSensitiveValue')]
            path.write_text(json.dumps(data))
        case('normalized-invalid-uninstalled-dev', uninstalled_dev, category=category)
        case('normalized-supported-internal-space-dev', lambda d,g: coordinated_normalized(d,g,'dev-foo bar'), expected=0)
        case('normalized-supported-default-alias', lambda d,g: coordinated_normalized(d,g,'9999999-dev'), expected=0)
        # Expected outputs from the pinned upstream successfulNormalizedVersions/Branches.
        for label, pretty, normalized in (
            ('stable', '1.2.3.4', '1.2.3.4'),
            ('zero-padding', '00.01.03.04', '00.01.03.04'),
            ('maximum-major', '99999', '99999.0.0.0'),
            ('date', 'v20100102', '20100102'),
            ('date-short', '100000', '100000'),
            ('calver', '20230131.0.0', '20230131.0.0'),
            ('datetime', '2010-01-02-10-20-30.0.3', '2010.01.02.10.20.30.0.3'),
            ('date-patch', '20100102-203040-p1', '20100102.203040-patch1'),
            ('alpha-compound', '1.0.0-alpha-2.1-3+foo', '1.0.0.0-alpha2.1-3'),
            ('beta', '10.4.13-beta', '10.4.13.0-beta'),
            ('rc-dev', '1.0.0RC1dev', '1.0.0.0-RC1-dev'),
            ('patch-dev', '1.0.0.pl3-dev', '1.0.0.0-patch3-dev'),
            ('numeric-dev', '1.0-dev', '1.0.0.0-dev'),
            ('branch', '1.x-dev', '1.9999999.9999999.9999999-dev'),
            ('date-branch', '20100102.x-dev', '20100102.9999999.9999999.9999999-dev'),
            ('named-dev', 'dev-master', 'dev-master'),
            ('slash-dev', 'dev-feature/foo', 'dev-feature/foo'),
            ('plus-dev', 'dev-feature+issue-1', 'dev-feature+issue-1'),
            ('mixed-case-dev', 'DEV-FOOBAR', 'dev-FOOBAR'),
            ('comparison-dev', 'dev-1.0.0-dev<1.0.5-dev', 'dev-1.0.0-dev<1.0.5-dev'),
        ):
            def supported(d, g, pretty=pretty, normalized=normalized):
                coordinated_normalized(d, g, normalized)
                for filename in ('composer.lock', 'vendor/composer/installed.json'):
                    metadata(d, filename, lambda p: p.update(version=pretty))
                path = d / 'vendor/composer/installed.php'
                path.write_text(path.read_text().replace('v1.2.3', pretty))
            case('normalized-supported-' + label, supported, expected=0)
        case('lock-normalized-valid', locked_normalized, expected=0)
        case('lock-normalized-coordinated-mismatch', lambda d,g: locked_normalized(d,g,'1.2.4.0','1.2.4.0'))
        case('lock-normalized-json-missing', lambda d,g: locked_normalized(d,g,None))
        case('lock-normalized-json-mismatch', lambda d,g: locked_normalized(d,g,'1.2.4.0'))
        case('lock-normalized-php-mismatch', lambda d,g: locked_normalized(d,g,php_version='1.2.4.0'))
        def no_reference(d, g, kind, php_reference):
            for filename in ('composer.lock', 'vendor/composer/installed.json'):
                def change(p):
                    p.pop('dist')
                    if kind is not None: p[kind] = {'type': 'zip'}
                metadata(d, filename, change)
            (d / 'vendor/composer/installed.php').write_text(PHP.replace("'reference' => 'abc'", "'reference' => " + php_reference))
        for kind in (None, 'source', 'dist'):
            case('absent-reference-' + str(kind), lambda d,g,k=kind: no_reference(d,g,k,"'stale'"))
            case('null-reference-' + str(kind), lambda d,g,k=kind: no_reference(d,g,k,'null'), expected=0)
        def source_reference(d, g, source, php_reference):
            for filename in ('composer.lock', 'vendor/composer/installed.json'):
                metadata(d, filename, lambda p: p.update(source=source))
            (d / 'vendor/composer/installed.php').write_text(PHP.replace("'reference' => 'abc'", "'reference' => " + php_reference))
        for label, source in (
            ('null', {'reference': None}),
            ('missing', {}),
            ('empty', {'reference': ''}),
        ):
            case('source-reference-' + label + '-dist-valid', lambda d,g,s=source: source_reference(d,g,s,"'abc'"), expected=0)
            case('source-reference-' + label + '-dist-mismatch', lambda d,g,s=source: source_reference(d,g,s,"'stale'"))
            case('source-reference-' + label + '-dist-null-mismatch', lambda d,g,s=source: source_reference(d,g,s,'null'))
        case('source-reference-precedence-valid', lambda d,g: source_reference(d,g,{'reference': 'validSourceReferenceValue'},"'validSourceReferenceValue'"), expected=0)
        case('source-reference-precedence-mismatch', lambda d,g: source_reference(d,g,{'reference': 'validSourceReferenceValue'},"'abc'"))
        def references(d, g, source, dist, php_reference):
            for filename in ('composer.lock', 'vendor/composer/installed.json'):
                metadata(d, filename, lambda p: p.update(source={'reference': source}, dist={'reference': dist}))
            (d / 'vendor/composer/installed.php').write_text(PHP.replace("'reference' => 'abc'", "'reference' => " + php_reference))
        for label, value, php_value in (
            ('integer', 123456789, '123456789'),
            ('float', 98765.4321, '98765.4321'),
            ('list', ['referenceSensitiveValue'], "array ('referenceSensitiveValue')"),
            ('object', {'value': 'referenceSensitiveValue'}, "array ('value' => 'referenceSensitiveValue')"),
            ('bool', True, 'true'),
            ('false', False, 'false'),
        ):
            case('source-reference-' + label + '-php-matching', lambda d,g,v=value,p=php_value: references(d,g,v,'abc',p), category='vendor Composer reference type invalid')
            case('source-reference-' + label + '-dist-valid', lambda d,g,v=value: references(d,g,v,'abc',"'abc'"), category='vendor Composer reference type invalid')
            case('dist-reference-' + label + '-php-matching', lambda d,g,v=value,p=php_value: references(d,g,None,v,p), category='vendor Composer reference type invalid')
            case('dist-reference-' + label + '-source-valid', lambda d,g,v=value: references(d,g,'validSourceReferenceValue',v,"'validSourceReferenceValue'"), category='vendor Composer reference type invalid')
        for label, value in (('null', None), ('empty', '')):
            case('dist-reference-' + label + '-source-valid', lambda d,g,v=value: references(d,g,'validSourceReferenceValue',v,"'validSourceReferenceValue'"), expected=0)
            case('references-empty-source-dist-' + label, lambda d,g,v=value: references(d,g,'',v,'null'), expected=0)
            case('references-empty-source-dist-' + label + '-php-empty', lambda d,g,v=value: references(d,g,'',v,"''"))
        def metapackage(d, g, json_path, php_path):
            metadata(d, 'composer.lock', lambda p: p.update(type='metapackage'))
            metadata(d, 'vendor/composer/installed.json', lambda p: p.update(type='metapackage', **{'install-path': json_path}))
            (d / 'vendor/composer/installed.php').write_text(PHP.replace("__DIR__ . '/../example/library'", php_path))
        case('metapackage-valid', lambda d,g: metapackage(d,g,None,'null'), expected=0)
        case('metapackage-json-path', lambda d,g: metapackage(d,g,'../example/library','null'))
        case('metapackage-php-path', lambda d,g: metapackage(d,g,None,"__DIR__ . '/../example/library'"))
        case('reference-mismatch', lambda d,g: (d / 'vendor/composer/installed.php').write_text(PHP.replace("'abc'", "'other'")))
        case('missing-php', lambda d,g: (d / 'vendor/composer/installed.php').unlink())
        case('missing-json', lambda d,g: (d / 'vendor/composer/installed.json').unlink())
        case('malformed-json', lambda d,g: (d / 'vendor/composer/installed.json').write_text('{'))
        case('missing-lock', lambda d,g: (d / 'composer.lock').unlink())
        case('duplicate-lock', lambda d,g: (d / 'composer.lock').write_text('{"packages":[],"packages":[],"packages-dev":[]}'))
        case('metadata-link', lambda d,g: ((d / 'vendor/composer/installed.json').unlink(), (d / 'vendor/composer/installed.json').symlink_to('../../composer.lock')))
        case('generic-source-secret', lambda d,g: (d / 'source.php').write_text('token=fixtureSensitiveValue\n'))
        case('nested-vendor', lambda d,g: ((d / 'src/vendor').mkdir(parents=True), (d / 'src/vendor/code.php').write_bytes(b'\x00')))
        assert (base / 'global').read_bytes() == b''

if __name__ == '__main__': main()
