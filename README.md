# AI Workflow

Codex와 Cursor에서 공유하는 단계별 에이전트 운영 규칙입니다. 개정 `2026-11-10`, 프로젝트 관리 구조 버전 `5`입니다.

**작업용 PC의 WSL2에 한 번 설치**하고 여러 프로젝트에서 사용합니다. 전역 지침에는 짧은 연결 문구만 넣고 에이전트가 역할별 필수 원문을 읽습니다. 프로젝트 기록은 해당 프로젝트의 `.ai-work/`에 두고 Git에서 제외합니다.

## 설치와 사용

[WSL 설치 안내](docs/installation.md)를 순서대로 진행합니다. 운영체제별 설치 방법을 선택할 필요가 없습니다.

| 순서 | 할 일 |
|---|---|
| 1. 공통 설치 | WSL에서 clone → sync → 연결 지침 생성 |
| 2. 도구 연결 | Codex는 전역 AGENTS.md, Cursor는 MCP와 User Rules 등록 |
| 3. 연결 확인 | 실제 작업 창의 새 대화에서 고정 커밋과 본문 읽기 확인 |
| 4. 프로젝트 사용 | [사용자 가이드](docs/user-guide.md)의 단계별 요청 |

**Cursor로 원격 SSH 서버에서 작업할 때만** [추가 연결](docs/mcp.md)을 설정합니다. PC WSL의 HTTP MCP에 SSH 터널로 연결하므로 서버에는 MCP URL·토큰 설정만 필요하며 레포·Python을 설치하지 않습니다.

## 파일과 읽기 흐름

```text
PC의 WSL: ~/.ai-workflow/
├── source/                       원본 Git clone과 관리 도구
└── runtime/
    ├── active.json               새 작업의 커밋과 스냅샷 위치
    ├── sync-status.json          마지막 원격 확인 결과·시각
    ├── snapshots/<커밋>/         고정 버전의 문서 묶음
    └── connectors/               Codex·Cursor 연결 지침과 MCP 설정
```

Codex는 연결 지침에서 WSL 파일을 직접 읽고, Cursor는 MCP로 같은 사본을 읽습니다. 상태 확인 → 고정 커밋의 `workflow/entry.md` → 해당 역할의 필수 문서 → 프로젝트 작업지시서 순서입니다. 전체 규칙을 자동 첨부하는 방식은 아닙니다.

| 저장소 위치 | 내용 |
|---|---|
| `workflow/entry.md` | 역할별 읽기 목록·버전 고정의 진입점 |
| `workflow/` | 공통·모델·기록·품질과 역할별 운영 규칙 원본 |
| `docs/installation.md` | WSL 설치·도구 연결·확인·갱신 |
| `docs/mcp.md` | SSH 작업 시 추가 연결 |
| `docs/user-guide.md` | 단계별 사용 예시 |
| `docs/maintenance.md` | 개정·배포·보존 기준 |
| `scripts/`, `templates/`, `tests/` | 설치·MCP 도구, 짧은 연결 지침, 검사 |

저장소의 `AGENTS.md`는 유지보수 안내입니다. 전역 지침에는 설치 도구가 생성한 연결 문구를 넣습니다. 문서 검토나 태그 인용을 프로젝트 실행으로 해석하지 않습니다.

## 운영·배포 기준

- 최초 모델: 계획 3단계, 총괄·통합 2단계, 실행·사용자검증·커밋목록 1단계.
- 실행·통합은 동일 문제에서 지정 모델로 최초 시도 포함 2회 실패한 뒤 바로 위 단계로 1회만 시도합니다. 다시 실패하면 중단·보고합니다.
- 총괄은 명시적으로 호출하며 현재 조건에서 독립적으로 수행 가능한 작업을 병렬 배정합니다. 충돌 발견 시 총괄 지시를 따릅니다.
- 최종 수락은 통합 담당자가 판단합니다. 커밋목록 작성은 실제 staging·commit을 수행하지 않습니다.
- 설치 안내는 원격 `master`를 `sync --branch master`로 읽습니다. sync는 source 작업 파일을 덮어쓰지 않고 커밋별 사본을 만들며 이전 사본을 보존합니다.
- 새 작업은 새 커밋을 선택하고 기존 작업·하위 에이전트는 고정한 버전을 유지합니다. 원격 확인 실패·오프라인 사용을 최신 확인 성공으로 표시하지 않습니다.

## 검사

```bash
python3 scripts/check_docs.py
python3 -m unittest discover -s tests -v
```

[유지보수 안내](docs/maintenance.md)는 문서·스크립트 검사와 실제 앱의 지침 로딩·모델 전환 검증을 구분합니다. 모델 계열의 버전 기준일은 `2026-11-07`이며 현재 환경의 가용성은 배정 시 확인합니다.
