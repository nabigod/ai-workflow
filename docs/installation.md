# WSL 설치와 갱신

개정: 2026-11-10

워크플로우는 **작업용 PC의 WSL2에 한 번 설치**합니다. 아래 명령은 모두 같은 WSL 배포판의 Bash에서 실행합니다. WSL에 Git·Python 3.10 이상과 GitHub SSH 접근이 준비되어 있어야 합니다. Codex·Cursor는 기존에 설치한 앱을 사용합니다.

순서는 **공통 설치 → 사용하는 도구 연결 → 새 대화에서 확인**입니다. SSH 서버에서 작업할 때만 [원격 연결](mcp.md)을 추가합니다. 이 안내는 원격 `master`의 배포본을 사용합니다.

## 1. 공통 설치

경로를 지정합니다. 기존 WSL clone이 있다면 `workflow_source`만 실제 위치로 바꾸고 clone 명령은 건너뜁니다. 새 터미널에서 관리 명령을 사용할 때도 이 변수부터 지정합니다.

```bash
workflow_source="$HOME/.ai-workflow/source"
workflow_state="$HOME/.ai-workflow/runtime"
```

**처음 설치할 때만** 저장소를 받습니다. clone이 성공한 뒤 다음 명령으로 넘어갑니다.

```bash
git clone --branch master git@github.com:nabigod/ai-workflow.git "$workflow_source"
```

고정 사본과 연결 지침을 만듭니다. 기존 clone은 먼저 아래 갱신 절차로 `master`의 도구를 받습니다.

```bash
python3 "$workflow_source/scripts/workflow.py" sync --repo "$workflow_source" --state-dir "$workflow_state" --branch master &&
python3 "$workflow_source/scripts/workflow.py" render --state-dir "$workflow_state" --shell bash
```

제품 프로젝트 밖의 WSL 홈에 다음 자료가 생깁니다. 변수는 현재 터미널용이며 영구 환경변수 등록은 필요 없습니다.

```text
~/.ai-workflow/
├── source/                       원본과 관리 도구의 Git clone
└── runtime/
    ├── active.json               선택한 커밋·스냅샷·entry 절대 경로
    ├── sync-status.json          마지막 원격 확인 결과와 시각
    ├── snapshots/<커밋>/         작업에 사용할 고정 사본
    └── connectors/               도구에 등록할 연결 지침·설정
```

`sync`는 원격을 fetch해 사본을 만들고 source 작업 파일은 변경하지 않습니다. 실패하면 기존 active를 유지하고 실패 결과를 기록합니다. `render`만으로 앱 설정이 바뀌지는 않으므로 이어서 사용하는 도구를 연결합니다.

### PowerShell 설치에서 옮기는 경우

위 순서로 WSL에 공통 자료를 준비한 뒤 아래 도구 연결을 다시 수행합니다. Windows의 active.json에는 Windows 절대 경로가 들어 있으므로 WSL에 그대로 복사하지 않습니다. 기존 작업이 Windows의 고정 사본을 참조할 수 있어 이전 runtime은 보존합니다. 새 대화의 연결 확인이 끝나면 새 작업부터 WSL 사본을 사용합니다.

## 2. 사용하는 도구 연결

### Codex 연결

