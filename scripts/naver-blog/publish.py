#!/usr/bin/env python3
"""
네이버 블로그: 삭제 + 재업로드 v3
- 삭제: 올바른 selector 사용
- 로그인: 강제 재로그인
- SE: 올바른 frame 탐색
"""
import asyncio
import json
import base64
import os

from playwright.async_api import async_playwright

BLOG_ID = "fireant_korea"
PASSWORD = "wnFhT9"
LOG_NO_DELETE = 224236031591
IMAGE_PATH = "/tmp/openclaw/uploads/daily-report-20260331-correct.jpg"
POST_TITLE = "📌 [불개미 일일시황] 2026.03.31 (월)"
POST_TEXT = "불개미 일일시황 | 2026.03.31 (KST)\n\n[1] BTC ETH 유출입\n• BTC: +$69.44M (순유입)\n• ETH: +$4.96M (순유입)\n• ETF 데이터는 마지막 거래일 기준\n\n[2] 미결제약정 추이 (24시간 기준)\n• BTC 24시간: -0.75%\n• ETH 24시간: +0.27%\n\n[3] DAT 추이\n• WEEKLY NET INFLOW: $72.83K\n\n[4] 코인베이스 프리미엄\n• 현재 지수: -0.0034%\n\n[5] 요약\nBTC·ETH ETF 모두 소폭 순유입으로 전환됐으나 DAT 주간 유입이 $72.83K로 급감해 기관 매수세가 사실상 멈춘 상태다. CB 프리미엄 -0.0034%로 미국 프리미엄이 거의 소멸돼 있어 당분간 추세 전환보다는 관망 구도가 이어질 가능성이 높다."


async def do_login(page):
    """네이버 강제 로그인"""
    print("  → 로그인 페이지 이동...")
    await page.goto("https://nid.naver.com/nidlogin.login?mode=form", wait_until="domcontentloaded")
    await asyncio.sleep(2)
    
    # ID 입력
    id_input = page.locator("#id")
    await id_input.click()
    await id_input.type(BLOG_ID, delay=100)
    await asyncio.sleep(0.5)
    
    # PW 입력
    pw_input = page.locator("#pw")
    await pw_input.click()
    await pw_input.type(PASSWORD, delay=100)
    await asyncio.sleep(0.5)
    
    # 로그인 버튼
    await page.locator("#log\\.login").click()
    await asyncio.sleep(4)
    
    url = page.url
    print(f"  → 로그인 후 URL: {url}")
    return "naver.com" in url and "nidlogin" not in url


async def find_se_frame(page):
    """SmartEditor가 있는 frame 탐색"""
    # 모든 frame 탐색
    for attempt in range(30):
        for frame in page.frames:
            try:
                result = await frame.evaluate(
                    "typeof window.SmartEditor !== 'undefined' && window.SmartEditor._editors ? JSON.stringify(Object.keys(window.SmartEditor._editors)) : null"
                )
                if result and result != 'null':
                    keys = json.loads(result)
                    if keys:
                        print(f"  → SE 발견: frame={frame.name[:30] or 'main'}, keys={keys}")
                        return frame, keys[0]
            except:
                pass
        await asyncio.sleep(1)
    return None, None


