#!/usr/bin/env python3
"""Create a Google Calendar event using the same OAuth2 credential pattern
discovered in sync_bridge34_calendar.py.

Auth method:  OAuth2 token file (google-bridge34-token.json)
API:          google-api-python-client, calendar v3
Calendar:     primary
"""
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
        d['token'] = creds.token
        with open(TOKEN_PATH, 'w') as f:
            json.dump(d, f)
        print("Token refreshed.")
    return creds

def main():
    creds = get_creds()
    service = build('calendar', 'v3', credentials=creds)

    event = {
        'summary': '블록스트릿 혜디 디너',
        'start': {
            'dateTime': '2026-04-15T18:30:00+09:00',
            'timeZone': 'Asia/Seoul',
        },
        'end': {
            'dateTime': '2026-04-15T20:30:00+09:00',
            'timeZone': 'Asia/Seoul',
        },
    }

    calendar_id = 'primary'
    result = service.events().insert(calendarId=calendar_id, body=event).execute()

    print("=" * 60)
    print("Event created successfully!")
    print("=" * 60)
    print(f"  Title:       {result.get('summary')}")
    print(f"  Start:       {result['start'].get('dateTime')}")
    print(f"  End:         {result['end'].get('dateTime')}")
    print(f"  Calendar ID: {calendar_id}")
    print(f"  Event ID:    {result.get('id')}")
    print(f"  Event Link:  {result.get('htmlLink')}")
    print(f"  Status:      {result.get('status')}")
    print("=" * 60)
    return result

if __name__ == '__main__':
    main()
