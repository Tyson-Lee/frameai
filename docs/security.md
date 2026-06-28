# FrameAI 사내 보안 가이드

> 사내 (특히 반도체/메모리 사업부 같은 보안 민감 환경) 에서 FrameAI 를
> 배포·운영할 때 알아야 하는 것들. 무엇이 이미 보호되고 있고, 무엇이
> 아직 보호되지 않으며, 어떤 운영 정책을 권장하는가를 정직하게 정리.

## 한 줄 요약

**FrameAI 는 Claude (Anthropic) API 를 호출한다 — 데이터가 외부 인프라로
전송된다.** 사내 데이터 분류상 외부 전송이 허용되는 데이터에 한해 사용
하고, 민감도 높은 데이터는 AWS Bedrock 서울 리전 라우팅 또는 마스킹 후
호출하라.

## 1. 이미 작동 중인 보호 장치

다음은 git clone + `./setup.sh` 만으로 즉시 활성화되는 보호 장치들.

| 장치 | 위치 | 효과 |
|---|---|---|
| `secret_guard` 훅 | `project/.claude/hooks/secret_guard.py` | PreToolUse 단계에서 `*.env`, `*.pem`, API 키 패턴 (sk-, ghp_, AKIA…) 의 Write/Edit 차단 |
| `dangerous_command_guard` 훅 | `project/.claude/hooks/dangerous_command_guard.py` | `rm -rf`, `dd if=`, `mkfs.*` 등 파괴적 명령 차단 |
| 매 실행 감사 archive | `automations/<slug>/runs/<ts>/` | 입력·프롬프트·출력·로그 4종 모두 영구 보관 (git 으로 추적) |
| `validate_research_claim` | `scripts/validate_research_claim.py` | 출처 없는 정량 클레임 자동 거부 (`no-source = no-claim` 규칙) |
| `flock` + `registry_edit` | `scripts/flock_edit.sh`, `scripts/registry_edit.sh` | 공유 파일 (issues.md, STATUS.md) 동시 쓰기 race 방지 |
| `separate-context auditor` | `agents/synthesizer-auditor.md`, `agents/review-merge-auditor.md`, `agents/research-auditor.md` | refute-first 프롬프트로 별도 컨텍스트에서 검증 → 셀프-체크 sycophancy 차단 |

## 2. 가장 중요한 트레이드오프 — 데이터 라우팅

### 기본 동작
`claude` CLI 는 기본적으로 **Anthropic 의 미국 인프라** 로 API 호출을
보냅니다. 따라서:
- 입력 파일 (PDF, 이미지, CSV) 의 전체 또는 일부가 미국으로 전송됨
- 프롬프트·시스템 메시지·도구 결과 모두 동일하게 전송
- Anthropic 의 데이터 보관 정책 적용 (영업비밀 / 한국 내 데이터 잔류
  의무 충족 여부는 별도 검토 필요)

### 사내 데이터 분류상 외부 금지 데이터

다음 데이터는 **Anthropic 미국 인프라로 전송 금지** 가 일반적:
- 공정 레시피·마스크 데이터·미발표 디바이스 스펙
- 고객사 (NVIDIA, Apple 등) 의 NDA 보호 자료
- 직원·고객 PII (주민번호, 이메일, 연락처 등)
- "Confidential" 또는 그 이상 라벨이 붙은 모든 문서

### 옵션 A — AWS Bedrock 서울 리전 라우팅 (권장)

Anthropic 모델은 AWS Bedrock 에서도 호스팅되며, **서울 리전 (`ap-northeast-2`)
에서 한국 내 데이터 잔류** 가 가능합니다. 호출 경로 변경:

```bash
# .env 또는 직접 export
export CLAUDE_CODE_USE_BEDROCK=1
export AWS_REGION=ap-northeast-2
export AWS_PROFILE=<사내-bedrock-프로필>
```

이후 모든 `claude` / `frame run` 호출이 서울 리전 Bedrock 으로 라우팅.
설정 검증:
```bash
claude --print "Which region am I running in?"
# 사내 Bedrock 셋업이 완료되었으면 ap-northeast-2 응답
```

대안: `CLAUDE_CODE_USE_VERTEX=1` + Google Vertex AI 한국 (`asia-northeast3`).
사내 Vertex 사용 시.

### 옵션 B — 마스킹 후 외부 API 호출

Bedrock 셋업이 어렵거나 일시적으로 외부 API 사용 시 PII / 식별자 마스킹.
**현재 frameai 는 마스킹 레이어 미구현** — 사내 자체 마스킹 도구 (DLP)
의 출력만 frame 에 입력하는 운영 정책으로 보완.

