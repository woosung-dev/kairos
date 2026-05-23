# 외부 dogfooder 5명 1:1 미팅 walkthrough (12분)

> Sprint 27b GA dogfooding sprint. ADR-024 종료 기준 = 5명 중 3명+ 2주 활성 + 1명+ 지불 의사. founder 본인 1:1 진행 sheet.

---

## 사전 준비 (미팅 전 5분, founder 단독)

| 체크 | 항목 |
|---|---|
| ☐ | Clerk Production 인스턴스 활성화 — `pk_live_*` / `sk_live_*` GCP+Vercel 갱신 완료 |
| ☐ | Svix webhook URL 등록 — `https://kairos-api-imrsiyibaa-du.a.run.app/api/v1/users/sync` |
| ☐ | dogfooder 이름 + 회사 + 도메인 1줄 사전 인지 (어떤 회의를 자주 하는지) |
| ☐ | Zoom/Meet 화면 공유 가능 환경 (브라우저 1 + Kairos 1 + Slack 1) |
| ☐ | 12분 타이머 (스마트폰) — 정량 진행 강제, 만나면 추가 토크 시간은 별도 |

---

## 0:00 ~ 5:00 — 계정 생성 + 첫 회의 업로드 (5분)

### 0:00 — 컨텍스트 60초 (founder)

"Kairos 는 회의 / 노트 / 자료를 AI 가 distillation 해서 RAG 인사이트로 꺼내주는 세컨드 브레인입니다. 오늘 12분 동안 첫 회의 1건만 같이 업로드해보고, 2주 동안 그쪽 회의로 직접 써보시는 게 본 미팅 목적이에요. 끝에 5분만 솔직한 피드백 받겠습니다."

### 1:00 — Clerk 가입 (사용자 직접)

- `https://kairos-zeta-ebon.vercel.app/sign-up` 화면 공유
- Google OAuth 또는 이메일 가입 — Clerk dashboard 의 `user.created` event 가 Svix webhook 으로 sync_user endpoint 호출 → BE User row 생성 (verify: founder admin tab 에서 row 확인)
- **자동 lazy seed**: 첫 인증 요청 시 personal workspace `{이름}의 개인 Kairos` 자동 생성 (`uq_workspaces_owner_personal` partial unique index, race-safe)

**예상 시간**: 90초. 초과 시 founder 가 직접 가입 화면 driver.

### 2:30 — 첫 회의 업로드 (사용자 직접)

- 우상단 "회의 업로드" 버튼 → 사용자 본인 mp3/m4a 1건 (5분 이내 짧은 회의 권장)
- 파일 선택 → 자동 R2 업로드 + 백그라운드 Whisper transcription + pyannote diarization
- "처리 중 (1~2분)" 상태 카드 표시

**Founder 청취 포인트**:
- 업로드 버튼 위치 즉시 찾는지 (안 찾으면 OBN-02 카피 개선 필요)
- 파일 선택 흐름 (drag-and-drop vs picker) 어느 쪽 시도하는지

---

## 5:00 ~ 10:00 — Inbox + Memory + Action (5분)

### 5:00 — Distillation 결과 확인 (1분)

- 처리 완료 (2~3분 후) → 회의 상세 페이지 자동 이동
- Gemini 3.1-flash-lite 결과: 요약 / action item / 키워드 / 화자 별 발화 시간
- **확인 포인트**: 사용자가 "내가 말한 것 vs 상대방이 말한 것" 구분되는지 알아보는지

### 6:30 — Inbox 자동 분류 (1분 30초)

- 좌측 사이드바 "Inbox" 진입 — 회의가 어느 프로젝트에 속할지 confidence 점수와 함께 제안
- 사용자가 직접 "확인" 또는 "다른 프로젝트로" 클릭 → ProjectLink N:M 생성
- **확인 포인트**: confidence 임계값 (0.9 default) 가 너무 보수적인지 적극적인지 (이 회의가 자동 분류됐는지, 아니면 manual 였는지)