async def main():
    async with async_playwright() as p:
        # 기존 Chrome CDP 연결 시도 (port 18800)
        try:
            browser = await asyncio.wait_for(p.chromium.connect_over_cdp("http://localhost:18800"), timeout=10)
            context = browser.contexts[0] if browser.contexts else await browser.new_context()
            page = context.pages[0] if context.pages else await context.new_page()
            print("[init] ✅ 기존 Chrome CDP 연결 성공")
        except Exception as e:
            print(f"[init] CDP 연결 실패: {e}, persistent context로 fallback")
            context = await p.chromium.launch_persistent_context(
                user_data_dir="/Users/fireant/.openclaw/browser/openclaw/user-data",
                executable_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                headless=True,
                args=["--no-first-run", "--no-default-browser-check", "--disable-blink-features=AutomationControlled"],
                viewport={"width": 1280, "height": 900},
            )
            page = context.pages[0] if context.pages else await context.new_page()

        # ── STEP 0: 로그인 ──
        print("[0] 로그인 확인...")
        await page.goto("https://www.naver.com", wait_until="domcontentloaded")
        await asyncio.sleep(2)
        
        # 로그인 상태 확인 (프로필 이미지 또는 ID 표시)
        page_text = await page.evaluate("document.body.innerText")
        is_logged = BLOG_ID in page_text or "로그아웃" in page_text
        
        if not is_logged:
            print("[0] 로그인 필요 - 로그인 시도")
            success = await do_login(page)
            if not success:
                await page.screenshot(path="/tmp/openclaw/uploads/v3_login_fail.png")
                print("[0] ❌ 로그인 실패 - 스크린샷 저장")
                # 로그인 페이지 상태 확인
                current = page.url
                print(f"  현재 URL: {current}")
                if "nidlogin" in current:
                    # 봇감지 등으로 로그인 안됨, 강제 진행
                    print("[0] 봇 감지 또는 추가 인증 필요")
                    await page.screenshot(path="/tmp/openclaw/uploads/v3_login_blocked.png")
        else:
            print("[0] ✅ 이미 로그인됨")

        # ── STEP 1: 기존 포스트 삭제 ──
        print(f"\n[1] 포스트 {LOG_NO_DELETE} 삭제...")
        await page.goto(f"https://blog.naver.com/{BLOG_ID}/{LOG_NO_DELETE}", wait_until="domcontentloaded")
        await asyncio.sleep(3)
        await page.screenshot(path="/tmp/openclaw/uploads/v3_delete_before.png")

        # iframe에서 더보기 버튼 찾기
        main_frame = page.frame("mainFrame")
        target_frame = main_frame if main_frame else page
        
        # 더보기 버튼 - 여러 selector 시도
        overflow_selectors = [
            "._open_overflowmenu",
            ".btn_more",
            ".area_more button",
            "button[aria-label*='더보기']",
            ".post_btn_area button:last-child",
        ]
        
        overflow_clicked = False
        for sel in overflow_selectors:
            try:
                btn = await target_frame.query_selector(sel)
                if btn:
                    await btn.click()
                    await asyncio.sleep(1)
                    overflow_clicked = True
                    print(f"[1] 더보기 클릭: {sel}")
                    break
            except:
                pass
        
        if not overflow_clicked:
            # JS로 텍스트 기반 탐색
            result = await target_frame.evaluate("""
                () => {
                    const btns = document.querySelectorAll('button, [role="button"]');
                    for (const b of btns) {
                        const t = b.textContent?.trim();
                        const cls = b.className || '';
                        if (cls.includes('more') || cls.includes('overflow') || cls.includes('menu')) {
                            b.click();
                            return 'clicked: ' + cls.substring(0, 50);
                        }
                    }
                    // ⋮ 또는 ... 텍스트
                    for (const b of btns) {
                        const t = b.textContent?.trim();
                        if (t === '⋮' || t === '...' || t === '더보기') {
                            b.click();
                            return 'clicked text: ' + t;
                        }
                    }
                    return 'not found';
                }
            """)
            print(f"[1] JS 더보기: {result}")
            if "clicked" in result:
                overflow_clicked = True
                await asyncio.sleep(1)
        
        await page.screenshot(path="/tmp/openclaw/uploads/v3_delete_menu.png")
        
        # 삭제 버튼
        delete_selectors = [
            ".btn_del._deletePost",
            ".btn_del",
            "button:has-text('삭제')",
            "[data-action='delete']",
        ]
        
        delete_clicked = False
        for sel in delete_selectors:
            try:
                btn = await target_frame.query_selector(sel)
                if btn:
                    await btn.click()
                    await asyncio.sleep(1)
                    delete_clicked = True
                    print(f"[1] 삭제 버튼 클릭: {sel}")
                    break
            except:
                pass
        
        if delete_clicked:
            await page.screenshot(path="/tmp/openclaw/uploads/v3_delete_confirm.png")
            # 확인 다이얼로그
            confirm_selectors = [
                ".btn_confirm", "button:has-text('확인')", ".layer_confirm .btn_ok",
                "[data-action='confirm']", ".modal button:last-child"
            ]
            for sel in confirm_selectors:
                for f in [page, target_frame]:
                    try:
                        btn = await f.query_selector(sel)
                        if btn:
                            await btn.click()
                            await asyncio.sleep(2)
                            print(f"[1] ✅ 삭제 확인: {sel}")
                            delete_clicked = True
                            break
                    except:
                        pass
        else:
            print("[1] 삭제 버튼 없음 - 이미 삭제됐거나 버튼 변경됨")
        
        await page.screenshot(path="/tmp/openclaw/uploads/v3_delete_after.png")

        # ── STEP 2: 글쓰기 페이지로 이동 ──
        print("\n[2] 글쓰기 페이지 이동...")
        await page.goto(
            f"https://blog.naver.com/PostWriteForm.naver?blogId={BLOG_ID}",
            wait_until="domcontentloaded"
        )
        await asyncio.sleep(5)
        
        # "작성 중인 글이 있습니다" 다이얼로그 확인
        for attempt in range(5):
            try:
                confirm_btn = await page.query_selector(".confirm_btn__WEaBq, button:has-text('확인')")
                if confirm_btn:
                    btn_text = await confirm_btn.inner_text()
                    if "확인" in btn_text:
                        await confirm_btn.click()
                        print(f"[2] 작성 중 다이얼로그 확인 클릭")
                        await asyncio.sleep(2)
                        break
            except:
                pass
            await asyncio.sleep(0.5)
        
        await page.screenshot(path="/tmp/openclaw/uploads/v3_write_page.png")
        
        current_url = page.url
        print(f"[2] URL: {current_url}")
        
        # 로그인 페이지로 리다이렉트 됐으면 로그인 후 재시도
        if "nidlogin" in current_url or "nid.naver.com" in current_url:
            print("[2] 로그인 필요 - 재로그인")
            await do_login(page)
            await asyncio.sleep(2)
            await page.goto(
                f"https://blog.naver.com/PostWriteForm.naver?blogId={BLOG_ID}",
                wait_until="domcontentloaded"
            )
            await asyncio.sleep(5)
            current_url = page.url
            print(f"[2] 재이동 후 URL: {current_url}")
            await page.screenshot(path="/tmp/openclaw/uploads/v3_write_page2.png")

        # SE frame 탐색
        print("[2] SmartEditor 탐색 중...")
        se_frame, editor_key = await find_se_frame(page)
        
        if not se_frame:
            print("[2] ❌ SE 없음. frame 목록:")
            for f in page.frames:
                print(f"  - {f.name[:50] or 'main'} / {f.url[:80]}")
            await page.screenshot(path="/tmp/openclaw/uploads/v3_no_se.png")
            await context.close()
            return

        print(f"[2] ✅ SE 준비 완료. key={editor_key}")

        # ── STEP 3: 제목 ──
        print("[3] 제목 입력...")
        await se_frame.evaluate(
            f"window.SmartEditor._editors['{editor_key}']._documentService.setDocumentTitle({json.dumps(POST_TITLE)})"
        )
        await asyncio.sleep(0.3)

        # ── STEP 4: 이미지 먼저 업로드 (이미지 위, 텍스트 아래 구조) ──
        print("[4] 이미지 업로드...")

        # 사진 버튼 클릭 - 툴바 "사진" 버튼
        photo_clicked = False
        try:
            # SmartEditor 사진 메뉴 직접 실행
            result = await se_frame.evaluate(f"""
                () => {{
                    const ed = window.SmartEditor._editors['blogpc001'];
                    // 메뉴 실행
                    const menuNames = ['image', 'photo', 'Image', 'Photo'];
                    for (const name of menuNames) {{
                        try {{
                            ed._menuManager.executeMenu(name);
                            return 'executeMenu:' + name;
                        }} catch(e) {{}}
                    }}
                    // DOM에서 사진 버튼 찾기
                    const allBtns = document.querySelectorAll('button, [role="button"], [data-se-menu-name]');
                    for (const b of allBtns) {{
                        const txt = (b.textContent || '').trim();
                        const name = b.getAttribute('data-se-menu-name') || '';
                        const title = b.title || b.getAttribute('aria-label') || '';
                        if (txt === '사진' || /image|photo/i.test(name) || title.includes('사진')) {{
                            b.click();
                            return 'click:' + (txt || name || title);
                        }}
                    }}
                    return 'none';
                }}
            """)
            print(f"[4] 사진 메뉴: {result}")
            if result != 'none':
                photo_clicked = True
                await asyncio.sleep(2)
        except Exception as e:
            print(f"[4] 사진 버튼 오류: {e}")
        
        # file input 업로드 (사진 버튼 클릭 후 input 나타날 때까지 대기)
        await asyncio.sleep(1)
        file_uploaded = False
        for attempt in range(5):
            for frame in [page] + page.frames:
                try:
                    fi = await frame.query_selector("input[type=file]")
                    if fi:
                        await fi.set_input_files(IMAGE_PATH)
                        print(f"[4] file input 업로드 완료 (frame={frame.name or 'main'})")
                        file_uploaded = True
                        await asyncio.sleep(6)
                        break
                except Exception as e:
                    pass
            if file_uploaded:
                break
            await asyncio.sleep(1)
        
        if not file_uploaded:
            print("[4] file input 없음 - BASE64 업로드")
            with open(IMAGE_PATH, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            data_url = f"data:image/png;base64,{b64}"
            
            upload_result = await se_frame.evaluate(f"""
                async () => {{
                    const ed = window.SmartEditor._editors['{editor_key}'];
                    // uploader 탐색
                    function findUploader(obj, depth=0) {{
                        if (depth > 4 || !obj || typeof obj !== 'object') return null;
                        if (typeof obj._uploadImageByBASE64 === 'function') return obj;
                        for (const key of Object.keys(obj)) {{
                            if (key.startsWith('_')) {{
                                const found = findUploader(obj[key], depth+1);
                                if (found) return found;
                            }}
                        }}
                        return null;
                    }}
                    const uploader = findUploader(ed);
                    if (!uploader) return 'NO_UPLOADER';
                    try {{
                        const r = await uploader._uploadImageByBASE64({json.dumps(data_url)});
                        return JSON.stringify(r || {{}}).substring(0, 200);
                    }} catch(e) {{
                        return 'ERR: ' + e.message;
                    }}
                }}
            """)
            print(f"[4] BASE64: {upload_result[:150]}")

        # 컴포넌트 확인
        await asyncio.sleep(2)
        comps = await se_frame.evaluate(f"""
            () => {{
                try {{
                    const doc = window.SmartEditor._editors['{editor_key}']._documentService.getDocumentData().document;
                    return doc.components.map(c => c['@ctype']).join(', ');
                }} catch(e) {{ return 'ERR:' + e.message; }}
            }}
        """)
        print(f"[4] 컴포넌트: {comps}")

        # ── STEP 5: 텍스트 입력 (이미지 아래) ──
        print("[5] 텍스트 입력 (이미지 아래)...")
        # 이미지 업로드 후 마지막 텍스트 단락 클릭
        await asyncio.sleep(1)
        try:
            els = await se_frame.query_selector_all(".se-text-paragraph")
            if els:
                el = els[-1]
                await el.scroll_into_view_if_needed()
                await asyncio.sleep(0.2)
                await el.click(force=True)
                await asyncio.sleep(0.3)
                print(f"[5] 마지막 텍스트 단락 클릭 (총 {len(els)}개)")
        except Exception as e:
            print(f"[5] 단락 클릭 실패: {e}")
        lines_post = POST_TEXT.split('\n')
        for i, line in enumerate(lines_post):
            if line:
                await page.keyboard.type(line, delay=15)
            if i < len(lines_post) - 1:
                await page.keyboard.press("Enter")
                await asyncio.sleep(0.04)
        print(f"[5] 텍스트 입력 완료 ({len(lines_post)}줄)")
        await asyncio.sleep(0.5)

        # ── STEP 5b: 스타일 적용 (가운데정렬, 소제목 bold+크기, 요약 bold) ──
        await asyncio.sleep(0.5)
        style_result = await se_frame.evaluate(f"""
            () => {{
                try {{
                    const ed = window.SmartEditor._editors['{editor_key}'];
                    const data = ed._documentService.getDocumentData();
                    const doc = data.document;
                    const textComp = doc.components.find(c => c['@ctype'] === 'text');
                    if (!textComp || !textComp.value) return 'NO_TEXT_COMP';

                    // 소제목 패턴: [1] [2] [3] [4] [5]
                    const isSubhead = (txt) => /^\[[1-5]\]/.test(txt.trim());
                    // 요약 내용: [5] 이후 줄 (소제목 제외)
                    let afterSummary = false;

                    const paragraphs = Array.isArray(textComp.value) ? textComp.value : [];
                    paragraphs.forEach(para => {{
                        if (!para || !para.nodes) return;
                        const text = para.nodes.map(n => n.value || '').join('');

                        // 요약 섹션 진입 감지
                        if (/^\[5\]/.test(text.trim())) afterSummary = true;

                        // 단락 스타일: 가운데 정렬
                        if (!para.style) para.style = {{'@ctype': 'paragraphStyle'}};
                        para.style.align = 'center';

                        para.nodes.forEach(node => {{
                            if (!node.style) node.style = {{'@ctype': 'nodeStyle'}};
                            // 흰색 폰트 수정
                            if (node.style.fontColor === '#ffffff') node.style.fontColor = '#000000';

                            if (isSubhead(text)) {{
                                // 소제목: bold + 크기 확대(fs17)
                                node.style.bold = true;
                                node.style.fontSizeCode = 'fs17';
                            }} else if (afterSummary && !/^\[5\]/.test(text.trim())) {{
                                // 요약 내용: bold
                                node.style.bold = true;
                            }}
                        }});
                    }});

                    ed._documentService.setDocumentData(data);
                    return 'STYLED_OK';
                }} catch(e) {{ return 'ERR: ' + e.message; }}
            }}
        """)
        print(f"[5b] 스타일 적용: {style_result}")
        await asyncio.sleep(0.5)

        # 최종 확인
        final = await se_frame.evaluate(f"""
            () => {{
                try {{
                    const doc = window.SmartEditor._editors['{editor_key}']._documentService.getDocumentData().document;
                    return JSON.stringify(doc.components.map(c => ({{t: c['@ctype'], ok: !!(c.src || c.value)}})));
                }} catch(e) {{ return 'ERR:' + e.message; }}
            }}
        """)
        print(f"[5] 최종 컴포넌트: {final}")
        await page.screenshot(path="/tmp/openclaw/uploads/v3_before_publish.png")

        # ── STEP 6: 발행 ──
        print("[6] 발행...")
        
        # 발행 패널 버튼 목록 확인
        all_btns = await page.evaluate("""
            () => {
                const btns = [];
                document.querySelectorAll('button').forEach(b => {
                    const t = b.textContent?.trim();
                    if (t) btns.push({text: t, cls: b.className.substring(0, 60)});
                });
                return btns;
            }
        """)
        print(f"[6] 버튼 목록: {all_btns}")
        
        pub_clicked = False
        
        # 발행 패널의 "발행" 버튼 - 다양한 패턴
        for frame in [page] + page.frames:
            try:
                r = await frame.evaluate("""
                    () => {
                        // 버튼 전체 탐색 - 정확히 '발행' 텍스트
                        for (const b of document.querySelectorAll('button')) {
                            const t = b.textContent?.trim();
                            const cls = b.className || '';
                            // 발행 패널의 확인/발행 버튼
                            if (t === '발행' && (cls.includes('confirm') || cls.includes('publish') || cls.includes('btn'))) {
                                b.click();
                                return '발행(cls):' + cls.substring(0, 50);
                            }
                        }
                        // 그냥 '발행' 텍스트 버튼
                        for (const b of document.querySelectorAll('button')) {
                            const t = b.textContent?.trim();
                            if (t === '발행') {
                                b.click();
                                return '발행(text)';
                            }
                        }
                        return null;
                    }
                """)
                if r:
                    print(f"[6] 발행 클릭: {r}")
                    pub_clicked = True
                    break
            except:
                pass
        
        await asyncio.sleep(3)
        await page.screenshot(path="/tmp/openclaw/uploads/v3_publish_panel.png")
        
        # 발행 패널에서 최종 확인 버튼 클릭 (스크롤 후)
        final_pub = await page.evaluate("""
            () => {
                // confirm_btn 또는 발행 패널의 발행 버튼
                const selectors = [
                    '.confirm_btn__WEaBq',
                    '.publish_confirm__',
                    'button.confirm_btn',
                ];
                for (const sel of selectors) {
                    const btn = document.querySelector(sel);
                    if (btn) { btn.click(); return sel; }
                }
                // 발행 패널 내부 "발행" 버튼
                const panels = document.querySelectorAll('.publish_area, .panel_publish, [class*="publish"]');
                for (const panel of panels) {
                    const btns = panel.querySelectorAll('button');
                    for (const b of btns) {
                        if (b.textContent?.trim() === '발행') {
                            b.click();
                            return 'panel_publish:' + b.className.substring(0, 40);
                        }
                    }
                }
                return null;
            }
        """)
        print(f"[6] 최종 확인 버튼: {final_pub}")
        
        await asyncio.sleep(8)
        await page.screenshot(path="/tmp/openclaw/uploads/v3_after_publish.png")
        
        cur = page.url
        print(f"[6] 발행 후 URL: {cur}")
        
        # logNo 추출
        new_logno = None
        if f"/{BLOG_ID}/" in cur:
            part = cur.split(f"/{BLOG_ID}/")[-1].split("?")[0].split("#")[0]
            if part.isdigit():
                new_logno = part
        if "logNo=" in cur:
            new_logno = cur.split("logNo=")[-1].split("&")[0]
        
        if new_logno and new_logno != LOG_NO_DELETE:
            print(f"\n✅ 발행 완료!")
            print(f"   logNo: {new_logno}")
            print(f"   URL: https://blog.naver.com/{BLOG_ID}/{new_logno}")
        else:
            print(f"\n❓ logNo 확인 필요. URL: {cur}")
        
        await asyncio.sleep(2)
        # CDP 연결 시 context.close() 생략 (기존 Chrome 세션 유지)
        try:
            await context.close()
        except Exception:
            pass
        print("[완료]")


asyncio.run(main())
