# Imports
# Standard
from urllib.parse import urlparse, parse_qsl

# User
from taskwebapp.multipart import MultipartStream, MultipartLexer, MultipartParser


# Definitions
# Data
variable_text_encodings = {
    'text/xml',
    'application/xml',
    'text/css',
    'text/csv',
    'text/html',
    'text/calendar',
    'application/json',
    'application/ld+json',
    'text/javascript',
    'application/x-httpd-php',
    'application/x-sh',
    'image/svg+xml',
    'text/plain',
    'application/xhtml+xml',
    'application/vnd.mozilla.xul+xml'
}

content_type_suffix_mapping = {
    '.xml': {
        '__default__': 'text/xml',
        'readable': 'text/xml',
        'not-readable': 'application/xml'
    },
    '.3gp': {
        '__default__': 'video/3gpp',
        'video': 'video/3gpp',
        'audio-only': 'audio/3gpp'
    },
    '.3g2': {
        '__default__': 'video/3gpp2',
        'video': 'video/3gpp2',
        'audio-only': 'audio/3gpp2'
    },
    '.aac': 'audio/aac',
    '.abw': 'application/x-abiword',
    '.arc': 'application/x-freearc',
    '.avi': 'video/x-msvideo',
    '.azw': 'application/vnd.amazon.ebook',
    '.bin': 'application/octet-stream',
    '.bmp': 'image/bmp',
    '.bz': 'application/x-bzip',
    '.bz2': 'application/x-bzip2',
    '.csh': 'application/x-csh',
    '.css': 'text/css',
    '.csv': 'text/csv',
    '.doc': 'application/msword',
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    '.eot': 'application/vnd.ms-fontobject',
    '.epub': 'application/epub+zip',
    '.gz': 'application/gzip',
    '.gif': 'image/gif',
    '.htm': 'text/html',
    '.html': 'text/html',
    '.ico': 'image/vnd.microsoft.icon',
    '.ics': 'text/calendar',
    '.jar': 'application/java-archive',
    '.jpeg': 'image/jpeg',
    '.jpg': 'image/jpeg',
    '.js': 'text/javascript',
    '.json': 'application/json',
    '.jsonld': 'application/ld+json',
    '.mid': 'audio/midi',
    '.midi': 'audio/midi',
    '.mjs': 'text/javascript',
    '.mp3': 'audio/mpeg',
    '.mpeg': 'video/mpeg',
    '.mpkg': 'application/vnd.apple.installer+xml',
    '.odp': 'application/vnd.oasis.opendocument.presentation',
    '.ods': 'application/vnd.oasis.opendocument.spreadsheet',
    '.odt': 'application/vnd.oasis.opendocument.text',
    '.oga': 'audio/ogg',
    '.ogv': 'video/ogg',
    '.ogx': 'application/ogg',
    '.opus': 'audio/opus',
    '.otf': 'font/otf',
    '.png': 'image/png',
    '.pdf': 'application/pdf',
    '.php': 'application/x-httpd-php',
    '.ppt': 'application/vnd.ms-powerpoint',
    '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    '.rar': 'application/vnd.rar',
    '.rtf': 'application/rtf',
    '.sh': 'application/x-sh',
    '.svg': 'image/svg+xml',
    '.swf': 'application/x-shockwave-flash',
    '.tar': 'application/x-tar',
    '.tif': 'image/tiff',
    '.tiff': 'image/tiff',
    '.ts': 'video/mp2t',
    '.ttf': 'font/ttf',
    '.txt': 'text/plain',
    '.vsd': 'application/vnd.visio',
    '.wav': 'audio/wav',
    '.weba': 'audio/webm',
    '.webm': 'video/webm',
    '.webp': 'image/webp',
    '.woff': 'font/woff',
    '.woff2': 'font/woff2',
    '.xhtml': 'application/xhtml+xml',
    '.xls': 'application/vnd.ms-excel',
    '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    '.xul': 'application/vnd.mozilla.xul+xml',
    '.zip': 'application/zip',
    '.7z': 'application/x-7z-compressed'
}


# Functions
def get_content_type(ext, addendum=None, var_text_enc='utf-8'):
    if not ext in content_type_suffix_mapping:
        type = 'application/octet-stream'
    else:
        mapping = content_type_suffix_mapping[ext]
        if isinstance(mapping, str):
            type = mapping
        elif not addendum:
            type = mapping['__default__']
        else:
            type = mapping[addendum]
    
    if type in variable_text_encodings:
        return content_type_value(type, var_text_enc)
    else:
        return type

def content_type_value(type, charset):
    return f'{type}; charset={charset}'

def write_chunked(generator, wfile, charset):
    for part in generator:
        data = part.encode(charset)
        wfile.write(f'{len(data):02X}\r\n'.encode(charset))
        wfile.write(data)
        wfile.write('\r\n'.encode(charset))
    
    wfile.write('0\r\n'.encode(charset))



# Classes
class RequestProcessor:

    def __init__(self, handler):
        self.handler = handler
        self.multipart_parser = None
        self.parameters = None
        self.parts = None
    
    
    
    def process_parameters(self):
        if self.parameters:
            raise Exception()
        
        handler = self.handler
        parameters = self.parameters = RequestParameterData()
        
        query = urlparse(handler.path).query
        qlist = parse_qsl(query)
        if not qlist and query:
            qlist = [(query, '')]
            
        for name, value in qlist:
            parameters.add(name, value)
        
        headers = handler.headers
        content_type = headers.get_content_type()
        if content_type == 'application/x-www-form-urlencoded':
            for name, value in parse_qsl(handler.rfile.read()):
                parameters.add(name, value)
        
        elif content_type == 'multipart/form-data':
            stream = MultipartStream(handler.rfile, int(handler.headers['Content-Length']))
            lexer = MultipartLexer(stream, handler.headers.get_boundary())
            parser = self.multipart_parser = MultipartParser(lexer, 'utf-8')
            parts = self.parts = RequestParameterData()
            
            for part in parser.multipart():
                parts.add(part.name, part)
                if not part.is_file:
                    parameters.add(part.name, part.value.decode('utf-8', 'replace'))
                
    
    def close(self):
        multipart_parser = self.multipart_parser
        if multipart_parser:
            multipart_parser.dispose()

    
    def __enter__(self):
        self.process_parameters()
        return self
    
    def __exit__(self, exc_typ, exc_value, traceback):
        self.close()



class RequestParameterData:
    
    def __init__(self):
        self.parameters = {}
    
    def __contains__(self, key):
        return key in self.parameters
        
 
    def add(self, name, value):
        parameters = self.parameters
        
        if name in parameters:
            values = parameters[name]
        else:
            parameters[name] = values = []
            
        values.append(value)
    
    
    def get(self, name):
        parameters = self.parameters
        if name not in parameters:
            return None
        
        return parameters[name][0]
        
    
    def get_all(self, name):
        parameters = self.parameters
        return list(parameters[name]) if name in parameters else []
    
    def __iter__(self):
        return iter(self.parameters.items())
    
    