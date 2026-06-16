// RAG 답변 마크다운 렌더러 + 인라인 출처([N]) 보존 (Sprint 29 R4 rag-markdown).
// "use client" 미선언 — rag-chat(client)에서 import 되어 client 번들에 포함되므로 hook 사용 가능.
// 별도 모듈이라 RSC client-entry serialization 경고를 피하고 단위 테스트가 용이하다.
import {
  Children,
  cloneElement,
  isValidElement,
  useMemo,
  type ReactNode,
} from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import { CitationBadge } from "./citation-badge";

/** [1], [2] 등 인라인 출처 표기를 감지하여 CitationBadge로 변환 */
export function renderContentWithCitations(
  content: string,
  onCitationClick: (num: number) => void,
  activeCitation: number | null,
): ReactNode[] {
  const parts: ReactNode[] = [];
  const regex = /\[(\d+)\]/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null = null;

  while ((match = regex.exec(content)) !== null) {
    if (match.index > lastIndex) {
      parts.push(content.slice(lastIndex, match.index));
    }
    const citNum = parseInt(match[1], 10);
    parts.push(
      <CitationBadge
        key={`cit-${match.index}`}
        number={citNum}
        onClick={() => onCitationClick(citNum)}
        isActive={activeCitation === citNum}
      />,
    );
    lastIndex = regex.lastIndex;
  }

  if (lastIndex < content.length) {
    parts.push(content.slice(lastIndex));
  }

  return parts;
}

/** ReactMarkdown 이 렌더한 children 에서 [N] 을 CitationBadge 로 치환.
 *  Sprint 29 R4 (codex review): 중첩 인라인 노드(**굵게 [1]**, _기울임 [1]_ 등) 안의
 *  [N] 도 보존하도록 element children 으로 재귀한다. 문자열 leaf 에서만 치환. */
function injectCitations(
  children: ReactNode,
  onCitationClick: (num: number) => void,
  activeCitation: number | null,
): ReactNode {
  return Children.map(children, (child) => {
    if (typeof child === "string") {
      return renderContentWithCitations(child, onCitationClick, activeCitation);
    }
    if (isValidElement(child)) {
      const props = child.props as { children?: ReactNode };
      if (props.children !== undefined && props.children !== null) {
        return cloneElement(
          child,
          undefined,
          injectCitations(props.children, onCitationClick, activeCitation),
        );
      }
    }
    return child;
  });
}

/** RAG 답변 마크다운 렌더 — 이전엔 `###`/`**` 가 raw 노출됐다.
 *  react-markdown + remark-gfm 로 렌더하면서 텍스트를 담는 p/li/heading 의 children 에
 *  [N] CitationBadge 를 주입해 인라인 출처 클릭을 보존한다(회귀 방지). */
export function MarkdownMessage({
  content,
  onCitationClick,
  activeCitation,
}: {
  content: string;
  onCitationClick: (num: number) => void;
  activeCitation: number | null;
}) {
  const components = useMemo<Components>(
    () => ({
      p: ({ children }) => (
        <p>{injectCitations(children, onCitationClick, activeCitation)}</p>
      ),
      li: ({ children }) => (
        <li>{injectCitations(children, onCitationClick, activeCitation)}</li>
      ),
      h1: ({ children }) => (
        <h1>{injectCitations(children, onCitationClick, activeCitation)}</h1>
      ),
      h2: ({ children }) => (
        <h2>{injectCitations(children, onCitationClick, activeCitation)}</h2>
      ),
      h3: ({ children }) => (
        <h3>{injectCitations(children, onCitationClick, activeCitation)}</h3>
      ),
      a: ({ children, href }) => (
        <a
          href={href}
          target="_blank"
          rel="noreferrer"
          style={{ color: "var(--accent)" }}
        >
          {children}
        </a>
      ),
    }),
    [onCitationClick, activeCitation],
  );

  return (
    <div className="rag-markdown">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {content}
      </ReactMarkdown>
    </div>
  );
}
