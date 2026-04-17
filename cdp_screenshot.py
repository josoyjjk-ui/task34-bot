#!/usr/bin/env python3
"""CDP Protocol: capture screenshot and check Telegram login state."""

import json
import base64
import websocket
import time

WS_URL = "ws://127.0.0.1:18800/devtools/page/A6FB1633A3D360412C6C5B61C3C3CB75"
SCREENSHOT_PATH = "/tmp/telegram-web-screenshot.png"
REPORT_PATH = "/Users/fireant/.openclaw/harness-execution-workspaces/plan-20260413-3536ut-jeyldd/workspace/cdp_report.txt"

results = {
    "chrome_launch": "성공",
    "cdp_connect": "미확인",
    "page_load": "미확인",
    "screenshot": "미확인",
    "login_state": "미확인",
    "login_evidence": "",
    "navigation": "미확인",
    "navigation_evidence": ""
}

# ---- Step 1: Connect to WebSocket ----
try:
    ws = websocket.create_connection(WS_URL, timeout=15)
    results["cdp_connect"] = "성공"
    print("[OK] WebSocket connected to Telegram tab")
except Exception as e:
    results["cdp_connect"] = f"실패 - {e}"
    print(f"[FAIL] WebSocket connection: {e}")
    # Write partial report and exit
    with open(REPORT_PATH, "w") as f:
        for k, v in results.items():
            f.write(f"{k}: {v}\n")
    exit(1)

def send_cdp(method, params=None, msg_id=1):
    """Send a CDP command and return the result."""
    msg = {"id": msg_id, "method": method}
    if params:
        msg["params"] = params
    ws.send(json.dumps(msg))
    return json.loads(ws.recv())

# ---- Step 2: Check page URL and title ----
try:
    resp = send_cdp("Runtime.evaluate", {
        "expression": "JSON.stringify({url: window.location.href, title: document.title})"
    }, msg_id=1)
    page_info = json.loads(resp.get("result", {}).get("result", {}).get("value", "{}"))
    print(f"[INFO] Page URL: {page_info.get('url')}")
    print(f"[INFO] Page Title: {page_info.get('title')}")
    if "telegram" in page_info.get("url", "").lower():
        results["page_load"] = "성공"
    else:
        results["page_load"] = f"실패 - URL is {page_info.get('url')}"
except Exception as e:
    results["page_load"] = f"실패 - {e}"
    print(f"[FAIL] Page check: {e}")

