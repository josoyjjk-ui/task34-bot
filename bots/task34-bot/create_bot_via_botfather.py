#!/usr/bin/env python3
import asyncio
import re
import subprocess
from telethon import TelegramClient

SESSION='/Users/fireant/.openclaw/workspace/secrets/tg-user-session.session'
CANDIDATES=['task34bot','task34_bot','task34reminder_bot']


def kc(name: str) -> str:
    return subprocess.check_output(['security','find-generic-password','-s',name,'-w'], text=True).strip()


async def wait_reply(client, entity, after_id, timeout=25):
    for _ in range(timeout * 2):
        msgs = await client.get_messages(entity, limit=8)
        for m in msgs:
            if m.id > after_id and not m.out:
                return m
        await asyncio.sleep(0.5)
    return None


async def main():
    api_id = int(kc('telegram-user-api-id'))
    api_hash = kc('telegram-user-api-hash')
    client = TelegramClient(SESSION, api_id, api_hash)

    await client.connect()
    if not await client.is_user_authorized():
        raise RuntimeError('세션이 인증되지 않음. Telethon 재로그인 필요')

    botfather = await client.get_entity('BotFather')
    await client.send_message(botfather, '/cancel')
    await asyncio.sleep(1)

    m = await client.send_message(botfather, '/newbot')
    r = await wait_reply(client, botfather, m.id)
    if not r:
        raise RuntimeError('/newbot 응답 없음')

    m = await client.send_message(botfather, 'Task34')
    r = await wait_reply(client, botfather, m.id)
    if not r:
        raise RuntimeError('봇 이름 전송 후 응답 없음')

    token = None
    chosen = None
    for username in CANDIDATES:
        m = await client.send_message(botfather, username)
        r = await wait_reply(client, botfather, m.id)
        if not r:
            raise RuntimeError(f'username {username} 응답 없음')
        txt = r.message or ''
        matched = re.search(r'(\d{8,12}:[A-Za-z0-9_-]{30,})', txt)
        if matched:
            token = matched.group(1)
            chosen = username
            break

    if not token:
        raise RuntimeError('토큰 파싱 실패. BotFather 대화 확인 필요')

    subprocess.run(['security', 'delete-generic-password', '-s', 'task34-bot-token'], check=False)
    subprocess.check_call(['security', 'add-generic-password', '-s', 'task34-bot-token', '-a', chosen, '-w', token])
    print(f'완료: {chosen}, keychain=task34-bot-token 저장')


if __name__ == '__main__':
    asyncio.run(main())
