# weekly-memory-news

메모리 반도체 4사 (**Micron / SK Hynix / SanDisk / Kioxia**) 의 지난 7일
공개 뉴스를 웹 검색으로 모아 사내 공유용 **한국어 주간 보고서** 를 생성
하는 스킬입니다.

매주 월요일 아침 임원·전략 부서 공유용으로 쓸 수 있도록 다음 결과물을
한 번에 만듭니다:

1. `executive_summary.md` — 임원용 1 페이지 요약
2. `companies/<slug>.md` — 회사별 주요 발표 + 출처 URL + 원문 인용
3. `report.md` — 위 두 가지를 합친 단일 보고서
4. `audit.md` — 별도 컨텍스트 auditor 의 출처·인용 검증 결과

## 한 줄 사용법

### A. CLI 배치 (`frame run`)

```bash
# 기본 — 4 사 모두, 오늘 기준 지난 7 일
./frame run weekly-memory-news "이번 주 메모리 경쟁사 동향 정리해줘"

# watchlist 로 회사 set 을 바꾸고 싶을 때
./frame run weekly-memory-news \
  --in automations/weekly-memory-news/samples/sample-1.txt \
  "HBM 중심으로"
```

`--in` 으로 전달된 파일이 `runs/<UTC-ts>/inputs/` 에 복사되고, 결과는
`runs/<UTC-ts>/outputs/` 아래에 떨어집니다.

### B. Claude Code 채팅에서

```
/weekly-memory-news 이번 주 메모리 경쟁사 동향 정리
```

또는 자연어로:

```
메모리 4 사 지난 한 주 뉴스 한국어 보고서 만들어줘
```

라고 적으면 스킬이 직접 `automations/weekly-memory-news/runs/<UTC-ts>/`
아래에 archive 폴더를 만들고 같은 출력을 생성합니다.

## 매주 월요일 자동 실행

`/schedule` 또는 `/loop` 와 조합해 월요일 09:00 KST 에 자동 호출할 수
있습니다 (예시):

```
/schedule
```

cron: `0 0 * * 1` (UTC = 월요일 09:00 KST 근사) → prompt:
`./frame run weekly-memory-news "월요일 자동 실행"`.
세션 활성 / 권한 / 사용 비용은 사용자 책임입니다.

## 입력

| 종류 | 필수 | 비고 |
|---|---|---|
| 자유 텍스트 인자 | ⛔ | 강조 주제 / 톤 (선택) |
| `watchlist.txt` | ⛔ | 한 줄에 회사 한 개. 미제공 시 기본 4 사. |
| `focus.md` | ⛔ | 이번 주 집중 영역 (예: "HBM4 우선") |

`watchlist.txt` 에 기본 4 사 외 다른 회사를 적으면 그 회사도 동일한
포맷으로 보고서에 포함됩니다 (예: Samsung Memory, YMTC, CXMT). 단,
보고서의 기본 컨셉은 "메모리 반도체" 이므로 무관한 산업의 회사를 넣어도
스킬은 그대로 처리하되 결과 품질은 보장되지 않습니다.

## 출력 (`runs/<UTC-ts>/outputs/` 아래)

| 파일 | 내용 |
|---|---|
| `executive_summary.md` | 한 페이지 (≤ 35 줄). lede / 회사별 한 줄 / 주목 테마 / 다음 주 관전 포인트 |
| `companies/micron.md` | Micron 의 3-6 개 bullet, 각 bullet 은 출처 URL + 원문 인용 동반 |
| `companies/sk-hynix.md` | SK 하이닉스 동일 포맷 |
| `companies/sandisk.md` | SanDisk 동일 포맷 |
| `companies/kioxia.md` | Kioxia 동일 포맷 |
| `report.md` | 위 모든 것을 합친 단일 보고서 (helper 가 결정적으로 생성) |
| `audit.md` | 별도 컨텍스트 auditor 의 출처·인용 검증 verdict |
| `prepare.json` | window + watchlist 결정 trace (디버깅용) |

스킬은 완료 시 위 파일 경로 목록을 사용자에게 출력합니다. Claude Code
채팅 모드에서는 인라인 렌더링되고, CLI 모드에서는 `runs/<ts>/log.txt`
에도 남습니다.

## 샘플로 한 번에 검증

```bash
# 1) 기본 4 사 + 자유 텍스트
./frame run weekly-memory-news \
  --in automations/weekly-memory-news/samples/sample-1.txt \
  "기본 4 사 정리"

# 2) HBM 집중 보고서
./frame run weekly-memory-news \
  --in automations/weekly-memory-news/samples/sample-2.txt \
  "HBM 중심으로"
```

각 `runs/<ts>/outputs/` 에서 `report.md`, `executive_summary.md`,
`companies/*.md`, `audit.md` 가 모두 생성되는지 확인하세요. 출처 URL 이
실제로 열리는지 한두 개 spot-check 권장.

## Limits (정직)

- **공개 웹 한정**. 사내 시스템, 사내 인텔리전스 슬랙 채널, 유료 리서치
  (Gartner / Counterpoint / TrendForce 페이월) 는 다루지 않습니다.
- **검색 엔진 편향**. WebSearch 결과는 검색 엔진의 시점·지역·언어 편향을
  그대로 반영합니다. 한 주 동안 한국어 매체에서만 보도된 사건은 영어
  쿼리에서 빠질 수 있고 반대도 마찬가지 — 한·영 양쪽 쿼리를 fan-out
  하지만 완전성은 보장하지 않습니다.
- **No-source = no-claim**. 출처 URL 과 원문 인용을 동반하지 못하는
  주장은 보고서에서 제외됩니다. 빈약한 한 주는 그대로 빈약하게
  표시됩니다. "이번 주 공개된 메모리 관련 발표 없음" 이라는 한 줄이
  들어갈 수 있고, 그게 정상입니다.
- **번역은 의역 수준**. 한국어 본문은 원문 인용을 사실 추가 없이 한
  문장으로 요약한 것입니다. 인용은 항상 원문 언어 (영어 / 일본어 /
  한국어 등) 로 보존합니다.
- **시점은 UTC 기준**. KST 발행 기사라도 UTC 기준 지난 7 일 안이면
  포함됩니다 (~9 시간 격차 발생 가능).
- **competitive intelligence 한정**. 가격 예측, 투자 판단, 기술 평가는
  하지 않습니다. 발표 사실의 압축 요약만 제공합니다.
- **페이월 미돌파**. 페이월 또는 cookie wall 페이지는 WebFetch 가
  내용을 읽지 못하므로 자동 제외됩니다 (그 결과 헤드라인만 강한 한
  주는 본문이 빈약할 수 있음).
- **자동 발송 없음**. 결과는 작업 트리에만 기록됩니다. Slack /
  이메일 배포는 사용자가 수동으로 진행하세요.

## 디렉토리 구조

```
automations/weekly-memory-news/
├── input.md            # 사용자가 처음 적은 자연어 (수정 금지)
├── README.md           # 이 파일
├── before_after.md     # 수동 vs 자동 시간 비교
├── samples/
│   ├── sample-1.txt    # 기본 4 사 watchlist
│   └── sample-2.txt    # HBM 집중 focus brief
└── runs/<UTC-ts>/      # frame run / 채팅 호출마다 1 개씩 생성
    ├── inputs/
    └── outputs/
        ├── report.md
        ├── executive_summary.md
        ├── companies/
        │   ├── micron.md
        │   ├── sk-hynix.md
        │   ├── sandisk.md
        │   └── kioxia.md
        ├── audit.md
        └── prepare.json
```
