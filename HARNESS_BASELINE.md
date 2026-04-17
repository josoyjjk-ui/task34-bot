# Harness Stable Baseline (Reference)

## Latest stable snapshot
- Alias path: `/Users/fireant/.openclaw/backups/harness-stable-latest`
- Concrete path: `/Users/fireant/.openclaw/backups/harness-stable-20260414-063551`
- Created: 2026-04-14 06:35:51 (Asia/Seoul)

## Why this exists
- Used as known-good restore point when harness behavior regresses.
- Preserves current working state for config, auth profiles, plugin runtime, and workspace policy files.

## Quick integrity check
```bash
cd /Users/fireant/.openclaw/backups/harness-stable-latest
shasum -a 256 -c checksums.sha256
```

## Quick restore
```bash
/Users/fireant/.openclaw/backups/harness-stable-latest/restore.sh
openclaw gateway restart
sleep 2
openclaw gateway probe
```

## Included set
- `openclaw.json`, `models.json`
- `auth-profiles.json`, `auth-state.json`
- harness plugin runtime: `dist/index.js`
- workspace policy/context: `AGENTS.md`, `SOUL.md`, `TOOLS.md`, `IDENTITY.md`, `USER.md`
- launch agents and watchdog script

## Operational note
- If a new patch causes errors, restore this baseline first, verify gateway probe, then re-apply changes incrementally.

