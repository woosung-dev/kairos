SELECT projects.id, projects.workspace_id, projects.title, projects.description, projects.status, projects.visibility, projects.tags, projects.sort_order, projects.created_by_id, projects.created_at, projects.updated_at 
FROM projects 
WHERE projects.workspace_id = %(workspace_id_1)s::UUID AND (projects.visibility = %(visibility_1)s OR projects.visibility = %(visibility_2)s AND projects.created_by_id = %(created_by_id_1)s::UUID OR projects.visibility = %(visibility_3)s AND (EXISTS (SELECT * 
FROM project_members, workspace_members 
WHERE project_members.project_id = projects.id AND project_members.user_id = %(user_id_1)s::UUID AND workspace_members.workspace_id = projects.workspace_id AND workspace_members.user_id = %(user_id_2)s::UUID)))
