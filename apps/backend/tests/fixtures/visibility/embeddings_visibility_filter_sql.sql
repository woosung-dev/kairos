
            AND (
                project_id IS NULL
                OR :req_role IN ('admin', 'owner')
                OR EXISTS (
                    SELECT 1 FROM projects p
                    WHERE p.id = embedding_chunks.project_id
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
            )
