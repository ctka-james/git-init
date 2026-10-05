module.exports = {
  defaultIgnores: false,
  extends: ['@commitlint/config-conventional'],
  rules: {
    'type-enum': [2, 'always', ['feat', 'fix', 'refactor', 'docs', 'test', 'chore', 'style']],
    'scope-empty': [2, 'never'],
    'body-empty': [2, 'never'],
    'body-leading-blank': [2, 'always'],
    'subject-empty': [2, 'never'],
    'subject-case': [0]
  }
};
