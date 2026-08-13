import { beforeEach, describe, expect, it } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { RagSources } from "../rag-sources";
import { SearchScope } from "../search-scope";
import { useRagStore } from "../../store";
import type { RagSource } from "../../types";

const EXTERNAL_DOCUMENT_SOURCE: RagSource = {
  id: "chunk-id",
  sourceId: "document-id",
  text: "문서 스니펫",
  source: "외부 회의록",
  sourceType: "external_document",
  date: "2026-07-31",
  score: 0.9,
  freshness: "recent",
};

beforeEach(() => {
  useRagStore.setState({ searchFilter: {} });
});

describe("external_document RAG seam", () => {
  it("인용을 한국어 유형 라벨로 렌더한다", () => {
    render(<RagSources sources={[EXTERNAL_DOCUMENT_SOURCE]} />);

    fireEvent.click(screen.getByTestId("rag-sources"));

    expect(screen.getByText("외부 문서")).toBeInTheDocument();
    expect(screen.queryByText("external_document")).not.toBeInTheDocument();
  });

  it("검색 유형 드롭다운에서 외부 문서를 선택한다", () => {
    render(<SearchScope />);

    const sourceTypeSelect = screen.getAllByRole("combobox")[1];
    fireEvent.change(sourceTypeSelect, {
      target: { value: "external_document" },
    });

    expect(useRagStore.getState().searchFilter.sourceType).toBe(
      "external_document",
    );
  });
});
