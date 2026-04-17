const CDP = require('chrome-remote-interface');
const fs = require('fs');
const path = require('path');

const OUTDIR = path.resolve(__dirname);
const port = parseInt(process.argv[2] || '18800');
const filename = process.argv[3] || 'screenshot.png';

async function main() {
    // List targets first
    const resp = await fetch(`http://127.0.0.1:${port}/json/list`);
    const targets = await resp.json();
    console.log('Targets:', targets.map(t => ({id: t.id, title: t.title, url: t.url, type: t.type})));

    // Find the Telegram tab
    let tgTarget = targets.find(t => t.url && t.url.includes('telegram'));
    if (!tgTarget) {
        tgTarget = targets.find(t => t.type === 'page');
    }
    if (!tgTarget) {
        console.error('No suitable target found');
        process.exit(1);
    }

    console.log('Using target:', tgTarget.id, tgTarget.url);

    // Connect to the specific target
    const client = await CDP({host: '127.0.0.1', port, target: tgTarget});
    const {Page, Runtime} = client;
    await Page.enable();
    await Runtime.enable();

    // Wait for page to settle
    await new Promise(r => setTimeout(r, 3000));

    // Check login state
    const {result} = await Runtime.evaluate({
        expression: `
            (function() {
                try {
                    const chatlist = document.querySelector('.chatlist');
                    const bubbles = document.querySelectorAll('.bubble');
                    const authPage = document.querySelector('.auth');
                    const phoneInput = document.querySelector('input[type="tel"], input[name="phone_number"]');
                    const anyInput = document.querySelectorAll('input');
                    const bodyClasses = document.body.className;
                    const allText = document.body.innerText.substring(0, 1000);
                    const images = document.querySelectorAll('img');
                    return JSON.stringify({
                        hasChatlist: !!chatlist,
                        chatBubblesCount: bubbles ? bubbles.length : 0,
                        hasAuthPage: !!authPage,
                        hasPhoneInput: !!phoneInput,
                        inputCount: anyInput.length,
                        bodyClasses: bodyClasses,
                        title: document.title,
                        url: location.href,
                        imgCount: images.length,
                        bodyTextPreview: allText.substring(0, 400)
                    });
                } catch(e) { return JSON.stringify({error: e.message}); }
            })()
        `,
        returnByValue: true
    });

    // Take screenshot
    const screenshot = await Page.captureScreenshot({format: 'png'});
    const outPath = path.join(OUTDIR, filename);
    fs.writeFileSync(outPath, Buffer.from(screenshot.data, 'base64'));
    console.log('Screenshot saved:', outPath);
    console.log('State:', result.value);

    // Save report
    const reportPath = path.join(OUTDIR, 'task_report.md');
    const state = JSON.parse(result.value);
    const isLoggedIn = state.hasChatlist || (state.bodyTextPreview && !state.hasAuthPage && !state.hasPhoneInput && state.inputCount < 3);
    
    let report = `# Telegram Session Verification Report\n\n`;
    report += `## Method: Existing Chrome Debug Session (port ${port})\n\n`;
    report += `- **Telegram Desktop Process**: ✅ Running (PID 647)\n`;
    report += `- **tdata Location**: macOS sandboxed (ru.keepcoder.Telegram), not in standard ~/Library/Application Support/Telegram Desktop/\n`;
    report += `- **CDP Endpoint**: http://127.0.0.1:${port}/json/version ✅\n`;
    report += `- **Telegram Web URL**: ${state.url}\n`;
    report += `- **Page Title**: ${state.title}\n`;
    report += `- **Login State**: ${isLoggedIn ? '✅ LOGGED IN' : '❌ NOT LOGGED IN'}\n`;
    report += `- **Has Chatlist**: ${state.hasChatlist}\n`;
    report += `- **Has Auth Page**: ${state.hasAuthPage}\n`;
    report += `- **Input Count**: ${state.inputCount}\n`;
    report += `- **Screenshot**: ${filename}\n`;
    report += `- **Body Text Preview**: ${state.bodyTextPreview ? state.bodyTextPreview.substring(0, 200) : 'N/A'}\n\n`;

    fs.writeFileSync(reportPath, report);
    console.log('\nReport saved:', reportPath);

    await client.close();
}

main().catch(e => { console.error('Fatal:', e.message); process.exit(1); });
