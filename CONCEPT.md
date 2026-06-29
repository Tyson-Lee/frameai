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
- **단일 작성자 가정**: 현재 구현은 한 명이 자동화를 추가/수정하는
  시나리오에 맞춰져 있음. 다중 작성자 환경에서 필요한 거버넌스
  (OWNERS, PR 자동 리뷰, 충돌 처리) 는 [Future Works](#future-works) 참고
- **데이터 라우팅**: 기본 Anthropic 미국 인프라 호출. 사내 사용 시 AWS
  Bedrock 서울 리전 등으로 라우팅 필수 — 상세는 [docs/security.md](docs/security.md)

## Future Works

FrameAI 가 단일 작성자 → 팀 → 조직 라이브러리로 진화하기 위한 마일스톤.

### 마일스톤 1 — 다중 작성자 가버넌스 (3-6 개월)

현재 가정인 "자동화 작성자 1인" 을 N 인으로 확장:

- **`skills/<slug>/OWNERS`** 파일 — 자동화별 책임자 명단
- **PR 자동 리뷰** — 새 스킬 / 스킬 수정 commit 은 자동 `/code-review` +
  `/security-review` + `/audit-egress` 트리거 후 머지
- **세맨틱 버저닝** — 같은 슬러그의 두 버전 공존 (`/ecn-writer@v1`,
  `/ecn-writer@v2`) 으로 breaking change 흡수
- **충돌 해결** — 두 작성자가 같은 슬러그로 commit 시도 시 자동 감지 +
  병합 또는 분기 가이드
- **변경 알림** — 자동화를 자주 쓰는 사용자에게 그 자동화 변경 시 알림

### 마일스톤 2 — 보안 강화 (3-6 개월, 마일스톤 1 과 병행)

- **자동 PII 마스킹** — 입력 파일에서 주민번호/이메일/lot ID 자동 감지 +
  대체. `automations/<slug>/SECURITY.md` 에 마스킹 규칙 선언
- **네트워크 egress 매니페스트** — 스킬이 호출하는 모든 외부 도메인 명시
  + 사내 보안팀 승인 도메인만 통과
- **데이터 분류 게이트** — 입력 파일의 분류 라벨 (Public/Internal/
  Confidential) 자동 감지 + Confidential 은 Bedrock 라우팅 강제
- **승인 워크플로** — 이메일 발송, DB 쓰기 같은 민감 액션은 두 단계
  실행 (dry-run → 사람 검토 → 실제 실행)
- **모델 응답 PII 필터** — 출력에 PII 가 포함되면 자동 마스킹 + 로그

### 마일스톤 3 — 사내 마켓플레이스 + 네이티브 설치 (6-12 개월)

- **사내 FrameAI 서버** — 조직의 모든 자동화가 한 곳에 누적, 검색 가능,
  사용량 통계
- **per-skill 권한** — 부서별/직급별 실행 권한 (e.g. `salary-report` 는
  HR 그룹만)
- **벤치마크 / A-B 테스트** — 같은 자연어 인풋에 다른 빌드 (다른 모델,
  다른 프롬프트) 를 만들어 자동 비교
- **자동화 자체의 자동화 (메타)** — FrameAI 가 새 스킬·에이전트를 자기
  자신에게 추가 (현재 실험적으로 작동)
- **사용 통계 대시보드** — 어떤 자동화가 얼마나 쓰이는지 → 폐기 판단 +
  투자 우선순위
- **Claude Code 네이티브 plugin 마이그레이션** — 현재 `install.sh` +
  `git clone` 으로 배포되는 구조를 `/plugin install frameai` 한 명령으로
  대체. 매트릭스 P3-P5 가 확인하듯 plugin subagent 는 `hooks:`,
  `mcpServers:`, `permissionMode:` 사용 불가 → 기존 훅을 `hooks/hooks.json`
  으로 마이그레이션 + 스킬 namespace 처리 필요. 마쳐지면 진정한 "터미널
  0회 + git 0회" 설치 가능
- **GUI 설치 패키지** — macOS `.pkg` / Windows `.msi` 로 클릭 한 번 설치.
  코드사인 + 사내 배포 채널 (예: 사내 소프트웨어 카탈로그) 필요
- **학습 데이터 도달 — *"FrameAI 설치해줘"* 한 마디 매직** — Anthropic
  의 모델이 FrameAI 를 알게 되는 시점이 오면 (오픈소스 채택 + 공개
  레퍼런스 누적 후 수개월-연 단위) 사용자가 install URL 을 paste 할
  필요 없이 자연어 한 마디로 설치 가능. 현재는 사내 공지 한 줄을
  복사-paste 하는 운영 방식이 가장 현실적

### 마일스톤 4 — 멀티 클라이언트 (MCP 서버화, 6-12 개월)

현재 FrameAI 는 Claude Code 의 skills / agents / hooks / 헤드리스 모드
위에서 동작합니다. 사용자가 다른 AI 클라이언트 (ChatGPT 데스크톱,
Cursor, Continue, Cline 등) 를 선호해도 같은 자동화 라이브러리에
접근할 수 있도록 **Model Context Protocol (MCP) 서버** 로 재배치.

- **MCP 서버화** — FrameAI 의 스킬·에이전트·훅 시스템을 MCP 의 tool /
  resource / prompt 인터페이스로 매핑. 한 번 만든 자동화가:
    - Claude Code (현재 — 그대로 작동)
    - ChatGPT 데스크톱 (MCP 클라이언트 모드)
    - Cursor / Continue / Cline 등 MCP 호환 IDE
  모두에서 같은 슬래시 명령 또는 자연어 호출로 작동
- **작업 규모**: 기존 SKILL.md 의 dual-mode 계약을 MCP `tools/list` +
  `tools/call` 인터페이스로 매핑, 훅을 MCP 미들웨어로 이전, settings
  시스템 추상화. 1-2 개월 작업으로 추정
- **사내 측면 효과**: 엔지니어가 선호하는 IDE / 채팅 도구와 무관하게
  같은 자동화 라이브러리 공유 가능 → **AI 도구 종속성 해소**. 부서별/
  개인별 도구 선호 차이를 라이브러리 통일성과 양립
- **데이터 라우팅 트레이드오프 유지**: ChatGPT 데스크톱 사용 시
  OpenAI 인프라로 데이터 흐름. Samsung 사내 Confidential 데이터는
  여전히 Claude + Bedrock 서울 라우팅 권장. MCP 호환이 *어디서 호출
  가능한지* 를 확장하는 것이지 *데이터 안전성을 보장하는 게* 아님 —
  사용자/팀 단위 선택의 문제

## 한 줄

> 다른 팀이 *어떤 일* 을 자동화하는 도구를 만들 때, FrameAI 는 *그 도구를
> 만드는 도구* 입니다. 그리고 그 도구는 자기 자신을 만들었습니다.
