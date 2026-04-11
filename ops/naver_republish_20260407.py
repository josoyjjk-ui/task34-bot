#!/usr/bin/env python3
import asyncio
import base64
import json
import re
from playwright.async_api import async_playwright

BLOG_ID = "fireant_korea"
PASSWORD = "wnFhT9"
LOG_NO_DELETE = "224244107556"
IMAGE_PATH = "/Users/fireant/.openclaw/workspace/daily-report-latest.png"
POST_TITLE = "📌 [불개미 일일시황] 2026.04.07 화"
POST_TEXT = """📌 불개미 일일시황 | 2026.04.07 (화)

1️⃣ BTC ETH 유출입
• BTC: +$471.32M (순유입)
• ETH: +$120.24M (순유입)
• ETF 데이터는 마지막 거래일 기준

2️⃣ 미결제약정 추이 (24시간 기준)
• BTC 24시간: -2.74%
• ETH 24시간: -3.32%

3️⃣ DAT 추이
• WEEKLY NET INFLOW: +$735.45M

4️⃣ 코인베이스 프리미엄
• 현재 지수: +0.011%

5️⃣ 요약
BTC·ETH 현물 ETF 모두 강한 순유입을 기록하며 기관 매수세가 이어지고 있습니다.
미결제약정은 BTC -2.74%, ETH -3.32%로 단기 레버리지 축소가 진행 중이며, 코인베이스 프리미엄은 소폭 플러스권을 유지 중입니다."""


async def do_login(page):
    await page.goto("https://nid.naver.com/nidlogin.login?mode=form", wait_until="domcontentloaded")
    await asyncio.sleep(1.5)
    await page.locator("#id").click()
    await page.locator("#id").fill(BLOG_ID)
    await page.locator("#pw").click()
    await page.locator("#pw").fill(PASSWORD)
    await page.locator("#log\\.login").click()
    await asyncio.sleep(4)
    return "nidlogin" not in page.url


async def find_se_frame(page):
    for _ in range(30):
        for frame in page.frames:
            try:
                result = await frame.evaluate(
                    "typeof window.SmartEditor !== 'undefined' && window.SmartEditor._editors ? JSON.stringify(Object.keys(window.SmartEditor._editors)) : null"
                )
                if result and result != "null":
                    keys = json.loads(result)
                    if keys:
                        return frame, keys[0]
            except Exception:
                pass
        await asyncio.sleep(1)
    return None, None


async def delete_post(page):
    await page.goto(f"https://blog.naver.com/{BLOG_ID}/{LOG_NO_DELETE}", wait_until="domcontentloaded")
    await asyncio.sleep(3)
    main_frame = page.frame("mainFrame")
    target = main_frame if main_frame else page

    opened = False
    for sel in ["._open_overflowmenu", ".btn_more", ".area_more button", "button[aria-label*='더보기']"]:
        try:
            btn = await target.query_selector(sel)
            if btn:
                await btn.click()
                await asyncio.sleep(0.8)
                opened = True
                break
        except Exception:
            pass

    if not opened:
        await target.evaluate("""
            () => {
              const cands = [...document.querySelectorAll('button,[role="button"]')];
              for (const b of cands) {
                const t = (b.textContent||'').trim();
                const c = (b.className||'').toString();
                if (t==='더보기' || t==='⋮' || /more|overflow|menu/.test(c)) { b.click(); return; }
              }
            }
        """)
        await asyncio.sleep(0.8)

    deleted = False
    for sel in [".btn_del._deletePost", ".btn_del", "button:has-text('삭제')", "[data-action='delete']"]:
        try:
            btn = await target.query_selector(sel)
            if btn:
                await btn.click()
                await asyncio.sleep(0.8)
                deleted = True
                break
        except Exception:
            pass

    if deleted:
        for frame in [page, target]:
            for sel in [".btn_confirm", "button:has-text('확인')", ".layer_confirm .btn_ok", "[data-action='confirm']"]:
                try:
                    btn = await frame.query_selector(sel)
                    if btn:
                        await btn.click()
                        await asyncio.sleep(2)
                        return True
                except Exception:
                    pass
    return deleted


