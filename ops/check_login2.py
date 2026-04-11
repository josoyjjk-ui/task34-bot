import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://localhost:18800")
        context = browser.contexts[0]
        # Get or create a page
        pages = context.pages
        print(f"Pages: {len(pages)}")
        if pages:
            page = pages[0]
        else:
            page = await context.new_page()

        print(f"Current URL: {page.url}")
        try:
            await page.goto("https://www.naver.com", wait_until="domcontentloaded", timeout=15000)
            await asyncio.sleep(2)
            text = await page.evaluate("document.body.innerText")
            logged = "fireant_korea" in text or "로그아웃" in text
            print(f"Logged in: {logged}")
            await page.screenshot(path="/Users/fireant/.openclaw/workspace/ops/check_login2.png")
        except Exception as e:
            print(f"Error: {e}")

asyncio.run(main())
