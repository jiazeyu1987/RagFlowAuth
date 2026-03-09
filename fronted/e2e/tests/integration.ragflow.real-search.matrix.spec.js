// @ts-check
const { test, expect, request } = require('@playwright/test');
const { FRONTEND_BASE_URL, BACKEND_BASE_URL, preflightAdmin, uiLogin } = require('../helpers/integration');
const { getRealDataConfig, listDatasetIds, pickSearchTermsWithHits } = require('../helpers/ragflowRealData');

test('ragflow real search: keyword matrix on agents page @integration @agents @realdata', async ({ page }) => {
  test.setTimeout(300_000);

  const cfg = getRealDataConfig();
  const pre = await preflightAdmin();
  if (!pre.ok) {
    if (cfg.strict) throw new Error(pre.reason);
    test.skip(true, pre.reason);
  }

  const headers = { Authorization: `Bearer ${pre.tokens.access_token}` };
  const api = await request.newContext({ baseURL: BACKEND_BASE_URL });

  try {
    const datasetInfo = await listDatasetIds(api, headers);
    if (!datasetInfo.ok) {
      if (cfg.strict) throw new Error(datasetInfo.reason);
      test.skip(true, datasetInfo.reason);
    }

    const selectedTerms = await pickSearchTermsWithHits(
      api,
      headers,
      datasetInfo.datasetIds,
      cfg.searchTerms,
      Math.max(1, cfg.maxTerms)
    );

    const selectedSummary = selectedTerms.map((x) => `${x.term}:${x.hitCount}`).join(', ');
    test.info().annotations.push({
      type: 'realdata',
      description: `terms_file=${cfg.searchTermsFile}; selected=${selectedSummary || 'none'}`,
    });

    if (selectedTerms.length < cfg.minHitTerms) {
      const reason = `search terms with hits not enough: ${selectedTerms.length}/${cfg.minHitTerms}; terms_file=${cfg.searchTermsFile}`;
      if (cfg.strict) throw new Error(reason);
      test.skip(true, reason);
    }

    await uiLogin(page);
    await page.goto(`${FRONTEND_BASE_URL}/agents`);
    await expect(page.getByTestId('agents-search-input')).toBeVisible({ timeout: 30_000 });

    for (const item of selectedTerms) {
      const term = String(item.term || '').trim();
      expect(term).toBeTruthy();

      await page.getByTestId('agents-search-input').fill(term);
      await expect(page.getByTestId('agents-search-button')).toBeEnabled({ timeout: 30_000 });

      const [searchResp] = await Promise.all([
        page.waitForResponse((resp) => resp.url().includes('/api/search') && resp.request().method() === 'POST'),
        page.getByTestId('agents-search-button').click(),
      ]);

      expect(searchResp.ok(), `agents search failed for term=${term}`).toBeTruthy();

      const reqPayload = searchResp.request().postDataJSON();
      expect(String(reqPayload?.question || '').trim()).toBe(term);
      const datasetIds = Array.isArray(reqPayload?.dataset_ids) ? reqPayload.dataset_ids : [];
      expect(datasetIds.length).toBeGreaterThan(0);

      const payload = await searchResp.json();
      const chunks = Array.isArray(payload?.chunks) ? payload.chunks : [];
      expect(chunks.length, `no chunks returned for term=${term}`).toBeGreaterThan(0);

      await expect(page.getByTestId('agents-result-item-0')).toBeVisible({ timeout: 60_000 });
      await expect(page.getByTestId('agents-results-summary')).toContainText(/\d+/);
      await expect(page.getByTestId('agents-error')).toHaveCount(0);
    }
  } finally {
    await api.dispose();
  }
});
