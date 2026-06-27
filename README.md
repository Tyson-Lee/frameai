# FrameAI

> **내 일은 AI가, AI 일은 AI가.** 자동화를 자동화하는 AI 빌드 파이프라인.

사용자가 반복 업무를 자연어로 한 문단 설명하면, AI 에이전트 팀이 기획 →
설계 → 구현 → 테스트 → 배포 → 사용 가이드까지 자율 수행해 바로 쓸 수
있는 자동화를 만들어 냅니다. 결과는 `automations/<slug>/` 폴더에
자가 완결된 형태로 쌓이고, Git처럼 공유 · 버전 관리 · 리뷰가 가능합니다.

## Quickstart

```bash
# 1. 새 자동화 추가 (자연어 한 문단이면 끝)
./frame add "매주 월요일 아침에 GitHub 저장소의 지난주 PR과 이슈를
요약해서 Slack #engineering 채널에 한 줄씩 보내고 싶다."

# 2. 빌드 중 진행 상황 보기
./frame list

# 3. 빌드 끝나면 실행
./frame run weekly-status-report

# 4. 팀에 공유 (커밋 + push)
./frame share weekly-status-report
git push
```

`frame add` 는 Claude Code 를 헤드리스 모드 (`claude --print`) 로 호출해
**사용자 추가 입력 없이** 전체 파이프라인을 자율 수행합니다. 사용자 개입은
처음 한 문단과 (필요 시) 의사결정 confirm 몇 번 뿐입니다.

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
   automations/<slug>/
   ├── input.md         ← 사용자가 처음 적은 자연어
   ├── generated/       ← AI가 만든 코드·스크립트·문서
   ├── run.sh           ← 사용법 한 줄
   └── before_after.md  ← 시간 절감 증거
```

각 단계 안에서 36개 전문 에이전트 (architect, developer, reviewer,
diagnostician 등) 가 git worktree 로 격리된 채 병렬 작업하고, 단계별
체크포인트가 검증된 후에만 다음 단계로 넘어갑니다. 검토는 별도 컨텍스트의
auditor 에이전트가 refute-first 프롬프트로 수행해 셀프-체크의 사이코펀시
(sycophancy) 문제를 피합니다.

## Repo 구조

```
frameai/
├── README.md              ← 이 파일
├── CONCEPT.md             ← Git-like 공유 비전 (디테일)
├── CLAUDE.md              ← AI 어시스턴트용 프로젝트 컨텍스트
├── frame                  ← CLI 진입점 (한 파일 Python)
│
├── automations/           ← ★ 빌드된 자동화 라이브러리
│   └── (사용자가 frame add 로 추가)
│
├── agents/                ← 36 전문 에이전트 (.md 프롬프트)
├── skills/                ← 9 파이프라인 단계 (prd / kickoff / sprint ...)
├── scripts/               ← 21 헬퍼 (synthesizer, validator, hook 등)
├── project/.claude/       ← Claude Code 훅 + 설정 스니펫
├── templates/             ← PRD / 요구사항 / 아키텍처 등 결과물 템플릿
├── docs/                  ← CC 지원 매트릭스, 캐싱 노트 등
└── tests/                 ← 회귀 가드 (lint + delegation guard + 통합)
```

## 평가 기준 매핑

| 평가 항목 | FrameAI 가 어떻게 응답하는가 |
|---|---|
| **영향력 (30점)** | `automations/<slug>/before_after.md` 가 사용자가 직접 했을 때 vs 자동화 후의 시간/비용을 명시. 시연 자동화의 실측 수치로 응답 |
| **자율성 (25점)** | `frame add` 한 줄 입력 → 헤드리스 Claude Code 가 36 에이전트를 통해 전체 빌드. sprint_state.md / STATUS.md 로 진행 가시화 |
| **기술 완성도 (20점)** | 36 에이전트 · 9 스킬 · 21 스크립트 + 200+ 회귀 테스트. 모든 차단 의사결정은 별도 컨텍스트 auditor 의 refute-first 검증을 거침 |
| **사용자 경험 (15점)** | `frame list`/`frame run`/`frame share` 만으로 라이브러리 관리. 진행 중 실시간 STATUS.md + 단계별 체크포인트 |
| **확장성 (10점)** | `automations/` 폴더 자체가 답 — 새 자동화 = 새 폴더, 다른 팀이 PR 로 자기 자동화 기여 가능 |

## 비전: Git-like 자동화 라이브러리

상세는 [CONCEPT.md](CONCEPT.md) 참고. 요약:

- 한 사람이 만든 자동화가 `git push` 한 번으로 팀의 자산이 됩니다
- 다른 사람은 `git pull` + `frame run <name>` 으로 즉시 활용
- 자동화가 깨지면 `frame add --refine <name> "<수정 지시>"` 로 AI 가 개선판을 PR
- 조직 차원에서는 사내 FrameAI 서버에 모든 자동화가 쌓이고, 그 자체가 그 조직의 **업무 자산 인덱스** 가 됩니다

## 빌드 방식 및 활용 AI 툴

- **모델**: Anthropic Claude (Opus 4.7 / Sonnet 4.6) + 자동 폴백
  (`fallbackModel: ["claude-sonnet-4-6", "claude-haiku-4-5"]`)
- **런타임**: Claude Code v2.1.145+ (자체 검증된 지원 매트릭스는
  [`docs/cc_feature_matrix.md`](docs/cc_feature_matrix.md) 참고)
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

## 라이선스

MIT. 자세한 내용은 [LICENSE](LICENSE) 참고.

## 크레딧

FrameAI 는 저자의 오픈소스 프로젝트 `claude-dev-kit` 에서 검증된
파이프라인 (PRD → 킥오프 → 스프린트 → 리뷰 → 십) 위에 컨테스트 컨텍스트로
재포지셔닝되었습니다. Claude Code 의 플러그인 시스템 · 훅 이벤트 · 캐싱
정책 등 런타임 캐퍼빌리티를 적극 활용합니다.
