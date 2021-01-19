# Imports

# Standard
import re
import os.path

from abc import ABC
from datetime import datetime

# User
import taskwebapp.requestutils as requestutils

from taskwebapp.controller import Field, DateTimeField, ValidationException, BadRequestException, NotFoundException
from taskwebapp.domain import Task, TaskStatus, TaskNote, MultipartWrapper
from taskwebapp.domain.task.search import TaskSearchLogicalOp, TaskSearchStrOp, TaskSearchNumOp, TaskSearchSimpleExpr, \
        TaskSearchIsAnyExpr, TaskSearchExpr, TaskSearchField




# Definitions

# Controller
class TaskController:
    
    new_note_pattern = re.compile(r'^newNote_(\d+)$')
    existing_note_pattern = re.compile(r'^note_(\d+)$')
    

    def __init__(self, task_service, note_service, attachment_service):
        self.task_service = task_service
        self.note_service = note_service
        self.attachment_service = attachment_service
    
    def do_search(self, context):
        
        criteria = TaskSearchCriteria()
        fields = {}
        for processor in field_processors:
            processor.define_field(context, fields)
            processor.process_search(context, fields, criteria)
        
        if criteria.expr:
            results = self.task_service.search(criteria.expr)
            if not results:
                none_found = True
            else:
                none_found = False
        else:
            results = []
            none_found = False
        
        context.set_attribute('fields', fields)
        context.set_attribute('results', results)
        context.set_attribute('none_found', none_found)
        context.render_template('task-inq.html')
 
    
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
                
                cache.new_attachment_files_by_note_id[id] = [MultipartWrapper(p) for p in new_attachment_files]
        
        
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
                if local_id in cache.pinned:
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
        

class TaskSearchCriteria:
    def __init__(self, expr=None):
        self.expr = expr
    
    def i_and(self, expr):
        if self.expr:
            self.expr = TaskSearchExpr(self.expr, TaskSearchLogicalOp.AND, expr)
        else:
            self.expr = expr
    
    def __str__(self):
        return str(self.expr)


# Processors
class SearchProcessor(ABC):
    
    str_operator_options = [
        ('STARTS_WITH', 'Starts With'),
        ('CONTAINS', 'Contains'),
        ('EQUALS', 'Equals')
    ]
    
    num_operator_options = [
        ('EQ', '='),
        ('GTE', '>='),
        ('LTE', '<='),
        ('GT', '>'),
        ('LT', '<'),
        ('NE', '<>')
    ]

    
    @classmethod
    def get_operator_field_name(cls):
        return f'{cls.field_name}_operator'
    
    @classmethod
    def get_str_op(cls, value):
        if not value:
            return None
        try:
            return TaskSearchStrOp[value.upper()]
        except KeyError:
            return None
    
    @classmethod
    def get_num_op(cls, value):
        if not value:
            return None
        try:
            return TaskSearchNumOp[value.upper()]
        except:
            return None

class NameFieldProcessor(SearchProcessor):
    
    field_name = 'name'
    field_label = 'Name'
    
    @classmethod
    def define_field(cls, context, fields):
        fields[cls.field_name] = Field(
            name=cls.field_name,
            label=cls.field_label
        )
        
    
    @classmethod
    def inquiry_setup(cls, context, fields, task):
        fields[cls.field_name].value = task.name

    @classmethod
    def process_field(cls, context, fields, task):
        field = fields[cls.field_name]
        value = context.get_parameter(cls.field_name)
        
        if not value:
            field.error = 'Task name is required.'
        
        field.value = task.name = value
    
    @classmethod
    def process_search(cls, context, fields, criteria):
        field_name = cls.get_operator_field_name()
        fields[field_name] = Field(
            name=field_name,
            type='select',
            options=SearchProcessor.str_operator_options,
            value=context.get_parameter(field_name)
        )
        
        value = fields[cls.field_name].value = context.get_parameter(cls.field_name)
        operator = cls.get_str_op(context.get_parameter(field_name))
        if value and operator:
            criteria.i_and(TaskSearchSimpleExpr(TaskSearchField.NAME, operator, value))


