
# Imports
import re
import os
import tempfile

from enum import Enum, auto
from datetime import datetime, timezone, timedelta


# Definitions
class MediaType:
    def __init__(self, type, subtype, parameters):
        self.type = type
        self.subtype = subtype
        self.parameters = parameters

class Header:
    def __init__(self, name, value, media_type):
        self.name = name
        self.value = value
        self.media_type = media_type
    
    def get_param(self, name):
        media_type = self.media_type
        return media_type.parameters[name] if media_type and name in media_type.parameters else None
    
    def has_param(self, name):
        media_type = self.media_type
        return name in media_type.parameters if media_type else False
    
    @property
    def type(self):
        media_type = self.media_type
        return media_type.type if media_type else None
    
    @property
    def subtype(self):
        media_type = self.media_type
        return media_type.subtype if media_type else None


class ContentDispositionHeader(Header):
    def __init__(self, header):
        super().__init__(header.name, header.value, header.media_type)
    
    @property
    def field_name(self):
        return self.get_param('name')
    
    @property
    def filename(self):
        raw_name = self.get_param('filename')
        # TODO Sanitize to name.suffix
        return raw_name
    
    @property
    def creation_dt(self):
        return get_rfc2822_date(self.get_param('creation-date')) if self.has_param('creation-date') else None
    
    @property
    def mod_dt(self):
        return get_rfc2822_date(self.get_param('modification-date')) if self.has_param('modification-date') else None
    
    @property
    def read_dt(self):
        return get_rfc2822_date(self.get_param('read-date')) if self.has_param('read-date') else None
    
    @property
    def size(self):
        return int(self.get_param('size')) if self.has_param('size') else None


class HeaderMapping:
    
    def __init__(self):
        self.mapping = {}
    
    def __getitem__(self, key):
        return self.mapping[key.casefold()]
    
    def __setitem__(self, key, value):
        self.mapping[key.casefold()] = value
    
    def __contains__(self, key):
        return key.casefold() in self.mapping
    
    def __str__(self):
        return str(self.mapping)



class Part:
    def __init__(self, headers, body):
        self.headers = headers
        self._body = body

    @property
    def is_file(self):
        return self._body.is_file
    
    @property
    def name(self):
        return self.headers['Content-Disposition'].field_name
    
    @property
    def filename(self):
        return self.headers['Content-Disposition'].filename
    
    @property
    def value(self):
        return self._body.value
    
    def __str__(self):
        return f'{self.name}({self.filename}): {self.value}'
    
    
    

# Exceptions

class IllegalTokenException(Exception):
    def __init__(self, token):
        self.token = token

class UnsupportedFeatureException(Exception):
    def __init__(self, feature):
        self.feature = feature

class ProtocolViolationException(Exception):
    pass

class UnexpectedEOFException(Exception):
    pass


# Common Definitions

ASCII_SPACE = 32

def is_ascii(cp):
    return cp != 58 and 33 <= cp <= 126

def is_hex(cp):
    return 48 <= cp <= 57 or 65 <= cp <= 70 or 97 <= cp <= 102
    
def is_hwsp(cp):
    return cp in (9, 32)

def is_percent(cp):
    return cp == 37
    
def is_colon(cp):
    return cp == 58

def is_cr(cp):
    return cp == 13
    
def is_lf(cp):
    return cp == 10

def is_comma(cp):
    return cp == 44

def is_semi(cp):
    return cp == 59

def is_eq(cp):
    return cp == 61

def is_quote(cp):
    return cp == 34

def is_reverse_solidus(cp):
    return cp == 92

def is_lparen(cp):
    return cp == 40

def is_rparen(cp):
    return cp == 41

def is_solidus(cp):
    return cp == 47

def is_tspecial(cp):
    return cp in (40, 41, 60, 62, 64, 44, 59, 58, 92, 34, 47, 91, 93, 63, 61)


RFC2822_DATE_PATTERN = re.compile(r'(?:(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s*,)?\s*(\d{2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{4})(?:\s+(\d{2}):(\d{2})(?::(\d{2}))\s+([+-])(\d{2})(\d{2}))?')
RFC2822_WEEKDAY_MAPPING = {
    'Mon': 0,
    'Tue': 1,
    'Wed': 2,
    'Thu': 3,
    'Fri': 4,
    'Sat': 5,
    'Sun': 6
}

