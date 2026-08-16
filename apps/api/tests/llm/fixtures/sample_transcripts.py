# Sprint 24 Wave 2 Phase B Post-Swap Delta 측정용 5 시나리오 fixture (T-2)
"""Phase B Gemini swap (gemini-2.5-flash → gemini-3.1-flash-lite, commit 003908a)
품질 회귀 검증을 위한 5 시나리오 입력 데이터.

- DELTA-1: RAG 답변 품질 (5 질문) — 동일 회의 인덱싱 후 다양한 질문 패턴
- DELTA-2: 회의 요약 길이/완전성 (5분 분량 sample transcript)
- DELTA-3: 액션 아이템 추출 precision/recall (5 sample + ground truth)
- DELTA-4: 한국어 처리 (이모지/방언/영한 혼용 3 sample)
- DELTA-5: Inbox 자동 분류 confidence (5 회의 + 5 노트, 기존 project 추천 포함)

ground_truth 일자는 2026년 기준 (Phase B 측정 시점).
"""
from __future__ import annotations

# ── DELTA-1: RAG 답변 품질 (5 질문) ──
# 동일 회의 컨텍스트 (DELTA_2_MEETING_TRANSCRIPT) 를 sources_text 로 사용.
DELTA_1_RAG_QUESTIONS: list[str] = [
    "이 회의에서 결정된 액션은?",          # Q1: action 추출
    "발표자가 누구였나?",                  # Q2: factoid
    "프로젝트 일정은 어떻게 변경되나?",    # Q3: synthesis
    "5월 안에 해야 할 일?",               # Q4: date filter
    "철수가 한 말 중 중요한 것?",         # Q5: entity + opinion (철수 미등장 → 정상 응답: "없음" 또는 "찾지 못함")
]

# ── DELTA-2: 회의 요약 (5분 분량 transcript) ──
# Q3 로드맵 회의 — 결정 2건 + 참여자 3명 + 일정 변경 + 리스크 명시
DELTA_2_MEETING_TRANSCRIPT: str = """김PM: 오늘 회의 주제는 Q3 로드맵입니다. 우선 인증 모듈 진행 상황부터 공유 부탁드립니다.
박개발: 인증 모듈은 7월 25일까지 완료할 예정입니다. 현재 OAuth 통합 90% 완료했고 SSO 테스트만 남았습니다.
김PM: 좋습니다. 일정대로 가능할까요?
박개발: 네, 8월 1일 QA 시작 가능합니다. 다만 외부 SSO 벤더 응답이 느려서 1주 buffer 가 필요할 수 있습니다.
이마케팅: 랜딩 페이지 리뉴얼은 8월 첫째주에 시작하겠습니다. 디자인 시안은 다음주 월요일까지 1차 공유 드릴게요.
김PM: 디자인 리뷰는 누가 담당하나요?
이마케팅: 박개발님과 저, 그리고 김PM님 셋이서 30분 sync 잡으면 좋겠습니다.
김PM: 다음주 화요일 오후 3시로 잡겠습니다.
박개발: 한 가지 리스크 — SSO 벤더 측 응답 지연이 1주 이상 이어지면 8월 QA 일정에 영향이 갑니다.
김PM: 알겠습니다. 그 경우 8월 8일로 QA 1주 연기로 잡겠습니다.
이마케팅: 마케팅 캠페인은 인증 GA 일정에 맞춰서 9월 1일로 잡았습니다. 변경되면 다시 sync 필요합니다.
김PM: 결정사항 정리하겠습니다. 첫째 인증 마감 7월 25일 박개발님, 둘째 랜딩 시작 8월 1일 이마케팅님, 셋째 SSO 지연 시 QA 8월 8일로 연기. 다음 회의는 다음주 화요일 오후 3시 디자인 리뷰입니다.
박개발: 확인했습니다.
이마케팅: 네, 진행하겠습니다.
"""

# ── DELTA-3: 액션 아이템 추출 precision/recall (5 sample) ──
# ground_truth 는 manual baseline. assignee / due_date / title 일치 여부로 precision/recall 계산.
# due_date 는 2026년 (Phase B 측정 시점). 연도 미명시 input → AI 가 2026 으로 추론해야 정답.
DELTA_3_ACTION_SAMPLES: list[dict] = [
    {
        "transcript": "박개발이 7월 25일까지 인증 모듈 완료해야 합니다. 이마케팅은 8월 첫째주 랜딩 페이지 시작 예정입니다.",
        "summary": "Q3 로드맵 회의 — 인증 7/25, 랜딩 8/1 결정.",
        "ground_truth": [
            {"assignee": "박개발", "due_date": "2026-07-25", "title_hint": "인증 모듈"},
            {"assignee": "이마케팅", "due_date": "2026-08-01", "title_hint": "랜딩"},
        ],
    },
    {
        "transcript": "디자인 시안은 다음주 월요일까지 이마케팅님이 1차 공유. 박개발님은 SSO 테스트 결과를 이번주 금요일까지 정리.",
        "summary": "디자인 시안 공유 + SSO 테스트 정리 액션.",
        "ground_truth": [
            {"assignee": "이마케팅", "due_date": None, "title_hint": "디자인 시안"},
            {"assignee": "박개발", "due_date": None, "title_hint": "SSO 테스트"},
        ],
    },
    {
        "transcript": "김PM이 9월 1일 마케팅 캠페인 launch 날짜 확정 공지. 박개발은 8월 8일 QA 대비 SSO 벤더 escalation 진행.",
        "summary": "9/1 캠페인 launch + 8/8 QA escalation.",
        "ground_truth": [
            {"assignee": "김PM", "due_date": "2026-09-01", "title_hint": "마케팅 캠페인"},
            {"assignee": "박개발", "due_date": "2026-08-08", "title_hint": "SSO"},
        ],
    },
    {
        "transcript": "회의록 정리는 김PM이 오늘 안에 슬랙 공유. 다음 회의는 다음주 화요일 오후 3시 디자인 리뷰.",
        "summary": "회의록 공유 + 다음 회의 일정.",
        "ground_truth": [
            {"assignee": "김PM", "due_date": None, "title_hint": "회의록"},
        ],
    },
    {
        "transcript": "이번주 안에 박개발님이 SSO 통합 테스트 완료. 이마케팅님은 랜딩 카피 초안을 7월 30일까지 작성.",
        "summary": "SSO 테스트 + 랜딩 카피 액션.",
        "ground_truth": [
            {"assignee": "박개발", "due_date": None, "title_hint": "SSO 통합 테스트"},
            {"assignee": "이마케팅", "due_date": "2026-07-30", "title_hint": "랜딩 카피"},
        ],
    },
]