class DueTimeFieldProcessor(SearchProcessor):
    
    field_name = 'due'
    field_label = 'Due'
    
    @classmethod
    def define_field(cls, context, fields):
        fields[cls.field_name] = field = Field(
            name=cls.field_name,
            label=cls.field_label,
            type='datetime'
        )
    
    @classmethod
    def inquiry_setup(cls, context, fields, task):
        fields[cls.field_name].value = DateTimeField.from_timestamp(task.due_ts)
    
    @classmethod
    def process_field(cls, context, fields, task):
        field = fields[cls.field_name]
        
        try:
            value = DateTimeField.get_value(context, cls.field_name)
        except ValidationException as e:
            field.error = e.message
            field.value = e.value
        else:
            field.value = value
        
        if not field.error:
            task.due_ts = value.timestamp
    
    @classmethod
    def process_search(cls, context, fields, criteria):
        # Search Field
        search_field_name = cls.get_operator_field_name()
        fields[search_field_name] = Field(
            name=search_field_name,
            type='select',
            options=SearchProcessor.num_operator_options,
            value=context.get_parameter(search_field_name)
        )
        
        # Date Value
        if context.get_parameter(cls.field_name):
            value_field = fields[cls.field_name]
            try:
                value = DateTimeField.get_value(context, cls.field_name)
            except ValidationException as e:
                value_field.error = e.message
                value_field.value = e.value
            else:
                value_field.value = value
                operator = cls.get_num_op(context.get_parameter(search_field_name))
                if value and operator:
                    criteria.i_and(TaskSearchSimpleExpr(TaskSearchField.DUE, operator, value.timestamp))
                



class StatusFieldProcessor(SearchProcessor):
    
    field_name = 'status'
    field_label = 'Status'
    
    @classmethod
    def define_field(cls, context, fields):
        fields[cls.field_name] = Field(
            name=cls.field_name,
            label=cls.field_label,
            type='select',
            options=[(item.name, item.name) for item in list(TaskStatus)]
        )
    
    @classmethod
    def inquiry_setup(cls, context, fields, task):
        fields[cls.field_name].value = task.status.name

    @classmethod
    def process_field(cls, context, fields, task):
        field = fields[cls.field_name]
        raw_value = field.value = context.get_parameter(cls.field_name)
        
        try:
            value = TaskStatus[raw_value]
        except KeyError:
            field.error = 'Invalid status.'
        else:
            task.status = value
    
    @classmethod
    def process_search(cls, context, fields, criteria):
        field_name = cls.get_operator_field_name()
        fields[field_name] = Field(
            name=field_name,
            readonly=True,
            value='Is Any'
        )
        
        field = fields[cls.field_name]
        field.multiple = True
        raw_values = field.value = context.get_parameter_values(cls.field_name)
        
        values = []
        for raw_value in raw_values:
            try:
                values.append(TaskStatus[raw_value])
            except KeyError:
                field.error = 'Invalid status.'
                break
        else:
            if values:
                criteria.i_and(TaskSearchIsAnyExpr(TaskSearchField.STATUS, values))


class TagsFieldProcessor:
    
    field_name = 'tags'
    field_label = 'Tags'
    
    @classmethod
    def define_field(cls, context, fields):
        fields[cls.field_name] = Field(
            name=cls.field_name,
            label=cls.field_label
        )
    
    @classmethod
    def inquiry_setup(cls, context, fields, task):
        fields[cls.field_name].value = task.tags
    
    @classmethod
    def process_field(cls, context, fields, task):
        tags = context.get_parameter_values(cls.field_name)
        task.tags = tags
        fields[cls.field_name].value = tags
    
    @classmethod
    def process_search(cls, context, fields, criteria):
        values = fields[cls.field_name].value = context.get_parameter_values(cls.field_name)
        if values:
            criteria.i_and(TaskSearchIsAnyExpr(TaskSearchField.TAGS, values))


field_processors = [
    NameFieldProcessor,
    DueTimeFieldProcessor,
    StatusFieldProcessor,
    TagsFieldProcessor
]