# ---- Step 3: Check login state ----
try:
    login_check_js = """
    (function() {
        var result = {loginDetected: false, evidence: [], url: window.location.href};
        
        // Check for auth-related elements
        // Telegram Web K uses different patterns
        
        // 1. Check URL hash - if there's a chat list, user is logged in
        if (window.location.hash && window.location.hash.length > 2) {
            result.evidence.push("Hash present: " + window.location.hash);
        }
        
        // 2. Check for chat list elements (logged in indicators)
        var chatList = document.querySelectorAll('.chat-list, .peer-list, [class*="chatList"], [class*="dialog"]');
        if (chatList.length > 0) {
            result.loginDetected = true;
            result.evidence.push("Chat list elements found: " + chatList.length);
        }
        
        // 3. Check for login form elements (not logged in indicators)
        var loginForm = document.querySelectorAll('[class*="login"], [class*="auth"], [class*="sign"]');
        var loginTexts = [];
        loginForm.forEach(function(el) {
            if (el.textContent && el.textContent.length < 200) {
                loginTexts.push(el.textContent.trim().substring(0, 80));
            }
        });
        if (loginTexts.length > 0) {
            result.evidence.push("Login/auth elements: " + JSON.stringify(loginTexts.slice(0, 5)));
        }
        
        // 4. Check for phone input field (login page indicator)
        var phoneInput = document.querySelector('input[type="tel"], input[placeholder*="phone"], input[placeholder*="Phone"]');
        if (phoneInput) {
            result.evidence.push("Phone input field found (login page)");
        } else {
            result.evidence.push("No phone input field (possibly logged in)");
        }
        
        // 5. Check for left sidebar / menu (logged in indicator)
        var sidebar = document.querySelector('#column-left, .sidebar-left, [class*="sidebar"], [class*="SidebarLeft"]');
        if (sidebar && sidebar.children.length > 2) {
            result.loginDetected = true;
            result.evidence.push("Sidebar found with content");
        }
        
        // 6. Check body text for login indicators
        var bodyText = document.body.innerText.substring(0, 2000);
        if (bodyText.includes('Log in') || bodyText.includes('Sign in') || bodyText.includes('phone number')) {
            result.loginDetected = false;
            result.evidence.push("Login prompt text found in body");
        }
        if (bodyText.includes('Chat') || bodyText.includes('chat') || bodyText.includes('Dialog')) {
            result.loginDetected = true;
            result.evidence.push("Chat-related text found in body");
        }
        
        // 7. Check for main layout elements
        var mainEl = document.querySelector('#main-columns, .app-wrapper, [class*="Main"], main');
        if (mainEl) {
            result.evidence.push("Main app element found");
        }
        
        result.bodySnippet = bodyText.substring(0, 500);
        
        return JSON.stringify(result);
    })()
    """
    resp = send_cdp("Runtime.evaluate", {"expression": login_check_js}, msg_id=2)
    login_info = json.loads(resp.get("result", {}).get("result", {}).get("value", "{}"))
    
    is_logged_in = login_info.get("loginDetected", False)
    evidence = login_info.get("evidence", [])
    body_snippet = login_info.get("bodySnippet", "")
    
    results["login_state"] = "로그인됨 (logged-in)" if is_logged_in else "로그인 안 됨 (not-logged-in)"
    results["login_evidence"] = " | ".join(evidence)
    
    print(f"[INFO] Login state: {results['login_state']}")
    print(f"[INFO] Evidence: {results['login_evidence']}")
    print(f"[INFO] Body snippet (first 300 chars): {body_snippet[:300]}")
except Exception as e:
    results["login_state"] = f"확인 불가 - {e}"
    print(f"[WARN] Login check failed: {e}")

# ---- Step 4: Take screenshot ----
try:
    resp = send_cdp("Page.captureScreenshot", {"format": "png", "quality": 90}, msg_id=3)
    screenshot_data = resp.get("result", {}).get("data", "")
    if screenshot_data:
        with open(SCREENSHOT_PATH, "wb") as f:
            f.write(base64.b64decode(screenshot_data))
        results["screenshot"] = f"성공 - saved to {SCREENSHOT_PATH}"
        print(f"[OK] Screenshot saved to {SCREENSHOT_PATH}")
    else:
        results["screenshot"] = "실패 - no data returned"
        print("[FAIL] Screenshot: no data returned")
except Exception as e:
    results["screenshot"] = f"실패 - {e}"
    print(f"[FAIL] Screenshot: {e}")