# ── DELTA-4: 한국어 처리 (이모지/방언/영한 혼용 3 sample) ──
DELTA_4_KOREAN_SAMPLES: list[dict] = [
    {
        "label": "emoji_polite",
        "content": "어제 회의에서 김PM이 다음주까지 보고서 마무리할 거에요 🙂. 이마케팅님도 자료 준비 부탁드린다고 하셨어요!",
        "expects": "이모지 보존 + 존댓말 + 액션 추출 정상",
    },
    {
        "label": "dialect",
        "content": "회의 끝났습니데이. 박개발이 다음주 월요일에 코드 리뷰 마무리하기로 했심더. 그래도 일정은 미뤄질 수도 있다 카네요.",
        "expects": "방언 의미 보존 + 액션 정상 인식",
    },
    {
        "label": "korean_english_mix",
        "content": "오늘 미팅 cancel ㅠㅠ. 대신 박개발이 PR review 마무리하고, 이마케팅이 launch checklist 다시 보내준다고 했음.",
        "expects": "한영 혼용 + 한국어 이모티콘 보존 + 액션 추출",
    },
]

# ── DELTA-5: Inbox 자동 분류 confidence (5 회의 + 5 노트) ──
# existing_projects 는 동일 fixture 로 고정. 자동 분류 추천 일관성 + confidence 평균 비교.
DELTA_5_EXISTING_PROJECTS: list[dict] = [
    {"id": "11111111-1111-1111-1111-111111111111", "title": "Q3 인증 모듈", "status": "active"},
    {"id": "22222222-2222-2222-2222-222222222222", "title": "랜딩 페이지 리뉴얼", "status": "active"},
    {"id": "33333333-3333-3333-3333-333333333333", "title": "마케팅 9월 캠페인", "status": "planning"},
    {"id": "44444444-4444-4444-4444-444444444444", "title": "데이터 분석 인프라", "status": "active"},
    {"id": "55555555-5555-5555-5555-555555555555", "title": "고객 온보딩 개선", "status": "active"},
]

DELTA_5_INBOX_CLASSIFY: list[dict] = [
    # 5 회의
    {
        "kind": "meeting",
        "content": "OAuth 통합 90% 완료, SSO 테스트 남았음. 7월 25일 마감 목표. 박개발이 진행 중.",
        "expected_project_hint": "Q3 인증 모듈",
    },
    {
        "kind": "meeting",
        "content": "랜딩 페이지 시안 1차 공유. 디자인 리뷰는 박개발+이마케팅+김PM 30분 sync. 8월 1일 개발 시작 목표.",
        "expected_project_hint": "랜딩 페이지 리뉴얼",
    },
    {
        "kind": "meeting",
        "content": "9월 1일 마케팅 캠페인 launch 일정 확정. 카피 초안과 배너 디자인 분리해서 진행 결정.",
        "expected_project_hint": "마케팅 9월 캠페인",
    },
    {
        "kind": "meeting",
        "content": "데이터 웨어하우스 BigQuery 마이그레이션 일정 논의. 8월 중순 dry-run 후 9월 전환 결정.",
        "expected_project_hint": "데이터 분석 인프라",
    },
    {
        "kind": "meeting",
        "content": "신규 가입자 첫 1주차 retention 27% — 온보딩 체크리스트 개편 결정. UX 카피 점검과 튜토리얼 단축 진행.",
        "expected_project_hint": "고객 온보딩 개선",
    },
    # 5 노트
    {
        "kind": "note",
        "content": "SSO 벤더 응답 시간이 길어지고 있음. escalation 필요. 백업 IDP 도 검토.",
        "expected_project_hint": "Q3 인증 모듈",
    },
    {
        "kind": "note",
        "content": "랜딩 페이지 카피 톤 정리 — 신규 사용자 첫 화면에서 가치 전달 1줄 명확화 필요.",
        "expected_project_hint": "랜딩 페이지 리뉴얼",
    },
    {
        "kind": "note",
        "content": "9월 캠페인 채널 — 페이스북/구글애드/뉴스레터 3채널. 예산은 다음주 확정.",
        "expected_project_hint": "마케팅 9월 캠페인",
    },
    {
        "kind": "note",
        "content": "Looker 대시보드에서 daily active 사용자 추적용 view 신설 필요. SQL 초안 작성.",
        "expected_project_hint": "데이터 분석 인프라",
    },
    {
        "kind": "note",
        "content": "튜토리얼 3단계 완료율이 41% — 2단계로 줄이는 안 검토. 사용자 인터뷰 5명 일정 잡기.",
        "expected_project_hint": "고객 온보딩 개선",
    },
]
