// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');

adminTest('nmpa links: opens expected urls @regression @tools @nmpa', async ({ page }) => {
  await page.addInitScript(() => {
    window.__openedUrls = [];
    window.open = (...args) => {
      window.__openedUrls.push(String(args[0] || ''));
      return null;
    };
  });

  await page.goto('/tools/nmpa');

  await expect(page.getByTestId('nmpa-tool-page')).toBeVisible();

  await page.getByTestId('nmpa-home-btn').click();
  await page.getByTestId('nmpa-catalog-btn').click();

  await expect
    .poll(() => page.evaluate(() => (window.__openedUrls || []).length), { timeout: 10_000 })
    .toBe(2);

  const opened = await page.evaluate(() => window.__openedUrls || []);
  expect(opened).toEqual([
    'https://www.cmde.org.cn/index.html',
    'https://www.cmde.org.cn/flfg/zdyz/flmlbzh/flmlylqx/index.html',
  ]);
});
