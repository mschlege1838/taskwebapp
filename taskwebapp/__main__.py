
# Imports
# Standard
import importlib.util
import re
import json
import traceback
import os.path

from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
from argparse import ArgumentParser

# Third Party
from jinja2 import Environment, PackageLoader, ChainableUndefined

# User
from taskwebapp.util import RequestContext, ServerThread, JinjaRenderer
from taskwebapp.requestutils import RequestProcessor
from taskwebapp.handlers import StaticResourceHandler, HomePageHandler, TaskHandler, TagHandler, AttachmentHandler
from taskwebapp.service.sqlite import TaskService, TagService, AttachmentService, NoteService
from taskwebapp.controller.task import TaskController


# Definitions
def jinja_finalize(expr):
    return expr if expr is not None else ''


# args
arg_parser = ArgumentParser(description='A task management webapp.')
arg_parser.add_argument('--port', type=int, default=8092)
arg_parser.add_argument('--shutdown-timeout', type=float, default=5.0)
arg_parser.add_argument('--encoding', default='utf-8')
arg_parser.add_argument('--sqlite-db', default=os.path.join(os.path.expanduser('~'), '.taskwebapp.sqlite'))

args = arg_parser.parse_args()


port_number = args.port
encoding = args.encoding
shutdown_timeout_s = args.shutdown_timeout
db_fname = args.sqlite_db



# Config
base_package_name = 'taskwebapp'
static_content_dirs = {
    'content': [
        re.compile('.+')
    ],
    'node_modules': [
        re.compile('@mschlege1838/autocomplete-input/include/.+')
    ]
}




# Setup

# Jinja
jinja_env = Environment(loader=PackageLoader(base_package_name, encoding=encoding), finalize=jinja_finalize, undefined=ChainableUndefined)
jinja_env.filters['sn'] = jinja_finalize
jinja_env.filters['json'] = json.dumps
renderer = JinjaRenderer(jinja_env, encoding)

# Resolve static content directories.
base_dir = Path(importlib.util.find_spec(base_package_name).submodule_search_locations[0])
static_content_dirs = dict((base_dir.joinpath(d), ps) for d, ps in static_content_dirs.items())



# Services
task_service = TaskService(db_fname)
note_service = NoteService(db_fname)
attachment_service = AttachmentService(db_fname)
tag_service = TagService(db_fname)


# Controllers
task_controller = TaskController(task_service, note_service, attachment_service)


# Handlers
handlers = [
    (re.compile('^/$'), HomePageHandler(task_service))
    , (re.compile('/content/(.+)'), StaticResourceHandler(encoding, static_content_dirs))
    , (re.compile('/tasks(/?.*)'), TaskHandler(task_controller))
    , (re.compile('/tags(/?.*)'), TagHandler(tag_service))
    , (re.compile('/attachments(/?.*)'), AttachmentHandler(attachment_service))
]





# Program
class RequestHandler(BaseHTTPRequestHandler):

    protocol_version = 'HTTP/1.1'
    
    def _handle(self, target_name):
        path = urlparse(self.path).path
        
        for expr, handler in handlers:
            match = expr.match(path)
            if match:
                break
        else:
            self.send_error(404)
            return
        
        if not hasattr(handler, target_name):
            self.send_error(405)
            return
        
        
        attributes = {}
        
        with RequestProcessor(self) as p:
            try:
                getattr(handler, target_name)(RequestContext(self, p.parameters, p.parts, match, renderer, encoding, attributes))
            except:
                traceback.print_exc()
                print()
                self.send_error(500)
            
    
    def do_GET(self):
        self._handle('do_get')

    def do_POST(self):
        self._handle('do_post')
    



# Start Server

print('Starting server on', port_number)
print('Control-C to stop.')

server = ThreadingHTTPServer(('', port_number), RequestHandler)
t = ServerThread(server)
t.start()


try:
    while True:
        pass
except KeyboardInterrupt:
    print('Keyboard Interrupt: shutting down server.')
    server.shutdown()
    t.join(timeout=shutdown_timeout_s)
    if t.is_alive():
        print('Server is not shut down after timeout period.')
    else:
        print('Server shut down.')
    