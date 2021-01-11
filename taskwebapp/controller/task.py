# Imports

# Standard
import re
import os.path

from datetime import datetime

# User
import taskwebapp.requestutils as requestutils

from taskwebapp.controller import Field, DateTimeField, ValidationException, BadRequestException, NotFoundException
from taskwebapp.domain import Task, TaskStatus, TaskNote, MultipartWrapper




# Definitions

# Controller
class TaskController:
    
    new_note_pattern = re.compile(r'^newNote_(\d+)$')
    existing_note_pattern = re.compile(r'^note_(\d+)$')
    

    def __init__(self, task_service, note_service, attachment_service):
        self.task_service = task_service
        self.note_service = note_service
        self.attachment_service = attachment_service
        
    
    def do_initial(self, context):
        fields = {}
        for processor in field_processors:
            processor.define_field(context, fields)
        
        context.set_attribute('fields', fields)
        context.render_template('task.html')
    
    def do_inquiry(self, context):
        try:
            task_id = int(context.match[1][1:])
        except ValueError:
            raise BadRequestException()
        
        task = self.task_service.get_task(task_id)
        if not task:
            raise NotFoundException()
        
        fields = {}
        for processor in field_processors:
            processor.define_field(context, fields)
            processor.inquiry_setup(context, fields, task)
        
        context.set_attribute('fields', fields)
        context.set_attribute('task', task)
        context.render_template('task.html')
    
    
    def do_create(self, context):
        task_service = self.task_service
        note_service = self.note_service
        attachment_service = self.attachment_service
        
        task = Task()
        
        # ---Processing---
        # Simple Fields
        fields = {}
        for processor in field_processors:
            processor.define_field(context, fields)
            processor.process_field(context, fields, task)
        
        # Notes/Attachments
        self.__handle_notes(context, task)
        
        # ---Post-Processing---
        # Determine whether request should be rejected.
        error = False
        for field in fields.values():
            if field.error:
                error = True
                break
        
        # Route Request/Complete Creation (if applicable).
        if error:
            context.set_attribute('fields', fields)
            context.set_attribute('task', task)
            context.render_template('task.html')
        else:
            task_service.create_task(task)
            context.redirect(f'/tasks/{task.task_id}')
        
    
    def do_update(self, context):
        task_service = self.task_service
        
        # Fetch task.
        try:
            task_id = int(context.match[1][1:])
        except ValueError:
            raise BadRequestException()
        
        task = task_service.get_task(task_id)
        if not task:
            raise NotFoundException()

        # ---Processing---
        # Simple Fields
        fields = {}
        for processor in field_processors:
            processor.define_field(context, fields)
            processor.process_field(context, fields, task)
        
        # Notes/Attachments
        self.__handle_notes(context, task)
        
        # ---Post-Processing---
        # Determine whether request should be rejected.
        error = False
        for field in fields.values():
            if field.error:
                error = True
                break
        
        if error:
            context.set_attribute('fields', fields)
            context.set_attribute('task', task)
            context.render_template('task.html')
        else:
            task_service.update_task(task)
            context.redirect(f'/tasks/{task.task_id}')
    
    
    
    def __handle_notes(self, context, task):
        note_service = self.note_service
        attachment_service = self.attachment_service
        
        new_notes = NoteCache()
        existing_notes = NoteCache()
        
        # Read request data/create new attachments.
        for pattern, cache in [(TaskController.new_note_pattern, new_notes), (TaskController.existing_note_pattern, existing_notes)]:
            for name, values in context.parameters:
                match = pattern.match(name)
                if not match:
                    continue
                
                id = int(match[1])
                if id in cache.note_text_by_note_id:
                    raise BadRequestException()
                
                cache.note_text_by_note_id[id] = values[0]
                if context.bool_param(f'{name}_pinned'):
                    cache.pinned.add(id)
                
                cache.attachment_ids_by_note_id[id] = set(int(i) for i in context.get_parameter_values(f'{name}_attachments'))
                
                new_attachment_files = []
                filenames = set()
                for part in context.get_parts(f'{name}_newAttachments'):
                    if not part.filename:
                        continue
                    new_attachment_files.append(part)
                    filenames.add(part.filename)
                
                if len(new_attachment_files) != len(filenames):
                    raise BadRequestException()
                
                cache.new_attachment_files_by_note_id[id] = new_attachment_files
        
        
        # Common Operations
        for cache in (new_notes, existing_notes):
            # Resolve/Create attachments.
            for id, attachment_references in attachment_service.resolve_attachments(cache.attachment_ids_by_note_id).items():
                for attachment_reference in attachment_references:
                    cache.get_attachment_references(id).append(attachment_reference)
            for id, attachment_references in attachment_service.create_attachments(cache.new_attachment_files_by_note_id).items():
                for attachment_reference in attachment_references:
                    cache.get_attachment_references(id).append(attachment_reference)
        
            # Build Notes
            for id, text in cache.note_text_by_note_id.items():
                cache.notes[id] = TaskNote(id, text, cache.get_attachment_references(id))
        
        
        # Create/Update notes.
        note_service.create_notes(new_notes.notes)
        note_service.update_notes(existing_notes.notes.values())
        
        
        # Map back to task
        task.notes = []
        task.pinned_notes = []
        for cache in (new_notes, existing_notes):
            for local_id, note in cache.notes.items():
                if local_id in new_notes.pinned:
                    task.pinned_notes.append(note)
                else:
                    task.notes.append(note)


