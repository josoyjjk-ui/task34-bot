# 공통일정 1회 표기 원칙 — 사전 점검 체크리스트

> **목적:** 구현 작업 전, 동일 일정이 여러 카테고리/뷰에 중복 표기되지 않도록 **1회만 표기**하는 원칙이 올바르게 적용될 수 있는지 사전 점검  
> **대상 모듈:** dashboard.bridge34.com 일정 모듈 (데이터 수집 → 렌더링 → 표시 전체 흐름)  
> **작성일:** 2026-04-13

---

## 1. 데이터 소스 중복 점검

### 점검 항목명
일정 API 응답 내 동일 `schedule_id` 중복 반환 여부

### 점검 방법
1. 브라우저 DevTools **Network** 탭을 연다.
2. 대시보드 페이지를 로드하여 일정 API 요청(`/api/schedules` 등)을 캡처한다.
3. 응답 JSON을 복사하여 `schedule_id`별 카운트를 수행한다.
   ```javascript
   // 콘솔에서 API 응답粘贴 후 실행
   const ids = response.map(s => s.schedule_id);
   const freq = {};
   ids.forEach(id => freq[id] = (freq[id] || 0) + 1);
   const dupes = Object.entries(freq).filter(([,v]) => v > 1);
   console.log('중복 schedule_id:', dupes.length ? dupes : '없음');
   console.log('총 건수:', ids.length, '/ 유니크 건수:', Object.keys(freq).length);
   ```
4. 여러 엔드포인트(`/api/schedules`, `/api/events`, `/api/calendar` 등) 간에도 동일 `schedule_id`가 교차 반환되는지 비교한다.

### 합격/불합격 기준
| 결과 | 기준 |
|------|------|
| **합격** | 동일 `schedule_id`가 전체 API 응답 내에 **정확히 1건만** 존재 |
| **불합격** | 동일 `schedule_id`가 **2건 이상** 반환됨 (단일 응답 내 중복 또는 다중 엔드포인트 간 중복 포함) |

---

## 2. 카테고리-일정 매핑 중복 점검

### 점검 항목명
단일 일정이 복수 카테고리에 동시 매핑되어 양쪽 뷰에 각각 렌더링되는지 여부

### 점검 방법
1. 단일 일정이 **Category A**와 **Category B**에 동시 매핑된 샘플 데이터를 생성하여 주입한다.
   ```json
   {
     "schedule_id": "test-dup-001",
     "title": "중복테스트 일정",
     "categories": ["AMA", "Fireweek"],
     "start_at": "2026-04-20T10:00:00Z",
     "end_at": "2026-04-20T11:00:00Z"
   }
   ```
2. **Category A(AMA)** 뷰에서 렌더링 결과를 스크린샷 캡처한다.
3. **Category B(Fireweek)** 뷰에서 렌더링 결과를 스크린샷 캡처한다.
4. 두 스크린샷을 비교하여 동일 일정이 양쪽에 모두 표시되는지 확인한다.
5. 브라우저 콘솔에서 DOM 기반 검증:
   ```javascript
   const allCards = document.querySelectorAll('[data-schedule-id="test-dup-001"]');
   console.log('동일 schedule_id DOM 노드 수:', allCards.length);
   ```

### 합격/불합격 기준
| 결과 | 기준 |
|------|------|
| **합격** | 어느 한 카테고리 뷰에만 **1회 표기**되거나, 양쪽 모두 표기 시 **동일 DOM 요소가 중복 생성되지 않음** (총 DOM 노드 수 ≤ 1) |
| **불합격** | 동일 `schedule_id`의 DOM 노드가 **2개 이상** 생성되어 각 카테고리 뷰에 별도로 렌더링됨 |

---

## 3. 프론트엔드 중복 제거 로직 점검

### 점검 항목명
렌더링 함수 내 deduplication(중복 제거) 로직 존재 여부 및 동작 검증

### 점검 방법
1. **소스코드 리뷰** — 렌더링 함수(`scheduleCard`, `timeline`, `renderEvents` 등)에서 다음 패턴이 존재하는지 확인:
   - `Map<schedule_id, boolean>` 또는 `Set` 기반 중복 필터
   - `Array.filter((item, idx, arr) => arr.findIndex(i => i.schedule_id === item.schedule_id) === idx)` 패턴
   - React/Vue의 `key={schedule_id}` prop 사용
2. **단위테스트 작성 및 실행:**
   ```javascript
   test('중복 schedule_id 제거 후 배열 길이 감소', () => {
     const input = [
       { schedule_id: 'A', title: '일정1' },
       { schedule_id: 'A', title: '일정1' },
       { schedule_id: 'B', title: '일정2' },
     ];
     const result = deduplicateSchedules(input); // 점검 대상 함수
     expect(result.length).toBe(2); // 3 → 2로 감소
     expect(result.map(s => s.schedule_id)).toEqual(['A', 'B']);
   });
   ```
3. 중복 제거 로직이 **렌더링 직전**(DOM 삽입 직전)에 실행되는지 호출 시점을 확인한다.

