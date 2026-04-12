import { chromium } from 'playwright';

const SCREENSHOTS = [
  {
    url: 'https://josoyjjk-ui.github.io/fireant-dashboard/',
    output: '/tmp/fireant-dashboard.png',
    label: 'Dashboard',
  },
  {
    url: 'https://josoyjjk-ui.github.io/fireant-dashboard/events/',
    output: '/tmp/fireant-events.png',
    label: 'Events',
  },
];

async function capture() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 2,
  });

  for (const shot of SCREENSHOTS) {
    console.log(`[INFO] Navigating to ${shot.url} ...`);
    const page = await context.newPage();
    try {
      await page.goto(shot.url, { waitUntil: 'networkidle', timeout: 30000 });
      // Extra wait for any JS rendering
      await page.waitForTimeout(3000);
      await page.screenshot({
        path: shot.output,
        fullPage: true,
      });
      console.log(`[OK] ${shot.label} screenshot saved → ${shot.output}`);
    } catch (err) {
      console.error(`[FAIL] ${shot.label}: ${err.message}`);
    } finally {
      await page.close();
    }
  }

  await browser.close();
  console.log('[DONE] All captures finished.');
}

capture().catch((err) => {
  console.error('Fatal:', err);
  process.exit(1);
});
