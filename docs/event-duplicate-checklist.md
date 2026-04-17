# dashboard.bridge34.com 일정 중복 표기 점검 체크리스트

> **원칙:** 동일한 일정(이벤트)이 여러 카테고리·뷰·섹션에 중복 표기되지 않도록 **1회만 표기**  
> **대상:** `events/index.html`, `events.html`, 메인 대시보드 내 이벤트 카드(`.ev-card`, `.ev-card-sm`)  
> **작성일:** 2026-04-13

---

## 1. 데이터 소스 레벨 중복 점검

### 점검 항목명
원천 데이터(HTML 하드코딩·JSON·시트) 내 동일 이벤트 중복 레코드 존재 여부

### 점검 방법
1. `events/index.html`과 `events.html` 파일 내 모든 `.ev-card`, `.ev-card-sm` 요소를 추출한다.
2. 각 카드의 `data-start` + `data-end` + 제목 텍스트(`.ev-title` 내부 텍스트)를 키로 삼아 해시맵을 구성한다.
3. 동일한 `(제목, data-start, data-end)` 조합이 2회 이상 등장하는지 검사한다.
4. `events.json`이 존재할 경우, JSON 내 배열 항목에 대해서도 동일 키 기준 중복을 검사한다.
5. 구체적 명령어 예시:
   ```bash
   # events/index.html 내 카드 제목 + 날짜 추출 후 중복 탐지
   grep -oP '(?<=class="ev-title">)[^<]+' events/index.html | sort | uniq -d
   # events.html 과 교차 중복 확인
   comm -12 <(grep -oP '(?<=class="ev-title">)[^<]+' events/index.html | sort) \
            <(grep -oP '(?<=class="ev-title">)[^<]+' events.html | sort)
   ```

### 합격/불합격 기준
| 결과 | 기준 |
|------|------|
| **합격** | 동일 `(제목, data-start, data-end)` 조합이 전체 소스에서 **정확히 1건**만 존재 |
| **불합격** | 동일 조합이 **2건 이상** 발견됨 (같은 파일 내 중복 또는 `events.html` ↔ `events/index.html` 간 중복 포함) |

---

## 2. 카테고리 분류 중복 점검

### 점검 항목명
동일 이벤트가 복수 카테고리(`AMA`, `Fireweek`, `친구초대`, `캠페인`, `에어드랍` 등)에 걸쳐 중복 분류되었는지 여부

### 점검 방법
1. 각 `.ev-card` 요소 내 `.ev-tag` 요소를 모두 수집한다.
2. 하나의 카드에 부여된 태그 개수를 확인하고, **동일한 의미의 태그가 여러 카드에 서로 다른 카테고리명으로 분산되었는지** 점검한다.
3. 예: "Billions 친구초대 이벤트"가 한 카드에서는 `친구초대` 태그로, 다른 카드에서는 `캠페인` 태그로 각각 별도 카드로 존재하는지 확인.
4. 실제 점검 순서:
   - 브라우저 개발자도구에서 `document.querySelectorAll('.ev-card .ev-tag')` 실행
   - 각 태그의 `textContent`와 부모 카드의 제목을 매핑하여 스프레드시트에 정리
   - 동일 제목의 카드가 2개 이상의 서로 다른 태그 세트로 존재하면 중복 분류

### 합격/불합격 기준
| 결과 | 기준 |
|------|------|
| **합격** | 동일 이벤트(제목 기준)가 **단일 카드에만** 존재하며, 해당 카드의 태그 세트가 **1개의 주 카테고리**로 명확히 분류됨 |
| **불합격** | 동일 이벤트가 **2개 이상의 카드**로 각각 다른 카테고리 태그를 달아 분리 등록되어 있음 |

---

## 3. 뷰/필터 간 중복 점검

### 점검 항목명
"불개미 주관 이벤트" 섹션과 "외부 참여 가능 이벤트" 섹션, 그리고 "종료된 이벤트" 접이식 영역 간에 동일 이벤트가 이중 카운트되는지 여부

