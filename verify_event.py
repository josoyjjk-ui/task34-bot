#!/usr/bin/env python3
"""Verify the created event by fetching it back from Google Calendar."""
import json
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

TOKEN_PATH = '/Users/fireant/.openclaw/workspace/secrets/google-bridge34-token.json'

def get_creds():
    with open(TOKEN_PATH) as f:
        d = json.load(f)
    creds = Credentials(
        token=d.get('token'),
        refresh_token=d.get('refresh_token'),
        token_uri='https://oauth2.googleapis.com/token',
        client_id=d.get('client_id'),
        client_secret=d.get('client_secret'),
    )
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return creds

def main():
    creds = get_creds()
    service = build('calendar', 'v3', credentials=creds)

    event_id = 'd02c32pmf76ipp5i1t4hhrf764'
    result = service.events().get(calendarId='primary', eventId=event_id).execute()

    print("Verification result:")
    print(f"  Summary:   {result.get('summary')}")
    print(f"  Start:     {result['start'].get('dateTime')}")
    print(f"  End:       {result['end'].get('dateTime')}")
    print(f"  Status:    {result.get('status')}")
    print(f"  Event ID:  {result.get('id')}")
    print(f"  HTML Link: {result.get('htmlLink')}")
    assert result.get('summary') == '블록스트릿 혜디 디너', "Summary mismatch!"
    assert result.get('status') == 'confirmed', "Status not confirmed!"
    print("\n✅ Verification PASSED — event exists and matches expected data.")

if __name__ == '__main__':
    main()
