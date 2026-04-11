import asyncio
from playwright.async_api import async_playwright

BLOG_ID = "fireant_korea"
PASSWORD = "wnFhT9"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://localhost:18800")
        context = browser.contexts[0]
        pages = context.pages
        page = pages[0] if pages else await context.new_page()

        print("Navigating to login...")
        await page.goto("https://nid.naver.com/nidlogin.login?mode=form", wait_until="domcontentloaded")
        await asyncio.sleep(2)

        await page.screenshot(path="/Users/fireant/.openclaw/workspace/ops/login_before.png")

        # 아이디 입력
        await page.locator("#id").click()
        await asyncio.sleep(0.3)
        for ch in BLOG_ID:
            await page.keyboard.type(ch, delay=80)
        await asyncio.sleep(0.5)

        # 패스워드 입력
        await page.locator("#pw").click()
        await asyncio.sleep(0.3)
        for ch in PASSWORD:
            await page.keyboard.type(ch, delay=80)
        await asyncio.sleep(0.5)

        await page.screenshot(path="/Users/fireant/.openclaw/workspace/ops/login_filled.png")

        # 로그인 버튼
        await page.locator("#log\\.login").click()
        await asyncio.sleep(5)

        cur = page.url
        print(f"After login URL: {cur}")
        await page.screenshot(path="/Users/fireant/.openclaw/workspace/ops/login_after.png")
        ok = "nidlogin" not in cur
        print(f"Login success: {ok}")

asyncio.run(main())