### 점검 방법
1. 브라우저에서 `events/index.html` 페이지를 연다.
2. JS 함수 `updateEventStatuses()`가 실행된 후, 다음을 확인한다:
   - **"불개미 주관 이벤트"** 섹션(`#events > .ev-card`)에 남아있는 LIVE 카드 수
   - **"종료된 이벤트"** 섹션(`#ended-events-container > .ev-card`)으로 이동된 카드 수
   - **"외부 참여 가능 이벤트"**(`.ev-card-sm`)에 표시된 카드 수
3. 세 영역의 카드 제목을 각각 수집하여 교집합이 없는지 확인:
   ```javascript
   // 브라우저 콘솔에서 실행
   const live    = [...document.querySelectorAll('#events > .ev-card .ev-title')].map(e => e.textContent.trim());
   const ended   = [...document.querySelectorAll('#ended-events-container .ev-title')].map(e => e.textContent.trim());
   const ext     = [...document.querySelectorAll('.ev-card-sm .ev-title')].map(e => e.textContent.trim());
   const all     = [...live, ...ended, ...ext];
   const dupes   = all.filter((v, i) => all.indexOf(v) !== i);
   console.log('중복 항목:', dupes.length ? dupes : '없음');
   ```
4. LIVE 카운트 배지(`.section-head .count`)의 숫자가 실제 LIVE 카드 수와 일치하는지 확인.

### 합격/불합격 기준
| 결과 | 기준 |
|------|------|
| **합격** | 세 영역(주관/외부/종료)의 카드 제목 교집합이 **0건**이고, LIVE 카운트 배지 숫자가 실제 LIVE 카드 수와 **정확히 일치** |
| **불합격** | 교집합이 **1건 이상** 존재하거나, 카운트 배지가 실제 카드 수와 **불일치** |

---

## 4. DOM 렌더링 중복 점검

### 점검 항목명
동일 이벤트의 DOM 요소가 화면에 2개 이상 렌더링되는지 여부 (JS 동적 생성·이동 로직에 의한 이중 렌더링 포함)

### 점검 방법
1. 브라우저에서 페이지 로드 완료 후 개발자도구 콘솔에서 실행:
   ```javascript
   // data-start/data-end 속성을 가진 모든 카드의 data-start 값 빈도수 확인
   const starts = [...document.querySelectorAll('[data-start][data-end]')]
     .map(el => el.dataset.start + '|' + el.dataset.end);
   const freq = {};
   starts.forEach(s => freq[s] = (freq[s] || 0) + 1);
   const dupes = Object.entries(freq).filter(([,v]) => v > 1);
   console.log('data-start+end 중복:', dupes.length ? dupes : '없음');
   ```
2. `updateEventStatuses()` 함수가 종료된 카드를 `#ended-events-container`로 이동(`appendChild`)할 때, **원본 위치에 잔여 노드가 남지 않는지** DOM 트리에서 확인:
   ```javascript
   // 이동된 카드가 #events 내에도 복제본으로 남아있는지 확인
   const movedSet = new Set(
     [...document.querySelectorAll('#ended-events-container .ev-card')]
       .map(el => el.querySelector('.ev-title')?.textContent.trim())
   );
   const stillInEvents = [...document.querySelectorAll('#events > .ev-card .ev-title')]
     .map(el => el.textContent.trim())
     .filter(t => movedSet.has(t));
   console.log('이동 후 원본위치 잔여:', stillInEvents.length ? stillInEvents : '없음');
   ```
3. 화면에 보이는(visible) 카드 총 개수가 예상 이벤트 수와 일치하는지 확인:
   ```javascript
   const visible = [...document.querySelectorAll('.ev-card, .ev-card-sm')]
     .filter(el => el.offsetParent !== null && el.style.display !== 'none');
   console.log('화면에 보이는 카드 수:', visible.length);
   ```

### 합격/불합격 기준
| 결과 | 기준 |
|------|------|
| **합격** | 동일 `data-start + data-end` 조합의 DOM 요소가 **1개만** 존재하고, `appendChild` 이동 후 원본 위치에 잔여 노드 **0개** |
| **불합격** | 동일 시간 범위의 카드가 **2개 이상** 렌더링되거나, 이동 후 원본 위치에 **복제/잔여 노드** 존재 |

