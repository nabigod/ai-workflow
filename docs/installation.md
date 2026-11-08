# PC별 설치와 갱신

설치는 **공통 파일 준비 → 사용하는 도구 연결 → 새 대화에서 연결 확인** 순서입니다. 공통 준비만으로 Codex나 Cursor 설정이 바뀌지는 않습니다. Codex는 Python 명령으로 전역 지침을 갱신하고, Cursor는 생성한 연결 지침을 User Rules에 붙여넣습니다.

## 1. 실행 환경과 저장 위치 정하기

Git과 Python 3.10 이상, 해당 환경에서의 GitHub SSH 접근이 필요합니다. 이 명령은 Git·Python·SSH 키를 자동 설치하지 않습니다. 다른 PC에서 받으려면 배포할 파일이 원격 `main`에 커밋·푸시되어 있어야 합니다.

Windows와 WSL은 Python·Git·홈 디렉토리·경로 표기가 다릅니다. 실제 에이전트가 파일을 읽고 명령을 실행하는 환경을 선택하세요. 같은 물리 PC라도 접근 환경이 다르면 각각 준비할 수 있습니다. WSL에서 생성한 `/home/...` 경로가 Windows나 클라우드 에이전트에서도 그대로 통한다고 가정하지 않습니다.

기본 배치는 다음과 같습니다. 소스와 runtime은 제품 프로젝트 밖에 둡니다.

```text
~/.ai-workflow/                    ← workflow_root: 설치 자료의 기준 폴더
├── source/                       ← workflow_source: Git clone
│   ├── workflow/                 규칙 원본
│   ├── docs/                     사용자 설명
│   └── scripts/workflow.py       동기화·연결 지침 생성·Codex 설치 도구
└── runtime/                      ← workflow_state: 생성되는 배포 자료
    ├── active.json               사용할 커밋·스냅샷·entry.md 절대 경로
    ├── sync-status.json          마지막 원격 확인 결과와 시각
    ├── snapshots/<커밋>/         해당 커밋의 전체 파일 묶음
    └── connectors/
        ├── codex.md              Codex 전역 지침에 넣을 내용
        └── cursor.md             Cursor User Rules에 넣을 내용
```

Windows 예시의 기준 폴더는 `$env:USERPROFILE\.ai-workflow`, Bash 예시에서는 `$HOME/.ai-workflow`입니다. `workflow_root`는 clone 폴더 자체가 아니라 `source`와 `runtime`을 묶는 기본 경로입니다. 기존 clone을 다른 위치에서 사용해도 되고 runtime도 별도로 지정할 수 있습니다.

이 경로 변수들은 현재 터미널에서 명령을 편하게 쓰기 위한 셸 변수입니다. `export`나 운영체제의 영구 환경변수 등록은 필요 없습니다. 에이전트는 변수 이름 대신 생성된 연결 지침의 절대 경로를 사용합니다. 새 터미널에서는 관리 명령을 실행하기 전에 같은 경로로 변수를 다시 지정하세요.

## 2. 공통 파일 준비

아래에서 사용하는 환경 하나를 선택합니다. 각 명령이 실패하면 다음 단계로 넘어가지 말고 오류를 확인하세요.

| 명령 | 수행 내용 | 아직 하지 않는 일 |
|---|---|---|
| `git clone` | 원격 저장소를 source에 복제 | runtime 생성·도구 연결 |
| `sync` | 원격 main을 fetch하고 고정 사본·active.json·확인 결과 생성 | source 작업 파일 갱신·도구 설정 변경 |
| `render` | 해당 PC의 절대 경로를 넣어 두 connectors 파일 생성 | Codex·Cursor 설정 등록 |

### Windows PowerShell

**처음 설치할 때** 다음을 실행합니다.

```powershell
$workflowRoot = Join-Path $env:USERPROFILE '.ai-workflow'
$workflowSource = Join-Path $workflowRoot 'source'
$workflowState = Join-Path $workflowRoot 'runtime'
git clone git@github.com:nabigod/ai-workflow.git $workflowSource
if ($LASTEXITCODE -ne 0) { throw 'clone failed' }
```