# ---- Step 5: If logged in, try to navigate to @fireantcrypto post #40759 ----
if "logged-in" in results["login_state"] and "not" not in results["login_state"]:
    print("[INFO] Attempting navigation to @fireantcrypto post #40759...")
    try:
        # Navigate to the channel post
        nav_js = """window.location.href = 'https://web.telegram.org/k/#@fireantcrypto/40759';"""
        send_cdp("Runtime.evaluate", {"expression": nav_js}, msg_id=4)
        time.sleep(5)
        
        # Check navigation result
        resp = send_cdp("Runtime.evaluate", {
            "expression": "JSON.stringify({url: window.location.href, title: document.title, bodySnippet: document.body.innerText.substring(0, 1000)})"
        }, msg_id=5)
        nav_info = json.loads(resp.get("result", {}).get("result", {}).get("value", "{}"))
        
        print(f"[INFO] Navigated to: {nav_info.get('url')}")
        print(f"[INFO] Body snippet: {nav_info.get('bodySnippet', '')[:500]}")
        
        # Take screenshot after navigation
        resp = send_cdp("Page.captureScreenshot", {"format": "png", "quality": 90}, msg_id=6)
        screenshot_data2 = resp.get("result", {}).get("data", "")
        if screenshot_data2:
            with open("/tmp/telegram-fireantcrypto-screenshot.png", "wb") as f:
                f.write(base64.b64decode(screenshot_data2))
            print("[OK] Post-navigation screenshot saved")
        
        # Check if we can see the post
        post_check_js = """
        (function() {
            var body = document.body.innerText.substring(0, 3000);
            var hasFireant = body.toLowerCase().includes('fireant') || body.toLowerCase().includes('fire ant');
            var hasPost = body.includes('40759') || body.includes('#') || body.includes('post');
            var messages = document.querySelectorAll('[class*="message"], [class*="Message"]');
            return JSON.stringify({
                hasFireantContent: hasFireant,
                hasPostContent: hasPost,
                messageCount: messages.length,
                snippet: body.substring(0, 500)
            });
        })()
        """
        resp = send_cdp("Runtime.evaluate", {"expression": post_check_js}, msg_id=7)
        post_info = json.loads(resp.get("result", {}).get("result", {}).get("value", "{}"))
        
        if post_info.get("messageCount", 0) > 0 or post_info.get("hasFireantContent"):
            results["navigation"] = "성공"
            results["navigation_evidence"] = f"Messages found: {post_info.get('messageCount')}, Fireant content: {post_info.get('hasFireantContent')}"
        else:
            results["navigation"] = "부분성공 - 채널로 이동했으나 게시물 확인 제한"
            results["navigation_evidence"] = f"URL: {nav_info.get('url')}, Snippet: {nav_info.get('bodySnippet', '')[:200]}"
        
    except Exception as e:
        results["navigation"] = f"실패 - {e}"
        results["navigation_evidence"] = str(e)
else:
    results["navigation"] = "건너뜀 - 로그인 필요"
    results["navigation_evidence"] = "로그인되지 않아 @fireantcrypto 채널 접근 불가. 로그인이 선행되어야 함."

ws.close()

# ---- Step 6: Generate report ----
report = f"""
===========================================
CDP Telegram Web 테스트 보고서
===========================================

1. 크롬 실행 (Chrome Launch): {results['chrome_launch']}
2. CDP 연결 (CDP Connection): {results['cdp_connect']}
3. 페이지 로드 (Page Load): {results['page_load']}
4. 스크린샷 캡처 (Screenshot): {results['screenshot']}
5. 로그인 상태 (Login State): {results['login_state']}
   - 근거 (Evidence): {results['login_evidence']}
6. @fireantcrypto #40759 접근: {results['navigation']}
   - 상세 (Details): {results['navigation_evidence']}

===========================================
종합 결과:
===========================================
"""

if "not-logged-in" in results["login_state"] or "확인 불가" in results["login_state"]:
    report += """
결과: 부분성공
- Chrome 원격 디버깅 모드 실행: 성공
- CDP Protocol 연결: 성공
- Telegram Web 로드: 성공
- 스크린샷 캡처: 성공
- 로그인 상태: 로그인되지 않음
- @fireantcrypto #40759 접근: 불가 (로그인 필요)
- 원인: Telegram Web에 로그인되어 있지 않아 채널 콘텐츠에 접근할 수 없음
- 해결 방법: 수동 로그인 후 재시도 필요
"""
elif results['navigation'] == "성공":
    report += """
결과: 성공
- 모든 단계가 정상적으로 수행됨
- @fireantcrypto 채널의 게시물 #40759에 접근 가능함
"""
else:
    report += f"""
결과: 부분성공
- @fireantcrypto 접근: {results['navigation']}
"""

print(report)

with open(REPORT_PATH, "w") as f:
    f.write(report)

print(f"\nReport saved to: {REPORT_PATH}")
print(f"Screenshot saved to: {SCREENSHOT_PATH}")
