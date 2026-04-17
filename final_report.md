# sync_bridge34_calendar.py 실행 결과 보고서

## 실행 명령
```
python3 /Users/fireant/.openclaw/workspace/scripts/sync_bridge34_calendar.py
```

## 종료 코드
1 (비정상 종료)

## STDOUT
(출력 없음)

## STDERR (전체)
```
/Users/fireant/Library/Python/3.9/lib/python/site-packages/google/oauth2/__init__.py:40: FutureWarning: You are using a Python version 3.9 past its end of life. Google will update google-auth with critical bug fixes on a best-effort basis, but not with any other fixes or features. Please upgrade your Python version, and then update google-auth.
  warnings.warn(eol_message.format("3.9"), FutureWarning)
/Users/fireant/Library/Python/3.9/lib/python/site-packages/google/auth/__init__.py:54: FutureWarning: You are using a Python version 3.9 past its end of life. Google will update google-auth with critical bug fixes on a best-effort basis, but not with any other fixes or features. Please upgrade your Python version, and then update google-auth.
  warnings.warn(eol_message.format("3.9"), FutureWarning)
/Users/fireant/Library/Python/3.9/lib/python/site-packages/urllib3/__init__.py:35: NotOpenSSLWarning: urllib3 v2 only supports OpenSSL 1.1.1+, currently the 'ssl' module is compiled with 'LibreSSL 2.8.3'. See: https://github.com/urllib3/urllib3/issues/3020
  warnings.warn(
/Users/fireant/Library/Python/3.9/lib/python/site-packages/google/api_core/_python_version_support.py:246: FutureWarning: You are using a non-supported Python version (3.9.6). Google will not post any further updates to google.api_core supporting this Python version. Please upgrade to the latest Python version, or at least Python 3.10, and update google.api_core.
  warnings.warn(message, FutureWarning)
Traceback (most recent call last):
  File "/Users/fireant/.openclaw/workspace/scripts/sync_bridge34_calendar.py", line 100, in <module>
    events = fetch_events(days_ahead=7)
  File "/Users/fireant/.openclaw/workspace/scripts/sync_bridge34_calendar.py", line 42, in fetch_events
    cals = service.calendarList().list().execute()
  File "/Users/fireant/Library/Python/3.9/lib/python/site-packages/googleapiclient/_helpers.py", line 130, in positional_wrapper
    return wrapped(*args, **kwargs)
  File "/Users/fireant/Library/Python/3.9/lib/python/site-packages/googleapiclient/http.py", line 923, in execute
    resp, content = _retry_request(
  File "/Users/fireant/Library/Python/3.9/lib/python/site-packages/googleapiclient/http.py", line 191, in _retry_request
    resp, content = http.request(uri, method, *args, **kwargs)
  File "/Users/fireant/Library/Python/3.9/lib/python/site-packages/google_auth_httplib2.py", line 242, in request
    self.credentials.refresh(self._request)
  File "/Users/fireant/Library/Python/3.9/lib/python/site-packages/google/oauth2/credentials.py", line 412, in refresh
    ) = reauth.refresh_grant(
  File "/Users/fireant/Library/Python/3.9/lib/python/site-packages/google/oauth2/reauth.py", line 370, in refresh_grant
    _client._handle_error_response(response_data, retryable_error)
  File "/Users/fireant/Library/Python/3.9/lib/python/site-packages/google/oauth2/_client.py", line 69, in _handle_error_response
    raise exceptions.RefreshError(
google.auth.exceptions.RefreshError: ('invalid_grant: Token has been expired or revoked.', {'error': 'invalid_grant', 'error_description': 'Token has been expired or revoked.'})
```

## 원인 요약
Google OAuth 리프레시 토큰이 만료 또는 취소됨(invalid_grant). 재인증 필요.

## 3줄 요약
1. 스크립트 실행 시 Google Calendar API 인증에서 OAuth 리프레시 토큰 만료(invalid_grant)로 실패, 종료 코드 1
2. stdout 출력 없음, stderr에 FutureWarning 4건과 RefreshError 트레이스백 출력
3. 재인증(토큰 재발급) 필요, Python 3.9 EOL로 버전 업그레이드 권장