**이미 clone했다면** 위 clone 명령을 실행하지 않고 경로만 지정합니다. 아래 source 예시는 실제 clone 위치로 바꾸세요.

```powershell
$workflowRoot = Join-Path $env:USERPROFILE '.ai-workflow'
$workflowSource = 'C:\work\ai-workflow'
$workflowState = Join-Path $workflowRoot 'runtime'
```

어느 경우든 이어서 공통으로 실행합니다.

```powershell
py -3 "$workflowSource/scripts/workflow.py" sync --repo $workflowSource --state-dir $workflowState
if ($LASTEXITCODE -ne 0) { throw 'sync failed' }
py -3 "$workflowSource/scripts/workflow.py" render --state-dir $workflowState --shell powershell
if ($LASTEXITCODE -ne 0) { throw 'render failed' }
```

### Bash / WSL / Linux / macOS

**처음 설치할 때** 다음을 실행합니다.

```bash
workflow_root="$HOME/.ai-workflow"
workflow_source="$workflow_root/source"
workflow_state="$workflow_root/runtime"
git clone git@github.com:nabigod/ai-workflow.git "$workflow_source"
```

**이미 clone했다면** 위 clone 명령을 실행하지 않고 경로만 지정합니다. 예를 들어 기존 WSL 저장소를 그대로 사용하려면 다음과 같습니다.

```bash
workflow_root="$HOME/.ai-workflow"
workflow_source="/home/nabi/work/ai-workflow"
workflow_state="$workflow_root/runtime"
```

어느 경우든 clone 성공과 경로를 확인한 뒤 이어서 실행합니다.

```bash
python3 "$workflow_source/scripts/workflow.py" sync --repo "$workflow_source" --state-dir "$workflow_state" &&
python3 "$workflow_source/scripts/workflow.py" render --state-dir "$workflow_state" --shell bash
```

명령의 파일명은 `workflow.py`이며 점 앞에 역슬래시를 넣지 않습니다. 위 예시에서는 홈 아래에 runtime이 생성되고, 기존 clone을 재사용하면 source 파일은 기존 위치에 남습니다.

### 생성되는 파일

`sync` 성공 시 `runtime/active.json`, `sync-status.json`, `snapshots/<커밋>/`이 생기고, `render` 성공 시 `runtime/connectors/codex.md`와 `cursor.md`가 생깁니다. render는 연결 지침을 화면에도 출력합니다. 이 단계가 끝나면 사용할 도구를 아래에서 연결합니다.

`active.json`은 문서 본문이 아니라 현재 선택한 커밋과 파일 위치를 담습니다. `remote_checked_at`은 그 시각에 원격을 확인했다는 뜻이며 계속 최신이라는 보장이 아닙니다. 실패한 sync는 기존 active.json을 유지하고 sync-status.json에 실패를 기록합니다. 스냅샷은 직접 수정하지 않으며 진행 중인 작업이 사용할 수 있어 과거 사본을 자동 삭제하지 않습니다.

## 3. 사용하는 도구 연결

Codex와 Cursor 모두 같은 runtime을 읽을 수 있는 환경이라면 공통 파일은 공유하고 연결만 각각 등록합니다. 두 도구에서 접근 가능한 경로가 다르면 각 환경에서 생성한 연결 지침을 사용하세요.

### Codex 연결

연결은 **`install-codex`가 전역 `AGENTS.md`에 내용을 직접 넣는 방식**입니다. 연결 지침을 검토한 뒤 앞 단계와 같은 터미널에서 해당 환경의 명령 하나를 실행합니다.

PowerShell:

```powershell
Get-Content -Raw "$workflowState/connectors/codex.md"
py -3 "$workflowSource/scripts/workflow.py" install-codex --state-dir $workflowState --shell powershell
```

Bash:

```bash
cat "$workflow_state/connectors/codex.md"
python3 "$workflow_source/scripts/workflow.py" install-codex --state-dir "$workflow_state" --shell bash
```

이 명령은 연결 지침을 다시 생성하고 다음 순서로 처리합니다.

