SELECT projects.id, projects.workspace_id, projects.title, projects.description, projects.status, projects.visibility, projects.tags, projects.sort_order, projects.created_by_id, projects.created_at, projects.updated_at 
FROM projects 
WHERE projects.workspace_id = %(workspace_id_1)s::UUID AND projects.visibility = %(visibility_1)s
