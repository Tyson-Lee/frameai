# FrameAI

> **내 일은 AI가, AI 일은 AI가.** 자동화를 자동화하는 AI 빌드 파이프라인.

사용자가 반복 업무를 자연어로 한 문단 설명하면, AI 에이전트 팀이 기획 →
설계 → 구현 → 테스트 → 배포 → 사용 가이드까지 자율 수행해 **재사용
가능한 Claude Code 스킬**을 만들어 냅니다. 만들어진 스킬은 누구나
`frame run <이름>` 또는 Claude Code 안에서 `/이름` 으로 호출 가능하고,
파일·이미지·텍스트 어떤 입력이든 받아 결과 파일을 그 회의 `runs/<시각>/`
폴더에 영구 보관합니다.

## 두 가지 사용 흐름

| 사용자 | 어떻게 호출 | 언제 |
|---|---|---|
| **현장 엔지니어** | Claude Code 채팅창에 파일 드래그 + 자연어 (또는 `/<스킬명>`) | 일상 사용 |
| **자동화 작성자 (1인)** | `frame add` CLI 한 줄 | 새 자동화 만들 때 |
| **CI / cron / 배치** | `frame run --in ...` CLI | 스케줄링 / 외부 시스템 연동 |

같은 자동화를 두 UX 모두로 호출할 수 있습니다 — 내부적으로 같은 `SKILL.md` 를 호출하기 때문입니다.

### 현장 엔지니어 (CLI 안 침)

1. **frame 폴더에서 `claude` 실행** (Claude Code 앱이 자동으로 frameai 의 `.claude/` 발견)
2. 화면에 spec.pdf / defect.png 등을 **드래그**
3. 채팅창에 자연어로: *"이 변경 사항으로 ECN 작성해 줘"* (또는 `/ecn-writer M1 CD 22→18nm`)
4. 결과 파일이 인라인 표시 + `automations/ecn-writer/runs/<시각>/outputs/` 에 자동 저장

### 자동화 작성자 (CLI Quickstart)

```bash
# 1. 새 자동화 만들기 (자연어 한 문단)
./frame add "엔지니어가 공정 변경을 한 문장으로 적으면 ECN 양식 +
한국어/영어 통지문 draft 를 만들어 줘."

# 2. 매 회 사용 (반복) — 파일 + 이미지 + 텍스트 입력
./frame run ecn-writer --in spec.pdf "M1 line CD 22nm → 18nm"
./frame run fa-report --image defect-sem.png --in measurements.csv \
                       "Lot 24Q2-8821 신뢰성 시험 8D 양식"

# 3. 결과 확인 — runs/<timestamp>/outputs/ 안에 파일 자동 저장
./frame list                # 자동화별 상태 + 실행 회수
ls automations/ecn-writer/runs/

# 4. 개선 (스킬 진화)
./frame refine ecn-writer "통지문에 JEDEC 표준 인용 추가해 줘"

# 5. 팀 공유 (Git)
./frame share ecn-writer
git push
# 동료: git pull → 즉시 /ecn-writer 사용 가능
```

### Claude Code 가 스킬을 어떻게 찾는가

frameai repo 안의 `.claude/` 디렉토리가 Claude Code 의 표준 발견 경로입니다.

```
frameai/.claude/
├── skills/     → ../skills    (심볼릭 링크)
├── agents/    → ../agents     (심볼릭 링크)
├── hooks/     → ../project/.claude/hooks
└── settings.json              (fallbackModel + 훅 wiring 포함)
```

이 구조 덕분에:
- `cd frameai && claude` 하면 즉시 10개 vendored skill (`/sprint`, `/prd` 등)
  과 13개 런타임 built-in (`/code-review`, `/deep-research` 등) 모두 노출
- 새로 빌드된 `skills/<slug>/` 도 자동 발견 (별도 install / register 불필요)
- 별도 "프로젝트 등록" 작업 없음 — Claude Code 앱은 폴더 자체를 프로젝트로
  인식. cmux/Desktop 앱은 Recent Projects 사이드바에서 한 번 열면 등록

`frame add` 와 `frame run` 둘 다 Claude Code 를 헤드리스 (`claude --print`)
로 호출합니다. **사용자 추가 입력 없이** 전체 빌드/실행이 진행되고, 진행
상황은 stdout 으로 흘러나옵니다.

## 파일 · 이미지 · 멀티모달 입력