1. 대상 설정 폴더를 `--codex-home` 지정값 → `CODEX_HOME` 환경변수 → Python 실행 환경의 사용자 홈 아래 `.codex` 순서로 선택합니다.
2. 그 폴더의 `AGENTS.md`에 워크플로우 연결 구역을 추가하거나 갱신합니다. 파일이 없으면 만듭니다.
3. 기존 파일을 변경할 경우 옆에 `AGENTS.md.bak-<고유값>`으로 백업하고, 연결 구역 밖의 사용자 지침은 보존합니다.
4. 성공하면 대상 `AGENTS.md` 경로를 출력합니다. 이미 같은 내용이면 다시 쓰거나 백업을 추가하지 않습니다.

출력된 경로는 설치 결과입니다. 사용자가 그 파일을 `runtime/connectors/codex.md`로 교체하는 추가 작업은 없습니다. 심볼릭 링크를 만드는 방식도 아니며 연결 지침의 내용을 복사해 넣습니다. 저장소 루트의 `source/AGENTS.md`는 저장소 유지보수 규칙이므로 전역 지침에 복사하지 않습니다.

**실제로 쓰는 Codex 설정 폴더인지 확인하세요.** WSL에서 실행하면 기본값은 WSL 홈의 `.codex`이며 Windows 앱의 설정 위치와 다를 수 있습니다. 필요한 경우 위 설치 명령에 `--codex-home "실제 설정 폴더의 절대 경로"`를 추가합니다. 해당 Codex에서 runtime 경로도 읽을 수 있어야 합니다.

