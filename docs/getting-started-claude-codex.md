# FrameAI 처음 사용하기: Claude Code / Codex CLI 실습 가이드

이 문서는 FrameAI를 처음 접하는 사람이 설치부터 샘플 자동화 실행까지
그대로 따라 하며 새 provider 구현을 확인할 수 있도록 작성한 안내서입니다.
명령은 별도 표시가 없으면 FrameAI 저장소 최상위 폴더에서 실행합니다.

## 0. 먼저 알아둘 점

- FrameAI는 반복 업무를 재사용 가능한 자동화 스킬로 만들고 실행합니다.
- 현재 기본 provider는 Claude Code입니다.
- Codex CLI는 `--provider codex`를 붙여 명시적으로 선택합니다.
- 현재 설치 스크립트는 공통 환경 구성 과정에서 `claude` CLI를 필수로
  확인합니다. 따라서 Codex 경로만 시험하더라도 Claude Code를 먼저 설치해야
  합니다. Codex CLI도 별도로 설치하고 로그인해야 합니다.
- AI provider 호출은 계정 사용량을 소비할 수 있고 저장소 안에 파일을
  생성합니다. 이 문서의 첫 실습은 포함된 합성 샘플만 사용합니다.

## 1. 사전 준비

다음 프로그램을 준비합니다.

- Git
- Python 3.11 이상
- Claude Code CLI와 유효한 로그인
- Codex 경로도 시험하려면 Codex CLI와 유효한 로그인

터미널에서 설치 여부를 확인합니다.

```bash
git --version
python3 --version
claude --version
codex --version
```

Windows PowerShell에서는 Python 명령이 `python`일 수 있습니다. 이후 예제의
`python3`를 `python`으로 바꾸면 됩니다. `claude` 또는 `codex` 명령을 찾지
못한다면 해당 제품의 공식 설치 및 로그인 절차를 먼저 완료합니다. API 키나
토큰을 FrameAI 명령 인자에 붙이지 마십시오. 인증은 각 CLI가 관리합니다.

## 2. FrameAI 설치

### macOS / Linux

```bash
curl -fsSL https://raw.githubusercontent.com/Tyson-Lee/frameai/main/install.sh | bash
cd ~/frameai
```

이미 저장소를 직접 clone했다면 해당 폴더로 이동한 뒤 다음 명령을 실행합니다.

```bash
bash setup.sh
```

### Windows PowerShell

```powershell
irm https://raw.githubusercontent.com/Tyson-Lee/frameai/main/install.ps1 | iex
cd "$HOME\frameai"
```

이미 저장소를 직접 clone했다면 다음을 실행합니다.

```powershell
.\setup.ps1
```

PowerShell의 `curl`은 환경에 따라 `Invoke-WebRequest` 별칭일 수 있으므로,
Windows에서는 위의 `irm ... | iex` 명령을 사용합니다.

## 3. 공통 사전 점검

FrameAI 폴더에서 다음을 실행합니다.

```bash
./frame list
./frame run --help
```

Windows PowerShell에서는 `./frame` 대신 `.\frame`을 사용합니다.
목록에 `meeting-summarizer`가 `ready`로 보이면 샘플 실행 준비가 끝난
것입니다.

실제 AI를 호출하기 전에 생성될 prompt만 보고 싶다면 다음 명령을 사용합니다.
`--dry-run`도 실행 폴더와 prompt 파일은 만들 수 있으므로, 완전한 무변경
명령은 아닙니다.

```bash
./frame run meeting-summarizer \
  --in automations/meeting-summarizer/samples/sample-1.ko.md \
  "테스트 실행" --dry-run
```

## 4. Claude Code로 FrameAI 사용하기

### 4-1. CLI 배치 실행

`--provider`를 생략하면 Claude Code가 선택됩니다.

```bash
./frame run meeting-summarizer \
  --in automations/meeting-summarizer/samples/sample-1.ko.md \
  "주간 팀 미팅 정리 부탁해"
```

명시적으로 쓰고 싶다면 같은 명령에 `--provider claude`를 추가합니다.

```bash
./frame run meeting-summarizer \
  --in automations/meeting-summarizer/samples/sample-1.ko.md \
  "주간 팀 미팅 정리 부탁해" \
  --provider claude
```

실행이 끝나면 터미널에 출력 파일 경로가 표시됩니다. 가장 최근 실행을
확인합니다.

```bash
ls -dt automations/meeting-summarizer/runs/* | head -1
```

표시된 폴더의 `outputs/` 안에서 다음 결과를 확인합니다.

- `summary.md`: 한 페이지 회의 요약
- `action_items.md`: 담당자별 액션 아이템
- `emails/`: 담당자별 후속 메일 초안
- `audit.md`: 누락 가능성을 점검한 감사 결과

### 4-2. Claude Code 대화창에서 실행

FrameAI 폴더에서 Claude Code를 시작합니다.

```bash
claude
```

대화창에 다음을 입력합니다.

```text
/meeting-summarizer 이번 주 디자인 동기화 미팅 정리해줘
```

그다음 `automations/meeting-summarizer/samples/sample-1.ko.md` 파일을
대화에 첨부하거나 해당 경로를 알려 줍니다. 완료 후 Claude가 나열한
`automations/meeting-summarizer/runs/<시각>/outputs/` 파일을 엽니다.

## 5. Codex CLI로 FrameAI 사용하기

### 5-1. 로그인과 선택 확인

Codex CLI의 공식 로그인 절차를 마친 뒤 다음을 확인합니다.

```bash
codex --version
./frame run --help
```