def get_rfc2822_date(value):
    m = RFC2822_DATE_PATTERN.match(value)
    if not m:
        raise IllegalTokenException(value)
    
    week_day = m[1]
    month_day = int(m[2])
    month = int(m[3])
    year = int(m[4])
    hour = int(m[5]) if m[5] else 0
    minute = int(m[6]) if m[6] else 0
    second = int(m[7]) if m[7] else 0
    zone_sign = m[8]
    zone_hr = int(m[9]) if m[9] else None
    zone_min = int(m[10]) if m[10] else None
    
    if year < 1900:
        raise ProtocolViolationException()
    
    if zone_hr is not None:
        tzinfo = timezone(timedelta(hours=zone_hr, minutes=zone_min))
        if zone_sign == '-':
            tzinfo = -1 * tzinfo
    else:
        tzinfo = None
    
    try:
        result = datetime(year, month, month_day, hour, minute, second, 0, tzinfo)
    except ValueError:
        raise ProtocolViolationException()
    
    if week_day and RFC2822_DATE_PATTERN[week_day] != result.weekday():
        raise ProtocolViolationException()
    
    return result




# Multipart Segments
    
#--------------------------------------------
# Stream
#--------------------------------------------

#class MultipartStream:
#    
#    def __init__(self, byte_stream, length):
#        self.data = byte_stream.read(length)
#        self.cur_index = 0
#        
#    def next_cp(self):
#        data = self.data
#        cur_index = self.cur_index
#        
#        if cur_index >= len(data):
#            return None
#        
#        self.cur_index += 1
#        return data[cur_index]
#    
#    def lookahead(self, k=1):
#        data = self.data
#        next_index = self.cur_index + k - 1
#        
#        return data[next_index] if next_index < len(data) else None

class MultipartStream:
    
    read_size = 1024000
    
    def __init__(self, byte_stream, length=None):
        self.byte_stream = byte_stream
        self.length = length
        
        self.total_read = 0
        
        self.buf = bytearray(MultipartStream.read_size)
        self.of_buf = None
        self.cur_max = -1
        self.cur_index = 0
        
    def next_cp(self):
        buf = self.buf
        cur_index = self.cur_index
        cur_max = self.cur_max
        
        if cur_index >= cur_max:
            self.__do_read()
            cur_index = self.cur_index
            if self.cur_max == 0:
                return None
        
        self.cur_index += 1
        
        if cur_index >= 0:
            return self.buf[cur_index]
        else:
            of_buf = self.of_buf
            return of_buf[len(of_buf) + cur_index]
    
    def lookahead(self, k=1):
        next_index = self.cur_index + k - 1
        cur_max = self.cur_max
        
        if next_index >= cur_max and cur_max > 0:
            self.__do_read()
            next_index = self.cur_index + k - 1
            if self.cur_max == 0:
                return None
        
        if next_index >= 0:
            return self.buf[next_index] if next_index < self.cur_max else None
        else:
            of_buf = self.of_buf
            return of_buf[len(of_buf) + next_index]
    
    def __do_read(self):
        cur_index = self.cur_index
        cur_max = self.cur_max
        buf = self.buf
        
        length = self.length
        if length is not None:
            total_read = self.total_read
            if total_read + len(buf) > length:
                buf = self.buf = bytearray(length - total_read)
            
        next_max = self.byte_stream.readinto(buf)
        self.total_read += next_max
            
        
        if cur_index < cur_max:
            self.of_buf = self.buf[cur_index:cur_max]
            self.cur_index = -1 * (cur_max - cur_index)
        else:
            self.of_buf = None
            self.cur_index = 0
        
        self.cur_max = next_max

#--------------------------------------------
# Lexer
#--------------------------------------------

class TokenType(Enum):
    OCTET_STR = auto()
    ASCII_STR = auto()
    COLON = auto()
    HWSP = auto()
    CR = auto()
    LF = auto()
    CRLF = auto()
    BOUNDARY = auto()
    END_OF_MESSAGE = auto()
    EOF = auto()

class Token:

    def __init__(self, type, value=None):
        self.type = type
        self.value = value
        
    def __str__(self):
        return f'{self.type}: "{self.value}"'
        
Token.COLON = Token(TokenType.COLON, ':')
Token.CR = Token(TokenType.CR, '\r')
Token.LF = Token(TokenType.LF, '\n')
Token.CRLF = Token(TokenType.CRLF, '\r\n')
Token.EOF = Token(TokenType.EOF)

