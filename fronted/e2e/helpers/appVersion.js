// @ts-check
const fs = require('node:fs');
const path = require('node:path');

function getAppVersionFromFrontend() {
  const projectRoot = path.resolve(__dirname, '..', '..');
  const filePath = path.join(projectRoot, 'src', 'hooks', 'useAuth.js');
  const src = fs.readFileSync(filePath, 'utf8');

  // e.g. const APP_VERSION = '6';
  const match = src.match(/const\s+APP_VERSION\s*=\s*['"]([^'"]+)['"]/);
  if (!match || !match[1]) {
    throw new Error(`Failed to parse APP_VERSION from ${filePath}`);
  }
  return match[1];
}

module.exports = { getAppVersionFromFrontend };
