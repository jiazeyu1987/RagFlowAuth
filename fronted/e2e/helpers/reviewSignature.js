// @ts-check
const { expect } = require('@playwright/test');

async function submitReviewSignature(page, {
  password = 'admin123',
  meaning,
  reason,
} = {}) {
  const modal = page.getByTestId('review-signature-modal');
  await expect(modal).toBeVisible();

  await page.getByTestId('review-signature-password').fill(password);
  if (typeof meaning === 'string') {
    await page.getByTestId('review-signature-meaning').fill(meaning);
  }
  if (typeof reason === 'string') {
    await page.getByTestId('review-signature-reason').fill(reason);
  }
  await page.getByTestId('review-signature-submit').click();
}

module.exports = {
  submitReviewSignature,
};