class MultipartLexer:
    
    def __init__(self, stream, boundary):
        self.stream = stream
        self.boundary_token = Token(TokenType.BOUNDARY, f'--{boundary}')
        self.end_message_token = Token(TokenType.END_OF_MESSAGE, f'--{boundary}--')
        self.buf = bytearray()
        self.la_token = None
    
    def next_token(self):
        stream = self.stream
        state = 0
        buf = self.buf
        
        if self.la_token:
            la_token = self.la_token
            self.la_token = None
            return la_token
            
        
        while True:
            cp = stream.next_cp()
            
            if cp is None:
                return Token.EOF
            
            if state == 0:
                if is_colon(cp):
                    return Token.COLON
                elif is_lf(cp):
                    return Token.LF
                    
                elif is_cr(cp):
                    if is_lf(stream.lookahead()):
                        stream.next_cp()
                        return Token.CRLF
                    else:
                        return Token.CR
                
                elif is_hwsp(cp):
                    state = 1
                elif is_ascii(cp):
                    state = 3
                else:
                    state = 4
                
            # HWSP_STR
            if state == 1:
                buf.append(cp)
                if not is_hwsp(stream.lookahead()):
                    result = Token(TokenType.HWSP, buf.decode('ascii'))
                    state = 0
                    buf.clear()
                    return result
            
            # ASCII_STR
            if state == 3:
                buf.append(cp)
                if not is_ascii(stream.lookahead()):
                    value = buf.decode('ascii')
                    if value == self.boundary_token.value:
                        result = self.boundary_token
                    elif value == self.end_message_token.value:
                        result = self.end_message_token
                    else:
                        result = Token(TokenType.ASCII_STR, value)
                    
                    state = 0
                    buf.clear()
                    return result
            
            # OCTET_STR
            if state == 4:
                buf.append(cp)
                if max([fn(stream.lookahead()) for fn in (is_ascii, is_hex, is_hwsp, is_colon, is_cr, is_lf, lambda cp: cp is None)]):
                    result = Token(TokenType.OCTET_STR, bytes(buf))
                    state = 0
                    buf.clear()
                    return result

    
    def lookahead(self):
        if self.la_token:
            return self.la_token
        
        la_token = self.la_token = self.next_token()
        return la_token


#--------------------------------------------
# Parser
#--------------------------------------------

class MultipartBodyBuffer:
    
    def __init__(self, temp_file=None):
        self.temp_file = temp_file
        self._handle = open(temp_file, 'wb') if temp_file else bytearray()
    
    def __iadd__(self, other):
        handle = self._handle
        
        if self.temp_file:
            handle.write(other)
        else:
            handle += other
        
        return self

    
    def finish(self):
        handle = self._handle
        if self.temp_file:
            handle.close()
            return MultipartBody(True, self.temp_file)
        else:
            return MultipartBody(False, bytes(handle))
        
        
    

class MultipartBody:
    def __init__(self, is_file, value):
        self.is_file = is_file
        self.value = value
    
    

