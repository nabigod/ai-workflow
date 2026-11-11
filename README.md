# AI Workflow

Codex와 Cursor에서 공유하는 단계별 에이전트 운영 규칙입니다. 규칙 기준 `2026-11-12`, 셋업 안내 개정 `2026-11-12`, 프로젝트 관리 구조 버전 `5`입니다.

**WSL 에이전트 + Windows Codex** 또는 **Linux 에이전트 + Windows Cursor**를 사용합니다. 워크플로우는 사용할 WSL·Linux 사용자 환경에 한 번씩 설치하고 여러 프로젝트에서 공유합니다. 전역 지침에는 짧은 연결 문구만 넣고 에이전트가 역할별 필수 원문을 읽습니다. 프로젝트 기록은 해당 프로젝트의 `.ai-work/`에 두고 Git에서 제외합니다.

## 설치와 사용

[실행 환경별 셋업 안내](docs/installation.md)의 공통 설치 후 해당 환경의 도구를 연결합니다. 두 환경 모두 로컬 파일을 직접 읽으며 MCP는 필요하지 않습니다.

| 환경 | 파일 읽기·명령 실행 | 워크플로우 연결 |
|---|---|---|
| WSL 에이전트 + Windows Codex | 작업용 WSL2 | WSL 원문 + 앱 전역 AGENTS.md |
| Linux 에이전트 + Windows Cursor | Remote SSH로 연결한 Linux 개발 PC | 개발 PC 원문 + Cursor User Rules |

| 순서 | 할 일 |
|---|---|
| 1. 공통 설치 | 사용할 WSL·Linux 개발 PC에서 각각 clone → sync → 연결 지침 생성 |
| 2. 도구 연결 | Codex 전역 AGENTS.md 또는 Cursor User Rules 등록 |
| 3. 연결 확인 | 실제 작업 창의 새 대화에서 고정 커밋과 본문 읽기 확인 |
| 4. 프로젝트 사용 | [사용자 가이드](docs/user-guide.md)의 단계별 요청 |

Linux 에이전트 환경에서는 하나의 개발 PC에서 총괄과 하위 에이전트를 운영하고 다른 testpc는 빌드·테스트 대상으로 사용합니다. 테스트만 실행하는 PC에는 워크플로우를 설치하지 않습니다. 문서를 다른 컴퓨터에서 제공해야 하는 경우에만 [선택 MCP 연결](docs/mcp.md)을 참고합니다.

기존 설치를 업데이트하려면 [소스 갱신·sync·연결 지침 재등록](docs/installation.md#4-업데이트와-sync)을 따릅니다.

## 파일과 읽기 흐름

```text
에이전트의 WSL 또는 Linux 사용자 홈: ~/.ai-workflow/
├── source/                       원본 Git clone과 관리 도구
└── runtime/
    ├── active.json               새 작업의 커밋과 스냅샷 위치
    ├── sync-status.json          마지막 원격 확인 결과·시각
    ├── snapshots/<커밋>/         고정 버전의 문서 묶음
    └── connectors/               Codex·Cursor의 짧은 연결 지침
```

Codex는 WSL 파일을, Cursor는 Remote SSH로 연결한 Linux 개발 PC의 파일을 직접 읽습니다. 상태 확인 → 고정 커밋의 `workflow/entry.md` → 해당 역할의 필수 문서 → 프로젝트 작업지시서 순서입니다. 전체 규칙을 자동 첨부하는 방식은 아닙니다.

| 저장소 위치 | 내용 |
|---|---|
| `workflow/entry.md` | 역할별 읽기 목록·버전 고정의 진입점 |
| `workflow/` | 공통·모델·기록·품질과 역할별 운영 규칙 원본 |
| `docs/installation.md` | 실행 환경별 공통 설치·도구 연결·확인·sync |
| `docs/mcp.md` | 문서와 작업 환경을 분리할 때의 선택 연결 |
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

[유지보수 안내](docs/maintenance.md)는 문서·스크립트 검사와 실제 앱의 지침 로딩·모델 전환 검증을 구분합니다. 모델의 기준 버전·추론 강도는 [모델 배정표](workflow/models.md)를 따르며 현재 환경의 가용성은 배정 시 확인합니다.
