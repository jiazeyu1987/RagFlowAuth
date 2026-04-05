// @ts-check
const fs = require('node:fs');
const path = require('node:path');

const DEFAULT_SUMMARY_PATH = path.resolve(__dirname, '..', '.auth', 'bootstrap-summary.json');

function loadBootstrapSummary(summaryPath = process.env.E2E_BOOTSTRAP_SUMMARY_PATH || DEFAULT_SUMMARY_PATH) {
  const resolvedPath = path.resolve(summaryPath);
  if (!fs.existsSync(resolvedPath)) {
    throw new Error(`Bootstrap summary not found: ${resolvedPath}`);
  }
  return JSON.parse(fs.readFileSync(resolvedPath, 'utf8'));
}

function loadDocFixtures(summaryPath) {
  const summary = loadBootstrapSummary(summaryPath);
  const fixtures = summary?.doc_fixtures;
  if (!fixtures || typeof fixtures !== 'object') {
    throw new Error('Doc fixtures missing from bootstrap summary');
  }
  return fixtures;
}

module.exports = {
  DEFAULT_SUMMARY_PATH,
  loadBootstrapSummary,
  loadDocFixtures,
};