class MultipartParser:

    def __init__(self, lexer, form_charset):
        self.lexer = lexer
        
        self.form_charset = form_charset
        self.file_registry = set()
        
    
    def multipart(self):
        parts = []
        while True:
            part = self.part()
            if not part:
                break
            parts.append(part)
        
        return parts
    
    def part(self):
        lexer = self.lexer
        
        # Parse Headers
        t = lexer.next_token()
        if t.type == TokenType.END_OF_MESSAGE:
            return None
            
        if t.type != TokenType.BOUNDARY:
            raise IllegalTokenException(t)
            
        t = lexer.next_token()
        if t.type != TokenType.CRLF:
            raise IllegalTokenException(t)
        
        headers = HeaderMapping()
        while True:
            header = self.header()
            if not header:
                break
            headers[header.name] = header


        # Process Headers
        if not 'Content-Disposition' in headers:
            raise ProtocolViolationException()
        
        content_disposition = headers['Content-Disposition']
        if content_disposition.type != 'form-data' or content_disposition.subtype:
            raise ProtocolViolationException()
        
        field_name = content_disposition.get_param('name')
        if not field_name:
            raise ProtocolViolationException()
        
        
        headers['Content-Disposition'] = ContentDispositionHeader(content_disposition)
        
        
        # Read Body
        if headers['Content-Disposition'].filename:
            tf = tempfile.mkstemp()
            self.file_registry.add(tf)
            f = tf[1]
            
            body = MultipartBodyBuffer(f)
        else:
            body = MultipartBodyBuffer()

        while True:
            t = lexer.next_token()
            if t.type == TokenType.OCTET_STR:
                body += t.value
            elif t.type in (TokenType.ASCII_STR, TokenType.COLON, TokenType.HWSP, TokenType.CR, TokenType.LF):
                body += t.value.encode('ascii')
            elif t.type == TokenType.CRLF:  
                la = lexer.lookahead()
                if la.type in (TokenType.BOUNDARY, TokenType.END_OF_MESSAGE):
                    return Part(headers, body.finish())
                elif la.type == TokenType.EOF:
                    raise IllegalTokenException(la)
                else:
                    body += t.value.encode('ascii')
    
    
    def header(self):
        lexer = self.lexer
        
        t = lexer.next_token()
        if t.type == TokenType.CRLF:
            return None
            
        if t.type != TokenType.ASCII_STR:
            raise IllegalTokenException(t)
        name = t.value
        
        t = lexer.next_token()
        if t.type != TokenType.COLON:
            raise IllegalTokenException(t)
        
        t = self.skip_hwsp()
        buf = bytearray()
        line_buf = bytearray()
        while True:
            if t.type in (TokenType.ASCII_STR, TokenType.COLON, TokenType.HWSP):
                buf += t.value.encode('ascii')
            elif t.type == TokenType.OCTET_STR:
                buf += t.value
            elif t.type == TokenType.CRLF:
                if lexer.lookahead().type == TokenType.HWSP:
                    # Blank fold lines not allowed (if all characters in line_buf are HWSP, raise exception)
                    if not len(line_buf) or min(map(line_buf, is_hwsp)):
                        raise IllegalTokenException(t)
                    buf += line_buf
                    line_buf.clear()
                    line_buf.append(ASCII_SPACE)
                    lexer.next_token()
                else:
                    buf += line_buf
                    break
            else:
                raise IllegalTokenException(t)
            
            t = lexer.next_token()
        
        if t.type != TokenType.CRLF:
            raise IllegalTokenException(t)
        
        value = bytes(buf)
        if name.casefold() in ('content-disposition', 'content-type'):
            header_stream = ParameterizedHeaderStream(value)
            header_lexer = ParameterizedHeaderLexer(header_stream, self.form_charset)
            header_parser = ParameterizedHeaderParser(header_lexer)
            
            media_type = header_parser.media_type()
            la = header_lexer.lookahead()
            if la.type != HeaderTokenType.EOF:
                raise IllegalTokenException(la)
            
            
            
        elif name.casefold() == 'content-transfer-encoding':
            raise UnsupportedFeatureException('Content-Transfer-Encoding')
        else:
            media_type = None
        
        return Header(name, value, media_type)
    
    
    def dispose(self):
        for fd, fname in self.file_registry:
            os.close(fd)
            os.unlink(fname)
        
        self.file_registry = None
    
    def skip_hwsp(self):
        lexer = self.lexer
        t = None
        while True:
            t = lexer.next_token()
            if t.type != TokenType.HWSP:
                return t
    


# Type Headers
    

#--------------------------------------------
# Stream
#--------------------------------------------

class ParameterizedHeaderStream:
    
    def __init__(self, data):
        self.data = data
        self.cur_index = 0
        
    def next_cp(self):
        data = self.data
        cur_index = self.cur_index
        
        if cur_index >= len(data):
            return None
        
        self.cur_index += 1
        return data[cur_index]
    
    def lookahead(self, k=1):
        data = self.data
        next_index = self.cur_index + k - 1
        
        return data[next_index] if next_index < len(data) else None
        

#--------------------------------------------
# Lexer
#--------------------------------------------



class HeaderTokenType(Enum):
    QUOTED_STR = auto()
    COMMENT = auto()
    HWSP = auto()
    COMMA = auto()
    SEMI = auto()
    EQ = auto()
    ATOM = auto()
    EOF = auto()
    SOLIDUS = auto()
    TSPECIAL = auto()

class HeaderToken:
    def __init__(self, type, value=None):
        self.type = type
        self.value = value
        
    def __str__(self):
        return f'{self.type}: "{self.value}"'
        
HeaderToken.COMMA = HeaderToken(HeaderTokenType.COMMA, ',')
HeaderToken.SEMI = HeaderToken(HeaderTokenType.SEMI, ';')
HeaderToken.EQ = HeaderToken(HeaderTokenType.EQ, '=')
HeaderToken.EOF = HeaderToken(HeaderTokenType.EOF)
HeaderToken.SOLIDUS = HeaderToken(HeaderTokenType.SOLIDUS, '/')


