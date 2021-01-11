
# Imports
# Standard
from threading import Thread

# User
import taskwebapp.requestutils as requestutils


# Definitions
class RequestContext:
    def __init__(self, handler, parameters, parts, match, renderer, encoding, attributes):
        self.handler = handler
        self.parameters = parameters
        self.parts = parts
        self.match = match
        self.renderer = renderer
        self.encoding = encoding
        self.attributes = attributes
    
    def get_parameter(self, name):
        return self.parameters.get(name)
    
    def get_parameter_values(self, name):
        return self.parameters.get_all(name)
    
    def get_part(self, name):
        if not self.parts:
            raise ValueError('Request does not have parts.')
            
        return self.parts.get(name)
    
    def get_parts(self, name):
        if not self.parts:
            raise ValueError('Request does not have parts.')
        
        return self.parts.get_all(name)
    
    def bool_param(self, name):
        param = self.get_parameter(name)
        return param is not None and param.casefold() != 'false'
    
    def set_attribute(self, name, value):
        self.attributes[name] = value
    
    def render_template(self, template_name):
        handler = self.handler
        
        resp = self.renderer.render(template_name, self.attributes)
        
        handler.send_response(200)
        handler.send_header('Content-Type', requestutils.content_type_value('text/html', self.encoding))
        handler.send_header('Content-Length', len(resp))
        handler.end_headers()
        
        handler.wfile.write(resp)
        
    
    
    def redirect(self, location, message='Redirecting...'):
        resp = bytes(f'<!DOCTYPE html><html><body><p>{message}</p>'
                     f'<p>If your browser does not do this automatically, click <a href="{location}">here</a>.</p></body></html>', self.encoding)
        
        handler = self.handler
        handler.send_response(302)
        handler.send_header('Location', location)
        handler.send_header('Content-Type', requestutils.content_type_value('text/html', self.encoding))
        handler.send_header('Content-Length', len(resp))
        handler.end_headers()
        
        handler.wfile.write(resp)



class ServerThread(Thread):
    def __init__(self, server):
        super().__init__()
        self.server = server
    
    def run(self):
        self.server.serve_forever()


class JinjaRenderer:
    def __init__(self, env, encoding):
        self.env = env
        self.encoding = encoding
    
    def render_chunked(self, template_name, wfile, variables=None):
        template = self.env.get_template(template_name)
        requestutils.write_chunked(template.generate(variables) if variables else template.generate(), wfile, self.encoding)
    
    def render(self, template_name, variables=None):
        template = self.env.get_template(template_name)
        return (template.render(variables) if variables else template.render()).encode(self.encoding)
    
