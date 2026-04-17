#!/usr/bin/env python3
"""
Update Google Sheet domain sharing permissions via Drive API.
Sets bridge34.com domain as viewer for spreadsheet 1UREQIQbaUIdsVNC7CgpGluApkGkiXnt3aPvomHE07cU
"""
import json
import urllib.request
import urllib.parse
import ssl
import sys

SECRETS_BASE = "/Users/fireant/.openclaw/workspace/secrets"
SPREADSHEET_ID = "1UREQIQbaUIdsVNC7CgpGluApkGkiXnt3aPvomHE07cU"
TARGET_DOMAIN = "bridge34.com"
TARGET_ROLE = "reader"

ctx = ssl.create_default_context()

def load_json(path):
    with open(path) as f:
        return json.load(f)

def refresh_access_token():
    """Refresh Google OAuth access token using josoyjjk credentials."""
    client = load_json(f"{SECRETS_BASE}/oauth-client.json")["installed"]
    token = load_json(f"{SECRETS_BASE}/google-josoyjjk-token.json")
    
    data = urllib.parse.urlencode({
        "client_id": client["client_id"],
        "client_secret": client["client_secret"],
        "refresh_token": token["refresh_token"],
        "grant_type": "refresh_token",
    }).encode()
    
    req = urllib.request.Request("https://oauth2.googleapis.com/token", data=data)
    try:
        with urllib.request.urlopen(req, context=ctx) as resp:
            result = json.loads(resp.read())
        print(f"[OK] Access token refreshed, expires in {result.get('expires_in')}s")
        return result["access_token"]
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(f"[ERROR] Token refresh failed: {e.code} {error_body}")
        sys.exit(1)

def api_call(access_token, method, url, body=None):
    """Make authenticated API call."""
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, context=ctx) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        return e.code, json.loads(error_body) if error_body else {}

def list_permissions(access_token):
    """List all current permissions on the file."""
    status, data = api_call(
        access_token, "GET",
        f"https://www.googleapis.com/drive/v3/files/{SPREADSHEET_ID}/permissions?fields=permissions(id,type,emailAddress,domain,role,allowFileDiscovery)"
    )
    if status != 200:
        print(f"[ERROR] permissions.list failed: {status} {data}")
        sys.exit(1)
    return data.get("permissions", [])

def create_domain_permission(access_token):
    """Create domain viewer permission."""
    body = {
        "type": "domain",
        "domain": TARGET_DOMAIN,
        "role": TARGET_ROLE,
    }
    # Use sendNotificationEmails=false to avoid spamming
    status, data = api_call(
        access_token, "POST",
        f"https://www.googleapis.com/drive/v3/files/{SPREADSHEET_ID}/permissions?sendNotificationEmails=false",
        body=body
    )
    return status, data

def main():
    print("=" * 60)
    print("Google Sheet Domain Permission Update")
    print(f"File: {SPREADSHEET_ID}")
    print(f"Target: domain={TARGET_DOMAIN}, role={TARGET_ROLE}")
    print("=" * 60)
    
    # Step 1: Get access token
    print("\n[1] Refreshing access token...")
    access_token = refresh_access_token()
    
    # Step 2: List existing permissions
    print("\n[2] Listing existing permissions...")
    perms = list_permissions(access_token)
    print(f"    Found {len(perms)} existing permissions:")
    for p in perms:
        identity = p.get("emailAddress") or p.get("domain") or p.get("id")
        print(f"      - id={p['id']}, type={p['type']}, role={p['role']}, identity={identity}")
    
    # Step 3: Check if domain permission already exists
    existing_domain_perms = [p for p in perms if p.get("domain") == TARGET_DOMAIN and p.get("type") == "domain"]
    if existing_domain_perms:
        print(f"\n[WARN] Domain permission for '{TARGET_DOMAIN}' already exists:")
        for p in existing_domain_perms:
            print(f"      - id={p['id']}, role={p['role']}")
        print("    Skipping creation to avoid duplication.")
        print("\n[DONE] No changes needed - permission already in place.")
        return
    
    # Step 4: Create new domain permission
    print(f"\n[3] Creating domain permission for '{TARGET_DOMAIN}' with role '{TARGET_ROLE}'...")
    status, data = create_domain_permission(access_token)
    
    if status == 200:
        print(f"    [SUCCESS] Permission created!")
        print(f"    Permission ID: {data.get('id')}")
        print(f"    Type: {data.get('type')}")
        print(f"    Domain: {data.get('domain')}")
        print(f"    Role: {data.get('role')}")
    else:
        print(f"    [ERROR] Failed with status {status}: {data}")
        sys.exit(1)
    
    # Step 5: Verify by listing permissions again
    print("\n[4] Verifying updated permissions...")
    perms_after = list_permissions(access_token)
    domain_perms = [p for p in perms_after if p.get("domain") == TARGET_DOMAIN]
    if domain_perms:
        print(f"    [VERIFIED] Domain permission for '{TARGET_DOMAIN}' is active:")
        for p in domain_perms:
            print(f"      - id={p['id']}, role={p['role']}")
    else:
        print("    [WARN] Domain permission not found in verification list!")
    
    print("\n[DONE] Permission update completed successfully.")

if __name__ == "__main__":
    main()
