# PC별 설치와 갱신

필요한 도구는 Git과 Python 3.10 이상입니다. 비공개 저장소이면 해당 실행 환경에서 GitHub SSH 접근을 먼저 준비합니다. 이 저장소의 명령은 필요한 도구나 SSH 키를 자동 설치하지 않습니다.

소스 저장소와 런타임 사본은 제품 프로젝트 밖의 사용자 폴더에 둡니다. Windows와 WSL은 Python·Git·홈 디렉토리·경로 표기가 다르므로 실제 에이전트가 명령을 실행하는 환경에서 설치합니다. 같은 물리 PC라도 서로 다른 파일 접근 환경이라면 각각 설치할 수 있습니다.

## Windows PowerShell

```powershell
$workflowRoot = Join-Path $env:USERPROFILE '.ai-workflow'
$workflowSource = Join-Path $workflowRoot 'source'
$workflowState = Join-Path $workflowRoot 'runtime'
git clone git@github.com:nabigod/ai-workflow.git $workflowSource
if ($LASTEXITCODE -ne 0) { throw 'clone failed' }
py -3 "$workflowSource/scripts/workflow.py" sync --repo $workflowSource --state-dir $workflowState
if ($LASTEXITCODE -ne 0) { throw 'sync failed' }
py -3 "$workflowSource/scripts/workflow.py" render --state-dir $workflowState --shell powershell
```

이미 source 폴더가 있다면 clone을 반복하지 않습니다.

## Bash / WSL / Linux / macOS

```bash
workflow_root="$HOME/.ai-workflow"
workflow_source="$workflow_root/source"
workflow_state="$workflow_root/runtime"
git clone git@github.com:nabigod/ai-workflow.git "$workflow_source" &&
python3 "$workflow_source/scripts/workflow.py" sync --repo "$workflow_source" --state-dir "$workflow_state" &&
python3 "$workflow_source/scripts/workflow.py" render --state-dir "$workflow_state" --shell bash
```

이미 복제했다면 clone을 반복하지 않고 아래 동기화 명령부터 사용합니다. PowerShell용 경로를 WSL 지침에 그대로 넣지 않습니다.

## 생성되는 파일

```text
runtime/
  active.json                   새 작업에서 선택할 커밋·진입 절대 경로
  sync-status.json              마지막 확인 시각·성공/실패·원격 확인 여부
  snapshots/<commit>/           해당 커밋의 고정 파일 묶음
  connectors/codex.md            Codex 연결 지침
  connectors/cursor.md           Cursor User Rules 연결 지침
```

`remote_checked_at`은 그 시각에 원격을 확인했다는 뜻이며 계속 최신이라는 보장이 아닙니다. 실패한 sync는 active.json을 유지하고 sync-status.json에 실패를 기록합니다. 진입 파일을 읽기 전에 마지막 확인 결과를 함께 확인하세요. 스냅샷을 직접 수정하지 않으며, 실행 중인 작업이 참조할 수 있어 과거 사본을 자동 삭제하지 않습니다.

## Codex 연결

`render` 결과를 먼저 확인한 뒤 아래 명령으로 사용자 전역 AGENTS.md에 연결 구역을 설치할 수 있습니다.

```powershell
py -3 "$workflowSource/scripts/workflow.py" install-codex --state-dir $workflowState --shell powershell
```

```bash
python3 "$workflow_source/scripts/workflow.py" install-codex --state-dir "$workflow_state" --shell bash
```

기본 대상은 `CODEX_HOME` 또는 사용자 홈 아래 `.codex`입니다. `--codex-home`으로 명시할 수 있습니다. 기존 파일은 옆에 `AGENTS.md.bak-<고유값>`으로 보존하고 표시된 연결 구역만 바꿉니다. 구역 밖 사용자 지침은 유지합니다. 기존 전체 phase-agent-workflow 본문이나 `AGENTS.override.md`가 있으면 중복·가림을 막기 위해 설치를 중단합니다. 해당 파일을 검토·백업한 뒤 오래된 워크플로우 본문만 제거하거나 적절한 진입 위치에 수동 반영하세요.

