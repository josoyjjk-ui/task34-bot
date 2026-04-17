# choaeong.com DNS/호스팅 진단 보고서

실행 일시: 2026-04-16
워크스페이스: /Users/fireant/.openclaw/harness-execution-workspaces/plan-20260416-431in4-Jsf8ib/workspace

---

## 1. dig choaeong.com A +short (원시 출력)
```
```
> 결과: 빈 출력 — A 레코드 없음

---

## 2. dig choaeong.com NS +short (원시 출력)
```
```
> 결과: 빈 출력 — NS 레코드 없음

---

## 3. dig choaeong.com CNAME +short (원시 출력)
```
```
> 결과: 빈 출력 — CNAME 레코드 없음

---

## 4. whois choaeong.com 2>/dev/null | grep -E "(Name Server|Registrar|Exp|Status|Updated)" | head -20 (원시 출력)
```
```
> 결과: 빈 출력 — 매칭 필드 없음

---

## 5. curl -sI https://choaeong.com 2>/dev/null | head -10 (원시 출력)
```
```
> 결과: 빈 출력 — 호스트 해석 불가

---

## 6. curl -sI http://choaeong.com 2>/dev/null | head -10 (원시 출력)
```
```
> 결과: 빈 출력 — 호스트 해석 불가

---

## 진단 보조 (원인 확인용)

### dig choaeong.com A +noall +answer
```
; <<>> DiG 9.10.6 <<>> choaeong.com A +noall +answer
;; global options: +cmd
```
→ Answer 섹션 비어 있음 (A 레코드 없음)

### whois choaeong.com (처음 50줄)
```
% IANA WHOIS server
% for more information on IANA, visit http://www.iana.org
% This query returned 1 object

refer:        whois.verisign-grs.com

domain:       COM

organisation: VeriSign Global Registry Services
address:      12061 Bluemont Way
address:      Reston VA 20190
address:      United States of America (the)

contact:      administrative
name:         Registry Customer Service
organisation: VeriSign Global Registry Services
address:      12061 Bluemont Way
address:      Reston VA 20190
address:      United States of America (the)
phone:        +1 703 925-6999
fax-no:       +1 703 948 3978
e-mail:       info@verisign-grs.com

contact:      technical
name:         Registry Customer Service
organisation: VeriSign Global Registry Services
address:      12061 Bluemont Way
address:      Reston VA 20190
address:      United States of America (the)
phone:        +1 703 925-6999
fax-no:       +1 703 948 3978
e-mail:       info@verisign-grs.com

nserver:      A.GTLD-SERVERS.NET 192.5.6.30 2001:503:a83e:0:0:0:2:30
nserver:      B.GTLD-SERVERS.NET 192.33.14.30 2001:503:231d:0:0:0:2:30
nserver:      C.GTLD-SERVERS.NET 192.26.92.30 2001:503:83eb:0:0:0:0:30
nserver:      D.GTLD-SERVERS.NET 192.31.80.30 2001:500:856e:0:0:0:0:30
nserver:      E.GTLD-SERVERS.NET 192.12.94.30 2001:502:1ca1:0:0:0:0:30
nserver:      F.GTLD-SERVERS.NET 192.35.51.30 2001:503:d414:0:0:0:0:30
nserver:      G.GTLD-SERVERS.NET 192.42.93.30 2001:503:eea3:0:0:0:0:30
nserver:      H.GTLD-SERVERS.NET 192.54.112.30 2001:502:8cc:0:0:0:0:30
nserver:      I.GTLD-SERVERS.NET 192.43.172.30 2001:503:39c1:0:0:0:0:30
nserver:      J.GTLD-SERVERS.NET 192.48.79.30 2001:502:7094:0:0:0:0:30
nserver:      K.GTLD-SERVERS.NET 192.52.178.30 2001:503:d2d:0:0:0:0:30
nserver:      L.GTLD-SERVERS.NET 192.41.162.30 2001:500:d937:0:0:0:0:30
nserver:      M.GTLD-SERVERS.NET 192.55.83.30 2001:501:b1f9:0:0:0:0:30
ds-rdata:     19718 13 2 8acbb0cd28f41250a80a491389424d341522d946b0da0c0291f2d3d771d7805a

whois:        whois.verisign-grs.com
```
→ IANA 루트에서 COM TLD 참조만 반환됨. choaeong.com의 Registrar, Name Server, Expiry 등 등록 정보가 존재하지 않음.

### curl -svI https://choaeong.com (에러 확인)
```
* Could not resolve host: choaeong.com
* Closing connection
```

### curl -svI http://choaeong.com (에러 확인)
```
* Could not resolve host: choaeong.com
* Closing connection
```

---

## 최종 요약

✅ choaeong.com DNS/호스팅 진단 6종 명령 실행 완료 — 모든 결과가 빈 출력(미등록 도메인)

요약:
1. (핵심 변경 내용) 요청한 6종 명령을 모두 원문 그대로 실행함. dig A/NS/CNAME +short 3종, whois 필터, curl -sI https/http 2종 모두 빈 출력.
2. (테스트 및 검증 결과) 보조 진단으로 원인 확인: dig Answer 섹션 비어있음, whois는 IANA 루트에서 COM TLD 참조만 반환(Registrar/NS/Expiry 정보 없음), curl은 "Could not resolve host: choaeong.com" 오류.
3. (남은 경고 또는 참고사항) choaeong.com은 DNS 레코드가 전혀 없고 whois 등록 정보도 없어 미등록 또는 만료된 도메인으로 판단됨.

변경 파일: dns-diagnostic-report.md

실행한 테스트:
- dig choaeong.com A +short → 빈 출력
- dig choaeong.com NS +short → 빈 출력
- dig choaeong.com CNAME +short → 빈 출력
- whois choaeong.com 2>/dev/null | grep -E "(Name Server|Registrar|Exp|Status|Updated)" | head -20 → 빈 출력
- curl -sI https://choaeong.com 2>/dev/null | head -10 → 빈 출력
- curl -sI http://choaeong.com 2>/dev/null | head -10 → 빈 출력

경고: choaeong.com은 미등록/만료 상태 도메인. DNS 레코드(A/NS/CNAME) 전무, whois에 Registrar/Name Server/Expiry/Status/Updated 필드 모두 부재.
