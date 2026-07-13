SELECT meetings.id, meetings.workspace_id, meetings.title, meetings.file_key, meetings.source, meetings.recorded_at, meetings.duration_sec, meetings.status, meetings.error_message, meetings.has_transcript, meetings.has_summary, meetings.action_item_count, meetings.created_by_id, meetings.created_at, meetings.updated_at 
FROM meetings 
WHERE meetings.workspace_id = %(workspace_id_1)s::UUID AND (NOT (EXISTS (SELECT * 
FROM meeting_project_links AS meeting_project_links_1 
WHERE meeting_project_links_1.meeting_id = meetings.id)) OR (EXISTS (SELECT * 
FROM meeting_project_links AS meeting_project_links_2, projects 
WHERE meeting_project_links_2.meeting_id = meetings.id AND meeting_project_links_2.project_id = projects.id AND (projects.visibility = %(visibility_1)s OR projects.visibility = %(visibility_2)s AND projects.created_by_id = %(created_by_id_1)s::UUID OR projects.visibility = %(visibility_3)s AND (EXISTS (SELECT * 
FROM project_members, workspace_members 
WHERE project_members.project_id = projects.id AND project_members.user_id = %(user_id_1)s::UUID AND workspace_members.workspace_id = projects.workspace_id AND workspace_members.user_id = %(user_id_2)s::UUID))))))
