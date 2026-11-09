import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'

export default [
  {ignores: ['node_modules/**', 'dist/**', 'coverage/**']},
  {
    files: ['src/**/*.{js,jsx}', 'vite.config.js', 'scripts/*.mjs', 'tests/*.mjs'],
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      parserOptions: {ecmaFeatures: {jsx: true}},
      globals: {...globals.browser, ...globals.node}
    },
    plugins: {'react-hooks': reactHooks},
    rules: {
      ...js.configs.recommended.rules,
      'no-unused-vars': 'off',
      'no-constant-condition': 'error',
      // The API path validator intentionally matches C0 control characters.
      'no-control-regex': 'off',
      'react-hooks/rules-of-hooks': 'error',
      'react-hooks/exhaustive-deps': 'warn'
    }
  }
]
