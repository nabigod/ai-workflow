# SSH 작업에서 WSL의 워크플로우 읽기

개정: 2026-11-10

이 문서는 **원격 SSH 서버에서 Cursor를 사용할 때만** 필요합니다. 먼저 PC의 [WSL 설치와 Cursor 연결](installation.md)을 마칩니다. WSL 로컬 프로젝트만 사용하면 여기의 추가 설정은 건너뜁니다.

워크플로우 source/runtime과 동기화는 PC의 WSL 한 곳에 둡니다. 서버에는 레포·Python·워크플로우 도구 대신 **MCP URL·인증 토큰 설정**만 등록합니다. 프로젝트 코드와 `.ai-work/` 기록은 기존 서버에 둡니다.

```text
PC의 WSL: runtime → 읽기 전용 HTTP MCP
                           ↑ SSH 터널
원격 서버: Cursor → http://127.0.0.1:8765/mcp
```

아래 명령은 모두 **PC의 같은 WSL 배포판**에서 실행합니다. 새 터미널에서는 설치 안내의 `workflow_source`·`workflow_state` 변수를 다시 지정합니다.

## 1. WSL에서 MCP 실행

공통 설치의 `prepare-mcp`가 만든 토큰·설정을 사용합니다. 다음 명령을 실행하고 터미널을 열어 둡니다.

```bash
python3 "$workflow_source/scripts/workflow_mcp.py" --state-dir "$workflow_state" --transport http
```

PC의 WSL `127.0.0.1:8765`에서 인증된 읽기 요청만 받습니다. `Ctrl+C`로 종료하며 자동 시작 서비스는 설치하지 않습니다.

## 2. WSL에서 SSH 터널 연결

**WSL의 다른 터미널**에서 실제 SSH 호스트·별칭을 지정합니다. 이 명령은 WSL의 SSH 설정과 키를 사용합니다.

```bash
workflow_ssh_host="my-server"
ssh -NT -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -R 127.0.0.1:8765:127.0.0.1:8765 "$workflow_ssh_host"
```

서버의 loopback 요청이 PC의 WSL MCP로 전달됩니다. 이 터미널도 열어 둡니다. 서버별로 터널 하나를 연결하고, 같은 서버의 여러 Cursor 창은 기존 터널을 공유합니다. 서버가 SSH 포트 전달을 허용해야 하며 포트 충돌·정책 오류가 나면 연결부터 해결합니다. 이 구성에는 Windows와 WSL 사이의 포트 전달이 필요 없습니다.

## 3. SSH 작업 창에 MCP 등록

Cursor로 해당 서버의 코드 폴더를 엽니다. PC의 WSL에서 다음 파일을 열어 **`mcpServers.ai-workflow` 항목만** 그 SSH 창의 사용자 전역 MCP 설정에 병합합니다.

```bash
cat "$workflow_state/connectors/cursor-mcp-http.json"
```

원격 설정은 일반적으로 해당 서버 사용자의 `~/.cursor/mcp.json`입니다. 설정 파일 전체를 덮어쓰지 말고 기존 항목을 보존합니다. 이 조각에는 인증 토큰이 있으므로 출력은 채팅·공개 로그·Git에 공유하지 않습니다. User Rules는 공통 설치에서 등록한 **동일한 `cursor-mcp.md` 지침**을 사용합니다.

SSH 창의 MCP 목록에 `ai-workflow`가 보이면 새 대화에서 [공통 연결 확인](installation.md#3-연결-확인)을 수행합니다. 로컬 MCP 등록이 원격 창에도 자동 전달된다고 가정하지 않습니다. 원격 창에는 WSL의 Python을 실행하는 stdio 설정 대신 HTTP 설정을 사용합니다.

## 동작과 문제 확인

| 도구 | 역할 |
|---|---|
| `get_workflow_status()` | active·sync-status 본문과 호스트 경로, 이번 관측 시각을 반환. manifest도 검증하며 entry 본문은 아직 읽지 않음 |
| `read_workflow_document(commit, path)` | 고정 커밋의 Markdown 원문, 논리 URI, 호스트 경로, 읽기 시각과 SHA-256 반환 |

status에서 커밋을 고정한 뒤 `workflow/entry.md`를 읽고 그 역할의 필수 문서만 같은 커밋으로 요청합니다. 상대 링크 `common.md`는 `workflow/common.md`입니다. 없는 고정 커밋을 최신으로 대체하지 않습니다. 원격 프로젝트의 작업지시서는 기존 파일 읽기 도구로 읽습니다.

- MCP가 안 보임: **그 SSH 창**의 설정·활성 상태·MCP 로그를 확인합니다.
- 연결 거부·시간 초과: WSL의 HTTP 프로세스와 해당 서버의 SSH 터널을 확인합니다.
- 401: 생성한 HTTP 설정과 WSL `runtime/mcp-token`이 일치하는지 확인합니다. 토큰은 재실행해도 유지됩니다.
- 포트 충돌: 기존 터널을 재사용하거나 다른 원격 포트와 그에 맞는 MCP URL을 함께 지정합니다. 기본 안내의 포트는 8765입니다.

규칙 갱신은 PC의 WSL에서 [기존 sync 명령](installation.md#4-갱신과-기존-작업)으로 수행합니다. 새 작업만 새 커밋을 선택하며 기존 작업은 고정 사본을 계속 읽습니다. MCP 읽기 시각은 원격 Git 확인 시각이 아닙니다. 동기화·명령 실행·쓰기 도구는 제공하지 않으며 `workflow/`·`docs/`의 Markdown만 읽습니다. 절대 경로·상위 경로·심볼릭 링크는 거부합니다. SHA-256은 읽은 본문의 식별값이고 스냅샷 전체 검증은 sync가 담당합니다.

HTTP MCP는 loopback과 SSH 터널 안에서 사용하고 인터넷에 직접 노출하지 않습니다. 토큰·생성 설정·백업은 Unix 권한 0600으로 생성합니다. 설정을 되돌릴 때는 백업을 검토해 `ai-workflow` 항목만 복원·제거하고 다른 MCP는 보존합니다.

자동 시험은 실제 stdio·loopback HTTP 통신, 인증·경로 제한·버전 고정·설정 보존을 검사합니다. 실제 Cursor의 지침 로딩·SSH 터널·모델 전환은 사용 PC에서 별도 확인합니다. [Cursor MCP 설정](https://cursor.com/docs/mcp)과 [MCP 전송 규격](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports)을 사용하며, HTTP는 JSON 응답의 stateless Streamable HTTP입니다.
