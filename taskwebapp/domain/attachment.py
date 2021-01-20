

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