---

## 5. 날짜 경계/반복 일정 중복 점검

### 점검 항목명
연속 일정·반복 일정이 `data-start`/`data-end` 속성 처리 방식으로 인해 여러 카드로 분리 노출되는지 여부

### 점검 방법
1. 동일 프로젝트/캠페인명(예: "Billions", "ETHGAS")이 포함된 카드를 모두 추출한다:
   ```javascript
   // 브라우저 콘솔
   const groups = {};
   document.querySelectorAll('.ev-card, .ev-card-sm').forEach(card => {
     const title = card.querySelector('.ev-title')?.textContent.trim() || '';
     // 프로젝트 키워드 추출 (태그 텍스트 기반)
     const tag = card.querySelector('.ev-tag')?.textContent.trim() || '';
     const key = tag;
     if (!groups[key]) groups[key] = [];
     groups[key].push({
       title,
       start: card.dataset.start,
       end: card.dataset.end
     });
   });
   console.table(
     Object.entries(groups)
       .filter(([,v]) => v.length > 1)
       .flatMap(([k, v]) => v.map(e => ({ category: k, ...e })))
   );
   ```
2. 동일 프로젝트의 여러 카드가 **실제로 별개의 일정**(예: "친구초대 이벤트" vs "Fireweek" vs "AMA 교육세션")인지, 아니면 **동일 일정의 기간 분할**(예: 1주차/2주차로 같은 캠페인을 의도 없이 분리 등록)인지 확인한다.
3. 날짜 범위가 겹치는(overlap) 카드가 있는지 검사:
   ```javascript
   const cards = [...document.querySelectorAll('.ev-card[data-start][data-end]')]
     .map(c => ({ title: c.querySelector('.ev-title')?.textContent.trim(),
                  s: new Date(c.dataset.start).getTime(),
                  e: new Date(c.dataset.end).getTime() }));
   const overlaps = [];
   for (let i = 0; i < cards.length; i++)
     for (let j = i+1; j < cards.length; j++)
       if (cards[i].s < cards[j].e && cards[j].s < cards[i].e)
         overlaps.push([cards[i].title, cards[j].title]);
   console.log('날짜 겹침:', overlaps.length ? overlaps : '없음');
   ```
   ※ Billions AMA(3/16 14:00~15:30)가 Fireweek(3/16~3/20) 기간 내에 있는 것은 **정상적 포함관계**이므로, 제목이 다르면 중복이 아님. **제목이 유사한데 기간만 분할된 경우**만 불합격.

### 합격/불합격 기준
| 결과 | 기준 |
|------|------|
| **합격** | 동일(또는 실질 동일) 제목의 일정이 **단일 카드로 통합**되어 있고, 기간 분할로 인한 분리 카드가 없음. 겹치는 기간의 카드는 **서로 다른 이벤트**로 명확히 구분됨 |
| **불합격** | 실질적으로 동일한 이벤트가 날짜 구간만 다른 **2개 이상의 카드**로 분리 노출되어 있거나, 동일 제목의 카드가 `data-start`/`data-end`만 다르게 중복 존재함 |

---

## 점검 결과 요약표

| # | 점검 항목 | 결과 | 비고 |
|---|-----------|------|------|
| 1 | 데이터 소스 레벨 중복 | ☐ 합격 / ☐ 불합격 | |
| 2 | 카테고리 분류 중복 | ☐ 합격 / ☐ 불합격 | |
| 3 | 뷰/필터 간 중복 | ☐ 합격 / ☐ 불합격 | |
| 4 | DOM 렌더링 중복 | ☐ 합격 / ☐ 불합격 | |
| 5 | 날짜 경계/반복 일정 중복 | ☐ 합격 / ☐ 불합격 | |

> 점검자: _________  점검일: _________  
> 불합격 항목에 대해서는 원인 분석 후 수정 이력을 기록할 것.
