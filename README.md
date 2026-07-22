# FrameAI

> **내 일은 AI가, AI 일은 AI가.** 자동화를 자동화하는 AI 빌드 파이프라인.

사용자가 반복 업무를 자연어로 한 문단 설명하면, AI 에이전트 팀이 기획 →
설계 → 구현 → 테스트 → 배포 → 사용 가이드까지 자율 수행해 **재사용
가능한 Claude Code 스킬**을 만들어 냅니다. CLI 빌드·실행·개선 작업은
기본 Claude Code 또는 선택 가능한 Codex CLI provider로 수행합니다. 만들어진
스킬은 누구나 `frame run <이름>` 또는 Claude Code 안에서 `/이름` 으로 호출 가능하고,
파일·이미지·텍스트 어떤 입력이든 받아 결과 파일을 그 회의 `runs/<시각>/`
폴더에 영구 보관합니다.

## 사용 흐름

| 사용자 | 어떻게 호출 | 언제 |
|---|---|---|
| **현장 엔지니어 (CLI 안 침)** | Claude Code 채팅창에 파일 드래그 + 자연어 (또는 `/<스킬명>`) | 일상 사용 |
| **현장 엔지니어 (Claude Desktop)** | Desktop 채팅에 자연어 → MCP tool 자동 호출 | install 시 자동 등록 (재시작 1 회) |
| **자동화 작성자 (1인)** | `frame add` CLI 한 줄 | 새 자동화 만들 때 |
| **CI / cron / 배치** | `frame run --in ...` CLI | 스케줄링 / 외부 시스템 연동 |

같은 자동화를 네 UX 모두로 호출할 수 있습니다 — 내부적으로 같은 `SKILL.md`
한 벌만 보고, Claude Code 는 네이티브로, Claude Desktop 은 MCP 서버를
거쳐서 노출됩니다.

### 첫 설치 — 한 번만 (터미널 없이)

**방법 A — Claude Code 채팅창에서 한 줄 paste (권장, 현장 엔지니어)**

1. Claude Code 앱 실행 (Anthropic 의 일반 설치 한 번이면 됨)
2. 사내 공지 (Slack/email/wiki) 에서 한 줄을 복사:
   ```
   curl -fsSL https://raw.githubusercontent.com/Tyson-Lee/frameai/main/install.sh | bash
   ```
3. 채팅창에 paste 하고 *"이거 실행해줘"* 라고 추가
4. Claude 가 자체 Bash 도구로 실행 → 5-10초 후 완료
5. 설치된 폴더 (`~/frameai/`) 를 Claude Code 에서 열기

> **정직히**: *"FrameAI 설치해줘"* 한 마디만으로 작동하려면 FrameAI 가
> Claude 의 학습 데이터에 포함되어야 합니다 (수개월~연 단위). 현재는
> 사용자가 install URL 을 직접 paste 해야 합니다. 사내 공지 한 번 뿌리는
> 게 가장 간단한 운영 방안.

**방법 B — 터미널 직접 (자동화 작성자 / IT)**

macOS / Linux:
```bash
curl -fsSL https://raw.githubusercontent.com/Tyson-Lee/frameai/main/install.sh | bash
# 또는 위치 / 사내 미러 지정:
FRAMEAI_HOME=~/my-frameai \
  FRAMEAI_REPO_URL=https://<사내-git>/frameai.git \
  bash install.sh
```

Windows (PowerShell):
```powershell
# 한 줄 설치 (irm = Invoke-RestMethod, iex = Invoke-Expression):
irm https://raw.githubusercontent.com/Tyson-Lee/frameai/main/install.ps1 | iex

# 또는 위치 / 사내 미러 지정:
$env:FRAMEAI_HOME = "$HOME\my-frameai"
$env:FRAMEAI_REPO_URL = "https://<사내-git>/frameai.git"
.\install.ps1
```

`install.sh` (Mac/Linux) 또는 `install.ps1` (Windows) 가 자동으로
git clone + `setup` 까지 실행합니다.