도움말에 `--provider {claude,codex}`가 나타나야 합니다.

### 5-2. 동일한 샘플을 Codex로 실행

```bash
./frame run meeting-summarizer \
  --in automations/meeting-summarizer/samples/sample-1.ko.md \
  "주간 팀 미팅 정리 부탁해" \
  --provider codex
```

FrameAI는 내부적으로 Codex CLI를 headless 방식으로 실행하고, Claude 경로와
동일한 `automations/meeting-summarizer/runs/<시각>/` 구조에 입력, prompt,
log, 출력을 보관합니다. 자연어 표현이 Claude 결과와 완전히 같을 필요는
없습니다. 파일 구조와 필수 내용이 충족되는지를 비교하십시오.

매번 옵션을 붙이지 않으려면 현재 셸에서 기본 provider를 지정할 수 있습니다.

```bash
export FRAMEAI_PROVIDER=codex
./frame run meeting-summarizer \
  --in automations/meeting-summarizer/samples/sample-2.en.vtt \
  "test run"
```

Windows PowerShell에서는 다음과 같습니다.

```powershell
$env:FRAMEAI_PROVIDER = "codex"
.\frame run meeting-summarizer `
  --in automations/meeting-summarizer/samples/sample-2.en.vtt `
  "test run"
```

명령의 `--provider`가 환경 변수보다 우선합니다. 다시 Claude를 기본값으로
돌리려면 macOS/Linux에서는 `unset FRAMEAI_PROVIDER`, PowerShell에서는
`Remove-Item Env:FRAMEAI_PROVIDER`를 실행합니다.

## 6. 새 자동화 만들기

샘플 실행이 성공한 뒤 별도의 테스트 자동화를 만들 수 있습니다. 아래 명령은
AI 사용량을 소비하고 `skills/`와 `automations/` 아래에 여러 파일을 생성할
수 있습니다.

Claude Code로 만들기:

```bash
./frame add \
  "짧은 업무 메모를 받아 핵심 요약과 체크리스트를 Markdown으로 만들어 줘" \
  --slug my-note-helper \
  --provider claude
```

Codex CLI로 만들기:

```bash
./frame add \
  "짧은 업무 메모를 받아 핵심 요약과 체크리스트를 Markdown으로 만들어 줘" \
  --slug my-note-helper-codex \
  --provider codex
```

빌드가 성공하면 확인합니다.

```bash
./frame list
sed -n '1,160p' automations/my-note-helper/README.md
```

생성된 자동화의 README에 적힌 입력 형식대로 `./frame run <slug> ...`을
실행합니다. 테스트 중 만든 자동화는 자동으로 commit 또는 push되지 않습니다.

## 7. 성공 판정 체크리스트

Claude와 Codex를 각각 한 번 실행한 뒤 아래 항목을 확인합니다.

- 명령 종료 코드가 `0`이다.
- 서로 다른 `runs/<UTC 시각>/` 폴더가 생성되었다.
- 각 실행 폴더에 `inputs/`, `outputs/`, `prompt.txt`, `log.txt`가 있다.
- `inputs/`에 사용한 샘플 파일이 복사되어 있다.
- `outputs/`에 `summary.md`, `action_items.md`, `audit.md`, `emails/*.md`가 있다.
- 원본 샘플 파일은 변경되지 않았다.
- 비밀키나 토큰이 명령 또는 공유할 log에 포함되지 않았다.

`git status --short`로 예상하지 못한 파일 변경도 확인합니다. `runs/`처럼
실행 아카이브가 추가되는 것은 정상이나, 기존 소스 파일이 바뀌었다면 내용을
검토한 뒤 다음 실습을 진행하십시오.

## 8. 자주 만나는 오류

### `FrameAI: 'claude' CLI not found on PATH`

Claude Code를 설치하고 새 터미널을 연 뒤 `claude --version`을 다시
확인합니다. 현재 공통 설치 스크립트도 Claude Code를 요구합니다.

### `FrameAI: 'codex' CLI not found on PATH`

Codex CLI를 설치하고 새 터미널에서 `codex --version`이 성공하는지
확인합니다.

### 인증 또는 사용량 오류

FrameAI가 아닌 해당 provider CLI에서 로그인을 확인합니다. 토큰을
`FRAMEAI_RUN_TEXT`나 명령 인자로 전달하지 마십시오. 자동 fallback이나
재시도는 없으며 provider의 종료 코드가 그대로 반환됩니다.

### `frame run: input file not found`

현재 위치가 FrameAI 저장소 최상위인지 `pwd`로 확인하고, `--in` 경로의
철자와 파일 존재 여부를 확인합니다.

### 결과 파일이 없거나 실행이 중단됨

가장 최근 `runs/<시각>/log.txt`를 로컬에서 확인합니다. 실패한 실행도 일부
파일을 남길 수 있으므로 자동 삭제하지 말고, 민감한 입력이 없다면 오류 부분만
가려서 공유하십시오. provider를 바꿔 자동 재시도하지 않으므로 같은 명령을
다시 실행할지는 사용자가 결정해야 합니다.

## 9. 테스트 결과 기록 양식

문제가 생기면 아래 형식으로 기록하면 재현하기 쉽습니다. 인증 정보와 실제
민감 입력은 넣지 않습니다.

```text
OS:
Python version:
Claude Code version:
Codex CLI version:
FrameAI commit:
실행한 provider: claude | codex
실행한 명령(민감 내용 제거):
종료 코드:
생성된 run 상대 경로:
생성된 output 파일 목록:
오류 메시지 또는 기대와 다른 점:
git status --short 결과(민감 경로 제거):
```
