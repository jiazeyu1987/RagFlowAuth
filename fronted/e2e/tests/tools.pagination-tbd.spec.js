// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');

adminTest('tools pagination covers all pages and all TBD cards stay disabled @regression @tools', async ({ page }) => {
  await page.addInitScript(() => {
    window.__openedUrls = [];
    window.__alertMessages = [];
    window.open = (...args) => {
      window.__openedUrls.push(String(args[0] || ''));
      return null;
    };
    window.alert = (...args) => {
      window.__alertMessages.push(String(args[0] || ''));
    };
  });

  await page.goto('/tools');

  await page.getByTestId('tool-card-nhsa_code_search').click();
  await page.getByTestId('tool-card-shanghai_tax').click();

  let totalTbdCardsChecked = 0;
  // Upper bound avoids accidental endless loops if pager state breaks.
  for (let i = 0; i < 10; i += 1) {
    const tbdCards = page.locator("[data-testid^='tool-card-tbd_']");
    const count = await tbdCards.count();
    totalTbdCardsChecked += count;
    for (let idx = 0; idx < count; idx += 1) {
      await expect(tbdCards.nth(idx)).toBeDisabled();
    }

    const nextDisabled = await page.getByTestId('tools-next-page').isDisabled();
    if (nextDisabled) break;
    await page.getByTestId('tools-next-page').click();
  }

  expect(totalTbdCardsChecked).toBeGreaterThanOrEqual(40);

  const openedUrls = await page.evaluate(() => window.__openedUrls || []);
  expect(openedUrls.some((url) => url.includes('code.nhsa.gov.cn'))).toBeTruthy();
  expect(openedUrls.some((url) => url.includes('tpass.shanghai.chinatax.gov.cn'))).toBeTruthy();

  const alerts = await page.evaluate(() => window.__alertMessages || []);
  expect(alerts.length).toBe(0);
});
