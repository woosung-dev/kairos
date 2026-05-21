<!-- upload 도메인 — R2 presigned URL + 프록시 업로드 + 입력 검증 -->

# upload CONTEXT

> 상위: `/backend/CONTEXT.md` → `/CONTEXT-MAP.md`.

---

## 1. 책임

- Cloudflare R2 presigned upload URL 발급 (`POST /presigned-url`)
- 브라우저 CORS 우회 프록시 업로드 (`POST /file`) — FE → BE → R2
- 입력 검증 (Sprint 25 T-SEC-3, BUG-SENTINEL-003): size · MIME · 확장자 · content signature 4계층

## 2. 비책임

- 업로드 파일 DB record 생성 (downstream meetings/notes 도메인이 fileKey 받아 처리)
- R2 객체 cleanup / TTL (Sprint 15 R-CRON 별도)
- 다운스트림 STT/AI 파이프라인 (`services/ai_processing.py`)

---

## 3. 엔티티 (소유)

- 없음 — stateless 도메인. R2 fileKey 만 반환, DB persist 는 downstream.

---

## 4. 의존 (in/out)

| 방향 | 대상 | 레벨 |
|---|---|---|
| in  | FE `useUpload` 훅 | L0 (HTTP) |
| in  | meetings/notes/attachments 후속 register flow | L0 (FE 흐름) |
| out | `common/r2.py` R2Service (presigned URL + putObject) | L1 |
| out | `auth/rbac.require_member` (workspace 멤버 보장) | L1 |

---

## 5. 핵심 불변식

- 모든 upload endpoint 는 `require_member` 통과 (workspace 권한)
- size > `MAX_UPLOAD_BYTES` (기본 500MB) → 413
- declared MIME ∉ `ALLOWED_UPLOAD_MIMES` 화이트리스트 → 415
- 확장자가 declared MIME family 와 불일치 → 415 (위장 차단)
- content head 512byte signature 가 declared MIME 와 contradicts → 415
- text/* 형식 + non-UTF8 bytes → 415
- 0 byte → 400

## 6. 노출 엔드포인트 (prefix `/api/v1/workspaces/{workspace_id}/upload`)

- `POST /presigned-url` — R2 presigned PUT URL + fileKey (3600s 만료)
- `POST /file` — 프록시 업로드 (FE → BE → R2), T-SEC-3 검증 적용. fileKey 반환.

---

## 7. 모듈 구조 (Sprint 25 T-SEC-3 expansion)

```
backend/src/upload/
├── router.py        # HTTP wire + UploadValidator Depends
├── service.py       # UploadValidator (AsyncSession 없음 — stateless)
├── exceptions.py    # 5 도메인 예외 (Empty/TooLarge/UnsupportedMime/MimeExtMismatch/ContentMismatch)
└── dependencies.py  # get_upload_validator() Depends 조립
```

settings (env override 가능):
- `MAX_UPLOAD_BYTES` (default 500_000_000 = 500MB)
- `ALLOWED_UPLOAD_MIMES` (default "audio/mpeg,audio/mp4,audio/x-m4a,audio/wav,audio/x-wav,audio/webm,audio/ogg,application/pdf,text/plain,text/markdown")

## 8. 검증 매트릭스

`backend/tests/upload/test_upload_validation.py` 6 case:

| 시나리오 | declared MIME | 확장자 | content | 결과 |
|---|---|---|---|---|
| 빈 파일 | audio/mp4 | .m4a | b"" | **400** |
| size 초과 | audio/mp4 | .m4a | > MAX_UPLOAD_BYTES | **413** |
| 비허용 MIME | image/png | .png | PNG magic | **415** |
| 확장자 불일치 | audio/mp4 | .png | valid MP4 | **415** |
| signature 위장 | audio/mp4 | .m4a | PDF magic | **415** |
| 정상 audio | audio/mp4 | .m4a | ftyp 헤더 | **201** |
