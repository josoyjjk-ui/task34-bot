const { google } = require('googleapis');
const fs = require('fs');

const TOKEN_PATH = '/Users/fireant/.openclaw/workspace/secrets/google-token.json';

async function main() {
  const tokenData = JSON.parse(fs.readFileSync(TOKEN_PATH, 'utf8'));
  console.log(`Token file: ${TOKEN_PATH}`);
  console.log(`Token expiry: ${tokenData.expiry}`);
  console.log(`Scopes: ${tokenData.scopes.join(', ')}`);

  const hasCalendarScope = tokenData.scopes.includes('https://www.googleapis.com/auth/calendar');
  console.log(`Calendar scope present: ${hasCalendarScope}`);

  const expiryDate = new Date(tokenData.expiry);
  const now = new Date();
  const isExpired = now > expiryDate;
  console.log(`Current time: ${now.toISOString()}`);
  console.log(`Token expired: ${isExpired}`);

  const oauth2Client = new google.auth.OAuth2(
    tokenData.client_id,
    tokenData.client_secret,
    'http://localhost'
  );

  oauth2Client.setCredentials({
    refresh_token: tokenData.refresh_token,
    access_token: tokenData.access_token || tokenData.token,
    expiry_date: expiryDate.getTime(),
  });

  if (isExpired) {
    console.log('\nRefreshing expired token...');
    try {
      const { credentials } = await oauth2Client.refreshAccessToken();
      console.log('✅ Token refreshed successfully!');
      console.log(`New expiry: ${credentials.expiry_date ? new Date(credentials.expiry_date).toISOString() : 'unknown'}`);

      const updatedToken = {
        ...tokenData,
        access_token: credentials.access_token,
        token: credentials.access_token,
        expiry: credentials.expiry_date ? new Date(credentials.expiry_date).toISOString() : undefined,
        refresh_token: credentials.refresh_token || tokenData.refresh_token,
        scopes: credentials.scope ? credentials.scope.split(' ') : tokenData.scopes
      };

      fs.writeFileSync(TOKEN_PATH, JSON.stringify(updatedToken, null, 2));
      console.log(`Token file updated: ${TOKEN_PATH}`);
    } catch (err) {
      console.error('Token refresh failed:', err.message);
      
      // Try with the credentials from google-calendar-credentials.json
      console.log('\nTrying with google-calendar-credentials.json client_id/secret...');
      const credData = JSON.parse(fs.readFileSync('/Users/fireant/.openclaw/workspace/secrets/google-calendar-credentials.json', 'utf8'));
      const installed = credData.installed;
      
      const oauth2Client2 = new google.auth.OAuth2(
        installed.client_id,
        installed.client_secret,
        'http://localhost'
      );
      
      oauth2Client2.setCredentials({
        refresh_token: tokenData.refresh_token,
      });
      
      try {
        const { credentials: creds2 } = await oauth2Client2.refreshAccessToken();
        console.log('✅ Token refreshed with alternate credentials!');
        console.log(`New expiry: ${creds2.expiry_date ? new Date(creds2.expiry_date).toISOString() : 'unknown'}`);
        
        const updatedToken = {
          ...tokenData,
          access_token: creds2.access_token,
          token: creds2.access_token,
          expiry: creds2.expiry_date ? new Date(creds2.expiry_date).toISOString() : undefined,
          refresh_token: creds2.refresh_token || tokenData.refresh_token,
          client_id: installed.client_id,
          client_secret: installed.client_secret,
          scopes: creds2.scope ? creds2.scope.split(' ') : tokenData.scopes
        };
        
        fs.writeFileSync(TOKEN_PATH, JSON.stringify(updatedToken, null, 2));
        console.log(`Token file updated: ${TOKEN_PATH}`);
      } catch (err2) {
        console.error('Alternate refresh also failed:', err2.message);
        process.exit(1);
      }
    }
  }

  // Validate with calendar API
  console.log('\nValidating token with Calendar API...');
  const calendar = google.calendar({ version: 'v3', auth: oauth2Client });
  
  try {
    const calendarList = await calendar.calendarList.list({ maxResults: 5 });
    console.log('✅ Calendar API access validated!');
    console.log('Calendars:', calendarList.data.items.map(c => `${c.summary} (${c.id})`).join(', '));
  } catch (err) {
    console.error('Calendar API validation failed:', err.message);
    process.exit(1);
  }
}

main().catch(err => {
  console.error('Fatal error:', err);
  process.exit(1);
});