### 8:00 — Memory promotion 시연 (1분)

- 회의 요약 중 "이 결정은 영구 보관" 단추 → MemoryItem 으로 promote (ADR-016 복제 + tombstone 패턴, 5 도메인 source 보존)
- distilled JSON 의 atomic_notes 1줄을 직접 promote 해서 보여줘야 함

### 9:00 — Recall (RAG) 시연 (1분)

- 우상단 검색 → "지난 회의에서 X 결정 어떻게 됐지?" 한국어 자연어 query
- pgvector HNSW halfvec 검색 + citation 링크 (원 회의 시점으로 jump)
- **확인 포인트**: 사용자가 본인 회의 도메인 단어 (예: "릴리즈 일정", "팀 OKR") 로 query 하는지

---

## 10:00 ~ 12:00 — 솔직한 피드백 + 지불 의사 청취 (2분)

### 10:00 — 단답 3 질문 (60초)

1. **"오늘 본 것 중에 본인 회의에 바로 쓰고 싶은 기능 1개는?"**
2. **"본인이 이걸 안 쓸 가장 큰 이유는?"** (시간 / 가격 / 정확도 / 보안 / 다른 것)
3. **"이 도구가 본인 시간 1시간/주 절감해 준다면, 월 얼마까지 낼 의사가 있나요?"**
   - 직접 가격 questionnaire — "$10/월? $30/월? $50/월?" 톤다운 가능
   - 거부 시: "지불 0원, 무료여야 함" / "내 회사 사주면 가능" / "조건부 (X 기능 추가 시)" 식으로 분류

### 11:00 — 2주 재사용 약속 (60초)

- "다음 2주 동안 회의 5건 + recall 3회 이상 써보시면 Day 14 후 다시 미팅 5분만 부탁드립니다."
- **Founder 측 제안**: 미팅 후 1시간 내 founder 가 personal Slack/이메일 으로 "오늘 12분 walkthrough 감사합니다 + 첫 회의 업로드 링크 + 2주 미팅 일정 잡기 캘린더 링크" 전송.

---

## 측정 표 (5명 row, founder 본인 채움)

| # | 이름 | 회사/도메인 | 가입일 | Day 7 활성 (capture 5+ / recall 3+) | Day 14 활성 | 지불 의사 (월 KRW) | 비고 |
|---|---|---|---|---|---|---|---|
| 1 | _____ | _____ | _____ | ☐ / ☐ | ☐ / ☐ | _____ | _____ |
| 2 | _____ | _____ | _____ | ☐ / ☐ | ☐ / ☐ | _____ | _____ |
| 3 | _____ | _____ | _____ | ☐ / ☐ | ☐ / ☐ | _____ | _____ |
| 4 | _____ | _____ | _____ | ☐ / ☐ | ☐ / ☐ | _____ | _____ |
| 5 | _____ | _____ | _____ | ☐ / ☐ | ☐ / ☐ | _____ | _____ |

### 활성 정의 (ADR-024)

- **capture 5+**: MemoryEvent.type='capture' (회의 업로드 / 노트 / 자료) ≥ 5건 / 14일
- **recall 3+**: MemoryEvent.type='recall' (RAG query) ≥ 3건 / 14일
- **둘 다 충족 = 활성** (3 도구 codex 권고 임계값)

### Day 14 분기 (ADR-024 §"회수 옵션")

| 결과 | Sprint 28 결정 |
|---|---|
| 3+ 활성 + 1+ 지불 의사 | paid customer onboarding (ADR-025 pricing 신설) |
| 1~2 활성 | onboarding UX 개선 + 재시도 |
| 0 활성 | PRD v3.1 office-hours retrofit (product pivot) |

---

## 사용자 액션 의존 체크

