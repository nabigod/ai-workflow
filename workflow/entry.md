# 단계별 워크플로우 진입

개정: 2026-11-17 · 관리 구조 버전: `5`

단계별 프로젝트 요청에 적용한다. 규칙 검토·개정이나 인용된 태그는 프로젝트 실행 명령이 아니다. 수동 모드가 기본이며 `[총괄]`은 명시적으로 호출한다.

시작 시 커밋·스냅샷을 고정하고 재개·하위 담당자도 같은 버전을 사용한다. 진행 중 활성 포인터를 다시 따르지 않는다. 명시적 개정 적용 요청에는 변경 영향을 확인한다. 원격 확인 실패를 최신 확인 성공으로 보고하지 않는다.

아래에서 현재 역할과 환경 하나, 실제 발생한 조건만 선택해 원문을 읽는다. 링크를 재귀적으로 모두 따라가지 않는다. 동일 버전 본문이 현재 컨텍스트에 있으면 재독하지 않으며 새 담당자·컨텍스트 유실 시 필요한 원문을 다시 확보한다. 요약·파일 목록은 필수 본문을 대신하지 못한다. 원문 접근 실패 시 인계 또는 접근 복구를 요청한다.

## 역할별 필수 문서

| 역할 | 문서 |
|---|---|
| 계획 | [공통](common.md), [모델](models.md), [작업 기록](records-state.md), [TC·증빙](records-evidence.md), [계획](planning.md) |
| 실행 | [공통](common.md), [모델](models.md), [작업 기록](records-state.md), [TC·증빙](records-evidence.md), [실행](execution.md) |
| 통합 | [공통](common.md), [모델](models.md), [작업 기록](records-state.md), [TC·증빙](records-evidence.md), [통합](integration.md) |
| 총괄 | [공통](common.md), [모델](models.md), [작업 기록](records-state.md), [위임](delegation.md), [총괄](orchestration.md) |
| 사용자검증 | [공통](common.md), [모델](models.md), [TC·증빙](records-evidence.md), [사용자검증](user-validation.md) |
| 커밋목록 | [공통](common.md), [모델](models.md), [커밋목록](commit-list.md) |
| 상태 조회 | [공통](common.md), [조회](status.md) |

프로젝트 입력은 index → 대상 지시·최신 결과·판정·미제출 변경 → 필요한 원자료·증빙 순서다. 과거 이력은 실패 누계·현재 판단·변경 영향에 필요한 범위만 읽는다. 오래된 index보다 해당 버전의 원본 근거를 우선한다.

## 환경 프로필

모델 문서가 필요한 역할만 아래에서 하나를 추가한다. 연결 지침의 환경과 현재 클라이언트를 대조하고 기존 정보로 확인되면 재질문하지 않는다. 불명확하면 환경만 확인하며 다른 환경 원문을 탐색하지 않는다. 환경과 파일 접근 방식은 독립적이다.

| 환경 | 문서 |
|---|---|
| codex | [Codex 모델](models-codex.md) |
| cursor | [Cursor 모델](models-cursor.md) |

## 조건부 문서

조건은 중첩될 수 있다. 해당 조건이 발생하면 연결된 원문을 반드시 추가한다. 상태 조회의 TC 요청은 질문 대상 TC만 읽는다.

| 조건 ID | 적용 역할 | 시점 | 문서 |
|---|---|---|---|
| layout | 계획, 통합 | 관리 구조를 처음 생성할 때 | [구조](records-layout.md) |
| migration | 계획, 통합 | 사용자가 기존 구조 전환을 요청했을 때 | [구조](records-layout.md), [전환](migration.md) |
| quality | 계획, 실행, 통합 | 제작·설계·검증 기준을 정하거나 적용할 때 | [품질](quality.md) |
| code | 계획, 실행, 통합 | 코드를 설계·작성·검토할 때; quality도 적용 | [품질](quality.md), [코드 품질](quality-code.md) |
| rust | 계획, 실행, 통합 | Rust 작업; quality·code도 적용 | [품질](quality.md), [코드 품질](quality-code.md), [Rust 시험](quality-rust.md) |
| retry | 실행, 통합, 총괄 | 실패 후 재시도·상향 또는 누적 실패가 있는 작업 배정 전 | [재시도](models-retry.md) |
| codex-limit | 실행, 통합, 총괄 | Codex 2단계의 실제 사용량 제한 발생 | [대체](models-codex-limit.md) |
| delegation | 계획, 실행, 통합, 총괄 | 다른 담당자에 위임·인계할 때 | [위임](delegation.md) |
| automatic | 실행, 통합, 총괄 | 총괄 배정·충돌 보고/조정 | [충돌 조정](coordination.md) |
| revision | 통합 | REV 지시서 작성 | [계획](planning.md) |
| state-write | 사용자검증 | 작업 문서·상태·index 갱신 전 | [작업 기록](records-state.md) |
| tests | 전체 | TC 개수·내용·현황 조회 요청 | [TC·증빙](records-evidence.md) |
| mcp | 전체 | MCP로 원문에 접근할 때 | [MCP 읽기](access-mcp.md) |
| dashboard | 계획, 실행, 통합 | 현황판 제작·수정·검토 요청 | [현황판](dashboard.md) |

사용자 설명·설치 요청에만 [사용자 가이드](../docs/user-guide.md)·[설치 안내](../docs/installation.md)를 읽는다. 기존 작업의 구조가 다르다는 이유만으로 전체 전환을 시작하지 않는다.
