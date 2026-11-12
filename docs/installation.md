# 실행 환경별 워크플로우 셋업

개정: 2026-11-12

아래 두 환경을 기준으로 합니다. **워크플로우는 에이전트가 파일을 읽고 명령을 실행하는 환경에 한 번 설치**하고 여러 프로젝트에서 공유합니다. 두 환경 모두 문서를 직접 읽으므로 MCP 설정은 필요하지 않습니다.

| 환경 | 요청하는 화면 | 파일 읽기·명령 실행 위치 | source / runtime 위치 |
|---|---|---|---|
| WSL 에이전트 + Windows | Windows Codex 앱 | 작업용 WSL2 배포판 | WSL의 원하는 경로 / WSL 사용자 홈 |
| Linux 에이전트 + Windows | Windows Cursor의 Remote SSH 창 | Linux 개발 PC | Linux의 원하는 경로 / Linux 사용자 홈 |

**WSL 에이전트 + Windows**에서는 WSL Bash, **Linux 에이전트 + Windows**에서는 Linux 개발 PC에 연결한 SSH 터미널에서 아래 공통 명령을 실행합니다. Git·Python 3.10 이상과 해당 환경의 GitHub SSH 접근이 준비되어 있어야 합니다. 배포 브랜치는 `main`입니다.

## 1. 공통 설치

사용할 WSL 또는 Linux 사용자 환경에서 **각각 한 번씩** 준비합니다. **원본 저장소는 원하는 위치에 clone하고, runtime은 사용자 홈에 따로 둡니다.** 두 경로를 함께 옮길 필요는 없습니다.

`workflow_source`를 해당 환경에서 읽고 쓸 수 있는 원하는 절대 경로로 바꿉니다. 아래 `/data/repos/ai-workflow`는 예시입니다. 기존 clone이 있다면 그 실제 위치를 지정하고 clone 명령은 건너뜁니다. `workflow_state`는 설치 후에도 같은 경로를 사용합니다. 새 터미널에서 관리 명령을 사용할 때도 이 변수부터 지정합니다.

```bash
workflow_source="/data/repos/ai-workflow"
workflow_state="$HOME/.ai-workflow/runtime"
```

runtime을 `~/.ai_workflow`에 두려면 처음 설치할 때 `workflow_state="$HOME/.ai_workflow"`로 지정해도 됩니다. 기존 안내의 `~/.ai-workflow/runtime`과는 다른 폴더이므로, 이미 설치했다면 기존 runtime 경로를 유지합니다. runtime에는 상태 JSON뿐 아니라 고정 사본과 연결 지침도 저장됩니다.

**처음 설치할 때만** 저장소를 받습니다. clone이 성공한 뒤 다음 명령으로 넘어갑니다.

```bash
git clone --branch main git@github.com:nabigod/ai-workflow.git "$workflow_source"
```

고정 사본과 연결 지침을 만듭니다. 기존 clone의 도구가 구버전이면 먼저 아래 갱신 절차로 `main`의 소스를 받습니다.

```bash
python3 "$workflow_source/scripts/workflow.py" sync --repo "$workflow_source" --state-dir "$workflow_state" --branch main &&
python3 "$workflow_source/scripts/workflow.py" render --state-dir "$workflow_state" --shell bash
```

원본과 runtime은 다음처럼 분리됩니다. 변수는 현재 터미널용이며 영구 환경변수 등록은 필요 없습니다.

```text
/data/repos/ai-workflow/           원하는 위치의 원본 Git clone과 관리 도구
~/.ai-workflow/runtime/            사용자 홈의 runtime (workflow_state)
├── active.json                   선택한 커밋·스냅샷·entry 절대 경로
├── sync-status.json              마지막 원격 확인 결과와 시각
├── snapshots/<커밋>/             작업에 사용할 고정 사본
└── connectors/
    ├── codex.md                  Windows Codex 전역 지침에 넣을 내용
    └── cursor.md                 Windows Cursor User Rules에 넣을 내용
```

`sync`는 원격을 fetch해 사본을 만들고 source 작업 파일은 변경하지 않습니다. 실패하면 기존 active를 유지하고 실패 결과를 기록합니다. `render`만으로 앱 설정이 바뀌지는 않으므로 이어서 해당 환경의 도구를 연결합니다.

WSL과 Linux 개발 PC는 경로가 다를 수 있으므로 각 환경에서 생성한 연결 지침을 사용합니다. Windows의 active.json이나 다른 환경의 연결 지침을 그대로 복사하지 않습니다. 이전 작업이 참조하는 runtime·고정 사본은 보존합니다.