기존 전체 phase-agent-workflow 본문, `AGENTS.override.md`, 심볼릭 링크인 `AGENTS.md` 등이 있으면 자동 설치를 중단합니다. 기존 파일을 검토·백업하고 충돌을 해소한 뒤 다시 설치하세요. 다른 사용자 규칙을 통째로 지우지 않습니다. Codex의 전역 지침과 override 적용은 [공식 안내](https://learn.chatgpt.com/docs/agent-configuration/agents-md)를 참고하세요. 실행 중인 대화의 지침은 이 명령으로 강제 교체되지 않습니다.

### Cursor 연결

Cursor에서는 **User Rules에 내용을 붙여넣는 단계가 Codex의 `install-codex`에 해당**합니다. `install-codex`를 실행할 필요가 없습니다.

1. 앞 단계에서 생성한 `runtime/connectors/cursor.md`를 엽니다. PowerShell에서는 `Get-Content -Raw "$workflowState/connectors/cursor.md"`, Bash에서는 `cat "$workflow_state/connectors/cursor.md"`로 내용을 볼 수 있습니다.
2. Cursor의 **Customize → Rules → User Rules**에 그 내용을 붙여넣습니다. 파일 경로만 붙이는 것이 아니라 파일 안의 연결 지침 전체를 넣습니다.
3. 기존 전체 워크플로우가 등록돼 있다면 백업 후 해당 부분을 새 연결 지침으로 교체하고 다른 사용자 규칙은 보존합니다.
4. 새 대화에서 아래의 첫 연결 확인을 수행합니다.

연결 지침에는 다음처럼 해당 PC의 실제 절대 경로가 들어갑니다. 아래 경로는 예시이므로 직접 복사하는 대신 자신의 PC에서 생성한 파일을 사용하세요.

```text
공통 배포 정보: /home/nabi/.ai-workflow/runtime/active.json
```

Cursor는 User Rules를 읽고 파일 읽기 도구로 이 경로에 접근합니다. active.json의 `entry` 값이 가리키는 `snapshots/<커밋>/workflow/entry.md`를 읽은 다음, 그 문서에 지정된 역할별 규칙을 읽습니다. 문서 전체가 자동 첨부되거나 User Rules 등록만으로 파일 접근 권한이 추가되는 것은 아닙니다.

User Rules는 여러 프로젝트에 적용되며 참조 파일은 에이전트가 필요할 때 읽습니다. 이 스크립트는 Cursor 설정을 직접 편집하지 않습니다. 다른 PC의 연결 지침을 그대로 붙여넣으면 경로가 맞지 않을 수 있으므로 각 PC에서 render한 내용을 등록하세요. [Cursor 규칙 공식 안내](https://cursor.com/docs/rules)

## 첫 연결 확인

**4단계: 설치를 끝낸 Codex와 Cursor 각각의 새 대화**에서 다음을 요청합니다. 파일 생성 성공과 실제 도구의 파일 접근 성공은 구분해서 확인합니다.

```text
프로젝트를 실행하지 말고 연결 확인만 해 줘.
워크플로우 active.json과 sync-status.json의 실제 경로,
선택된 커밋, entry.md 접근 여부와 실행 역할의 필수 문서 목록을 알려 줘.
원격 확인 시각과 실제 파일 읽기 여부를 구분해 줘.
```

다음 연결이 실제로 확인되면 설치가 끝난 것입니다.

```text
Codex 전역 AGENTS.md 또는 Cursor User Rules
    → active.json과 sync-status.json
    → snapshots/<커밋>/workflow/entry.md
    → 현재 역할의 필수 규칙
```

경로를 읽지 못하면 연결 지침의 절대 경로, 선택한 Windows/WSL 환경, 파일 접근 권한을 확인합니다. 클라우드·원격 에이전트는 PC의 경로에 자동 접근하지 못하므로 그 환경에도 문서 묶음과 연결 지침이 필요합니다. 전역 지침이 모든 하위 에이전트에 자동 전달된다고 가정하지 않으며, 부모가 고정 커밋·문서 경로·역할·필수 입력을 전달하고 접근을 확인합니다. [Cursor 서브에이전트 안내](https://cursor.com/docs/subagents)

연결 확인 후 [사용자 가이드](user-guide.md)의 단계별 요청을 사용합니다. 일반 프로젝트마다 공통 규칙을 복사하지 않으며 프로젝트 기록은 해당 프로젝트의 `.ai-work/`에 저장합니다.

## 새 작업과 기존 작업

새 작업 전에 원격을 확인하려면 같은 경로 변수를 지정하고 다음 중 환경에 맞는 명령을 실행합니다. 새 터미널이면 2단계의 변수 지정 부분만 다시 실행하며 clone을 반복하지 않습니다.

```bash
python3 "$workflow_source/scripts/workflow.py" sync --repo "$workflow_source" --state-dir "$workflow_state"
```

```powershell
py -3 "$workflowSource/scripts/workflow.py" sync --repo $workflowSource --state-dir $workflowState
```

`sync`는 fetch 후 원격 커밋에서 사본을 만들며 source의 작업 파일은 pull하지 않습니다. 미커밋 수정이나 로컬에만 있는 커밋은 기본 원격 동기화로 배포되지 않습니다. 원격 main에 반영한 뒤 다른 PC에서 sync해야 합니다. 전역 연결 지침은 허용된 환경에서 새 작업의 담당자 한 명이 필요한 동기화를 수행하도록 안내하며, OS 상시 서비스나 앱 hook을 설치하지 않습니다.

| 상황 | 필요한 조치 |
|---|---|
| 규칙 문서만 개정 | 원격 main에 반영 후 sync. 연결 경로·템플릿이 같으면 User Rules 재복사나 Codex 재설치는 필요 없음 |
| 연결 템플릿·동기화 도구 개정 | source의 로컬 변경을 확인한 뒤 `git -C "$workflow_source" pull --ff-only`로 도구 갱신. PowerShell은 `$workflowSource` 사용. sync → render → 해당 도구 연결 단계를 다시 수행 |
| source/runtime 위치 변경 또는 다른 PC 설치 | 해당 위치에서 sync·render하고 연결 지침 다시 등록. 진행 중인 작업이 쓰는 기존 사본은 보존 |
| 새 작업·하위 에이전트 | 선택된 커밋·스냅샷 경로를 고정하고 하위 에이전트에도 동일 값 전달 |
| 기존 작업 재개 | 기존에 고정한 사본 유지. 새 개정 적용을 명시적으로 요청한 경우 영향 확인 후 전환 |

원격 접근에 실패하면 기존 사본과 마지막 확인 결과를 보고하며, 최신 버전이 필수이면 시작을 보류합니다. 명시적으로 `--offline`을 추가하면 source의 로컬 HEAD로 사본을 만들지만 원격 최신 여부는 확인하지 않습니다. `.sync-lock`이 남으면 owner.json의 프로세스·진행 여부를 먼저 확인하고 활동 중인 잠금은 지우지 않습니다.
