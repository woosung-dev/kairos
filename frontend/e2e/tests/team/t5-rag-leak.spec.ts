// T5: RAG private 누수 0 — member 의 실 SSE 검색에 private(MAGENTA) chunk·answer 부재, public(CYAN) 은 검색됨
// timeRange="1m"(sseAsk 기본)로 시맨틱 캐시 skip → 매 호출 fresh vector search → visibility 필터 실제 관통.
import { test, expect } from "../../fixtures/team";
import { TOKEN_PRIVATE, TOKEN_PUBLIC } from "../../team-helpers";

test.describe("T5 RAG private 누수 격리", () => {
  test("member RAG ask: private MAGENTA 부재 + public CYAN 포함", async ({
    memberPage,
    sseAsk,
    ensureMemberBaseline,
  }) => {
    test.setTimeout(90_000); // 실 Gemini SSE 2회

    await ensureMemberBaseline();

    // member 가 private 내용을 직접 질의 → visibility 필터로 제외돼야 함 (chunk·answer 모두)
    const priv = await sseAsk(memberPage, {
      question: `${TOKEN_PRIVATE} 비밀 기밀 내용 요약해줘`,
      projectId: null,
    });
    // 결정적 oracle = search_results chunk (질문이 토큰을 echo 하므로 answer 텍스트는 신뢰 불가).
    expect(priv.cached, "timeRange 로 캐시 skip — fresh 검색이어야 mutation 관측 가능").toBe(false);
    expect(
      priv.chunks.some((c) => c.text.includes(TOKEN_PRIVATE)),
      "member 검색 결과(search_results)에 private chunk 없음 — 필터 제거 시 RED",
    ).toBe(false);

    // 대조군: public 내용 질의 → 검색됨 (필터가 전부 막은 게 아님 + parseSse 정상 작동 증명)
    const pub = await sseAsk(memberPage, {
      question: `${TOKEN_PUBLIC} 공개 프로젝트 내용`,
      projectId: null,
    });
    expect(
      pub.chunks.some((c) => c.text.includes(TOKEN_PUBLIC)),
      "member 는 public 토큰 chunk 를 검색할 수 있음",
    ).toBe(true);
  });
});
