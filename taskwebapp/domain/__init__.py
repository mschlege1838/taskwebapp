
# System
import os.path

# User
import taskwebapp.requestutils as requestutils


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