Codex의 전역 지침 경로와 override 우선순위는 [공식 안내](https://learn.chatgpt.com/docs/agent-configuration/agents-md)를 따릅니다. 설치 후 새 대화에서 실제 읽은 경로·커밋을 확인하세요. 이 설치 명령은 실행 중인 대화의 지침을 강제로 교체하지 않습니다.

## Cursor 연결

`runtime/connectors/cursor.md` 내용을 **Customize → Rules → User Rules**에 넣습니다. 기존 전체 워크플로우가 등록되어 있다면 백업 후 그 본문을 새 연결 지침으로 교체하며 다른 사용자 규칙은 보존합니다. 이 도구는 Cursor 계정 설정이나 비공개 설정 DB를 직접 편집하지 않습니다.

User Rules는 프로젝트 전역에 적용되며 참조 파일은 에이전트가 필요할 때 읽습니다. 서브에이전트에는 부모가 필수 정보를 전달해야 합니다. [Cursor 규칙](https://cursor.com/docs/rules), [서브에이전트](https://cursor.com/docs/subagents)

## 새 작업과 기존 작업

새 작업 시작 전 원격을 확인하려면 다음 명령을 실행합니다. 위 설치 예시의 변수가 없는 새 터미널에서는 먼저 해당 경로 변수들을 다시 지정하세요.

```bash
python3 "$workflow_source/scripts/workflow.py" sync --repo "$workflow_source" --state-dir "$workflow_state"
```

```powershell
py -3 "$workflowSource/scripts/workflow.py" sync --repo $workflowSource --state-dir $workflowState
```

전역 연결 지침은 허용된 환경에서 새 작업의 담당자 한 명이 이 동기화를 수행하도록 안내합니다. 서브에이전트마다 sync하지 않습니다. `sync`는 fetch만 하므로 source checkout의 미커밋 변경을 배포하지 않고 로컬 파일도 변경하지 않습니다. 별도 유지보수 목적의 `git pull`과 구분합니다.

- 새 작업: 동기화 결과의 커밋과 스냅샷 절대 경로를 작업 기록에 한 번 남깁니다. 그 안의 `workflow/entry.md`를 읽습니다.
- 하위 에이전트: 같은 커밋·경로, 역할과 필수 입력을 전달받고 접근을 확인합니다. 활성 포인터에서 임의로 다른 버전을 고르지 않습니다.
- 기존 작업 재개: 기록된 사본을 사용합니다. 새 개정 적용을 명시적으로 요청하면 변경 영향을 확인한 뒤 전환합니다.
- 연결 지침이나 동기화 도구 자체가 개정된 경우: source의 로컬 변경을 확인한 뒤 `git pull --ff-only`로 도구를 갱신하고 render·연결 지침 설치를 다시 수행합니다. 실행 중인 담당자의 사본은 유지합니다.
- 원격 접근 실패: 기존 사본과 마지막 확인 결과를 보고합니다. 최신이 필수이면 보류합니다. 명시적으로 `--offline`을 사용하면 source의 로컬 HEAD를 배포하며 원격 최신 여부는 확인하지 않습니다.
- `.sync-lock`이 남으면 owner.json의 프로세스·진행 여부를 먼저 확인합니다. 활동 중인 갱신의 잠금을 지우지 않습니다.

## 첫 연결 확인

Codex와 Cursor 각각의 새 대화에서 다음처럼 요청합니다.

```text
프로젝트를 실행하지 말고 연결 확인만 해 줘.
워크플로우 active.json과 sync-status.json의 실제 경로,
선택된 커밋, entry.md 접근 여부와 실행 역할의 필수 문서 목록을 알려 줘.
원격 확인 시각과 실제 파일 읽기 여부를 구분해 줘.
```

클라우드·원격 에이전트는 PC의 경로에 자동 접근하지 못합니다. 그 환경에도 문서 묶음과 연결 지침을 배포하고 같은 커밋을 전달해야 합니다. 전역 지침이 자동으로 모든 하위 에이전트에 전달된다고 가정하지 않습니다.