자동화가 받는 입력은 텍스트만이 아닙니다. **Claude Code 의 Read tool 이
PDF · PNG · JPG · 노트북을 네이티브 멀티모달로 처리**하므로, FrameAI 는
별도 OCR 이나 파싱 레이어 없이 파일을 그대로 전달합니다:

| 입력 종류 | CLI 옵션 | 처리 방식 |
|---|---|---|
| 텍스트 (인자) | `frame run <name> "<text>"` | `$FRAMEAI_RUN_TEXT` 로 전달 |
| 파일 (CSV/JSON/MD/PDF) | `--in PATH` (반복 가능) | `runs/<ts>/inputs/` 로 복사 → Read |
| 이미지 (PNG/JPG) | `--image PATH` (반복 가능) | 동일 위치 + 멀티모달 Read |

**예시**:
```bash
# 회의록 자동 정리: .vtt 자막 + 슬라이드 스샷 동시 입력
./frame run meeting-digest --in zoom-transcript.vtt \
                            --image slide-12.png \
                            "이번 주 글로벌 reliability 미팅"

# 고객 응대: 이메일 본문 + 첨부 PDF 함께 분류
./frame run customer-reply --in inquiry.eml --in datasheet.pdf \
                            "고객 등급 platinum"
```

## 출력은 어디로

스킬은 그 회의 실행에서만 **`$FRAMEAI_RUN_OUTPUTS`** (한 폴더) 에만 파일을
씁니다. 그 밖으로 쓰는 것은 SKILL.md 의 도구 정책으로 차단:

```
automations/ecn-writer/runs/2026-06-27T14-22-08/
├── inputs/                    ← 호출 시 --in / --image 로 받은 원본 사본
│   ├── spec.pdf
│   └── defect.png
├── outputs/                   ← 스킬이 작성한 결과물
│   ├── ecn-form.md
│   ├── notification-kr.md
│   ├── notification-en.md
│   └── attached-table.xlsx
├── prompt.txt                 ← 이 회의 정확한 디스패치 프롬프트
└── log.txt                    ← claude --print 표준 출력
```

이 구조 덕분에 **모든 실행이 감사 가능**합니다 — 입력·프롬프트·출력·로그가
한 디렉토리에 묶여 git 으로 영구 보관됩니다.

비-텍스트 출력 (xlsx, pptx, png 등) 은 스킬이 빌드 단계에서 `openpyxl`,
`python-pptx`, `matplotlib` 등 표준 라이브러리를 호출하는 헬퍼를
`skills/<slug>/helpers/` 에 자동 생성합니다.

## 어떻게 작동하는가

```
사용자 자연어 한 문단
       │
       ▼
   /prd  ──►  /kickoff  ──►  /sprint  ──►  /ship
   (PRD)      (계획·아키텍처·   (이슈별 병렬     (커밋
              이슈·테스트플랜)   구현 + 검토 +    + 통합)
                                테스트 + 문서)
       │
       ▼
   skills/<slug>/SKILL.md     ← 재사용 가능한 슬래시 명령
   skills/<slug>/helpers/     ← 결정적 헬퍼 (PDF 파서, 양식 변환 등)
   automations/<slug>/README  ← 사용 가이드
   automations/<slug>/runs/   ← 매 호출 archive
```

각 단계 안에서 36개 전문 에이전트가 git worktree 로 격리된 채 병렬
작업하고, 단계별 체크포인트가 검증된 후에만 다음 단계로 넘어갑니다.
검토는 별도 컨텍스트의 auditor 에이전트가 refute-first 프롬프트로
수행해 셀프-체크의 사이코펀시 문제를 피합니다.

## Repo 구조

```
frameai/
├── README.md              ← 이 파일
├── CONCEPT.md             ← Git-like 공유 비전 (디테일)
├── CLAUDE.md              ← AI 어시스턴트용 프로젝트 컨텍스트
├── frame                  ← CLI 진입점 (한 파일 Python)
│
├── skills/                ← 슬래시 명령들 (kit의 10개 + frame add 가 추가)
├── agents/                ← 36 전문 에이전트
├── scripts/               ← 21 헬퍼 (synthesizer, validator, hook 등)
├── project/.claude/       ← Claude Code 훅 + 설정 스니펫
├── templates/             ← PRD / 요구사항 / 아키텍처 등 결과물 템플릿
├── docs/                  ← CC 지원 매트릭스, 캐싱 노트 등
├── tests/                 ← 회귀 가드 (lint + delegation guard + 통합)
│
└── automations/           ← ★ 빌드된 자동화 라이브러리
    └── <slug>/
        ├── input.md           ← 처음 자연어
        ├── README.md          ← 사용 가이드 (AI 생성)
        ├── before_after.md
        └── runs/<ts>/         ← 매 호출 archive
            ├── inputs/
            ├── outputs/
            ├── prompt.txt
            └── log.txt
```