**Windows 사용 시 차이점**:
- **PowerShell 의 `curl` 은 `Invoke-WebRequest` 의 alias** — 실제 curl 이
  아니라서 `-fsSL` 같은 옵션 안 받음. 또한 `bash` 가 기본 미설치라
  `... | bash` 도 실패. 따라서 Windows 에서는 **`irm | iex` (PowerShell
  네이티브) 또는 Git Bash 안에서 `curl | bash` 둘 중 하나** 사용.
- `.claude\skills` 등은 **junction** 으로 생성 (symlink 대비 관리자 권한 불필요)
- CLI 호출은 `.\frame add ...` (자동으로 `frame.cmd` → `python frame ...` 라우팅)
- Git for Windows 가 함께 설치하는 bash 가 credential helper 의 inline 셸 함수를 실행하므로 push 패턴 동일

### 재설치 / 업데이트 — install 명령 재실행 시 동작

install 명령은 **idempotent** — 같은 명령을 다시 실행해도 안전:

| 상태 | install.sh / install.ps1 동작 |
|---|---|
| **`~/frameai/` 가 이미 FrameAI 레포** (`.git` 있음) | "이미 설치됨. 업데이트 진행..." 메시지 + `git pull --ff-only` + `setup.sh` 재실행. → 사실상 `./frame update` 와 동일 |
| **`~/frameai/` 에 commit 안 된 변경 존재** | `✘ uncommitted changes — resolve manually or set FRAMEAI_HOME=<other-path>` 출력 + 종료 (안전 가드) |
| **`~/frameai/` 가 FrameAI 아닌 다른 폴더** | `✘ exists but is not a FrameAI install. Set FRAMEAI_HOME=<other-path>.` 출력 + 종료 (기존 폴더 보호) |
| **`~/frameai/` 가 없음** | 정상 신규 설치 (clone + setup) |

**엣지 케이스**: 이미 *다른 경로* (예: `~/work/frameai-prod`) 에 clone
해둔 상태에서 그냥 install 재실행하면 **`~/frameai/` 에 별도 clone 이
새로 만들어짐** (중복). install 위치 분리하려면 `FRAMEAI_HOME=~/work/frameai-prod`
환경변수 명시 후 실행.

Claude Code 채팅에서 사용자가 install 명령 다시 paste 했을 때:
- 이미 설치된 사용자 → 자동 update 메시지, 자연스럽게 흐름
- 미설치 사용자 → 신규 설치 진행
- 추가 사용자 행동 0회

### 현장 엔지니어 (CLI 안 침)

1. **frame 폴더에서 `claude` 실행** (Claude Code 앱이 자동으로 frameai 의 `.claude/` 발견)
2. 화면에 spec.pdf / defect.png 등을 **드래그**
3. 채팅창에 자연어로: *"이 변경 사항으로 ECN 작성해 줘"* (또는 `/ecn-writer M1 CD 22→18nm`)
4. 결과 파일이 인라인 표시 + `automations/ecn-writer/runs/<시각>/outputs/` 에 자동 저장

### 최신 자동화 받기 (Claude Code 채팅에서)

채팅창에 한 줄:

> *"FrameAI 업데이트해줘"* 또는 `/frameai-update`

`/frameai-update` 슬래시 명령이 내부적으로 `./frame update` 를 호출하고,
새로 추가된 자동화를 한국어로 요약해서 보여줍니다. 터미널 0회.

(터미널을 쓰는 IT/자동화 작성자는 `./frame update` 도 동일하게 작동합니다.)

### Claude Desktop 에서 쓰기 (install 시 자동 등록)

`install.sh` / `install.ps1` 이 자동으로:
1. `mcp` Python 패키지 설치
2. Claude Desktop config 파일 (`~/Library/Application Support/Claude/claude_desktop_config.json`
   on macOS, `%APPDATA%\Claude\claude_desktop_config.json` on Windows) 에
   FrameAI MCP 서버 항목을 **safe-merge** (기존 mcpServers / preferences 보존)
3. Claude Desktop 미설치 시 자동 skip