class ParameterizedHeaderLexer:
    
    def __init__(self, stream, form_charset):
        self.stream = stream
        self.form_charset = form_charset
        self.state = 0
        self.buf = bytearray()
        self.la_token = None
    
    def next_token(self):
        stream = self.stream
        state = self.state
        buf = self.buf
        form_charset = self.form_charset
        
        if self.la_token:
            la_token = self.la_token
            self.la_token = None
            return la_token
        
        while True:
            cp = stream.next_cp()
            
            if cp is None:
                if state == 0:
                    return HeaderToken.EOF
                else:
                    raise UnexpectedEOFException()
                    
            
            if state == 0:
                if is_quote(cp):
                    state = self.state = 1
                    continue
                elif is_lparen(cp):
                    state = self.state = 3
                    continue
                elif is_hwsp(cp):
                    state = self.state = 5
                elif is_comma(cp):
                    return HeaderToken.COMMA
                elif is_semi(cp):
                    return HeaderToken.SEMI
                elif is_eq(cp):
                    return HeaderToken.EQ
                elif is_solidus(cp):
                    return HeaderToken.SOLIDUS
                elif is_tspecial(cp):
                    buf.append(cp)
                    result = HeaderToken(HeaderTokenType.TSPECIAL, buf.decode('utf-8'))
                    buf.clear()
                    return result
                else:
                    state = 6
            
            # Quoted String
            if state == 1:
                if is_quote(cp):
                    result = HeaderToken(HeaderTokenType.QUOTED_STR, buf.decode(form_charset))
                    buf.clear()
                    state = self.state = 0
                    return result
                elif is_reverse_solidus(cp):
                    state = self.state = 2
                    continue
                else:
                    buf.append(cp)
            
            # Quoted String/Quoted Pair
            if state == 2:
                buf.append(cp)
                state = self.state = 1
            
            # Comment
            if state == 3:
                if is_rparen(cp):
                    result = HeaderToken(HeaderTokenType.COMMENT, buf.decode(form_charset))
                    buf.clear()
                    state = self.state = 0
                    return result
                elif is_reverse_solidus(cp):
                    state = self.state = 4
                    continue
                else:
                    buf.append(cp)
            
            # Comment/Quoted Pair
            if state == 4:
                buf.append(cp)
                state = self.state = 3
            
            
            # HWSP
            if state == 5:
                buf.append(cp)
                if not is_hwsp(stream.lookahead()):
                    result = HeaderToken(HeaderTokenType.HWSP, buf.decode(form_charset))
                    buf.clear()
                    state = self.state = 0
                    return result
            
            # Atom
            if state == 6:
                buf.append(cp)
                if max([fn(stream.lookahead()) for fn in (is_hwsp, is_tspecial, lambda cp: cp is None)]):
                    result = HeaderToken(HeaderTokenType.ATOM, buf.decode(form_charset))
                    state = self.state = 0
                    buf.clear()
                    return result
        
    def lookahead(self):
        if self.la_token:
            return self.la_token
        
        self.la_token = la_token = self.next_token()
        return la_token

#--------------------------------------------
# Parser
#--------------------------------------------

class ParameterizedHeaderParser:

    def __init__(self, lexer):
        self.lexer = lexer
    
    def media_types(self):
        lexer = self.lexer
        
        media_types = []
        while lexer.lookahead().type != HeaderTokenType.EOF:
            media_types.append(self.media_type())
            
        return media_types
    
    
    def media_type(self):
        lexer = self.lexer
        
        t = self.skip_chwsp()
        if t.type != HeaderTokenType.ATOM:
            raise IllegalTokenException(t)
        type = t.value
        
        la = lexer.lookahead()
        if la.type == HeaderTokenType.SOLIDUS:
            lexer.next_token()
            t = lexer.next_token()
            if t.type != HeaderTokenType.ATOM:
                raise IllegalTokenException(t)
            subtype = t.value
        else:
            subtype = None
        
        parameters = HeaderMapping()
        while True:
            t = self.skip_chwsp()
            if t.type == HeaderTokenType.SEMI:
                parm_name, parm_value = self.parameter()
                parameters[parm_name] = parm_value
            elif t.type in (HeaderTokenType.COMMA, HeaderTokenType.EOF):
                break
            else:
                raise IllegalTokenException(t)
        
        return MediaType(type, subtype, parameters)
    
    def parameter(self):
        lexer = self.lexer
        
        t = self.skip_chwsp()
        if t.type != HeaderTokenType.ATOM:
            raise IllegalTokenException(t)
        name = t.value
        
        t = lexer.next_token()
        if t.type != HeaderTokenType.EQ:
            raise IllegalTokenException(t)
        
        t = lexer.next_token()
        if t.type not in (HeaderTokenType.ATOM, HeaderTokenType.QUOTED_STR):
            raise IllegalTokenException(t)
        value = t.value
        
        return (name, value)
        
    
    def skip_chwsp(self):
        lexer = self.lexer
        t = None
        while True:
            t = lexer.next_token()
            if t.type not in (HeaderTokenType.HWSP, HeaderTokenType.COMMENT):
                return t
        
        

    