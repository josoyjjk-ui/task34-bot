#!/usr/bin/env python3
"""Set Google Spreadsheet sharing to 'Anyone with the link can view'."""
import json
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Load OAuth credentials
TOKEN_FILE = "/Users/fireant/.openclaw/workspace/secrets/google-bridge34-token.json"

with open(TOKEN_FILE, "r") as f:
    token_data = json.load(f)

creds = Credentials.from_authorized_user_info(token_data)

# File ID of the target spreadsheet
FILE_ID = "1UREQIQbaUIdsVNC7CgpGluApkGkiXnt3aPvomHE07cU"

try:
    # Build Drive API service
    service = build("drive", "v3", credentials=creds)

    # Create permission: anyone with the link can view (reader)
    permission_body = {
        "role": "reader",
        "type": "anyone"
    }

    print(f"Calling permissions.create for file {FILE_ID}...")
    print(f"  role={permission_body['role']}, type={permission_body['type']}")

    result = service.permissions().create(
        fileId=FILE_ID,
        body=permission_body,
        fields="id,type,role"
    ).execute()

    print(f"\n✅ Permission created successfully!")
    print(f"   Permission ID: {result.get('id')}")
    print(f"   Type: {result.get('type')}")
    print(f"   Role: {result.get('role')}")

    # Verify: list permissions
    print(f"\n--- Verifying permissions.list ---")
    perms = service.permissions().list(
        fileId=FILE_ID,
        fields="permissions(id,type,role)"
    ).execute()

    for p in perms.get("permissions", []):
        marker = " ← NEW" if p.get("id") == result.get("id") else ""
        print(f"  {p.get('type'):15s} {p.get('role'):15s} id={p.get('id')}{marker}")

except HttpError as e:
    print(f"❌ HTTP Error: {e.status_code}")
    print(f"   Message: {e.error_details}")
    raise
except Exception as e:
    print(f"❌ Error: {e}")
    raise