활성 절차:
```
1) install (위 quickstart) → "Claude Desktop MCP registered" 메시지 확인
2) Claude Desktop 재시작
3) Settings → Connectors 에서 frameai 가 N tools available 로 보이면 활성
   (N = kit skill 11 + 빌드된 자동화 수)
4) 채팅창에 자연어로 "회의록 정리해줘" 등 입력
   → Desktop LLM 이 frameai 의 tool 자동 호출 (별도 / 메뉴 조작 불필요)
```

> Desktop UI 상 MCP **tools** 만 노출됨 (`/` 슬래시 메뉴는 Desktop 자체
> 명령 전용). 스킬은 모두 tool 로 등록되어 LLM 의 자연어 매칭으로 호출.

**무엇이 자동, 무엇이 수동**:

| 동작 | Claude Code | Claude Desktop |
|---|---|---|
| `./frame add` 로 새 스킬 빌드 | ✅ 자체 LLM | ❌ 빌드는 Claude Code 에서만 |
| 빌드된 스킬 사용 | ✅ `/<slug>` 자동 dispatch | ✅ 자연어로 LLM 이 tool 자동 호출 |
| 새 스킬 노출 (`frame add` 직후) | ✅ 즉시 | ✅ 다음 새 채팅 또는 Desktop 재시작 1 회 |
| 별도 컨텍스트 auditor | ✅ Task tool spawn | ⚠️ Desktop Task tool 제한 — 일부 self-check degraded |
| 파일 입출력 | ✅ Bash | ✅ MCP filesystem 등 Desktop 자체 도구 |

> Claude Desktop 경로는 *USE 전용*. 새 스킬 빌드는 Claude Code 가 정답.

### 자동화 작성자 — push 인증 (1 회 manual 셋업, 일반 사용자 불필요)

> **일반 사용자 (현장 엔지니어) 는 push 안 함** → 이 섹션 스킵.
> 자동화를 직접 만들어 사내 라이브러리에 commit/push 하는 사람만 해당.

setup.sh / setup.ps1 은 **자동 인증 셋업을 하지 않습니다** (이전 버전은
하드코딩된 식별자를 박았다가 보안적으로 부적절해 제거). 작성자는 본인
GitHub identity 로 직접 1 회 셋업:

**방식 A — 본인 username + PAT 환경변수**

```bash
# 본인 정보로 한 번만 (frameai 폴더 안에서):
git config credential.helper ""
git config --add credential.helper \
  '!f() { test -n "$GH_TOKEN" && test -n "$GH_USERNAME" && \
    printf "username=%s\npassword=%s\n" "$GH_USERNAME" "$GH_TOKEN"; }; f'
```

이후 push:
```bash
export GH_USERNAME=<your-github-username>
export GH_TOKEN=<your-PAT>
git push                          # 또는 ./frame share <slug> --push
```

`~/.zshrc` 또는 `.bashrc` 에 두 줄 export 두면 매 셸 자동.

**방식 B — SSH key (장기 권장, 더 안전)**

```bash
# 1회만:
ssh-keygen -t ed25519 -C "your@email.com"
# 출력된 public key 를 GitHub Settings → SSH and GPG keys 에 등록
git remote set-url origin git@github.com:<your-username>/<your-fork>.git
```

이후 `git push` / `./frame share <slug> --push` 가 SSH 키로 자동 인증.

**왜 자동 셋업 안 하는가**: setup.sh 가 일반 사용자 머신에 일괄 적용
되는데, 일반 사용자는 push 자체를 안 함. 작성자만 본인 정보로 명시
적으로 셋업하는 게 보안 + 정직성 둘 다 정답.

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

### AI provider 선택 — Claude Code / Codex CLI

`frame add`, `frame run`, `frame refine`는 Claude Code를 기본 provider로
사용합니다. Codex CLI를 사용하려면 해당 CLI를 별도로 설치·로그인한 뒤
명령에 `--provider codex`를 추가합니다:

```bash
./frame add "업무 메모를 요약하고 체크리스트로 만들어 줘" --provider codex
./frame run meeting-summarizer --in meeting.vtt "액션 아이템 정리" --provider codex
./frame refine meeting-summarizer "결정 사항 섹션을 추가해 줘" --provider codex
```

