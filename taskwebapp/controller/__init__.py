
import re

from datetime import datetime


class RequestException(Exception):
    def __init__(self, code):
        self.code = code


class BadRequestException(RequestException):
    def __init__(self):
        super().__init__(400)

class NotFoundException(RequestException):
    def __init__(self):
        super().__init__(404)


class ValidationException(Exception):
    def __init__(self, message, value):
        super().__init__(message, value)
        self.message = message
        self.value = value



class Field:
    def __init__(self, name, label=None, type=None, value=None, options=None, error=None, multiple=False, readonly=False):
        self.name = name
        self.label = label
        self.type = type
        self.value = value
        self.options = options
        self.error = error
        self.multiple = multiple
        self.readonly = readonly


class DateTimeField:
    
    no_colon_time_pattern = re.compile(r'\d{4}')
    
    @classmethod
    def get_value(cls, context, field_name):
        date_val = context.get_parameter(field_name)
        time_val = context.get_parameter(f'{field_name}_time')
        
        if not date_val and not time_val:
            return DateTimeField('', '', None)
        
        if not date_val:
            raise ValidationException('Invalid date time.', DateTimeField(date_val, time_val))
        
        if not time_val:
            time_val = '23:59'
        
        if DateTimeField.no_colon_time_pattern.match(time_val):
            t = time_val
            time_val = f'{t[0:2]}:{t[2:4]}'
        
        try:
            timestamp = datetime.strptime(f'{date_val}{time_val}', '%Y-%m-%d%H:%M')
        except:
            raise ValidationException('Invalid date time.', DateTimeField(date_val, time_val))
        else:
            return DateTimeField(date_val, time_val, timestamp)
    
    
    @classmethod
    def from_timestamp(cls, timestamp):
        return DateTimeField(timestamp.strftime('%Y-%m-%d'), timestamp.strftime('%H:%M'), timestamp) if timestamp else None
    
    
    def __init__(self, date_val, time_val, timestamp=None):
        self.date_val = date_val
        self.time_val = time_val
        self.timestamp = timestamp