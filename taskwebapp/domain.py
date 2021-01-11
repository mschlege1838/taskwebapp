
# System
import os.path

from enum import Enum

# User
import taskwebapp.requestutils as requestutils


class TaskStatus(Enum):
    READY = 1
    PENDING = 2
    COMPLETE = 3
    
    def __str__(self):
        return self.name
    
class TaskReference:
    def __init__(self, task_id, name, status, pending_upon, due_ts, last_action_ts):
        self.task_id = task_id
        self.name = name
        self.status = status
        self.pending_upon = pending_upon
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
    def __init__(self, note_id=None, text=None, attachment_references=None):
        self.note_id = note_id
        self.text = text
        self.attachment_references = attachment_references


class AttachmentReference:
    def __init__(self, attachment_id, name, mime_type, creation_ts):
        self.attachment_id = attachment_id
        self.name = name
        self.mime_type = mime_type
        self.creation_ts = creation_ts


class Attachment:
    def __init__(self, name, content, mime_type):
        self.name = name
        self.content = content
        self.mime_type = mime_type


class MultipartWrapper:
    def __init__(self, part):
        self.part = part
    
    @property
    def mime_type(self):
        part = self.part
        
        if 'Content-Type' in part.headers:
            return part.headers['Content-Type'].value.decode('utf-8')
        else:
            return requestutils.get_content_type(os.path.splitext(part.filename)[1])
    
    @property
    def filename(self):
        return self.part.filename
    
    @property
    def value(self):
        return self.part.value


class TaskDashboardData:
    def __init__(self, late, due_today, due_this_week, pending, due_later):
        self.late = late
        self.due_today = due_today
        self.due_this_week = due_this_week
        self.pending = pending
        self.due_later = due_later