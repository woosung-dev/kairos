-- Kairos DB 초기화 (ADR-028)
-- 이 스크립트는 db 볼륨이 비어 있을 때 최초 1회만 실행된다.
--
-- vector   : ADR-020 pgvector HNSW + halfvec. embeddings/repository.py 의
--            hnsw.iterative_scan='relaxed_order' 는 pgvector >= 0.8 을 요구한다.
-- pg_trgm  : 텍스트 유사도 검색.
--
-- Neon 이 기본 설치했던 pg_session_jwt 는 코드 사용처가 0건이라 재현하지 않는다.

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
