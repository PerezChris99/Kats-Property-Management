/**
 * One-shot source migration, executed in the existing perez branch.
 * TypeScript is used once as a syntax transformer ONLY; output retains JSX.
 * Commit generated JavaScript files and remove this migration script afterward.
 */
const fs = require('node:fs')
const path = require('node:path')
const ts = require('typescript')

const root = path.resolve(__dirname, '..')
const candidates = []
function walk(directory) {
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    const filepath = path.join(directory, entry.name)
    if (entry.isDirectory()) walk(filepath)
    else if (filepath.endsWith('.tsx') || filepath.endsWith('.ts')) candidates.push(filepath)
  }
}
walk(path.join(root, 'src'))
candidates.push(path.join(root, 'vite.config.ts'))

for (const file of candidates) {
  const original = fs.readFileSync(file, 'utf8')
  const transformed = ts.transpileModule(original, {
    fileName: file,
    compilerOptions: {
      target: ts.ScriptTarget.ES2022,
      module: ts.ModuleKind.ESNext,
      jsx: ts.JsxEmit.Preserve,
      isolatedModules: true,
      importHelpers: false,
      removeComments: false
    },
    reportDiagnostics: true
  })
  const errors = (transformed.diagnostics || []).filter(d => d.category === ts.DiagnosticCategory.Error)
  if (errors.length) {
    for (const d of errors) process.stderr.write(ts.flattenDiagnosticMessageText(d.messageText, '\n') + '\n')
    throw new Error('Failed to migrate: ' + file)
  }
  const output = file.replace(/\.tsx$/, '.jsx').replace(/\.ts$/, '.js')
  const code = transformed.outputText
  if (/\b(?:interface|type)\s+[A-Z]\w*\s*=/.test(code) || /from\s+['"][^'"]+\.(?:tsx?|ts)['"]/.test(code)) {
    throw new Error('Possible untransformed TypeScript in ' + output)
  }
  fs.writeFileSync(output, code, 'utf8')
  fs.unlinkSync(file)
  process.stdout.write(path.relative(root, file) + ' -> ' + path.relative(root, output) + '\n')
}

fs.unlinkSync(path.join(root, 'tsconfig.json'))
const indexFile = path.join(root, 'index.html')
let index = fs.readFileSync(indexFile, 'utf8')
if (!index.includes('/src/main.tsx')) throw new Error('HTML entry point changed unexpectedly')
index = index.replace('/src/main.tsx', '/src/main.jsx')
fs.writeFileSync(indexFile, index)

const pkgFile = path.join(root, 'package.json')
const pkg = JSON.parse(fs.readFileSync(pkgFile, 'utf8'))
pkg.scripts = {
  dev: 'vite --host 0.0.0.0',
  lint: 'eslint .',
  'check:jsx': 'node scripts/verify-jsx.mjs',
  test: 'node --test tests/*.test.mjs',
  check: 'npm run check:jsx && npm run lint && npm test',
  build: 'npm run check && vite build',
  preview: 'vite preview --host 0.0.0.0'
}
delete pkg.devDependencies.typescript
delete pkg.devDependencies['@types/react']
delete pkg.devDependencies['@types/react-dom']
pkg.devDependencies['@eslint/js'] = '^9.35.0'
pkg.devDependencies.eslint = '^9.35.0'
pkg.devDependencies['eslint-plugin-react-hooks'] = '^5.2.0'
pkg.devDependencies.globals = '^15.15.0'
fs.writeFileSync(pkgFile, JSON.stringify(pkg, null, 2) + '\n')
process.stdout.write('Converted ' + candidates.length + ' modules. All TSX/TS source removed.\n')
