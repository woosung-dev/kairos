# Sprint 23 D3 회귀 — dismiss 후 list (is_processed=false) 가 해당 item 제외 verify
"""D3 dogfood fix 회귀 spec.

검증 흐름:
1. InboxItem 시드 (is_processed=False)
2. POST /inbox/{id}/dismiss → BE 가 is_processed=True set + commit
3. GET /inbox?is_processed=false → dismissed 항목 부재 verify

이전 사용자 보고 "처리한 항목 재진입 시 재노출" 의 본질 = FE 가 explicit
is_processed=false 미사용 → 모든 items fetch → 사용자 인지 혼란.
본 fix: FE useInbox(wid, { isProcessed: false }) 명시 + autoProcessed 그룹 제거.
본 spec: BE filter 가 정확히 동작하는지 회귀 검증.
"""
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


@pytest_asyncio.fixture
async def inbox_client(integration_session, auth_user):
    """Inbox API 테스트용 AsyncClient — get_current_user + get_async_session override."""
    from src.auth.dependencies import get_current_user
    from src.common.database import get_async_session
    from src.main import app

    app.dependency_overrides[get_current_user] = lambda: auth_user
    app.dependency_overrides[get_async_session] = lambda: integration_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def seed_inbox_items(integration_session, personal_ws):
    """3 InboxItem seed: 2 unprocessed + 1 already processed."""
    from src.inbox.models import InboxItem

    items = []
    for i in range(2):
        item = InboxItem(
            workspace_id=personal_ws.id,
            title=f"미처리 항목 {i + 1}",
            source_type="note",
            source_id=uuid.uuid4(),
            is_processed=False,
        )
        integration_session.add(item)
        items.append(item)

    processed = InboxItem(
        workspace_id=personal_ws.id,
        title="이미 처리된 항목",
        source_type="note",
        source_id=uuid.uuid4(),
        is_processed=True,
    )
    integration_session.add(processed)
    items.append(processed)

    await integration_session.flush()
    await integration_session.commit()
    return items


@pytest.mark.asyncio
async def test_dismiss_then_list_filtered_excludes_item(
    inbox_client, integration_session, personal_ws, seed_inbox_items
):
    """dismiss → list ?is_processed=false → dismissed 항목 부재 verify."""
    target = seed_inbox_items[0]  # 미처리 첫 번째 항목

    # 1. dismiss 호출
    dismiss_response = await inbox_client.post(
        f"/api/v1/workspaces/{personal_ws.id}/inbox/{target.id}/dismiss",
    )
    assert dismiss_response.status_code == 200, dismiss_response.text
    dismiss_body = dismiss_response.json()
    assert dismiss_body["isProcessed"] is True

    # 2. list with is_processed=false → dismissed item 부재
    list_response = await inbox_client.get(
        f"/api/v1/workspaces/{personal_ws.id}/inbox",
        params={"isProcessed": "false"},
    )
    assert list_response.status_code == 200, list_response.text
    list_body = list_response.json()
    item_ids = [item["id"] for item in list_body["items"]]
    assert str(target.id) not in item_ids, (
        f"dismissed item {target.id} 가 list (is_processed=false) 에 포함됨 — D3 regression"
    )

    # 모든 반환 항목이 isProcessed=false 인지 verify (BE filter 정확)
    assert all(item["isProcessed"] is False for item in list_body["items"]), (
        "list ?is_processed=false 가 processed item 도 반환 — BE filter 위반"
    )

    # 미처리 2건 중 dismissed 1건 제외 = 남은 1건
    unprocessed_in_response = sum(
        1 for item in list_body["items"] if item["title"].startswith("미처리")
    )
    assert unprocessed_in_response == 1


@pytest.mark.asyncio
async def test_list_without_filter_returns_all(
    inbox_client, personal_ws, seed_inbox_items
):
    """params 없이 list → 모든 items 반환 (filter 미적용 baseline 확인)."""
    response = await inbox_client.get(
        f"/api/v1/workspaces/{personal_ws.id}/inbox",
    )
    assert response.status_code == 200
    body = response.json()
    # 3 seed items 모두 반환 (filter X = baseline 동작 유지)
    assert len(body["items"]) >= 3
