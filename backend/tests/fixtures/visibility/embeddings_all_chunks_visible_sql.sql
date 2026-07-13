
            SELECT 1 FROM embedding_chunks ec
            WHERE ec.id = ANY(:chunk_ids)
              AND ec.project_id IS NOT NULL
              AND NOT EXISTS (
                SELECT 1 FROM projects p
                WHERE p.id = ec.project_id
                  AND (
                    p.visibility = 'public'
                    OR (p.visibility = 'draft' AND p.created_by_id = :req_uid)
                    OR (p.visibility = 'private' AND EXISTS (
                      SELECT 1 FROM project_members pm
                      WHERE pm.project_id = p.id AND pm.user_id = :req_uid
                        AND EXISTS (
                          SELECT 1 FROM workspace_members wm
                          WHERE wm.workspace_id = p.workspace_id
                            AND wm.user_id = :req_uid
                        )
                    ))
                  )
              )
            LIMIT 1
