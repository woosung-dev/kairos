# Mobile — Day 3 Mission (80% recording stability + 알림 반응성)

> gemini F3: 픽셀 완벽도 NOT 우선. **녹음 안정성 + 알림 반응성에 80% 시간**.

---

## 정체성

너는 **출장/이동 중 모바일 회의 녹음 사용자**. 한 손 조작 / 불안정 네트워크 / BG 상태 회의 지속.

---

## 환경
- FE :3000 (Chromium responsive emulation)
- 자격증명: `E2E_OWNER_*`
- 도구: Playwright MCP + `browser_resize` + Chrome DevTools throttle
- 산출물: `mobile/report.md`

---

## 안전 게이트 + Anti-Stall (동일)

---

## 임무 (60-90분, 80% 핵심 + 20% viewport)

### 핵심 (80%, 50-70분)

#### SCN-MOB-RECORD-01 한 손 녹음 시작 (15분)
- `browser_resize 375 667` (iPhone SE)
- 회의 녹음 (Capture) 버튼 위치 + 한 손 도달
- 녹음 시작 → 마이크 권한 흐름 (Sprint 11 audio record)
- 권한 거부 시 fallback UI 명확?

#### SCN-MOB-RECORD-02 BG 업로드 지속 (15분)
- 회의 녹음 종료 → 업로드 시작 → 다른 탭/앱 전환 (browser_tabs)
- 다시 돌아왔을 때 status 정확? processing 끝났나?
- 의도적 페이지 reload 시 upload state 보존?

#### SCN-MOB-NAV BottomNav 터치 타겟 (10분)
- Sprint 22 OBN-04 collision fix 검증
- BottomNav 5개 버튼 ≥44pt (인접 영향)
- 스크린샷 + pixel measure

#### SCN-MOB-INBOX-NOTIF 알림 반응성 (10분)
- Inbox 새 항목 도착 시 UI 알림 (badge/toast)?
- 알림에서 항목으로 deep-link?

### 보조 (20%, 10-20분)

#### SCN-MOB-3G Network throttle (10분)
- Chrome DevTools "Slow 3G"
- 핵심 페이지 (dashboard, inbox, meeting detail) 로드 시간

#### SCN-MOB-VIEWPORT-01/02/03 (10분, 시각 점검 only)
- 375x667 (iPhone SE)
- 393x852 (iPhone 14)
- 412x892 (Pixel 6)
- 각 viewport 1 스크린샷 (dashboard 1컷씩) → 깨짐 있으면 mark, 없으면 PASS

---

## 산출물

`mobile/report.md`:
```markdown
# Mobile Day 3 — 모바일 사용자 보고서

## 80% 핵심 결과
- Recording stability: P/F + 막힘 지점
- BG 업로드 지속: P/F
- BottomNav 터치 타겟: P/F (≥44pt)
- 알림 반응성: P/F

## 20% 보조
- 3G load time
- 3 viewport 시각

## 신규 BL 후보
- ...

## 종료 검증
```

### 동시 갱신
- `evidence-matrix.md` Mobile 6행 결과 컬럼
