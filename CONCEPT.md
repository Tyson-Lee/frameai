# FrameAI Concept

> 자동화를 자동화한다. 그리고 그 자동화는 팀의 자산이 된다.

## 풀려는 문제

조직에서 반복되는 작업은 두 종류로 분류됩니다.

1. **누가 봐도 자동화 가치가 있는 것** — 주간 리포트, 데이터 정합성 체크,
   사내 양식 작성 등. **자동화하지 않은 이유**는 보통 시간이 없거나, 만들
   사람이 없거나, 만들었어도 본인만 쓰다 사라지기 때문입니다.
2. **암묵적으로 모두가 하고 있는 것** — 미팅 노트 정리, 코드 리뷰 의견
   집계, 문서 검색. **자동화 가치를 인식하지 못해** 자동화되지 않습니다.

기존 노코드/RPA 툴들이 (1) 일부는 해결했지만, 여전히:

- **만드는 데 시간이 듭니다** — 자동화 만들기가 또 다른 업무가 됨
- **만들면 그 사람만 씁니다** — 조직에 축적되지 않음
- **유지보수 부담** — 외부 시스템이 바뀌면 깨짐, 다시 만들어야 함

## FrameAI 의 답

**3개 레이어**로 답합니다.

### 레이어 1: 자동화 생성을 자동화

사용자가 적는 것: **자연어 한 문단**.

> "매주 월요일 아침에 GitHub 저장소의 지난주 PR과 이슈를 요약해서
> Slack #engineering 채널에 한 줄씩 보내고 싶다."

FrameAI 가 하는 것:

1. PRD 작성 (목적, 사용자, 입력, 출력)
2. 요구사항 + 아키텍처 + 이슈 분해 (kickoff)
3. 이슈별 병렬 구현 + 단위 테스트 (sprint)
4. 통합 + 리뷰 + 사용 가이드 (ship)

결과는 `automations/<slug>/` 폴더 하나. 사용자 입력은 처음 한 문단 + (필요 시)
의사결정 확인 몇 번이 전부입니다.

### 레이어 2: 자동화의 공유는 Git

`automations/<slug>/` 폴더 자체가 Git 의 한 디렉토리이므로:

- `git push` 한 번에 팀 자산이 됨
- `git log automations/<slug>/` 로 누가 언제 만들었는지 추적
- `git diff` 로 자동화 수정 내역 리뷰
- 깨졌으면 `git revert` 또는 `frame add --refine <name> "<수정>"`

이게 FrameAI 의 핵심 차별화입니다. 기존 RPA 가 **각자의 데스크톱에 갇혀
있다면**, FrameAI 의 자동화는 **팀의 코드 저장소에 살아있는 자산**으로
존재합니다.

### 레이어 3: 자동화의 진화도 AI 가

자동화가 깨졌을 때 (외부 API 변경, 데이터 형식 변경) 일반 RPA 는 사람이
다시 만들어야 합니다. FrameAI 는:

```bash
frame add --refine weekly-status-report "Slack API 가 v2 로 바뀌어서
'channels.send' 가 'conversations.message.send' 로 변경됐어. 고쳐줘."
```

AI 가 `automations/<slug>/generated/` 의 코드를 분석해 변경을 적용하고,
회귀 테스트를 다시 돌리고, before_after.md 를 갱신합니다.

## 평가 기준에 대한 응답 (정직한 매핑)

### 영향력 (30점)

FrameAI 자체의 임팩트는 **자동화 만드는 비용을 0 에 가깝게 낮추는 것**
입니다. 그 임팩트의 증거는 **시연 자동화의 before_after.md** 에 명시된
실측 시간 절감 수치로 보입니다.

예: 사용자가 매주 수동으로 2시간 30분 들이던 `weekly-status-report` →
`frame run` 한 줄 + 5초.

### 자율성 (25점)

