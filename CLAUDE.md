# CLAUDE.md — FrameAI Project Context

> 이 파일은 Claude Code 가 이 저장소에서 작업할 때 자동으로 읽는
> 프로젝트 컨텍스트입니다. FrameAI 의 의도, 구조, 작업 규약을 한 곳에
> 모아둡니다.

## 무엇

FrameAI 는 사용자가 자연어로 설명한 반복 업무를 AI 가 자율 수행해 만드는
**자동화 빌드 파이프라인** 입니다.

자세한 컨셉은 [`CONCEPT.md`](CONCEPT.md), 사용자 가이드는
[`README.md`](README.md) 에 있습니다. 이 파일은 그 위에서 **작업 규약**
만 다룹니다.

## 진입점

사용자는 `./frame` CLI 로 시작합니다.

```bash
./frame add "<자연어 한 문단>"   # 새 자동화
./frame list                    # 라이브러리 뷰
./frame run <slug>              # 실행
./frame share <slug>            # git commit
```

`frame add` 는 내부적으로 헤드리스 `claude --print` 를 호출하고, 그
프롬프트는 `/prd → /kickoff → /sprint → /ship` 파이프라인을 자율 수행
하도록 지시합니다. AI 어시스턴트인 당신이 직접 호출되는 경우, 위 파이프
라인을 사용자 개입 없이 끝까지 진행하는 것이 기본 동작입니다.

## 산출물 위치

```
automations/<slug>/
├── input.md         ← 사용자가 처음 적은 자연어 (수정 금지)
├── generated/       ← 코드·스크립트·문서가 들어가는 곳
├── run.sh           ← 사용자가 자동화를 호출하는 한 줄
└── before_after.md  ← 시간 절감 증거 (수동 vs 자동)
```

각 폴더 안의 `input.md` 와 `before_after.md` 는 **항상 작성**합니다.
없으면 시연 자료로 못 쓰입니다.

## 작업 규약

- **Platform-first**: 런타임이 더 잘하는 기능 (`/code-review`,
  `/security-review`, `/deep-research`, `/verify`) 은 직접 위임.
  `scripts/has_skill.py` 로 노출 여부 프로브 후 primary/degraded 분기.
- **별도 컨텍스트 auditor**: 모든 핵심 검증 단계는 separate Task
  invocation 으로 refute-first 프롬프트 실행. 셀프-체크 단독 의존 금지.
- **격리**: 병렬 에이전트는 git worktree 로 분리, 공유 파일 (`issues.md`,
  `STATUS.md`, `sprint_state.md`) 은 `bash scripts/registry_edit.sh` 로만
  쓰기.
- **No-source = no-claim**: 자동화 빌드 중 정량적 클레임이 필요하면
  반드시 출처 (URL + verbatim quote + accessed_at) 를 동반.
- **Honest framing**: 자동화가 무엇을 보장하고 무엇을 보장하지 않는지
  `automations/<slug>/README.md` 의 Limits 섹션에 명시.

## 모델 + 캐싱

- 기본 모델: 에이전트 frontmatter 의 `model:` (대부분 opus / sonnet)
- 폴백: `project/.claude/settings.snippet.json` 의 `fallbackModel`
- 에이전트 효성 (`effort:`) 은 작업 종류별로 미리 분류
  (xhigh / high / medium / low — `docs/cc_feature_matrix.md` 참고)
- 캐싱: `docs/cache_friendly_authoring.md` 의 stable-first / digest 패턴
  유지. 새 SDK 호출 스크립트가 등장하면 `cache_control` 적용 필수

## 테스트

```bash
python3 -m pytest -q
python3 scripts/lint_skill_cache_order.py
python3 scripts/gen_skills.py --dry-run
```

새 스킬 템플릿을 추가하면 `gen_skills.py` 로 `SKILL.md` 를 재생성하고,
모든 회귀 가드가 통과하는지 확인합니다.

## Git 워크플로

- 메인 브랜치: `main`
- 자동화 추가 commit 메시지 컨벤션:
  `feat(automations): add <slug>` (frame share 가 자동 생성)
- 코드 수정: Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:`,
  `refactor:`, `test:`, `ci:`)
- 시크릿 / API 키 / 토큰: **절대 커밋 금지** (PreToolUse 의
  `secret_guard.py` 훅이 차단)

## 환경 가정

- macOS / Linux
- Python 3.11+
- `claude` CLI (Claude Code v2.1.145+)
- `gh` CLI (GitHub 통합 시)
- `git`

## 한국어 / 영어

- 사용자 대면 문서 (README, CONCEPT, automations/<slug>/README) 는
  **한국어** 우선, 필요 시 영어 병기
- 내부 코드 / 테스트 / 커밋 메시지는 **영어** 표준
- AI 어시스턴트는 사용자가 한국어로 말하면 한국어로, 영어로 말하면 영어로
  응답

## 이 파일을 갱신할 때

- 사용자 대면 변화 → README.md 도 함께 갱신
- 비전 / 한계 변화 → CONCEPT.md 도 함께 갱신
- 개발 규약 변화만 → CLAUDE.md 만 갱신
