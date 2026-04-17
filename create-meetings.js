const { google } = require('googleapis');
const fs = require('fs');
const path = require('path');

const TOKEN_PATH = '/Users/fireant/.openclaw/workspace/secrets/google-bridge34-token.json';

async function main() {
  // Read token file
  console.log('=== Step 1: Locate and Validate Token ===');
  const tokenData = JSON.parse(fs.readFileSync(TOKEN_PATH, 'utf8'));
  console.log(`Token file found: ${TOKEN_PATH}`);
  console.log(`Token expiry: ${tokenData.expiry}`);
  console.log(`Scopes: ${tokenData.scopes.join(', ')}`);

  // Check if calendar scope is present
  const hasCalendarScope = tokenData.scopes.includes('https://www.googleapis.com/auth/calendar');
  console.log(`Calendar scope present: ${hasCalendarScope}`);

  // Check expiry
  const expiryDate = new Date(tokenData.expiry);
  const now = new Date();
  const isExpired = now > expiryDate;
  console.log(`Current time: ${now.toISOString()}`);
  console.log(`Token expired: ${isExpired}`);

  // Create OAuth2 client using credentials from the token file itself
  const client_id = tokenData.client_id;
  const client_secret = tokenData.client_secret;
  const redirect_uri = 'http://localhost';

  const oauth2Client = new google.auth.OAuth2(client_id, client_secret, redirect_uri);

  // Set credentials with refresh token
  oauth2Client.setCredentials({
    refresh_token: tokenData.refresh_token,
    access_token: tokenData.access_token || tokenData.token,
    expiry_date: expiryDate.getTime(),
    token_uri: tokenData.token_uri,
    scopes: tokenData.scopes
  });

  // If expired, refresh the token
  if (isExpired) {
    console.log('\n=== Step 2: Refreshing expired token ===');
    try {
      const { credentials } = await oauth2Client.refreshAccessToken();
      console.log('Token refreshed successfully!');
      console.log(`New expiry: ${credentials.expiry_date ? new Date(credentials.expiry_date).toISOString() : 'unknown'}`);

      // Update token file with new credentials
      const updatedToken = {
        ...tokenData,
        access_token: credentials.access_token,
        token: credentials.access_token,
        expiry: credentials.expiry_date ? new Date(credentials.expiry_date).toISOString() : undefined,
        refresh_token: credentials.refresh_token || tokenData.refresh_token,
        token_uri: credentials.token_uri || tokenData.token_uri,
        scopes: credentials.scope ? credentials.scope.split(' ') : tokenData.scopes
      };

      fs.writeFileSync(TOKEN_PATH, JSON.stringify(updatedToken, null, 2));
      console.log(`Token file updated: ${TOKEN_PATH}`);
    } catch (err) {
      console.error('Token refresh failed:', err.message);
      process.exit(1);
    }
  } else {
    console.log('Token is still valid, no refresh needed.');
  }

  // Validate the token by making a test API call
  console.log('\n=== Step 3: Validate Token with Calendar API ===');
  const calendar = google.calendar({ version: 'v3', auth: oauth2Client });
  
  try {
    const calendarList = await calendar.calendarList.list({ maxResults: 5 });
    console.log('Calendar API access validated successfully!');
    console.log('Calendars:', calendarList.data.items.map(c => `${c.summary} (${c.id})`).join(', '));
  } catch (err) {
    console.error('Calendar API validation failed:', err.message);
    process.exit(1);
  }

  // Create events
  console.log('\n=== Step 4: Create Calendar Events ===');
  
  const events = [
    {
      summary: '빌리언즈 에빈 미팅',
      start: { dateTime: '2026-04-15T14:30:00+09:00' },
      end: { dateTime: '2026-04-15T15:00:00+09:00' }
    },
    {
      summary: '카이아 샘 미팅',
      start: { dateTime: '2026-04-15T16:00:00+09:00' },
      end: { dateTime: '2026-04-15T16:30:00+09:00' }
    },
    {
      summary: '데이빗 미팅',
      start: { dateTime: '2026-04-15T16:30:00+09:00' },
      end: { dateTime: '2026-04-15T17:00:00+09:00' }
    }
  ];

  for (const event of events) {
    try {
      const res = await calendar.events.insert({
        calendarId: 'primary',
        resource: event
      });
      console.log(`✅ Created: "${event.summary}"`);
      console.log(`   Link: ${res.data.htmlLink}`);
      console.log(`   Event ID: ${res.data.id}`);
    } catch (err) {
      console.error(`❌ Failed to create "${event.summary}": ${err.message}`);
    }
  }

  console.log('\n=== Done ===');
}

main().catch(err => {
  console.error('Fatal error:', err);
  process.exit(1);
});