`frame add` 호출 후 사용자 개입은 평균 N회 이하 (시연 영상에 카운터
표시). 헤드리스 Claude Code 가 36 에이전트를 통해 전체 빌드 진행, 별도
컨텍스트 auditor 가 단계별 차단 검증.

비교 가능한 다른 시스템 (no-code 에이전트 빌더, AutoGPT 등) 은 보통
사용자 개입 10-30회 / 빌드. FrameAI 는 **선택지를 좁히고**, **차단
의사결정만 사람에게 묻습니다**.

### 기술적 완성도 (20점)

- 36 전문 에이전트 + 9 파이프라인 스킬 + 21 헬퍼 스크립트
- 200+ 회귀 테스트 (lint + 위임 가드 + 통합)
- **Platform-first 위임**: 런타임 `/code-review`, `/security-review`,
  `/deep-research`, `/verify` 를 직접 호출. 자체 재구현 (NIH) 대신 thin
  synthesis guard 만 책임
- **Graceful degrade**: 런타임 스킬이 미노출일 때 자체 폴백 (e.g.
  `scripts/has_skill.py` 의 3-state 프로빙)
- **Sycophancy 차단**: 모든 검증은 *separate context* 의 refute-first
  프롬프트로 수행 (synthesizer-auditor, review-merge-auditor)
- **격리**: git worktree + flock-protected registry_edit 으로 병렬
  에이전트의 동시 쓰기 안전

### 사용자 경험 (15점)

- 입력: 자연어 한 문단
- 진행 가시화: `sprint_state.md`, `STATUS.md` 실시간 갱신
- 단계별 게이트: 각 phase 끝에 mandatory checkpoint
- 라이브러리 뷰: `frame list` → 상태별 자동화 일람
- 공유: `frame share` → git commit 한 줄

### 확장성 (10점)

자동화 추가 = `frame add` 한 번. 도메인 무관 (개발, 영업, 운영, HR ...).
새 도메인 전용 에이전트 / 스킬이 필요하면 `agents/` 또는 `skills/` 폴더에
추가하면 즉시 통합 — kit 재빌드 불필요.

## 한계 (정직)

- **모델 비용**: 자동화 한 개 빌드에 $0.5 ~ $5 의 API 비용 (정도는 작업
  복잡도에 비례). 비용 추적은 `cc-statusline` 에 표시
- **첫 회 dry-run 권장**: 외부 시스템 변경을 수반하는 자동화는 사용자가
  처음 한 번 dry-run 으로 확인 후 적용
- **AI 환각 제로 아님**: 검증된 클레임에 verbatim 출처 인용 강제, 별도
  컨텍스트 auditor 가 paraphrase distortion 차단. 그러나 verbatim quote
  의 *해석 오류* 까지 잡지는 못함 — 관련: `docs/cache_friendly_authoring.md`,
  `templates/research_claim.md`
- **Git-like 공유의 완전한 형태**: 현재는 단일 repo 의 폴더. 사내
  마켓플레이스 + 자동 PR 리뷰 + 사용자 권한 모델은 다음 마일스톤

## 미래 비전

- **사내 FrameAI 서버**: 조직의 모든 자동화가 한 곳에 누적, 검색 가능
- **자동화 자체의 자동화 (메타)**: FrameAI 가 새 스킬·에이전트를 자기
  자신에게 추가 — 현재 실험적으로 작동
- **권한 모델**: 자동화별 실행 권한 (e.g. `weekly-report` 는 누구나,
  `database-write` 는 특정 그룹만)
- **벤치마크**: 같은 자연어 인풋에 다른 빌드 (다른 모델, 다른 프롬프트)
  를 만들어 자동 비교 — *자동화의 A/B 테스트*

## 한 줄

> 다른 팀이 *어떤 일* 을 자동화하는 도구를 만들 때, FrameAI 는 *그 도구를
> 만드는 도구* 입니다. 그리고 그 도구는 자기 자신을 만들었습니다.