# Util
class NoteCache:
    def __init__(self):
        self.note_text_by_note_id = {}
        self.attachment_ids_by_note_id = {}
        self.new_attachment_files_by_note_id = {}
        self.attachment_references_by_note_id = {}
        self.pinned = set()
        self.notes = {}
    
    def get_attachment_references(self, id):
        attachment_references_by_note_id = self.attachment_references_by_note_id
        if id in attachment_references_by_note_id:
            result = attachment_references_by_note_id[id]
        else:
            result = attachment_references_by_note_id[id] = []
        return result
        

# Processors
class NameFieldProcessor:
    
    field_name = 'name'
    
    @classmethod
    def define_field(cls, context, fields):
        fields[NameFieldProcessor.field_name] = Field(
            name=NameFieldProcessor.field_name,
            label='Name'
        )
    
    @classmethod
    def inquiry_setup(cls, context, fields, task):
        fields[NameFieldProcessor.field_name].value = task.name

    @classmethod
    def process_field(cls, context, fields, task):
        field = fields[NameFieldProcessor.field_name]
        value = context.get_parameter(NameFieldProcessor.field_name)
        
        if not value:
            field.error = 'Task name is required.'
        
        field.value = task.name = value


#Allow blank due time -- definition as backlog
class DueTimeFieldProcessor:
    
    field_name = 'due'
    
    @classmethod
    def define_field(cls, context, fields):
        fields[DueTimeFieldProcessor.field_name] = field = Field(
            name=DueTimeFieldProcessor.field_name,
            label='Due',
            type='datetime'
        )
    
    @classmethod
    def inquiry_setup(cls, context, fields, task):
        fields[DueTimeFieldProcessor.field_name].value = DateTimeField.from_timestamp(task.due_ts)
    
    @classmethod
    def process_field(cls, context, fields, task):
        field = fields[DueTimeFieldProcessor.field_name]
        
        try:
            value = DateTimeField.get_value(context, DueTimeFieldProcessor.field_name)
        except ValidationException as e:
            field.error = e.message
            field.value = e.value
        else:
            field.value = value
        
        if not field.error:
            task.due_ts = value.timestamp



class StatusFieldProcessor:
    
    field_name = 'status'
    
    @classmethod
    def define_field(cls, context, fields):
        fields[StatusFieldProcessor.field_name] = Field(
            name=StatusFieldProcessor.field_name,
            label='Status',
            options=[(item.name, item.name) for item in list(TaskStatus)],
            type='select'
        )
    
    @classmethod
    def inquiry_setup(cls, context, fields, task):
        fields[StatusFieldProcessor.field_name].value = task.status.name

    @classmethod
    def process_field(cls, context, fields, task):
        field = fields[StatusFieldProcessor.field_name]
        raw_value = field.value = context.get_parameter(StatusFieldProcessor.field_name)
        
        try:
            value = TaskStatus[raw_value]
        except KeyError:
            field.error = 'Invalid status.'
        else:
            task.status = value


class TagsFieldProcessor:
    
    field_name = 'tags'
    
    @classmethod
    def define_field(cls, context, fields):
        fields[TagsFieldProcessor.field_name] = Field(
            name=TagsFieldProcessor.field_name,
            label='Tags'
        )
    
    @classmethod
    def inquiry_setup(cls, context, fields, task):
        fields[TagsFieldProcessor.field_name].value = task.tags
    
    @classmethod
    def process_field(cls, context, fields, task):
        tags = context.get_parameter_values(TagsFieldProcessor.field_name)
        task.tags = tags
        fields[TagsFieldProcessor.field_name].value = tags


class NotesFieldProcessor:
    
    field_name = 'notes'
    
    @classmethod
    def define_field(cls, context, fields):
        fields[NotesFieldProcessor.field_name] = Field(
            name=NotesFieldProcessor.field_name,
            label='Notes'
        )
    
    @classmethod
    def inquiry_setup(cls, context, fields, task):
        fields[NotesFieldProcessor.field_name].value = task.notes
    
    @classmethod
    def process_field(cls, context, fields, task):
        task.notes = fields[NotesFieldProcessor.field_name].value = context.get_parameter(NotesFieldProcessor.field_name)


field_processors = [
    NameFieldProcessor,
    DueTimeFieldProcessor,
    StatusFieldProcessor,
    TagsFieldProcessor,
    NotesFieldProcessor
]


