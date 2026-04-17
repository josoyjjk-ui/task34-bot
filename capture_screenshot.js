const CDP = require('chrome-remote-interface');
const fs = require('fs');
const path = require('path');

const OUTDIR = path.resolve(__dirname);

async function capture(client, filename) {
    const {Page, Runtime} = client;
    await Page.enable();
    await Runtime.enable();

    // Wait a bit for page to settle
    await new Promise(r => setTimeout(r, 2000));

    // Check login state
    const {result} = await Runtime.evaluate({
        expression: `
            (function() {
                const chatlist = document.querySelector('.chatlist');
                const chatBubbles = document.querySelectorAll('.bubble');
                const loginForm = document.querySelector('.auth');
                const phoneInput = document.querySelector('input[type="tel"], input[name="phone_number"]');
                const bodyClasses = document.body.className;
                const allText = document.body.innerText.substring(0, 800);
                return JSON.stringify({
                    hasChatlist: !!chatlist,
                    chatBubblesCount: chatBubbles.length,
                    hasLoginForm: !!loginForm,
                    hasPhoneInput: !!phoneInput,
                    bodyClasses: bodyClasses,
                    title: document.title,
                    url: location.href,
                    bodyTextPreview: allText.substring(0, 300)
                });
            })()
        `,
        returnByValue: true
    });

    // Take screenshot
    const {data} = await Page.captureScreenshot({format: 'png'});
    const outPath = path.join(OUTDIR, filename);
    fs.writeFileSync(outPath, Buffer.from(data, 'base64'));
    console.log(`Screenshot saved: ${outPath}`);
    console.log(`Login state: ${result.value}`);
    return JSON.parse(result.value);
}

async function main() {
    const port = parseInt(process.argv[2] || '18800');
    const filename = process.argv[3] || 'screenshot.png';

    try {
        const client = await CDP({host: '127.0.0.1', port});
        const state = await capture(client, filename);
        await client.close();

        // Write state report
        const reportPath = path.join(OUTDIR, 'screenshot_report.json');
        const existing = fs.existsSync(reportPath) ? JSON.parse(fs.readFileSync(reportPath)) : {};
        existing[filename] = state;
        fs.writeFileSync(reportPath, JSON.stringify(existing, null, 2));

        console.log('RESULT: ' + (state.hasChatlist ? 'LOGGED_IN' : state.hasLoginForm ? 'LOGIN_FORM' : 'UNKNOWN'));
    } catch(e) {
        console.error('Error:', e.message);
        process.exit(1);
    }
}

main();
