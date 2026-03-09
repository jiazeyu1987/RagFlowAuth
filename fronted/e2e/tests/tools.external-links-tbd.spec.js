// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');

adminTest('tools external cards open links and TBD cards stay disabled @regression @tools', async ({ page }) => {
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

  const openedUrls = await page.evaluate(() => window.__openedUrls || []);
  expect(openedUrls[0]).toContain('code.nhsa.gov.cn');
  expect(openedUrls[1]).toContain('tpass.shanghai.chinatax.gov.cn');

  await expect(page.getByTestId('tool-card-tbd_4')).toBeDisabled();

  const alerts = await page.evaluate(() => window.__alertMessages || []);
  expect(alerts.length).toBe(0);
});
