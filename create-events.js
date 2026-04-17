const { google } = require('googleapis');
const fs = require('fs');

const CREDENTIALS_PATH = '/Users/fireant/.openclaw/workspace/secrets/google-calendar-credentials.json';
const TOKEN_PATHS = [
  '/Users/fireant/.openclaw/workspace/secrets/google-token.json',
  '/Users/fireant/.openclaw/workspace/secrets/google-bridge34-token.json',
];
const CALENDAR_ID = 'fireant@bridge34.com';

async function tryWithToken(tokenPath) {
  const credentials = JSON.parse(fs.readFileSync(CREDENTIALS_PATH, 'utf8'));
  const token = JSON.parse(fs.readFileSync(tokenPath, 'utf8'));
  console.log(`\nTrying token: ${tokenPath}`);
  console.log('Token expiry:', token.expiry);
  console.log('Token client_id:', token.client_id);
  console.log('Credentials client_id:', credentials.installed.client_id);

  // Use token's own client_id/secret since refresh_token was issued to that client
  const clientId = token.client_id;
  const clientSecret = token.client_secret;

  const oauth2Client = new google.auth.OAuth2(clientId, clientSecret, 'http://localhost');
  oauth2Client.setCredentials(token);

  // Test with a simple calendar list call first
  const calendar = google.calendar({ version: 'v3', auth: oauth2Client });

  try {
    const listRes = await calendar.events.list({
      calendarId: CALENDAR_ID,
      maxResults: 1,
      singleEvents: true,
      orderBy: 'startTime',
    });
    console.log('✅ Token is valid! Calendar accessible.');
    return { oauth2Client, calendar, token, tokenPath };
  } catch (err) {
    console.log('❌ Token failed:', err.message);
    return null;
  }
}

async function main() {
  let authResult = null;

  for (const tp of TOKEN_PATHS) {
    authResult = await tryWithToken(tp);
    if (authResult) break;
  }

  if (!authResult) {
    console.error('All tokens failed. Need to re-authenticate.');
    process.exit(1);
  }

  const { oauth2Client, calendar, token } = authResult;

  // Save refreshed tokens
  oauth2Client.on('tokens', (newTokens) => {
    if (newTokens.refresh_token) token.refresh_token = newTokens.refresh_token;
    token.access_token = newTokens.access_token;
    token.expiry = newTokens.expiry_date;
    fs.writeFileSync(authResult.tokenPath, JSON.stringify(token, null, 2));
    console.log('Token refreshed and saved.');
  });

  const events = [
    {
      summary: '빌리언즈 에빈 미팅',
      start: { dateTime: '2026-04-15T14:30:00+09:00' },
      end:   { dateTime: '2026-04-15T15:00:00+09:00' },
    },
    {
      summary: '카이아 샘 미팅',
      start: { dateTime: '2026-04-15T16:00:00+09:00' },
      end:   { dateTime: '2026-04-15T16:30:00+09:00' },
    },
    {
      summary: '데이빗 미팅',
      start: { dateTime: '2026-04-15T16:30:00+09:00' },
      end:   { dateTime: '2026-04-15T17:00:00+09:00' },
    },
  ];

  for (const evt of events) {
    try {
      const res = await calendar.events.insert({
        calendarId: CALENDAR_ID,
        resource: evt,
      });
      console.log(`✅ "${evt.summary}" created`);
      console.log(`   Link: ${res.data.htmlLink}`);
    } catch (err) {
      console.error(`❌ Failed to create "${evt.summary}":`, err.message);
      process.exit(1);
    }
  }

  console.log('\n🎉 All 3 events created successfully!');
}

main().catch(err => {
  console.error('Fatal error:', err.message);
  process.exit(1);
});
