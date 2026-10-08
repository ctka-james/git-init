This is a data corpus for the custom normalized-output policy, not a claim of
equivalence to the upstream parser. No PHP runtime is needed and upstream code
is never executed. Both PHP files are read as source data only, under the included
upstream LICENSE.

Pinned source: composer/semver 3.4.4, commit
`198166618906cb2de69b95d7d47e5fa8aa1b2b95`. File paths, raw GitHub URLs and
SHA-256 values are stored in `normalized-outputs.json`. The checked-in source
copies allow offline reproduction:

    python3 tests/extract_normalized_corpus.py
    python3 tests/extract_normalized_corpus.py tests/corpus/VersionParserTest.php --check
    python3 tests/normalized_corpus.py

Extraction verifies the exact source bytes, then reads every active labelled
literal pair from successfulNormalizedVersions (73 rows) and
successfulNormalizedBranches (13 rows). It excludes comments (including two
unsupported commented examples) and fails on unrecognized active syntax rather
than silently extracting a subset. No eval, PHP interpreter or upstream tests
are used. The local test executes only the production Python validator selected
by AST from git-init.

The corpus records changed input spellings alongside their actual upstream
expected outputs. Those facts are not blanket rejection rules: for example,
`dev-master as 1.0.0` and `dev-load-varnish-only-when-used@stable` normalize to
shorter names but also fit this policy's arbitrary dev- branch output grammar.
The local test separately classifies leading v, shorthand, numeric build
metadata, numeric wildcard and lowercase RC inputs against their actual expected
outputs. Lowercase numeric `1.2.3.0-stable` -> `1.2.3.0` is source-derived from
pinned normalize() lines 154-159, explicitly distinguished from provider rows.
Rejecting numeric -stable does not reject `dev-feature-stable`.

Plan A TDD evidence: `/tmp/git-init-plan-a-red.log` captured the first run after
adding only the coordinated stable-output fixture, before changing production.
All three modes expected exit 4 and returned 0; --init mutated its isolated
fixture. The fixture now requires the exact normalized-version category,
redaction and no mutation using the existing full snapshot harness. No grammar
expansion was needed: all 86 successful provider outputs pass.