## 평가 기준 매핑

| 평가 항목 | FrameAI 가 어떻게 응답하는가 |
|---|---|
| **영향력 (30점)** | `automations/<slug>/before_after.md` 시간 절감 + `runs/` 누적 사용량으로 *실측* 임팩트 입증 |
| **자율성 (25점)** | `frame add` 한 줄 입력 → 헤드리스 Claude Code 가 36 에이전트로 전체 빌드. 이후 `frame run` 마다 자연어 인자만 |
| **기술 완성도 (20점)** | 36 에이전트 · 10 스킬 · 21 스크립트 + 200+ 회귀 테스트. 모든 차단 의사결정은 별도 컨텍스트 auditor 의 refute-first 검증. **PDF · 이미지 멀티모달 입력 네이티브 지원** |
| **사용자 경험 (15점)** | `frame list` / `frame run` / `frame share` 3 명령. 진행 가시화 (STATUS.md, sprint_state.md). 매 호출은 입력·프롬프트·출력·로그가 한 폴더에 모임 |
| **확장성 (10점)** | 만들어진 자동화 = `SKILL.md` 한 파일 → git pull 한 번에 팀원 즉시 사용. `frame refine` 으로 AI 가 자동화 진화 |

## 비전: Git-like 자동화 라이브러리

상세는 [CONCEPT.md](CONCEPT.md) 참고. 요약:

- 한 사람이 만든 자동화가 `git push` 한 번으로 팀의 자산이 됩니다
- 다른 사람은 `git pull` + `frame run <name>` (또는 `/name` 슬래시 명령)
  으로 즉시 활용
- 자동화가 깨지면 `frame refine <name> "<수정 지시>"` 로 AI 가 진화시키고,
  변경 내역은 `automations/<name>/CHANGELOG.md` 에 누적
- 조직 차원에서는 사내 FrameAI 서버에 모든 자동화가 쌓이고, 그 자체가
  그 조직의 **업무 자산 인덱스** 가 됩니다

## 빌드 방식 및 활용 AI 툴

- **모델**: Anthropic Claude (Opus 4.7 / Sonnet 4.6) + 자동 폴백
  (`fallbackModel: ["claude-sonnet-4-6", "claude-haiku-4-5"]`)
- **런타임**: Claude Code v2.1.145+ (자체 검증된 지원 매트릭스는
  [`docs/cc_feature_matrix.md`](docs/cc_feature_matrix.md) 참고)
- **멀티모달**: Read tool 의 네이티브 PDF · 이미지 지원 (별도 OCR 불필요)
- **연동**: 런타임 `/code-review` · `/security-review` · `/deep-research`
  · `/verify` 직접 위임 (kit 재구현 대신 플랫폼 우선)
- **격리**: git worktree 기반 병렬 에이전트 작업, 공유 파일은 `flock` +
  `registry_edit` 으로 동시성 보호

## 한계와 정직한 면

- 빌드 결과의 **첫 회 검증은 자동**, 하지만 **최종 운영 책임은 사람** —
  자동화가 외부 API 토큰을 다루거나 데이터 변경을 수행할 때 사용자가
  최소 1회 dry-run + sign-off 를 권장
- AI 환각은 zero 가 아님 — 모든 검증된 주장에 verbatim 출처 인용 강제
  (`docs/cache_friendly_authoring.md`, `templates/research_claim.md`)
- Git-like 공유의 완전한 형태 (사내 마켓플레이스, 자동 PR 리뷰) 는 다음
  마일스톤. 현재는 단일 repo 의 폴더 기반 공유
- 매우 큰 PDF (수십 페이지+) 는 Read tool 의 `pages` 인자로 페이지 범위
  를 명시해야 안전

## 라이선스

MIT. 자세한 내용은 [LICENSE](LICENSE) 참고.

## 크레딧

FrameAI 는 저자의 오픈소스 프로젝트 `claude-dev-kit` 에서 검증된
파이프라인 (PRD → 킥오프 → 스프린트 → 리뷰 → 십) 위에 컨테스트 컨텍스트
로 재포지셔닝되었습니다. Claude Code 의 플러그인 시스템 · 훅 이벤트 ·
캐싱 정책 · 멀티모달 Read 등 런타임 캐퍼빌리티를 적극 활용합니다.
