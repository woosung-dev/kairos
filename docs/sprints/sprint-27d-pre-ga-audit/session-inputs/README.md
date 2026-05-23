# Session Inputs — 새 세션 복붙용 단일 메시지

이 디렉토리의 `.txt` 파일은 **새 CLI 세션 첫 메시지로 그대로 복붙** 할 수 있는 완성된 프롬프트.

| 파일 | CLI | 순서 | 용도 |
|------|-----|------|------|
| `agy.txt` | Antigravity CLI | 2nd | 결함 4건 fix + 검증 루프 + opus cross-check + DEFERRED 보강 |
| `codex.txt` | OpenAI Codex CLI | 3rd (마지막) | agy fix 회귀 가드 + adversarial + 3-세션 통합 + 최종 GO/NO-GO |

> opus (1st) 는 이미 완료 (commit `6d70eb2`, PR #108).

---

## 사용 절차

### 공통 (각 세션 시작 전)

```bash
cd /Users/woosung/project/agy-project/kairos
git fetch origin
git checkout sprint-27d/pre-ga-audit-prompts
git pull origin sprint-27d/pre-ga-audit-prompts

# 로컬 서버 기동 확인
curl -s -o /dev/null -w "FE: %{http_code} " http://localhost:3000/
curl -s -o /dev/null -w "BE: %{http_code}\n" http://localhost:8000/api/v1/health
# 둘 다 200 이어야 함. 아니면 백엔드/프론트 띄우기
```

### Step A — agy 세션 (Antigravity CLI)

1. Antigravity CLI 새 세션 시작
2. 첫 메시지: `cat docs/sprints/sprint-27d-pre-ga-audit/session-inputs/agy.txt` 출력 내용 **통째로 복붙**
3. 메시지에 포함된 `[GOAL ...]` 부분이 Stop hook 으로 작동하여 자동 끝까지 진행
4. 종료 시 agy 가 PR #108 에 push 완료. 종료 보고 받기.

### Step B — codex 세션 (OpenAI Codex CLI)

agy 세션 종료 후:

1. `git pull` 으로 agy 결과 fetch
2. OpenAI Codex CLI 새 세션 시작
3. 첫 메시지: `cat docs/sprints/sprint-27d-pre-ga-audit/session-inputs/codex.txt` 출력 내용 **통째로 복붙**
4. 메시지에 포함된 `[GOAL ...]` 부분이 Stop hook 으로 작동하여 자동 끝까지 진행
5. 종료 시 codex 가 PR #108 최종 업데이트 + 외부 5명 진입 GO/NO-GO 판정 보고

---

## 각 파일의 형식 (단일 메시지 구조)

```
너는 [CLI 이름] 자동 에이전트다. (페르소나)

[GOAL — Stop hook 자동 보장]
(goal condition 본문)

[환경]
(프로젝트 경로 / 브랜치 / 서버 / 계정 / 정책)

[opus(+ agy) 결과 요약]
(이전 세션 결과 + 결함 list + 산출물 위치)

[Step 0 ~ Step 5]
(각 단계 상세 실행 명령 + 검증 + 산출물 경로)

[도구]
(사용 가능 도구 list)

[종료 보고]
(보고 형식)

[시작 신호]
("opus 산출물 read 후 Step 0 부터" 등)
```

각 파일이 **self-contained** — 다른 파일 참조 없이 그대로 복붙 가능.

---

## 진입 시 주의

- **GOAL condition** 은 메시지 본문 안에 명시되어 있어, CLI 가 자동으로 Stop hook 으로 등록.
- 만약 CLI 가 `/goal` slash command 를 별도 지원하면, 사용자가 메시지 본문 앞에 `/goal <condition>` 한 줄 추가하면 더 명확.
- 세션 종료 직전 사용자에게 종료 보고가 옴 → 다음 세션 진입 결정.
- agy 세션이 fix 를 끝까지 못 한 경우 (예: pytest 실패), codex 세션은 fix 완료 여부를 확인 후 진입.

---

## 결함 prefix 컨벤션

| 세션 | prefix |
|------|--------|
| opus | `BUG-S27d-*` (1~7 발견) |
| agy | `BUG-S27d-AGY-*` (신규 발견 시) |
| codex | `BUG-S27d-CODEX-*` (신규 발견 시) |

→ 3 세션 모두 끝나면 `final-integrated-report.md` 에 모든 결함 종합.
