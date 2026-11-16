# 개정과 배포 관리

배포 안내 개정: 2026-11-17. 기본 셋업은 WSL 에이전트 + Windows Codex, Linux 에이전트 + Windows Cursor입니다. 두 환경에서 문서를 직접 읽으며 [MCP](mcp.md)는 문서와 작업 환경이 분리된 경우에만 선택합니다. 기존 도구의 호환 기능과 프로젝트 관리 구조 버전 5는 유지합니다.

Cursor 1단계는 Claude Haiku 최신 버전·`high`로 개정했으며 2026-11-12 기준 버전은 사용자 지정 5.5입니다. 역할별 최초 단계·실패 2회 후 상향 1회·통합 수락 권한은 유지합니다. 업데이트 절차는 [sync 안내](installation.md#4-업데이트와-sync)를 따릅니다.

## 규칙의 원본

`workflow/`의 역할별 문서가 규칙의 원본입니다. 하나의 규칙을 여러 역할 문서에 복사하지 않고 필요한 공통 문서로 연결합니다. `entry.md`에는 읽기 조건과 핵심 경계만 둡니다. 사용자 가이드와 설치 설명을 일반 작업의 필수 입력으로 만들지 않습니다.

첫 분리는 2026-11-08 단일 워크플로우를 기준으로 수행했습니다. 번호 참조를 보존하되 대상 파일로 연결했으며, 이후 파일 내 규칙을 독립적으로 개정할 수 있습니다.

| 기존 위치 | 현재 원본 |
|---|---|
| 품질·코드·Rust | [분야별 기준](../workflow/quality.md), [코드](../workflow/quality-code.md), [Rust](../workflow/quality-rust.md) |
| 공통 경계·위임/비용 | [공통](../workflow/common.md), [위임](../workflow/delegation.md) |
| 구조·상태·TC/검증 | [초기 구조](../workflow/records-layout.md), [작업 기록](../workflow/records-state.md), [TC·증빙](../workflow/records-evidence.md) |
| 모델·환경·재시도 | [역할 단계](../workflow/models.md), [Codex](../workflow/models-codex.md) 또는 [Cursor](../workflow/models-cursor.md), [재시도](../workflow/models-retry.md) |
| 2절 구조 전환 | [migration.md](../workflow/migration.md) |
| 6·7·8절 | [planning.md](../workflow/planning.md), [execution.md](../workflow/execution.md), [integration.md](../workflow/integration.md) |
| 11·12절 | [orchestration.md](../workflow/orchestration.md), [dashboard.md](../workflow/dashboard.md) |
| 13·14절 | [user-validation.md](../workflow/user-validation.md), [commit-list.md](../workflow/commit-list.md) |

## 개정 순서

1. 변경할 규칙의 원본과 영향을 받는 역할·설치 흐름을 확인합니다.
2. 원본·사용자 설명·역할별 읽기 목록을 함께 갱신합니다. `manifest.json`과 변경 문서에 개정일을 기록합니다. 같은 날의 여러 개정은 Git 커밋으로 구분합니다. 프로젝트 layout_version은 실제 관리 구조를 바꿀 때만 올립니다.
3. 문서 검사와 필요한 스크립트 시험을 수행하고 변경 diff를 검토합니다.
4. 검토가 끝난 커밋을 `main`에 반영합니다. 초안 작업은 다른 브랜치에서 수행하고 미완성 규칙을 배포 브랜치에 먼저 반영하지 않습니다.
5. WSL·Linux 개발 PC에서 각각 `sync --branch main`으로 배포 커밋의 새 사본을 만듭니다. 진행 중인 작업은 기존 커밋을 계속 참조합니다.

배포 브랜치·sync 기본값·설치 예시는 모두 `main`으로 통일합니다. 과거 `master`의 변경은 이력을 보존해 main에 통합하며, 이후 새 배포는 main을 사용합니다. 기존 master 설치는 [업데이트 절차](installation.md#4-업데이트와-sync)에 따라 source·active의 브랜치를 main으로 전환하고 연결 지침을 재생성·재등록합니다. 진행 중인 작업의 고정 커밋은 자동 전환하지 않습니다.

원격 조회·동기화는 유지보수 checkout의 미커밋 파일을 변경하지 않습니다. 활성 사본은 Git commit 내용을 추출하므로 미커밋 수정은 배포되지 않습니다. 다른 브랜치를 테스트하려면 `sync --branch <이름>`과 별도 state-dir을 사용합니다.

## 되돌리기와 보존

잘못 배포한 규칙은 검토한 revert 커밋을 main에 반영하고 다시 sync합니다. 원격 이력을 강제로 덮어쓰지 않습니다. 실행 중인 작업에 즉시 적용해야 한다면 사용자에게 영향과 새 버전을 알리고 담당 인계 후 명시적으로 전환합니다.

`snapshots/<commit>`은 실행 입력이므로 직접 수정하지 않습니다. sync는 이미 존재하는 사본이 해당 커밋 내용과 다르면 덮어쓰지 않고 중단합니다. 이전 사본을 정리할 때는 참조 중인 대화·프로젝트가 없는지 확인합니다. Codex 연결 지침은 설치 시 생성한 백업으로 복원하거나 표시된 연결 구역만 제거할 수 있습니다.

MCP도 문서를 요청할 때 전체 커밋을 필수로 받으며 active 갱신 후에도 과거 사본을 그대로 제공합니다. MCP 자체는 동기화·원격 명령·파일 쓰기를 제공하지 않습니다. PC에서 sync하고 MCP 도구 코드가 바뀐 경우 HTTP 프로세스를 재시작합니다. `prepare-mcp`는 기존 배포 사본에도 새 도구의 MCP 연결 템플릿을 적용할 수 있지만 역할 문서 본문은 해당 고정 스냅샷에서만 읽습니다. 토큰·생성 설정·런타임은 저장소 밖에 보관하고 mcp.json 변경은 명시적 설치 명령으로만 수행합니다.

## 읽기 분량과 실제 검증

기록·인계 최적화의 기준은 [위임 규칙](../workflow/delegation.md)과 [작업 문서 갱신 규칙](../workflow/records-state.md)입니다. 원본 문서의 부분 수정과 짧은 인계를 우선하며 별도 AI용 사본을 추가하지 않습니다. 예시는 사용자 가이드·examples에 두어 필수 운영 입력을 불필요하게 늘리지 않습니다. 실제 도구의 전체 대화 상속 설정·부분 편집 지원을 확인하고, 문서 개정만으로 기능을 구현했다고 보고하지 않습니다.

`scripts/check_docs.py`는 README·AGENTS·workflow·docs·templates·Markdown 예시의 링크/앵커와 entry의 역할·환경별 읽기 목록을 검사하고 원문 문자 수를 출력합니다. 환경 프로필은 하나만 선택하며 조건부 원문은 아래처럼 명시해 별도로 측정합니다. 문자 수는 모델 토큰 수나 요금이 아닙니다. 실제 절감 효과는 사용 환경에서 입력·캐시·출력 토큰과 재작업 횟수를 비교해야 합니다.

서브에이전트가 부모 대화 전체를 상속하거나 전역 설정에 이전 전체 문서가 남아 있으면 분리만으로 입력이 줄지 않습니다. 연결 확인 시 읽은 파일과 실제로 전달된 지침을 함께 확인하세요. 스크립트 테스트는 배포·설치 파일 처리의 검증이며 Codex/Cursor의 실제 에이전트 모델 전환·전역 로딩 시험을 대신하지 않습니다.

```bash
python3 scripts/check_docs.py --environment cursor --role 실행 --condition rust --condition automatic --json
python3 scripts/check_docs.py --environment codex --role 계획 --condition migration
python3 scripts/check_docs.py --environment cursor --role 실행 --retained workflow/common.md --json
```

`--condition`은 entry의 조건 ID로 반복 지정합니다. 코드·Rust 조건에는 필요한 공통 품질 원문이 함께 포함됩니다. `--retained`는 같은 버전 본문이 **실제로 현재 컨텍스트에 남아 있는 경우에만** 지정하며 경로 목록만 알고 있거나 컨텍스트가 유실됐으면 사용하지 않습니다. 전체 묶음 문자 수와 이번에 읽을 문자 수를 구분하며 전역 지침·프로젝트 입력·인계/출력·추론은 집계 밖입니다. `--json`의 tokens는 미측정이면 null입니다. 숫자를 실제 세션 토큰 절감으로 보고하지 않습니다.

2026-11-17 분리는 프로젝트 저장 구조를 바꾸지 않으므로 layout_version은 5입니다. 연결 지침에는 환경 식별이 추가됐습니다. 배포 후 기존 설치의 연결 지침을 render하고 해당 도구에 재등록해야 하며, 진행 중인 작업은 기존 스냅샷을 유지합니다. 새 도구로 이전 템플릿을 render하는 호환 동작도 유지합니다.