Codex 앱에서 **Agent environment와 통합 터미널을 WSL로 설정한 뒤 앱을 재시작**합니다. 에이전트 환경과 터미널 설정은 별개입니다. [공식 Windows 앱 안내](https://learn.chatgpt.com/docs/windows/windows-app)

WSL에서 **그 Codex가 실제 사용하는 설정 폴더**에 연결 지침을 설치합니다. 다음은 Windows Codex 앱의 기본 설정 폴더 예시입니다. `swook`을 실제 Windows 사용자 폴더 이름으로 바꾸고 별도 설정 폴더를 사용한다면 그 위치를 지정합니다.

```bash
workflow_codex_home="/mnt/c/Users/swook/.codex"
python3 "$workflow_source/scripts/workflow.py" install-codex --state-dir "$workflow_state" --shell bash --codex-home "$workflow_codex_home"
```

WSL 안의 Codex CLI에 연결한다면 위 `workflow_codex_home`을 `${CODEX_HOME:-$HOME/.codex}`로 지정합니다. Windows 앱과 WSL CLI의 기본 설정 폴더는 다르지만 workflow source/runtime은 같은 WSL 사본을 사용합니다.

명령은 대상 `AGENTS.md`의 워크플로우 구역만 추가·갱신하고 기존 사용자 지침은 보존합니다. 변경 전 백업을 만들며 출력된 경로가 설치 결과입니다. 추가 파일 복사나 심볼릭 링크 생성은 필요 없습니다. `AGENTS.override.md`, 이전 전체 워크플로우나 심볼릭 링크 때문에 중단되면 기존 설정을 검토하고 충돌만 해소합니다. [전역 지침 탐색 공식 안내](https://learn.chatgpt.com/docs/agent-configuration/agents-md)

### Cursor 연결

Cursor에서 **같은 WSL 배포판의 프로젝트 폴더를 연 창**을 사용합니다. 상태 표시와 터미널의 `/home/...` 경로를 확인합니다. MCP 설정 편집에서 여는 사용자 설정도 WSL의 `~/.cursor/mcp.json`인지 대조합니다. 다른 위치가 열리면 먼저 창의 WSL 연결을 확인합니다. 폴더를 여는 것은 프로젝트 실행이 아닙니다.

WSL에서 MCP 연결 자료를 만들고 WSL용 Cursor 설정에 등록합니다.

```bash
python3 "$workflow_source/scripts/workflow.py" prepare-mcp --state-dir "$workflow_state" &&
python3 "$workflow_source/scripts/workflow.py" install-cursor-mcp --state-dir "$workflow_state" --transport stdio
```

`~/.cursor/mcp.json`의 다른 MCP 항목은 보존하고 변경 전 백업합니다. 설치가 성공하면 연결 지침을 표시합니다.

```bash
cat "$workflow_state/connectors/cursor-mcp.md"
```

Cursor **Customize → Rules → User Rules**에서 기존 워크플로우 부분을 표시된 지침 전체로 교체합니다. 다른 사용자 규칙은 보존합니다. MCP 목록에서 `ai-workflow`와 두 읽기 도구가 보이는지 확인합니다. User Rules는 읽는 방법을 알려 주고 MCP는 실제 원문을 제공하므로 둘 다 필요합니다. [Cursor MCP 공식 안내](https://cursor.com/docs/mcp)

WSL 작업에서는 Cursor가 MCP 프로세스를 관리하므로 HTTP 서버나 터널을 별도로 켤 필요가 없습니다. **SSH 서버 작업에만 [원격 연결](mcp.md)을 추가**합니다.

## 3. 연결 확인

각 도구의 **실제 작업 창에서 새 대화**를 열고 다음을 요청합니다. 지침 본문이나 경로를 질문에 붙이지 않아야 자동 로딩 여부를 확인할 수 있습니다.

```text
프로젝트를 실행하지 말고 연결 확인만 해 줘.
자동으로 전달받은 지침에 ‘단계별 워크플로우 연결’이 있는지 알려 줘.
없으면 없다고 보고하고 임의로 설치 경로를 찾아 읽지 마.
있으면 지침의 방식으로 상태와 선택한 커밋의 entry.md 본문을 읽어 줘.
실제로 사용한 파일 읽기 또는 MCP 도구, 두 JSON의 호스트 경로,
고정 커밋·스냅샷 식별자와 실행 역할의 필수 문서 목록을 알려 줘.
필수 문서 목록 확인과 본문 읽기를 구분하고,
기록된 원격 확인 시각과 이번 실제 읽기 시각도 구분해 줘.
원격 동기화·프로젝트 실행·파일 변경은 하지 마.
```

자동 지침이 있고 두 JSON과 entry 본문을 읽었다면 연결이 확인된 것입니다. 이 확인은 현재 원격 최신 여부나 실제 모델 전환을 검증하지 않습니다. 읽기 실패는 실제 오류와 함께 보고하고 다른 환경의 경로로 임의 대체하지 않습니다.

## 4. 갱신과 기존 작업

새 터미널이면 1절의 경로 변수를 지정합니다. **도구나 연결 지침을 갱신할 때**는 로컬 수정 여부를 확인하고 `master`의 소스를 받습니다.

```bash
git -C "$workflow_source" status --short
git -C "$workflow_source" switch master &&
git -C "$workflow_source" pull --ff-only origin master
```

로컬 수정과 충돌하면 덮어쓰지 말고 해당 수정을 먼저 보존합니다. source를 받은 뒤 **규칙 사본을 갱신**합니다.

```bash
python3 "$workflow_source/scripts/workflow.py" sync --repo "$workflow_source" --state-dir "$workflow_state" --branch master
```

규칙 본문만 바뀌면 sync로 끝납니다. 연결 템플릿·설치 도구·경로가 바뀌면 2절의 도구 연결도 다시 수행합니다. SSH용 MCP 도구 코드를 갱신했으면 실행 중인 HTTP 프로세스도 재시작합니다.

새 작업은 새 active의 커밋을 선택하고 진행 중인 작업·하위 에이전트는 기존 고정 커밋을 유지합니다. 스냅샷을 직접 수정하거나 참조 중인 과거 사본을 삭제하지 않습니다. sync 실패 시 기존 사본을 최신이라고 부르지 않으며 최신 확인이 필수이면 시작을 보류합니다. `--offline`은 로컬 HEAD를 사용하고 원격 확인을 생략하는 명시적 선택입니다. 남은 `.sync-lock`은 owner.json의 프로세스·진행 여부부터 확인합니다.

설치가 끝나면 [사용자 가이드](user-guide.md)의 단계별 요청을 사용합니다.