현재 셸의 기본 provider를 바꾸려면 `FRAMEAI_PROVIDER`를 사용합니다. 명령의
`--provider`가 환경 변수보다 우선하며, 둘 다 생략하면 `claude`입니다.

```bash
export FRAMEAI_PROVIDER=codex
./frame run meeting-summarizer --in meeting.vtt "영문 요약"

# 한 번만 Claude Code로 실행
./frame run meeting-summarizer --in meeting.vtt "영문 요약" --provider claude
```

Codex adapter는 `codex exec --ephemeral`로 저장소 루트에서 실행되며,
FrameAI의 기존 prompt·입출력·`runs/<시각>/` archive 계약을 그대로 사용합니다.
인증과 설정은 설치된 Codex CLI가 관리하고 FrameAI가 provider 간 자동
fallback이나 retry를 수행하지 않습니다.

> **Codex 보안 경고**: 현재 adapter는 승인된 FrameAI host의 외부 격리를
> 전제로 Codex의 자체 approvals와 sandbox를 비활성화합니다. 신뢰할 수 있는
> checkout과 별도 격리 경계에서만 사용하고 production target에는 직접
> 사용하지 마십시오. 선택할 때마다 CLI에도 경고가 출력됩니다.

설치부터 샘플 비교 실행까지는
[`docs/getting-started-claude-codex.md`](docs/getting-started-claude-codex.md),
정확한 dispatch 계약·운영 점검·rollback은
[`docs/codex-adapter-operator.md`](docs/codex-adapter-operator.md)를 참고하십시오.

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
- `cd frameai && claude` 하면 즉시 11 개 kit skill (`/sprint`, `/prd`,
  `/brainstorm` 등) + `frame add` 로 빌드한 모든 자동화
  (예: `/meeting-summarizer`) + 다수의 Claude Code 런타임 built-in
  (`/code-review`, `/deep-research`, `/verify` 등) 모두 노출
- 새로 빌드된 `skills/<slug>/` 도 자동 발견 (별도 install / register 불필요)
- 별도 "프로젝트 등록" 작업 없음 — Claude Code 앱은 폴더 자체를 프로젝트로
  인식. cmux/Desktop 앱은 Recent Projects 사이드바에서 한 번 열면 등록

기본적으로 `frame add`, `frame run`, `frame refine`는 Claude Code를 헤드리스
(`claude --print`)로 호출합니다. `--provider codex` 또는
`FRAMEAI_PROVIDER=codex`를 지정하면 같은 FrameAI 계약으로 Codex CLI
(`codex exec`)를 호출합니다. **사용자 추가 입력 없이** 작업이 진행되고,
진행 상황은 stdout으로 흘러나옵니다.

## 파일 · 이미지 · 멀티모달 입력

자동화가 받는 입력은 텍스트만이 아닙니다. **Claude Code 의 Read tool 이
PDF · PNG · JPG · 노트북을 네이티브 멀티모달로 처리**하므로, FrameAI 는
별도 OCR 이나 파싱 레이어 없이 파일을 그대로 전달합니다:

| 입력 종류 | CLI 옵션 | 처리 방식 |
|---|---|---|
| 텍스트 (인자) | `frame run <name> "<text>"` | `$FRAMEAI_RUN_TEXT` 로 전달 |
| 파일 (CSV/JSON/MD/PDF) | `--in PATH` (반복 가능) | `runs/<ts>/inputs/` 로 복사 → Read |
| 이미지 (PNG/JPG) | `--image PATH` (반복 가능) | 동일 위치 + 멀티모달 Read |