async def upload_image(se_frame, editor_key):
    with open(IMAGE_PATH, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    data_url = f"data:image/png;base64,{b64}"

    result = await se_frame.evaluate(
        """
        async ({ editorKey, dataUrl }) => {
          const ed = window.SmartEditor._editors[editorKey];
          function findUploader(obj, depth=0) {
            if (!obj || depth > 6 || typeof obj !== 'object') return null;
            if (typeof obj._uploadImageByBASE64 === 'function') return obj;
            for (const k of Object.keys(obj)) {
              if (!k.startsWith('_')) continue;
              const f = findUploader(obj[k], depth + 1);
              if (f) return f;
            }
            return null;
          }
          const uploader = findUploader(ed);
          if (!uploader) return 'NO_UPLOADER';
          try {
            await uploader._uploadImageByBASE64(dataUrl);
            return 'OK';
          } catch (e) {
            return 'ERR:' + e.message;
          }
        }
        """,
        {"editorKey": editor_key, "dataUrl": data_url},
    )
    await asyncio.sleep(4)
    return result


async def insert_text(page, se_frame):
    els = await se_frame.query_selector_all(".se-text-paragraph")
    if els:
        await els[-1].click(force=True)
    await asyncio.sleep(0.3)
    lines = POST_TEXT.split("\n")
    for i, line in enumerate(lines):
        if line:
            await page.keyboard.type(line, delay=12)
        if i < len(lines) - 1:
            await page.keyboard.press("Enter")
            await asyncio.sleep(0.03)


async def apply_styles(se_frame, editor_key):
    result = await se_frame.evaluate(
        """
        ({ editorKey }) => {
          try {
            const ed = window.SmartEditor._editors[editorKey];
            const data = ed._documentService.getDocumentData();
            const doc = data.document;
            const textComp = (doc.components || []).find(c => c['@ctype'] === 'text');
            if (!textComp || !Array.isArray(textComp.value)) return 'NO_TEXT';

            const numRe = /([+-]\$\d[\d.,]*[MBK]?)|([+-]\d+(?:\.\d+)?%)/g;
            let inSummary = false;

            for (const para of textComp.value) {
              if (!para || !Array.isArray(para.nodes)) continue;
              const text = para.nodes.map(n => n.value || '').join('');
              const trimmed = text.trim();

              const isTitle = trimmed === '📌 불개미 일일시황 | 2026.04.07 (화)';
              const isSub = /^[1-5]️⃣\s/.test(trimmed);
              if (trimmed.startsWith('5️⃣ 요약')) inSummary = true;
              const summaryLine = inSummary && trimmed && !trimmed.startsWith('5️⃣ 요약');

              for (const node of para.nodes) {
                if (!node.style) node.style = {'@ctype': 'nodeStyle'};

                if (isTitle) {
                  node.style.bold = true;
                  node.style.fontSizeCode = 'fs20';
                  node.style.backgroundColor = '#fff799';
                  node.style.fontBackgroundColor = '#fff799';
                }

                if (isSub) {
                  node.style.bold = true;
                  node.style.fontSizeCode = 'fs17';
                }

                if (summaryLine) {
                  node.style.bold = true;
                }

                if (node.value && numRe.test(node.value)) {
                  node.style.bold = true;
                }
                numRe.lastIndex = 0;
              }
            }

            ed._documentService.setDocumentData(data);
            return 'OK';
          } catch (e) {
            return 'ERR:' + e.message;
          }
        }
        """,
        {"editorKey": editor_key},
    )
    await asyncio.sleep(1)
    return result


async def publish(page):
    # 1차 발행 버튼
    clicked = await page.evaluate(
        """
        () => {
          for (const b of document.querySelectorAll('button')) {
            if ((b.textContent||'').trim() === '발행') { b.click(); return true; }
          }
          return false;
        }
        """
    )
    await asyncio.sleep(2)

    # 최종 확인 발행
    await page.evaluate(
        """
        () => {
          const sels = ['.confirm_btn__WEaBq', 'button.confirm_btn', 'button'];
          for (const sel of sels) {
            const btns = sel === 'button' ? [...document.querySelectorAll('button')] : [...document.querySelectorAll(sel)];
            for (const b of btns) {
              if ((b.textContent||'').trim() === '발행' || (b.textContent||'').trim() === '확인') { b.click(); return; }
            }
          }
        }
        """
    )
    await asyncio.sleep(8)
    return clicked


async def main():
    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp("http://localhost:18800")
            context = browser.contexts[0] if browser.contexts else await browser.new_context()
            page = await context.new_page()
        except Exception:
            context = await p.chromium.launch_persistent_context(
                user_data_dir="/Users/fireant/.openclaw/browser/openclaw/user-data",
                executable_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                headless=True,
                args=["--remote-debugging-port=18800", "--no-first-run", "--no-default-browser-check"],
                viewport={"width": 1280, "height": 900},
            )
            page = context.pages[0] if context.pages else await context.new_page()

        await page.goto("https://www.naver.com", wait_until="domcontentloaded")
        await asyncio.sleep(1)
        text = await page.evaluate("document.body.innerText")
        if BLOG_ID not in text and "로그아웃" not in text:
            ok = await do_login(page)
            if not ok:
                raise RuntimeError("로그인 실패")

        deleted = await delete_post(page)

        await page.goto(f"https://blog.naver.com/PostWriteForm.naver?blogId={BLOG_ID}", wait_until="domcontentloaded")
        await asyncio.sleep(5)
        try:
            confirm_btn = await page.query_selector(".confirm_btn__WEaBq, button:has-text('확인')")
            if confirm_btn:
                await confirm_btn.click()
                await asyncio.sleep(1)
        except Exception:
            pass

        se_frame, editor_key = await find_se_frame(page)
        if not se_frame:
            raise RuntimeError("SmartEditor frame 미탐지")

        await se_frame.evaluate(
            """({ editorKey, title }) => {
                window.SmartEditor._editors[editorKey]._documentService.setDocumentTitle(title)
            }""",
            {"editorKey": editor_key, "title": POST_TITLE},
        )

        up = await upload_image(se_frame, editor_key)
        await insert_text(page, se_frame)
        st = await apply_styles(se_frame, editor_key)

        await page.screenshot(path="/Users/fireant/.openclaw/workspace/ops/naver_before_publish_20260407.png")

        await publish(page)
        cur = page.url

        new_logno = None
        m = re.search(rf"/{BLOG_ID}/(\d+)", cur)
        if m:
            new_logno = m.group(1)
        if not new_logno:
            m2 = re.search(r"logNo=(\d+)", cur)
            if m2:
                new_logno = m2.group(1)

        if not new_logno:
            raise RuntimeError(f"새 logNo 파싱 실패. URL={cur}")

        final_url = f"https://blog.naver.com/{BLOG_ID}/{new_logno}"
        await page.goto(final_url, wait_until="domcontentloaded")
        await asyncio.sleep(2)
        await page.screenshot(path="/Users/fireant/.openclaw/workspace/ops/naver_new_post_20260407.png", full_page=True)

        print(json.dumps({
            "deleted_attempted": True,
            "deleted_result": deleted,
            "upload_result": up,
            "style_result": st,
            "new_logno": new_logno,
            "new_url": final_url,
            "screenshot": "/Users/fireant/.openclaw/workspace/ops/naver_new_post_20260407.png"
        }, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
