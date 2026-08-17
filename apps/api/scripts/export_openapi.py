"""OpenAPI 계약 export → contracts/openapi/v1/openapi.json (ADR-027 D2).

사용:
    cd apps/api && uv run python -m scripts.export_openapi
    (루트에서는 `mise run openapi-export`)

CI:
    test.yml `contract-check` job 이 재생성 후 `git diff --exit-code` 로 drift 를 차단한다.

결정성:
    sort_keys=True + uv.lock 버전 핀 + .python-version(3.12) 고정.
    배열 순서(route/required/enum)는 코드 정의 순서에서 나오므로 커밋 단위로 안정적.
"""

import json
import os
import sys
from pathlib import Path

# src.main import 는 Settings 필수 필드 전부를 요구 (src/core/config.py).
# 로컬은 apps/api/.env 가 채우고, CI/신규 클론은 아래 fake 로 충족한다
# (test.yml backend-test job 의 fake env 블록과 동일 세트).
# 스키마 내용은 env "값"과 무관 — 출력 결정성에 영향 없음.
# 프로덕션의 openapi_url=None 게이팅(T-SEC-5)은 URL 노출만 막을 뿐
# in-process app.openapi() 호출과는 무관하다.
_FAKE_ENV = {
    "DATABASE_URL": "postgresql://fake:fake@localhost:5432/fake",
    "R2_ACCOUNT_ID": "fake",
    "R2_ACCESS_KEY_ID": "fake",
    "R2_SECRET_ACCESS_KEY": "fake",
    "R2_BUCKET_NAME": "fake",
    "GEMINI_API_KEY": "fake",
    "OPENAI_API_KEY": "fake",
}
for _k, _v in _FAKE_ENV.items():
    os.environ.setdefault(_k, _v)

from src.main import app  # noqa: E402 — env 주입 후 import 필수

# scripts → apps/api → apps → 레포 루트
OUT = Path(__file__).resolve().parents[3] / "contracts" / "openapi" / "v1" / "openapi.json"


def main() -> int:
    schema = app.openapi()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(schema, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"exported {OUT} ({len(schema.get('paths', {}))} paths)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