| 진입 차단 항목 | 진입 신호 |
|---|---|
| Clerk Production 발급 | dashboard 의 production mode toggle ON 확인 |
| Svix webhook 등록 | dashboard webhooks 에 `https://<api>/api/v1/users/sync` 목록에 보임 |
| GCP/Vercel 환경변수 | `CLERK_SECRET_KEY` / `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` / `CLERK_WEBHOOK_SECRET` 갱신 deploy 완료 |
| 5명 모집 | Sprint 15 R8 outreach 80 채널 응답 + 일정 잡힘 |

---

## 부록 A — 측정 SQL (Founder admin 직접 query)

Sprint 15 Stage 4 R7 metrics (`memory_events` 테이블) + Sprint 6 D-1 visibility
(personal workspace) 조합으로 5명 × 14일 측정 가능. dashboard page 신설 없이
PostgreSQL 직접 query 로 갈음 (Sprint 28 진입 분기 결정 시점).

### Day 7 활성 query

```sql
SELECT
  w.owner_id           AS dogfooder_user_id,
  u.email              AS email,
  COUNT(*) FILTER (WHERE e.event_type = 'capture') AS captures_7d,
  COUNT(*) FILTER (WHERE e.event_type = 'recall')  AS recalls_7d,
  COUNT(*) FILTER (WHERE e.event_type = 'promote') AS promotes_7d
FROM memory_events e
JOIN workspaces w ON e.workspace_id = w.id
JOIN users      u ON w.owner_id = u.id
WHERE w.type = 'personal'
  AND e.created_at > NOW() - INTERVAL '7 days'
  AND w.owner_id IN (<dogfooder_user_id_1>, <2>, <3>, <4>, <5>)
GROUP BY 1, 2
ORDER BY 1;
```

### Day 14 활성 + 임계 충족 분기

```sql
WITH metrics AS (
  SELECT
    w.owner_id AS uid,
    COUNT(*) FILTER (WHERE e.event_type = 'capture') AS cap,
    COUNT(*) FILTER (WHERE e.event_type = 'recall')  AS rec
  FROM memory_events e
  JOIN workspaces w ON e.workspace_id = w.id
  WHERE w.type = 'personal'
    AND e.created_at > NOW() - INTERVAL '14 days'
    AND w.owner_id IN (<5명 uid>)
  GROUP BY w.owner_id
)
SELECT
  uid,
  cap, rec,
  (cap >= 5 AND rec >= 3) AS is_active_14d
FROM metrics
ORDER BY is_active_14d DESC, cap DESC;
```

`is_active_14d = true` row 가 3건 이상이면 ADR-024 §"회수 옵션" 1번 (paid customer
onboarding) 분기 진입. 1~2건이면 onboarding UX 개선 + 재시도. 0건이면 product
pivot (PRD v3.1 office-hours).

### 신규 method 추가는 X

`backend/src/memory/repository.py:97 get_metrics_counts` 가 workspace 별
capture/recall/promote count 제공 (Sprint 15 C7). rolling window 필터는 SQL 직접
query 로 충분 — 본 sprint 에서는 admin dashboard page 신설 SKIP (Sprint 28 결정
시점에 5명 결과 보고 신설 여부 판단).

---

## 참조

- ADR-024 (`docs/adr/024-ga-readiness.md`) — GA readiness + 종료 기준 + 회수 옵션
- Sprint 27b plan (`docs/plans/active/sprint-27b-ga-launch.md`) — Wave 1~3
- Sprint 22 ADR-021 — Sentry 활성화 (외부 5명 운영 중 error 추적)
- Sprint 15 R7 metrics (`backend/src/memory/models.py:79 MemoryEvent`) — capture/recall/promote 이벤트 스키마
- Sprint 15 C7 (`backend/src/memory/repository.py:97 get_metrics_counts`) — workspace 별 count 함수
- memory `project_sprint15_stage4_done` — R8 outreach 80 채널
