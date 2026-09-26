
            SELECT 1 FROM unnest(CAST(:chunk_ids AS uuid[])) AS req(id)
            LEFT JOIN embedding_chunks ec ON ec.id = req.id
            WHERE (ec.id IS NULL AND COALESCE(:req_role, '') NOT IN ('admin', 'owner'))
               OR (
                 ec.source_type = 'memory'
                 AND NOT EXISTS (
                   SELECT 1 FROM memory_items mi
                   WHERE mi.id = ec.source_id
                     AND (mi.user_id = :req_uid OR mi.is_shared)
                 )
               )
               OR (
                 COALESCE(:req_role, '') NOT IN ('admin', 'owner')
                 AND (
                   (
                     ec.source_type = 'meeting'
                     AND EXISTS (
                       SELECT 1 FROM meeting_project_links ml
                       WHERE ml.meeting_id = ec.source_id
                     )
                     AND NOT EXISTS (
                       SELECT 1 FROM meeting_project_links ml
                       JOIN projects p ON p.id = ml.project_id
                       WHERE ml.meeting_id = ec.source_id
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
                   OR (
                     ec.source_type <> 'meeting'
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
                   )
                 )
               )
            LIMIT 1
