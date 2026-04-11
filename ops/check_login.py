import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://localhost:18800")
        context = browser.contexts[0] if browser.contexts else await browser.new_context()
        if not context.pages:
            page = await context.new_page()
        else:
            page = context.pages[0]

        await page.goto("https://www.naver.com", wait_until="domcontentloaded")
        await asyncio.sleep(2)
        text = await page.evaluate("document.body.innerText")
        url = page.url
        print(f"URL: {url}")
        logged = "fireant_korea" in text or "로그아웃" in text
        print(f"Logged in: {logged}")
        await page.screenshot(path="/Users/fireant/.openclaw/workspace/ops/check_login.png")

asyncio.run(main())