권장 마스킹 항목:
- Lot ID, Wafer ID → `LOT-XXXX` / `W-XXXX` 로 일관 대체
- 직원 ID, 이름 → 가명
- 고객사명 → `Customer A/B/C`
- 비공개 공정 노드 (`5nm`, `3nm`) → 일반화 (`AdvancedNode`)

마스킹 자동화는 미래 작업 (Future Works 참고).

## 3. 아직 없는 보호 장치 (정직히)

| 미흡 항목 | 영향 | 임시 해결책 | 권장 일정 |
|---|---|---|---|
| **자동 PII 마스킹** | 사용자가 실수로 PII 포함 데이터 입력 가능 | 사내 DLP 사전 통과 의무화 | 다음 마일스톤 |
| **네트워크 egress 선언** | 스킬이 어떤 외부 서비스에 접속하는지 불투명 | 스킬 추가 시 PR 리뷰 + 보안팀 review | 다음 마일스톤 |
| **승인 워크플로** | 이메일 발송, DB 쓰기 같은 민감 액션도 사용자 확인만 받음 | `automations/<slug>/README.md` 에 "민감 액션 dry-run 필수" 명시 | 마일스톤 2 |
| **데이터 분류 게이트** | "Confidential" 라벨 자동 감지 + 외부 API 차단 없음 | 사내 보안 정책 + 사용자 자기 검열 | 마일스톤 2 |
| **per-skill 권한** | 누구나 어떤 스킬도 실행 가능 | git 브랜치 보호 + commit 권한으로 간접 통제 | 마일스톤 3 |
| **모델 응답 PII 필터** | LLM 이 응답에 PII 를 그대로 echo 할 가능성 | 출력 review 사람이 매번 확인 | 마일스톤 3 |

## 4. 사내 배포 시 권장 운영 정책

### 사용 전 1회 — IT/보안팀
- [ ] Bedrock 서울 리전 (또는 Vertex 한국) 계정 셋업
- [ ] `CLAUDE_CODE_USE_BEDROCK=1` + `AWS_REGION=ap-northeast-2` 사내
      환경변수 표준화
- [ ] `secret_guard` 훅이 사내 시크릿 패턴 (사내 토큰 prefix 등) 도
      차단하도록 패턴 추가
- [ ] 사내 git 호스팅 (예: 사내 GitHub Enterprise / GitLab) 에 frameai
      미러
- [ ] 자동화별 OWNERS (책임자) 명단 운영

### 자동화 작성자 가이드 (skills/<slug>/ 추가 시)
- [ ] 입력 데이터 분류 레이블 명시 (Public / Internal / Confidential)
- [ ] 외부 서비스 호출 시 `automations/<slug>/README.md` 의 "Network
      egress" 섹션에 모든 도메인 나열
- [ ] 민감 액션 (메일 발송, 결재 시스템 호출 등) 은 *dry-run 우선* 패턴
      강제: 출력만 생성 후 사람이 확인 → 별도 `--send` 플래그로 실행
- [ ] `automations/<slug>/before_after.md` 에 "이 자동화가 다루는 데이터
      등급" 명시

### 사용자 가이드
- [ ] `frame run` 호출 전 입력 파일의 데이터 분류 자체 확인
- [ ] Confidential 데이터는 Bedrock 라우팅 환경에서만 사용
- [ ] `runs/<ts>/` archive 는 사내 정책에 따라 보존 기간 설정 (분기·연간
      자동 purge 스크립트 필요)
- [ ] 이상한 출력 발견 시 즉시 보안팀 보고 (LLM 응답에 의도치 않은 PII /
      영업비밀 노출 가능성)

## 5. 감사 (Audit) 접근

모든 `frame run` 호출은 다음 경로에 영구 기록:

```
automations/<slug>/runs/<UTC-timestamp>/
├── inputs/      ← 입력 파일 사본
├── outputs/     ← 생성된 결과
├── prompt.txt   ← 정확한 디스패치 프롬프트
└── log.txt      ← Claude Code 표준 출력 (모델 응답 포함)
```

감사 시 활용:
- **누가**: `git log automations/<slug>/runs/<ts>/` (git commit author)
- **언제**: `<UTC-timestamp>` (디렉토리명)
- **무엇**: `prompt.txt` + `inputs/` 로 입력 + `outputs/` 로 결과 확인
- **AI 가 무엇을 봤는가**: `log.txt` 에 모델 응답 + 도구 호출 전체 기록

## 6. Permission allowlist 정책 (`.claude/settings.local.json`)

