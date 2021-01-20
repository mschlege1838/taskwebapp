
from enum import Enum

class TaskStatus(Enum):
    READY = 1
    PENDING = 2
    COMPLETE = 3
    IN_PROGRESS = 4
    CANCELED = 5
    
    def __str__(self):
        return self.name
    
class TaskReference:
    def __init__(self, task_id, name, status, due_ts, last_action_ts):
        self.task_id = task_id
        self.name = name
        self.status = status
        self.due_ts = due_ts
        self.last_action_ts = last_action_ts

class Task:
    def __init__(self, task_id=None, name=None, status=None, due_ts=None, tags=None, pinned_notes=None, notes=None):
        self.task_id = task_id
        self.name = name
        self.status = status
        self.due_ts = due_ts
        self.tags = tags
        self.pinned_notes = pinned_notes
        self.notes = notes


class TaskNote:
    def __init__(self, note_id=None, text=None, attachment_references=None, mod_ts=None):
        self.note_id = note_id
        self.text = text
        self.attachment_references = attachment_references
        self.mod_ts = mod_ts

class TaskDashboardData:
    def __init__(self, late, due_today, due_this_week, pending, due_later, backlog, in_progress):
        self.late = late
        self.due_today = due_today
        self.due_this_week = due_this_week
        self.pending = pending
        self.due_later = due_later
        self.backlog = backlog
        self.in_progress = in_progress