# tests/embeddings/fixtures

> Sprint 16 ADR-020 (`docs/dev-log/020-pgvector-hnsw-halfvec.md`) recall@10 검증 fixture.

## 사용 (옵션 B 합성 corpus)

```bash
cd backend
uv run python tests/embeddings/fixtures/generate_recall_corpus.py
# → backend/tests/embeddings/fixtures/recall_corpus.json (gitignore)
```

옵션:

| flag | default | 비고 |
|---|---|---|
| `--chunks` | 200 | chunk row 수 |
| `--queries` | 30 | query 수 |
| `--dim` | 1536 | 임베딩 차원 (text-embedding-3-small) |
| `--seed` | 42 | random seed (결정론적) |

기본 200×30×1536d → JSON ~10 MB. recall 측정에 충분.
부족 시 `--chunks 1000 --queries 50` (당근 권고 규모).

## 옵션 A — production export (권장, 환경 의존)

```sql
COPY (
  SELECT id, chunk_text, embedding, workspace_id
  FROM embedding_chunks
  WHERE chunk_level = 2
  ORDER BY random()
  LIMIT 1000
) TO STDOUT WITH CSV;
```

후속 처리로 query 50건 추출 + cosine ground truth 산출 필요. 미구현 (BL-026 후속).

## bench_vector_search.py와의 연동

`backend/scripts/bench_vector_search.py --mode recall` 실행 시 본 디렉토리의
`recall_corpus.json`을 자동 로드. 미존재 시 안내 메시지 출력.

## ADR-020 합격선

- recall@10 >= baseline * 0.95
- nDCG@10 >= 0.95 (BL-026)
- precision@10 >= 0.90 (BL-026)
