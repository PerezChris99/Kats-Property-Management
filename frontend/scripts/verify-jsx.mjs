import fs from 'node:fs'
import path from 'node:path'

const root = path.resolve(import.meta.dirname, '..')
let count = 0
function walk(dir) {
  for (const entry of fs.readdirSync(dir, {withFileTypes: true})) {
    const file = path.join(dir, entry.name)
    if (entry.isDirectory()) {
      if (entry.name !== 'node_modules' && entry.name !== 'dist') walk(file)
      continue
    }
    if (/\.(tsx?|mts|cts)$/.test(entry.name)) {
      throw new Error('TypeScript source/config not allowed in React frontend: ' + path.relative(root, file))
    }
    if (entry.name.endsWith('.jsx')) count++
  }
}
walk(path.join(root, 'src'))
if (fs.existsSync(path.join(root, 'tsconfig.json'))) throw new Error('TypeScript configuration must be removed')
if (fs.existsSync(path.join(root, 'tsconfig.app.json'))) throw new Error('TypeScript configuration must be removed')
const pkg = JSON.parse(fs.readFileSync(path.join(root,'package.json'),'utf8'))
if (pkg.devDependencies?.typescript || pkg.dependencies?.typescript) throw new Error('TypeScript compiler remains a frontend dependency')
const html = fs.readFileSync(path.join(root, 'index.html'),'utf8')
if (!html.includes('/src/main.jsx') || html.includes('.tsx')) throw new Error('HTML entry must use JSX')
if (count < 8) throw new Error('Expected JSX source modules missing')
console.log('Verified ' + count + ' JSX source modules; no TypeScript frontend source or dependency')
