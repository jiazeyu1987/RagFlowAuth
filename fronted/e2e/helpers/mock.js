// @ts-check

async function mockJson(page, urlOrPattern, json, status = 200) {
  await page.route(urlOrPattern, async (route) => {
    await route.fulfill({
      status,
      contentType: 'application/json',
      body: JSON.stringify(json),
    });
  });
}

module.exports = { mockJson };

