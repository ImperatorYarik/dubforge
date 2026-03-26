import js from '@eslint/js'
import pluginVue from 'eslint-plugin-vue'

export default [
  js.configs.recommended,
  ...pluginVue.configs['flat/recommended'],
  {
    rules: {
      // Logic rules
      'no-console': 'warn',
      'no-empty': ['error', { allowEmptyCatch: true }],

      // Vue: disable purely stylistic formatting rules
      'vue/multi-word-component-names': 'off',
      'vue/max-attributes-per-line': 'off',
      'vue/html-self-closing': 'off',
      'vue/singleline-html-element-content-newline': 'off',
      'vue/multiline-html-element-content-newline': 'off',
      'vue/html-closing-bracket-spacing': 'off',
      'vue/attributes-order': 'off',
    },
  },
  {
    ignores: ['dist/**', 'node_modules/**'],
  },
]
