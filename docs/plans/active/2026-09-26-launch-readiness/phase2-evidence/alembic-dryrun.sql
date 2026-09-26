BEGIN;

-- Running upgrade c1a7e0b5d3f2 -> a9c4e2f7b1d0

ALTER TABLE memory_items ADD COLUMN is_shared BOOLEAN DEFAULT false NOT NULL;

UPDATE memory_items mi
        SET is_shared = true
        WHERE EXISTS (
            SELECT 1
            FROM memory_events me
            JOIN memory_items src
              ON CAST(src.id AS text) = me.event_metadata->>'source_memory_id'
            WHERE me.event_type = 'promote'
              AND me.event_metadata->>'new_memory_id' = CAST(mi.id AS text)
              AND src.user_id = me.user_id
        );

UPDATE alembic_version SET version_num='a9c4e2f7b1d0' WHERE alembic_version.version_num = 'c1a7e0b5d3f2';

-- Running upgrade a9c4e2f7b1d0 -> b3d5f8a1c2e4

UPDATE meetings SET error_message = '회의 처리 중 오류가 발생했습니다. 다시 시도하거나 관리자에게 문의하세요.' WHERE error_message IS NOT NULL AND error_message <> '회의 처리 중 오류가 발생했습니다. 다시 시도하거나 관리자에게 문의하세요.';

UPDATE alembic_version SET version_num='b3d5f8a1c2e4' WHERE alembic_version.version_num = 'a9c4e2f7b1d0';

COMMIT;

