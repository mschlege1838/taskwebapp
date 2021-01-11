# Imports

# Standard
import json

from enum import Enum, auto
from pathlib import Path

# User
import taskwebapp.requestutils as requestutils

from taskwebapp.domain import TaskStatus
from taskwebapp.controller import RequestException

# Definitions
class ValidationException(Exception):
    pass


# Static Resources
class StaticResourceHandler:
    
    def __init__(self, encoding, static_content_dirs):
        self.encoding = encoding
        self.static_content_dirs = static_content_dirs
    
    def do_get(self, context):
        handler = context.handler
        
        req_path = context.match[1]
        res_path = Path(*req_path.split('/'))
        for static_content_dir, allowed_patterns in self.static_content_dirs.items():
            target_path = static_content_dir.joinpath(res_path)
            if target_path.is_file():
                # Check if allowed
                allowed = False
                for allowed_pattern in allowed_patterns:
                    if allowed_pattern.match(req_path):
                        allowed = True
                        break
                
                if allowed:
                    break
        else:
            handler.send_error(404)
            return
        
        handler.send_response(200)
    
        handler.send_header('Content-Type', requestutils.get_content_type(target_path.suffix, self.encoding))
        handler.send_header('Content-Length', target_path.stat().st_size)
        handler.end_headers()
        
        with open(target_path, 'rb') as f:
            handler.wfile.write(f.read())



# Home Page
class HomePageHandler:
    def __init__(self, task_service):
        self.task_service = task_service
    
    def do_get(self, context):
        handler = context.handler
        
        context.set_attribute('data', self.task_service.get_dashboard_data())
        context.render_template('home.html')



# Task Management
class TaskRequestType(Enum):
    INQUIRY_OR_UPDATE = auto()
    CREATE = auto()
    SEARCH = auto()
    
    def get_request_type(context):
        sub_path = context.match[1]
        
        is_create = context.bool_param('_create_')
        is_default_path = not sub_path or sub_path == '/'
        
        if is_create:
            return TaskRequestType.CREATE if is_default_path else None
        elif is_default_path:
            return TaskRequestType.SEARCH
        else:
            return TaskRequestType.INQUIRY_OR_UPDATE
    
class TaskHandler:
    def __init__(self, controller):
        self.controller = controller
    
    def do_get(self, context):
        request_type = TaskRequestType.get_request_type(context)
        handler = context.handler
        controller = self.controller
        
        if request_type == TaskRequestType.CREATE:
            controller.do_initial(context)
        elif request_type == TaskRequestType.INQUIRY_OR_UPDATE:
            try:
                controller.do_inquiry(context)
            except RequestException as e:
                handler.send_error(e.code)
        elif request_type == TaskRequestType.SEARCH:
            handler.send_error(501)
        else:
            handler.send_error(400)
    
    
    def do_post(self, context):
        request_type = TaskRequestType.get_request_type(context)
        handler = context.handler
        controller = self.controller
        
        if request_type == TaskRequestType.INQUIRY_OR_UPDATE:
            controller.do_update(context)
        elif request_type == TaskRequestType.CREATE:
            controller.do_create(context)
        elif request_type == TaskRequestType.SEARCH:
            handler.send_error(501)
        else:
            handler.send_error(400)



# Tag Management
class TagHandler:
    def __init__(self, tag_service):
        self.tag_service = tag_service
    
    def do_get(self, context):
        matches = self.tag_service.get_matches(context.get_parameter('q'))
        
        resp = bytes(json.dumps(matches), 'utf-8')
        
        handler = context.handler
        handler.send_response(200)
        handler.send_header('Content-Type', 'application/json')
        handler.send_header('Content-Length', len(resp))
        handler.end_headers()
        
        handler.wfile.write(resp)


# Attachment Management
class AttachmentHandler:
    def __init__(self, attachment_service):
        self.attachment_service = attachment_service
    
    def do_get(self, context):
        handler = context.handler
    
        try:
            attachment_id = int(context.match[1][1:])
        except ValueError:
            handler.send_error(400)
            return
        
        attachment = self.attachment_service.fetch_attachment(attachment_id)
        if not attachment:
            handler.send_error(404)
            return
        
        
        handler.send_response(200)
        handler.send_header('Content-Type', attachment.mime_type)
        handler.send_header('Content-Length', len(attachment.content))
        handler.send_header('Content-Disposition', f'inline;filename="{attachment.name}"')
        handler.end_headers()
        
        handler.wfile.write(attachment.content)