FrameAI 의 `frame add` 빌드 파이프라인은 inner `claude --print` 세션을
띄우는데, 첫 도구 호출에서 권한 프롬프트가 뜨면 외부 세션이 hang 합니다.
이를 방지하기 위해 `.claude/settings.local.json` 에 사전 허용 도구 목록
을 commit 했습니다. 보안 원칙:

- **읽기 도구는 광범위 허용** — Read, Glob, Grep, Task, SlashCommand,
  WebFetch, WebSearch
- **쓰기 도구는 광범위 허용** (훅이 catch 함) — Write, Edit, MultiEdit
- **Bash 는 패턴별 한정**:
  - `git *` — 빌드 중 worktree 생성/merge 필요
  - `gh repo view*`, `gh pr view/list*`, `gh issue view/list*`,
    `gh api repos/*/contents/*`, `gh auth status*` — **읽기 전용**.
    `gh repo delete`, `gh pr close`, `gh release delete` 같은 쓰기 명령
    의도적으로 차단 (`GH_TOKEN` 셸에 있을 때 Tyson-Lee 계정 보호)
  - `python3 scripts/*` + `python3 -m pytest *` — 임의 Python 코드 실행
    금지, kit 내부 스크립트만
  - `bash scripts/*` — kit checkpoint/worktree 헬퍼
  - `./frame *`, `./setup.sh*` — FrameAI 자체 CLI
  - `mkdir`, `ls`, `cat`, `head`, `tail`, `grep`, `find`, `touch`,
    `cp`, `mv`, `chmod`, `echo`, `printf` — 안전 파일 시스템 명령
- **명시적으로 차단된 패턴**: `rm`, `dd`, `mkfs`, `Bash(*)`,
  `Bash(gh *)` 와일드카드, `Bash(python3 *)` 와일드카드 — 일부는
  dangerous_command_guard 훅이 추가 차단

**빌드 후 정리 권장**: 빌드가 완료되고 일상 작업으로 전환 시, 위
allowlist 를 더 좁은 일상용 set 으로 다시 commit. 또는 직접 일일이
prompt 받는 일반 모드로 전환.

## 7. 빌드 직전 보안 점검 (2026-06-28 수행)

첫 `frame add` 빌드 직전에 다음 점검을 거쳤습니다:

| 점검 항목 | 결과 |
|---|---|
| `Bash(gh *)` 광범위 권한 | ❌ 차단 → 읽기 전용 패턴으로 한정 |
| `Bash(python3 *)` 광범위 권한 | ❌ 차단 → `scripts/*` 와 `pytest` 만 |
| `runs/` 디렉토리 자동 공유 | ❌ 차단 → `.gitignore` 추가 |
| `.claude/settings.local.json` 의도된 commit | ✅ git ignore 글로벌 규칙 negate, 팀 동기화 보장 |
| secret_guard / dangerous_command_guard 훅 | ✅ PreToolUse 활성 |
| 인너 세션 권한 hang 위험 | ✅ allowlist 사전 부여 |
| /sprint 산출물 main 가시성 | ✅ ADD_PROMPT 에 명시적 절차 |
| PAT 처리 | ⚠️ env var only (`.git/config` 잔류 없음). 빌드 후 revoke 예정 |

**미해결 (Samsung production 배포 시 추가 필요)**:
- 빌드 후 broad allowlist 정리 (운영 단계 권한 더 좁힘)
- install.sh 공급망 — 커밋 해시 핀 + 사내 git mirror 라우팅
- AI 가 작성한 스킬 자체의 보안 리뷰 워크플로 (skill 별 `allowed-tools`
  최소 권한 검증, helpers/ 의 외부 호출 audit)

## 8. 보안 사고 시 대응

1. 즉시 `git revert <commit>` 으로 문제 자동화/입력 commit 되돌리기
2. `automations/<slug>/runs/` 의 영향 받은 run 디렉토리 격리 (별도 압축
   백업 후 삭제)
3. Anthropic API 사용량 / Bedrock CloudTrail 로 어떤 데이터가 외부로
   나갔는지 추적
4. 사내 정보보안팀에 본 가이드의 7-3 절 "데이터 라우팅" 위반 가능성
   보고

---

## Future Works — 다중 작성자 / 마켓플레이스 단계의 추가 보안

상세는 [`CONCEPT.md`](../CONCEPT.md) 의 Future Works 섹션 참고. 핵심:

- 사내 FrameAI 마켓플레이스 단계에서는 **skill 별 owners + PR 자동
  보안 review** 가 필수
- 스킬 publish 전 **자동 PII 마스킹 + egress 검증 게이트** 의무화
- 사용자별 **권한 모델** (이 자동화는 누가 실행 가능한가)