### 합격/불합격 기준
| 결과 | 기준 |
|------|------|
| **합격** | 렌더링 직전 `schedule_id`(unique key) 기준 **중복 제거 코드가 존재**하고, 단위테스트에서 **중복 제거 후 배열 길이가 원본 대비 감소**함을 통과 |
| **불합격** | 중복 제거 로직이 **존재하지 않거나**, 존재하더라도 렌더링 경로상 **우회 가능**하거나, 단위테스트 **미통과** |

---

## 4. 뷰/탭 전환 시 잔여 중복 점검

### 점검 항목명
월간→주간→일간 뷰 전환 시 이전 뷰의 일정 DOM 노드가 잔존하여 중복 표기되는지 여부

### 점검 방법
1. 브라우저 DevTools **Elements** 패널을 연다.
2. **월간 뷰**에서 특정 일정(`schedule_id: "test-persist-001"`)이 렌더링된 DOM 노드를 확인하고 기록한다.
3. **주간 뷰**로 전환한다.
4. Elements 패널에서 이전(월간 뷰)의 일정 DOM 노드가 여전히 존재하는지 검사:
   ```javascript
   // 뷰 전환 후 콘솔에서 실행
   const stale = document.querySelectorAll('[data-schedule-id="test-persist-001"]');
   console.log('전환 후 동일 schedule_id 노드 수:', stale.length);
   // 기대값: 1 (신규 뷰에만 1개 존재)
   ```
5. **일간 뷰**로 전환 후 동일하게 확인한다.
6. (선택) Performance 탭에서 뷰 전환 시 DOM Node 수 변화를 모니터링하여 누적 증가 여부를 확인한다.

### 합격/불합격 기준
| 결과 | 기준 |
|------|------|
| **합격** | 뷰 전환 시 이전 뷰의 일정 DOM이 **완전히 unmount**되고, 신규 뷰에 각 일정이 **1회만 mount**됨 (동일 schedule_id 노드 수 = 1) |
| **불합격** | 이전 뷰의 DOM 노드가 **잔존**하거나, 신규 뷰에 **2개 이상**의 동일 schedule_id 노드가 mount됨 |

---

## 5. End-to-End 시나리오 통합 점검

### 점검 항목명
3개 이상 카테고리에 걸친 다중 소속 일정이 대시보드 전체에서 각각 1회만 표시되는지 종합 검증

### 점검 방법
1. **테스트 데이터 5건**을 등록한다 (각각 3개 이상 카테고리에 소속):
   ```
   #1  schedule_id: E2E-001  카테고리: AMA, Fireweek, 친구초대
   #2  schedule_id: E2E-002  카테고리: 캠페인, 에어드랍, AMA
   #3  schedule_id: E2E-003  카테고리: Fireweek, 친구초대, 캠페인
   #4  schedule_id: E2E-004  카테고리: 에어드랍, AMA, Fireweek
   #5  schedule_id: E2E-005  카테고리: 친구초대, 캠페인, 에어드랍
   ```
2. 대시보드 **전체 영역**(메인 타임라인, 카테고리 사이드바, 위젯, 팝업 등)을 순회하며 각 `schedule_id`의 표기 횟수를 **수동 카운트**한다.
3. 브라우저 콘솔에서 자동 검증:
   ```javascript
   const e2eIds = ['E2E-001','E2E-002','E2E-003','E2E-004','E2E-005'];
   const counts = {};
   e2eIds.forEach(id => {
     counts[id] = document.querySelectorAll(`[data-schedule-id="${id}"]`).length;
   });
   console.table(counts);
   const total = Object.values(counts).reduce((a,b) => a+b, 0);
   console.log('총 표기 건수:', total, '/ 등록 건수: 5');
   console.log(total === 5 ? '✅ 합격' : '❌ 불합격');
   ```
4. 각 카테고리 필터/탭을 개별 선택했을 때도 동일 일정이 중복 표기되지 않는지 확인한다.

### 합격/불합격 기준
| 결과 | 기준 |
|------|------|
| **합격** | 등록한 **5건**이 대시보드 어느 영역에서든 **각각 정확히 1회씩만** 표시되고, **총 표기 건수 = 등록 건수(5)** 일치 |
| **불합격** | 5건 중 **어느 하나라도 2회 이상** 표시되거나, **총 표기 건수 ≠ 5** |

---

## 점검 결과 요약표

| # | 점검 항목 | 결과 | 비고 |
|---|-----------|------|------|
| 1 | 데이터 소스 중복 | ☐ 합격 / ☐ 불합격 | |
| 2 | 카테고리-일정 매핑 중복 | ☐ 합격 / ☐ 불합격 | |
| 3 | 프론트엔드 중복 제거 로직 | ☐ 합격 / ☐ 불합격 | |
| 4 | 뷰/탭 전환 시 잔여 중복 | ☐ 합격 / ☐ 불합격 | |
| 5 | End-to-End 시나리오 통합 | ☐ 합격 / ☐ 불합격 | |

> 점검자: _________  점검일: _________  
> **5개 항목 전부 합격 시에만 구현 착수 허가.**  
> 불합격 항목은 원인 분석 후 재점검.