## 2. 환경별 도구 연결

### WSL 에이전트 + Windows: Codex 연결

Codex 앱에서 **Agent environment와 통합 터미널을 WSL로 설정한 뒤 앱을 재시작**하고 해당 WSL의 프로젝트를 엽니다. 에이전트 환경과 터미널 설정은 별개입니다. [공식 Windows 앱 안내](https://learn.chatgpt.com/docs/windows/windows-app)

공통 설치를 수행한 **같은 WSL**에서 다음을 실행합니다. `swook`은 예시이므로 실제 Windows 사용자 폴더 이름으로 바꿉니다. 별도 Codex 설정 폴더를 사용한다면 그 실제 경로를 지정합니다.

```bash
workflow_codex_home="/mnt/c/Users/swook/.codex"
python3 "$workflow_source/scripts/workflow.py" install-codex --state-dir "$workflow_state" --shell bash --codex-home "$workflow_codex_home"
```

Windows Codex 앱의 기본 설정 폴더는 Windows 사용자 홈의 `.codex`입니다. WSL의 `~/.codex`를 앱의 설정 폴더라고 가정하지 않습니다. **워크플로우 원문은 WSL에 두고, 짧은 연결 지침만 앱의 실제 설정 폴더에 설치**하는 것입니다.

명령은 대상 `AGENTS.md`의 워크플로우 구역만 추가·갱신하고 기존 사용자 지침은 보존합니다. 변경 전 백업을 만들며 출력된 경로가 설치 결과입니다. 추가 파일 복사나 심볼릭 링크 생성은 필요 없습니다. `AGENTS.override.md`, 이전 전체 워크플로우나 심볼릭 링크 때문에 중단되면 기존 설정을 검토하고 충돌만 해소합니다. [전역 지침 탐색 공식 안내](https://learn.chatgpt.com/docs/agent-configuration/agents-md)

### Linux 에이전트 + Windows: Cursor 연결

Windows Cursor의 **Remote SSH로 모든 에이전트 작업을 수행할 Linux 개발 PC에 연결**하고 프로젝트 폴더를 엽니다. Windows에 파일만 마운트한 폴더를 여는 방식과 구분합니다. [Remote SSH 공식 안내](https://cursor.com/help/troubleshooting/network)

그 창의 터미널에서 실제 호스트와 프로젝트 경로를 확인합니다. **1절의 공통 설치도 이 Linux 사용자 환경에서 수행**합니다.

```bash
hostname
pwd
```

해당 Linux 개발 PC에서 생성한 연결 지침을 표시합니다.

```bash
cat "$workflow_state/connectors/cursor.md"
```

Windows Cursor의 **Customize → Rules → User Rules**에서 기존 워크플로우 부분을 표시된 지침 전체로 교체합니다. 다른 사용자 규칙은 보존합니다. 이 지침의 active.json 경로가 **에이전트가 작업하는 Linux 개발 PC의 실제 경로**인지 확인합니다. 파일 경로 한 줄만 붙이지 않고 생성된 연결 지침 전체를 등록합니다. [Cursor 규칙 공식 안내](https://cursor.com/docs/rules)

Cursor 설정을 등록하는 화면은 Windows에 있지만, 지침의 `/home/...` 경로는 해당 SSH 작업 창의 Linux 개발 PC에서 읽습니다. User Rules는 여러 프로젝트에 적용되므로 같은 개발 PC·사용자로 작업하는 창에서 사용합니다. Windows 로컬 창이나 다른 서버에서 같은 경로가 통한다고 가정하지 않습니다.

총괄과 하위 에이전트는 같은 개발 PC의 고정 사본을 읽습니다. 다른 testpc는 SSH 명령으로 빌드·테스트를 실행하거나 산출물을 마운트하는 대상으로 사용하고, 그곳에서 별도 에이전트를 실행하지 않는다면 워크플로우를 설치하지 않습니다.

### 기존 MCP 연결에서 옮기는 경우

Linux 개발 PC에 공통 자료를 준비하고 User Rules의 MCP 워크플로우 구역을 위 `cursor.md` 지침으로 교체합니다. 새 대화에서 아래 직접 읽기 확인이 끝나면, 기존 MCP 설정의 **`ai-workflow` 항목만** 비활성화하거나 백업 후 제거할 수 있습니다. 다른 MCP 설정과 이전 고정 사본은 보존합니다. 이 안내를 읽는 것만으로 실행 중인 서버·터널을 종료하거나 앱 설정을 변경하지 않습니다.

MCP는 문서와 에이전트가 서로 다른 환경에 있을 때의 [선택 연결](mcp.md)로 남깁니다. 위 두 기본 셋업에서는 사용하지 않습니다.

## 3. 연결 확인

**WSL 프로젝트를 연 Windows Codex** 또는 **Linux 개발 PC에 Remote SSH로 연결한 Windows Cursor**의 새 대화에서 다음을 요청합니다. 지침 본문이나 경로를 질문에 붙이지 않아야 자동 로딩 여부를 확인할 수 있습니다.

```text
프로젝트를 실행하지 말고 연결 확인만 해 줘.
자동으로 전달받은 지침에 ‘단계별 워크플로우 연결’이 있는지 알려 줘.
없으면 없다고 보고하고 임의로 설치 경로를 찾아 읽지 마.
있으면 지침의 파일 경로로 active.json·sync-status.json과
선택한 커밋의 entry.md 본문을 직접 읽어 줘. MCP는 사용하지 마.
이번 파일 읽기가 어느 환경에서 수행됐는지 확인 가능한 근거와 함께 알려 줘.
두 JSON의 실제 경로, 고정 커밋·스냅샷과 실행 역할의 필수 문서 목록을 보고해 줘.
필수 문서 목록 확인과 본문 읽기를 구분하고,
기록된 원격 확인 시각과 이번 실제 읽기 시각도 구분해 줘.
원격 동기화·프로젝트 실행·파일 변경은 하지 마.
```

자동 지침이 있고 두 JSON과 entry 본문을 직접 읽었다면 해당 환경의 연결이 확인된 것입니다. 이것은 현재 원격 최신 여부나 실제 모델 전환·하위 에이전트의 상속 설정 검증을 대신하지 않습니다.

파일 읽기가 실패하면 실제 오류를 확인합니다. WSL 에이전트 환경에서는 Codex의 WSL 설정·설정 폴더를, Linux 에이전트 환경에서는 SSH 호스트·사용자·Linux 경로를 대조합니다. 작업 공간 밖 읽기 승인이나 허용 경로가 필요한 경우에는 해당 runtime의 읽기 범위를 확인합니다. 다른 컴퓨터의 경로나 MCP로 임의 대체하지 않습니다.

## 4. 업데이트와 sync

### 소스 갱신 → sync → 연결 지침 재생성

기존 설치를 최신 배포본으로 업데이트할 때 아래 순서로 실행합니다. **WSL 에이전트 + Windows**에서는 WSL 터미널, **Linux 에이전트 + Windows**에서는 Linux 개발 PC의 SSH 터미널을 사용합니다. clone은 반복하지 않습니다.

새 터미널에서 `workflow_source`에 실제 clone 위치를, `workflow_state`에 기존 runtime 위치를 지정합니다. 아래 원본 경로는 예시이므로 설치할 때 선택한 경로로 바꿉니다.

```bash
workflow_source="/data/repos/ai-workflow"
workflow_state="$HOME/.ai-workflow/runtime"
git -C "$workflow_source" status --short
```

로컬 수정이 있으면 먼저 보존합니다. 이어서 아래 블록을 실행합니다. 명령이 실패하면 뒤 단계는 실행되지 않습니다.

```bash
git -C "$workflow_source" fetch origin &&
git -C "$workflow_source" switch main &&
git -C "$workflow_source" pull --ff-only origin main &&
python3 "$workflow_source/scripts/workflow.py" sync \
  --repo "$workflow_source" --state-dir "$workflow_state" --branch main &&
python3 "$workflow_source/scripts/workflow.py" render \
  --state-dir "$workflow_state" --shell bash
```

`pull`은 source의 도구·문서를 갱신하고, `sync`는 원격 `main`의 고정 사본과 active.json·확인 결과를 갱신합니다. `render`는 그 환경의 경로·동기화 브랜치가 들어간 연결 지침을 다시 만듭니다. sync 출력의 `commit`이 이번 선택 버전입니다. `render`만으로 앱에 이미 등록한 지침이 바뀌지는 않으므로 이어서 해당 환경의 연결을 갱신합니다.

sync의 기본 브랜치도 `main`이므로 `--branch`를 생략한 기존 명령도 같은 원격 브랜치를 확인합니다. 이전 `master` 설치는 위 fetch·switch·pull로 source를 `main`으로 전환합니다. sync 후 active.json의 `branch`와 재생성한 연결 지침의 동기화 명령이 모두 `main`인지 확인하고 아래 재등록을 수행합니다. 기존에 `main`을 사용한 설치는 그대로 이 절차를 따릅니다.

### WSL 에이전트 + Windows: Codex 지침 재등록

`swook`을 실제 Windows 사용자 폴더명으로 바꿉니다. 별도 설정 폴더를 쓰면 해당 경로를 지정합니다.

```bash
python3 "$workflow_source/scripts/workflow.py" install-codex \
  --state-dir "$workflow_state" --shell bash \
  --codex-home "/mnt/c/Users/swook/.codex"
```

기존 워크플로우 구역을 갱신하며 다른 사용자 지침은 보존합니다. 이미 같은 내용이면 다시 쓰거나 백업을 추가하지 않습니다.

### Linux 에이전트 + Windows: Cursor 지침 재등록

Linux 개발 PC에서 새 연결 지침을 표시합니다.

```bash
cat "$workflow_state/connectors/cursor.md"
```

출력 전체로 Windows Cursor **User Rules의 기존 워크플로우 구역만** 교체하고 다른 사용자 규칙은 보존합니다. 이전 MCP 지침이 있으면 이 직접 읽기 지침으로 교체합니다.

### 원본 clone 위치를 바꾸는 경우

기존 clone을 옮기거나 원하는 위치에 새로 clone한 뒤 `workflow_source`를 새 절대 경로로 지정합니다. 기존 clone의 로컬 수정·미추적 파일은 먼저 보존합니다. runtime은 기존 위치에 그대로 두고 다음을 실행합니다.

```bash
workflow_source="/새로운/경로/ai-workflow"
workflow_state="$HOME/.ai-workflow/runtime" # 기존에 사용하던 runtime 경로
python3 "$workflow_source/scripts/workflow.py" sync \
  --repo "$workflow_source" --state-dir "$workflow_state" --branch main &&
python3 "$workflow_source/scripts/workflow.py" render \
  --state-dir "$workflow_state" --shell bash
```

이어서 위의 환경별 지침 재등록을 수행합니다. Codex는 `install-codex`를 다시 실행하고, Cursor는 새 `cursor.md`로 기존 워크플로우 구역을 교체합니다. **변수만 바꾸면 이미 등록한 지침은 갱신되지 않습니다.** `sync`가 active.json의 원본 저장소 경로를 갱신하고, `render`와 재등록이 지침에 포함된 다음 동기화 명령까지 새 경로로 바꿉니다.

원본만 옮긴 경우 runtime과 기존 스냅샷은 이동할 필요가 없습니다. 기존에 `~/.ai_workflow` 등 다른 runtime을 사용했다면 위 `workflow_state`도 그 기존 경로로 지정합니다. 새 대화에서 아래 연결 확인을 마친 뒤 이전 clone의 정리 여부를 판단합니다.

### 적용 확인과 기존 작업

해당 환경의 **새 대화**에서 [연결 확인](#3-연결-확인)을 수행하고 실제 읽은 커밋을 sync 출력과 대조합니다. 문서 변경만으로 기존 대화의 지침이나 실제 선택 모델이 자동 전환되지는 않습니다. 모델 배정표가 바뀌었다면 [명령별 모델·추론 강도](user-guide.md#8-여러-대화와-모델-사용하기)도 확인해 앱에서 선택하거나 지원되는 위임 설정에 명시합니다.

규칙 본문만 갱신하고 경로·연결 지침이 그대로인 경우에는 `sync`만으로 새 사본을 선택할 수 있습니다. 소스 도구·연결 지침·모델 정책까지 포함된 배포본을 받을 때는 위 전체 흐름을 사용합니다. 여러 환경에서 같은 개정을 사용하려면 각각 sync한 뒤 커밋을 대조합니다.

진행 중인 작업·하위 에이전트는 기존 고정 커밋을 유지하고 새 작업부터 새 active를 선택합니다. 스냅샷을 직접 수정하거나 참조 중인 과거 사본을 삭제하지 않습니다. 원격 확인 실패를 최신 확인 성공으로 보고하지 않으며 최신 확인이 필수이면 시작을 보류합니다. `--offline`은 로컬 HEAD를 사용하고 원격 확인을 생략하는 명시적 선택입니다. 남은 `.sync-lock`은 owner.json의 프로세스·진행 여부부터 확인합니다.

Docker의 사내 Nexus 이미지 접근·DNS·프록시는 사용자 테스트 전까지 미확인입니다. 워크플로우 연결 확인과 별도로 다룹니다.

설치가 끝나면 [사용자 가이드](user-guide.md)의 단계별 요청을 사용합니다.
