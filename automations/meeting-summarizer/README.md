# meeting-summarizer

회의 녹취/자막 (Zoom·Teams `.vtt`, 또는 회의록 `.txt`/`.md`) 한 개를
입력받아 **한 페이지 요약 + 액션 아이템 표 + 책임자별 후속 메일 초안**
세 개의 마크다운 파일을 만들어 주는 스킬입니다.

입력이 한국어면 출력도 한국어 (정중한 어투), 영어면 영어 (professional
tone) 로 자동 전환됩니다.

## 한 줄 사용법

### A. CLI 배치 (`frame run`)

```bash
./frame run meeting-summarizer \
  --in automations/meeting-summarizer/samples/sample-1.ko.md \
  "주간 팀 미팅 정리 부탁해"
```

`--in` 으로 전달된 파일이 `runs/<UTC-ts>/inputs/` 에 복사되고, 결과 세
파일이 `runs/<UTC-ts>/outputs/` 아래에 떨어집니다.

### B. Claude Code 채팅에서

Claude Code 안에서:

```
/meeting-summarizer 이번 주 디자인 동기화 미팅 정리해줘
```

라고 적고 회의록 파일을 채팅에 드래그하거나 경로로 참조하면, 스킬이
직접 `automations/meeting-summarizer/runs/<UTC-ts>/` 아래에 archive
폴더를 만들고 같은 출력을 생성합니다.

## 입력

| 종류 | 필수 | 비고 |
|---|---|---|
| 회의 transcript 파일 | ✅ | `.vtt`, `.txt`, `.md` 중 하나 |
| 자유 텍스트 인자 | ⛔ | 강조하고 싶은 주제·문맥 (선택) |

여러 파일을 `--in` 으로 전달한 경우 **우선순위 `.vtt` > `.md` > `.txt`**
로 첫 번째 transcript 하나만 처리합니다. 다중 transcript 병합은 현재
범위 밖 (Limits 참고).

언어 강제 지정이 필요하면 파일명에 `.ko.` / `.en.` 을 포함시키면
됩니다 (예: `weekly.en.vtt` → 영어 출력 강제).

## 출력 (`runs/<UTC-ts>/outputs/` 아래)

| 파일 | 내용 |
|---|---|
| `summary.md` | H1 제목 + `## 의제 / ## 결정 사항 / ## 다음 단계` (영어: `Agenda / Decisions / Next Steps`) |
| `action_items.md` | `담당자 \| 액션 \| 기한 \| 우선순위` (영어: `Owner \| Action \| Due \| Priority`) — 미명시는 `TBD` |
| `emails/<slug>.md` | 책임자 1인당 1 파일. 정중한 어투, 해당 책임자의 액션만 나열 |
| `audit.md` | 별도 컨텍스트 auditor 가 refute-first 로 누락된 액션 후보를 보고. 누락이 있으면 본 스킬이 한 차례 재반영 후 audit.md 갱신 |

스킬은 완료 시 위 파일 경로 목록을 사용자에게 출력합니다. Claude Code
채팅 모드에서는 인라인 렌더링되고, CLI 모드에서는 `runs/<ts>/log.txt`
에도 남습니다.

## 샘플로 한 번에 검증

```bash
# 한국어 회의록
./frame run meeting-summarizer \
  --in automations/meeting-summarizer/samples/sample-1.ko.md \
  "테스트 실행"

# 영어 Zoom 자막
./frame run meeting-summarizer \
  --in automations/meeting-summarizer/samples/sample-2.en.vtt \
  "test run"
```

각 `runs/<ts>/outputs/` 에서 세 종류의 파일이 모두 생성되는지 확인하세요.

## Limits (정직)

- **액션 추출은 휴리스틱**. refute-first auditor 가 명시적인 미래
  동사·의뢰 표현을 다시 훑어 누락을 줄이지만, 화자가 *암묵적으로만*
  맡긴 일은 잡지 못할 수 있음. **발송 전 사람이 한 번 더 검토 필수**.
- **이메일은 초안**. 정중한 톤의 템플릿 + 액션 리스트일 뿐, 발신자
  서명·CC·첨부 등은 사용자가 직접 채워야 함.
- **자동 발송 없음**. 이 스킬은 Gmail / Slack / 메일 서버에 접속하지
  않으며 파일만 생성. 발송은 사용자가 손으로 진행.
- **한 회의 = 한 transcript**. 같은 회의의 여러 파일 (전·후반 자막 등)
  은 미리 합쳐 하나로 만들어 입력.
- **언어 자동감지는 Hangul 비율 휴리스틱**. 비공백 글자 중 한글 ≥ 20%
  면 한국어로 처리. 혼용 회의는 파일명에 `.ko.` / `.en.` 강제 태그를 권장.
- **기한 자연어 미해석**. "다음 주 월요일" 같은 표현은 원문 그대로
  보존 (캘린더 연동은 범위 외).
- **로컬 파일 시스템 한정**. 출력은 작업 트리 안에만 기록되고, 외부
  네트워크 호출은 없음. 사내 보안 정책상 안전.

## 디렉토리 구조

```
automations/meeting-summarizer/
├── input.md            # 사용자가 처음 적은 자연어 (수정 금지)
├── README.md           # 이 파일
├── before_after.md     # 수동 vs 자동 시간 비교
├── samples/
│   ├── sample-1.ko.md  # 한국어 회의록 샘플 (주간 제품 회의)
│   └── sample-2.en.vtt # 영어 Zoom 자막 샘플
└── runs/<UTC-ts>/      # frame run / 채팅 호출마다 1개씩 생성
    ├── inputs/
    └── outputs/
        ├── summary.md
        ├── action_items.md
        ├── emails/
        │   ├── <slug>.md
        │   └── ...
        └── audit.md
```
