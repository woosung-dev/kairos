SELECT action_items.id, action_items.workspace_id, action_items.meeting_id, action_items.project_id, action_items.title, action_items.description, action_items.assignee_id, action_items.due_date, action_items.priority, action_items.status, action_items.created_at, action_items.updated_at 
FROM action_items 
WHERE action_items.workspace_id = %(workspace_id_1)s::UUID AND (action_items.project_id IS NULL OR (EXISTS (SELECT * 
FROM projects 
WHERE projects.id = action_items.project_id AND (projects.visibility = %(visibility_1)s OR projects.visibility = %(visibility_2)s AND projects.created_by_id = %(created_by_id_1)s::UUID OR projects.visibility = %(visibility_3)s AND (EXISTS (SELECT * 
FROM project_members, workspace_members 
WHERE project_members.project_id = projects.id AND project_members.user_id = %(user_id_1)s::UUID AND workspace_members.workspace_id = projects.workspace_id AND workspace_members.user_id = %(user_id_2)s::UUID))))))