**예시** (`meeting-summarizer` 는 실제 빌드되어 있음; 나머지는 동일 패턴의
가설 자동화):
```bash
# 회의록 자동 정리: .vtt 자막 입력 → 요약 + action items + 담당자별 이메일 draft
./frame run meeting-summarizer \
    --in automations/meeting-summarizer/samples/sample-2.en.vtt \
    "팀 후속 조치 요약 부탁"

# 자동화 작성자가 새로 만들 수 있는 예시:
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

각 단계 안에서 21개 전문 에이전트가 git worktree 로 격리된 채 자동화
종류에 맞는 역할만 활성화되어 병렬 작업하고, 단계별 체크포인트가
검증된 후에만 다음 단계로 넘어갑니다. 검토는 별도 컨텍스트의 auditor
에이전트가 refute-first 프롬프트로 수행해 셀프-체크의 사이코펀시
문제를 피합니다.

## Repo 구조

비-UI 자동화 빌드에 필요한 lean 구성. UI/디자인/대규모 코드베이스 분석
같은 도메인 확장은 향후 마일스톤으로 분리.

```
frameai/
├── README.md              ← 이 파일
├── CONCEPT.md             ← Git-like 공유 비전 (디테일)
├── CLAUDE.md              ← AI 어시스턴트용 프로젝트 컨텍스트
├── frame                  ← CLI 진입점 (한 파일 Python)
│
├── skills/                ← 11 kit skill (PRD/킥오프/스프린트/리뷰/...) + 빌드된 자동화
├── agents/                ← 21 전문 에이전트 (PRD/계획/구현/리뷰/audit/...)
├── scripts/               ← 헬퍼 (synthesizer, validator, hook 등)
│   └── frameai_mcp_server.py  ← MCP 서버 — Desktop/Cursor 에서 tools 로 노출
├── project/.claude/       ← Claude Code 훅 + 설정 스니펫
├── templates/             ← PRD / 아키텍처 / 이슈 결과물 템플릿
├── docs/                  ← CC 지원 매트릭스, 캐싱 노트, 보안, 텔레메트리 schema
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

- **AI provider**: Claude Code (기본) 또는 Codex CLI (`--provider codex`)
- **Claude 모델**: Anthropic Claude (Opus 4.7 / Sonnet 4.6) + 자동 폴백
  (`fallbackModel: ["claude-sonnet-4-6", "claude-haiku-4-5"]`)
- **런타임**: Claude Code v2.1.145+ (자체 검증된 지원 매트릭스는
  [`docs/cc_feature_matrix.md`](docs/cc_feature_matrix.md) 참고)
- **멀티모달**: Read tool 의 네이티브 PDF · 이미지 지원 (별도 OCR 불필요)
- **연동**: 런타임 `/code-review` · `/security-review` · `/deep-research`
  · `/verify` 직접 위임 (kit 재구현 대신 플랫폼 우선)
- **격리**: git worktree 기반 병렬 에이전트 작업, 공유 파일은 `flock` +
  `registry_edit` 으로 동시성 보호

## 사내 배포 시 보안

**가장 중요**: 기본 설정에서 데이터는 Anthropic 미국 인프라로 전송됩니다.
사내 Confidential 데이터를 다루려면 **AWS Bedrock 서울 리전 라우팅**
(`CLAUDE_CODE_USE_BEDROCK=1` + `AWS_REGION=ap-northeast-2`) 필수.

상세 + 데이터 분류 권장 정책 + PII 마스킹 운영안: **[docs/security.md](docs/security.md)** 참고.

이미 작동 중인 보호 장치:
- `secret_guard` 훅 — API 키 / 토큰 패턴의 Write/Edit 자동 차단
- `dangerous_command_guard` 훅 — `rm -rf` 등 파괴적 명령 차단
- 매 호출 archive — `runs/<ts>/` 에 입력·프롬프트·출력·로그 4종 보관
- `separate-context auditor` — refute-first 프롬프트로 별도 컨텍스트 검증

아직 없는 부분 (마일스톤 별 로드맵은 [CONCEPT.md](CONCEPT.md#future-works)):
- 자동 PII 마스킹
- 네트워크 egress 매니페스트
- 데이터 분류 자동 게이트

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

FrameAI 는 오픈소스 프로젝트 `claude-dev-kit` (저자: pillip, MIT
License) 에서 검증된 파이프라인 (PRD → 킥오프 → 스프린트) 위에
컨테스트 컨텍스트로 재포지셔닝되었습니다. Claude Code 의 플러그인
시스템 · 훅 이벤트 · 캐싱 정책 · 멀티모달 Read 등 런타임 캐퍼빌리티를
적극 활용합니다.
