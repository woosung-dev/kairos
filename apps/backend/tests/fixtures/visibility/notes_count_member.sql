SELECT count(*) AS count_1 
FROM notes 
WHERE notes.workspace_id = %(workspace_id_1)s::UUID AND (notes.project_id IS NULL OR (EXISTS (SELECT * 
FROM projects 
WHERE projects.id = notes.project_id AND (projects.visibility = %(visibility_1)s OR projects.visibility = %(visibility_2)s AND projects.created_by_id = %(created_by_id_1)s::UUID OR projects.visibility = %(visibility_3)s AND (EXISTS (SELECT * 
FROM project_members, workspace_members 
WHERE project_members.project_id = projects.id AND project_members.user_id = %(user_id_1)s::UUID AND workspace_members.workspace_id = projects.workspace_id AND workspace_members.user_id = %(user_id_2)s::UUID))))))
