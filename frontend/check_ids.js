const fs = require('fs');

const html = fs.readFileSync('index.html', 'utf8');
const js = fs.readFileSync('app.js', 'utf8');

// Extract all id attributes from HTML
const htmlIds = [...html.matchAll(/id=["']([^"']+)["']/g)].map(m => m[1]);

// Extract all getElementById and $() calls from JS
const jsIds = [...js.matchAll(/\$\(["']([^"']+)["']\)|getElementById\(["']([^"']+)["']\)/g)]
  .map(m => m[1] || m[2]);

// Find IDs that JS references but HTML doesn't have
const missing = [...new Set(jsIds)].filter(id => !htmlIds.includes(id));

console.log('=== HTML IDs ===');
console.log(htmlIds.sort().join('\n'));
console.log('\n=== JS Referenced IDs ===');
console.log([...new Set(jsIds)].sort().join('\n'));
console.log('\n=== MISSING (JS references but not in HTML) ===');
console.log(missing.length ? missing.join('\n') : 'None');
