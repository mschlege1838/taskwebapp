# Imports

# Standard
import re
import sqlite3

from datetime import datetime, timedelta
from enum import Enum

# User
from taskwebapp.domain import TaskReference, TaskStatus, Task, AttachmentReference, TaskNote, Attachment, TaskDashboardData
from taskwebapp.domain.task.search import TaskSearchLogicalOp, TaskSearchStrOp, TaskSearchNumOp, TaskSearchField, \
    TaskSearchSimpleExpr, TaskSearchIsAnyExpr, TaskSearchExpr, TaskSearchGroupExpr



like_escape_pattern = re.compile('([_%+])')
def like_escape(val, case_sensitive=False):
    result = like_escape_pattern.sub('+\1', val)
    return result if case_sensitive else result.casefold()



schema_version = 1

def sqlite3_to_date(v):
    if v is None:
        return None
    if not isinstance(v, str):
        raise ValueError(f'TO_DATE: Expected str, got {type(v)}: {v}')
    return v[0:10]

def sqlite3_casefold(v):
    if v is None:
        return None
    if not isinstance(v, str):
        return v
    return v.casefold()

def get_connection(db_fname):
    connection = sqlite3.connect(db_fname, detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
    connection.row_factory = sqlite3.Row
    connection.create_function('TO_DATE', 1, sqlite3_to_date)
    connection.create_function('CASEFOLD', 1, sqlite3_casefold)
    
    try:
        c = connection.cursor()
        
        c.execute('PRAGMA user_version')
        if schema_version == next(c)[0]:
            c.close()
            return connection
        
        # DDL
        
        # TaskStatus
        c.execute('''
        CREATE TABLE STATUS_DM (
          STATUS_ID INTEGER PRIMARY KEY
          , STATUS_NM TEXT NOT NULL
        )
          WITHOUT ROWID
        ''')
        
        
        c.executemany('''
        INSERT INTO STATUS_DM
          (STATUS_ID, STATUS_NM)
          VALUES (?, ?)
        ''', [(v.value, v.name) for v in TaskStatus])
        
        
        # Task
        c.execute('''
        CREATE TABLE TASK (
          TASK_ID INTEGER PRIMARY KEY
          , TASK_NM TEXT NOT NULL
          , STATUS_ID INTEGER NOT NULL
          , DUE_TS TIMESTAMP
          , MOD_TS TIMESTAMP
          
          , CONSTRAINT FKTSK1
              FOREIGN KEY (STATUS_ID)
              REFERENCES STATUS_DM (STATUS_ID)
        )
        ''')
        
        # Note
        c.execute('''
        CREATE TABLE NOTE (
          NOTE_ID INTEGER PRIMARY KEY
          , TEXT TEXT
          , MOD_TS TIMESTAMP NOT NULL
        )
        ''')
        
        # Attachment
        c.execute('''
        CREATE TABLE ATTACHMENT (
          ATTACHMENT_ID INTEGER PRIMARY KEY
          , ATTACHMENT_NM TEXT NOT NULL
          , MIME_TYPE TEXT NOT NULL
          , CONTENT BLOB NOT NULL
          , CRTN_TS TIMESTAMP NOT NULL
        )
        ''')
        
        # Tags
        c.execute('''
        CREATE TABLE TAG (
          TAG_ID INTEGER PRIMARY KEY
          , TAG_TEXT TEXT
          
          , CONSTRAINT UTG1
              UNIQUE (TAG_TEXT)
        )
        ''')
        
        
        # Relationships
        c.execute('''
        CREATE TABLE TASK_TAG (
          TASK_ID INTEGER NOT NULL
          , TAG_ID INTEGER NOT NULL
          
          , CONSTRAINT PKTSKTG
              PRIMARY KEY (TASK_ID, TAG_ID)
        )
          WITHOUT ROWID
        ''')
        
        c.execute('''
        CREATE TABLE TASK_NOTE (
          TASK_ID INTEGER NOT NULL
          , NOTE_ID INTEGER NOT NULL
          , PINNED_IND INTEGER NOT NULL
          
          , CONSTRAINT PKTSKNT
              PRIMARY KEY (TASK_ID, NOTE_ID)
          
          , CONSTRAINT FKTSKNT1
              FOREIGN KEY (TASK_ID)
              REFERENCES TASK (NOTE_ID)
          
          , CONSTRAINT FKTSKNT2
              FOREIGN KEY (NOTE_ID)
              REFERENCES NOTE (NOTE_ID)
        )
          WITHOUT ROWID
        ''')
        
        c.execute('''
        CREATE TABLE NOTE_ATTACHMENT (
          NOTE_ID INTEGER NOT NULL
          , ATTACHMENT_ID INTEGER NOT NULL
          
          , CONSTRAINT PKNTATT
              PRIMARY KEY (NOTE_ID, ATTACHMENT_ID)
          
          , CONSTRAINT FKNTATT1
              FOREIGN KEY (NOTE_ID)
              REFERENCES NOTE (NOTE_ID)
          
          , CONSTRAINT FKNTATT2
              FOREIGN KEY (ATTACHMENT_ID)
              REFERENCES ATTACHMENT (ATTACHMENT_ID)
        )
          WITHOUT ROWID
        ''')
        
        
        c.execute(f'PRAGMA user_version = {schema_version}')
        
        connection.commit()
        c.close()
        return connection
    except Exception as e:
        connection.rollback()
        connection.close()
        raise e




class TaskService:
    def __init__(self, db_fname):
        self.db_fname = db_fname
    
    def get_dashboard_data(self):
        connection = get_connection(self.db_fname)
        
        now = datetime.now()
        next_sunday = now + timedelta(6 - now.weekday())
        try:
            c = connection.cursor()
            
            # Late
            c.execute('''
            SELECT
                TASK_ID
                , TASK_NM
                , STATUS_ID
                , DUE_TS
                , MOD_TS
              FROM TASK
              WHERE DUE_TS < ?
              ORDER BY DUE_TS
              LIMIT 20
            ''', (now,))
            
            late = [TaskReference(r['TASK_ID'], r['TASK_NM'], TaskStatus(r['STATUS_ID']), r['DUE_TS'], r['MOD_TS']) for r in c]
            
            
            # Due Today
            c.execute('''
            SELECT
                TASK_ID
                , TASK_NM
                , STATUS_ID
                , DUE_TS
                , MOD_TS
              FROM TASK
              WHERE TO_DATE(DUE_TS) = TO_DATE(?)
              ORDER BY DUE_TS
              LIMIT 20
            ''', (now,))
            
            due_today = [TaskReference(r['TASK_ID'], r['TASK_NM'], TaskStatus(r['STATUS_ID']), r['DUE_TS'], r['MOD_TS']) for r in c]
            
            
            # Due this week
            c.execute('''
            SELECT
                TASK_ID
                , TASK_NM
                , STATUS_ID
                , DUE_TS
                , MOD_TS
              FROM TASK
              WHERE TO_DATE(DUE_TS) BETWEEN TO_DATE(?) AND TO_DATE(?)
              ORDER BY DUE_TS
              LIMIT 20
            ''', (now, next_sunday))
            
            due_this_week = [TaskReference(r['TASK_ID'], r['TASK_NM'], TaskStatus(r['STATUS_ID']), r['DUE_TS'], r['MOD_TS']) for r in c]
        
            
            # Pending
            c.execute('''
            SELECT
                TASK_ID
                , TASK_NM
                , STATUS_ID
                , DUE_TS
                , MOD_TS
              FROM TASK
              WHERE STATUS_ID = 2
              ORDER BY DUE_TS
              LIMIT 20
            ''')
            
            pending = [TaskReference(r['TASK_ID'], r['TASK_NM'], TaskStatus(r['STATUS_ID']), r['DUE_TS'], r['MOD_TS']) for r in c]
            
            # Due Later
            c.execute('''
            SELECT
                TASK_ID
                , TASK_NM
                , STATUS_ID
                , DUE_TS
                , MOD_TS
              FROM TASK
              WHERE DUE_TS > ?
                AND STATUS_ID = 1
              ORDER BY DUE_TS
              LIMIT 20
            ''', (next_sunday,))
            
            due_later = [TaskReference(r['TASK_ID'], r['TASK_NM'], TaskStatus(r['STATUS_ID']), r['DUE_TS'], r['MOD_TS']) for r in c]
            
            
            connection.commit()
        except Exception as e:
            connection.rollback()
            raise e
        finally:
            connection.close()
        
        
        return TaskDashboardData(late, due_today, due_this_week, pending, due_later)  
    
    def search(self, criteria):
        if not criteria:
            return []
    
        builder = CriteriaBuilder()
        builder.add_criteria(criteria)
        
        sql = '''
        SELECT
            TASK_ID
            , TASK_NM
            , STATUS_ID
            , DUE_TS
            , MOD_TS
          FROM TASK
          WHERE $CLAUSE$
        '''.replace('$CLAUSE$', ' '.join(builder.sql))
        
        connection = get_connection(self.db_fname)
        try:
            c = connection.cursor()
            
            c.execute(sql, builder.params)
            result = [TaskReference(r['TASK_ID'], r['TASK_NM'], TaskStatus(r['STATUS_ID']), r['DUE_TS'], r['MOD_TS']) for r in c]
            
            connection.commit()
        except Exception as e:
            connection.rollback()
            raise e
        finally:
            connection.close()
        
        return result
    
    def get_task(self, id):
        connection = get_connection(self.db_fname)
        try:
            c = connection.cursor()
        
            # Base-Table fields.
            c.execute('''
            SELECT
                TASK_ID
                , TASK_NM
                , STATUS_ID
                , DUE_TS
              FROM TASK
              WHERE TASK_ID = ?
            ''', (id,))
            
            r = c.fetchone()
            if not r:
                connection.commit()
                return None
            else:
                task = Task(r['TASK_ID'], r['TASK_NM'], TaskStatus(r['STATUS_ID']), r['DUE_TS'], None, [], [])
            
            # Tags
            c.execute('''
            SELECT
                tg.TAG_TEXT
              FROM TASK_TAG tt
              JOIN TAG tg
                ON tg.TAG_ID = tt.TAG_ID
              WHERE tt.TASK_ID = ?
            ''', (id,))
            
            task.tags = [r['TAG_TEXT'] for r in c]
            
            # Notes
            c.execute('''
            SELECT
                n.NOTE_ID
                , n.TEXT
                , tn.PINNED_IND
                , n.MOD_TS
              FROM TASK_NOTE tn
              JOIN NOTE n
                ON n.NOTE_ID = tn.NOTE_ID
              WHERE tn.TASK_ID = ?
            ''', (id,))
            
            notes = {}
            for r in c:
                notes[r['NOTE_ID']] = (TaskNote(r['NOTE_ID'], r['TEXT'], [], r['MOD_TS']), r['PINNED_IND'])
            
            # Attachments
            c.execute('''
            SELECT
                na.NOTE_ID
                , a.ATTACHMENT_ID
                , a.ATTACHMENT_NM
                , a.MIME_TYPE
                , a.CRTN_TS
              FROM NOTE_ATTACHMENT na
              JOIN ATTACHMENT a
                ON a.ATTACHMENT_ID = na.ATTACHMENT_ID
              WHERE na.NOTE_ID IN (
                  SELECT NOTE_ID
                    FROM TASK_NOTE
                    WHERE TASK_ID = ?
              )
            ''', (id,))
            
            for r in c:
                notes[r['NOTE_ID']][0].attachment_references.append(AttachmentReference(r['ATTACHMENT_ID'], r['ATTACHMENT_NM'], r['MIME_TYPE'], r['CRTN_TS']))
            
            
            connection.commit()
        except Exception as e:
            connection.rollback()
            raise e
        finally:
            connection.close()
        
        
        for note, pinned in notes.values():
            if pinned:
                task.pinned_notes.append(note)
            else:
                task.notes.append(note)
        
        task.notes.sort(key=lambda v: -1 * v.mod_ts.timestamp())
        
        return task
    
    def create_task(self, task):
        '''
        task (Task): Task to create
        
        Creates task. Sets task_id on task. Also cleans up all orphaned notes/attachments. Attachment and note
        IDs are expected to be already assigned. Adds all tags that don't exist to storage. Ties note attachments
        to notes.
        '''
        
        now = datetime.now()
        connection = get_connection(self.db_fname)
        try:
            c = connection.cursor()
            
            # Base fields.
            c.execute('''
            INSERT INTO TASK
              (TASK_NM, STATUS_ID, DUE_TS, MOD_TS)
              VALUES (?, ?, ?, ?)
            ''', (task.name, task.status.value, task.due_ts, now))
            
            c.execute('SELECT last_insert_rowid()')
            task.task_id = task_id = next(c)[0]
            
            
            # Tags
            c.execute('''
            CREATE TEMPORARY TABLE TT_TAG (
              TAG_TEXT TEXT
            )
            ''')
            
            c.executemany('''
            INSERT INTO TT_TAG
              (TAG_TEXT)
              VALUES (?)
            ''', [(v,) for v in task.tags])
            
            c.execute('''
            INSERT INTO TAG
              (TAG_TEXT)
              SELECT
                  TAG_TEXT
                FROM TT_TAG
                WHERE TAG_TEXT NOT IN (
                    SELECT TAG_TEXT
                      FROM TT_TAG
                )
            ''')
            
            c.execute('''
            INSERT INTO TASK_TAG
              (TASK_ID, TAG_ID)
              SELECT
                  ?
                  , TAG_ID
                FROM TAG
                WHERE TAG_TEXT IN (
                    SELECT TAG_TEXT
                      FROM TT_TAG
                )
            ''', (task_id,))
            
            c.execute('DROP TABLE TT_TAG')
            
            
            # Notes
            c.executemany('''
            INSERT INTO TASK_NOTE
              (TASK_ID, NOTE_ID, PINNED_IND)
              VALUES (?, ?, ?)
            ''', [(task_id, v.note_id, 0) for v in task.notes] + [(task_id, v.note_id, 1) for v in task.pinned_notes])
            
            
            
            
            # Cleanup
            self.__cleanup(c)
            
            connection.commit()
        except Exception as e:
            connection.rollback()
            raise e
        finally:
            connection.close()
    
    def update_task(self, task):
        '''
        task (Task): Task to update
        
        Updates task, cleans up orphaned notes/attachments. Attachment and note
        IDs are expected to be already assigned. Adds all tags that don't exist to storage. Ties note attachments
        to notes.
        '''
        now = datetime.now()
        connection = get_connection(self.db_fname)
        try:
            c = connection.cursor()
            
            # Check if task exists
            c.execute('''
            SELECT COUNT(*)
              FROM TASK
              WHERE TASK_ID = ?
            ''', (task.task_id,))
            
            if next(c)[0] == 0:
                raise ValueError(f'Task does not exist: {task_id}')
            
            # Basic Fields
            c.execute('''
            UPDATE TASK
              SET TASK_NM = ?
                    , STATUS_ID = ?
                    , DUE_TS = ?
                    , MOD_TS = ?
                WHERE TASK_ID = ?
            ''', (task.name, task.status.value, task.due_ts, now, task.task_id))
            
            
            
            # Tags
            c.execute('''
            CREATE TEMPORARY TABLE TT_TAG (
              TAG_TEXT TEXT
            )
            ''')
            
            c.executemany('''
            INSERT INTO TT_TAG
              (TAG_TEXT)
              VALUES (?)
            ''', [(v,) for v in task.tags])
            
            
            c.execute('''
            INSERT INTO TAG
              (TAG_TEXT)
              SELECT
                  TAG_TEXT
                FROM TT_TAG
                WHERE TAG_TEXT NOT IN (
                    SELECT TAG_TEXT
                      FROM TAG
                )
            ''')
            
            
            c.execute('''
            DELETE FROM TASK_TAG
              WHERE TASK_ID = ?
                AND TAG_ID NOT IN (
                    SELECT TAG_ID
                      FROM TAG
                      WHERE TAG_TEXT IN (
                          SELECT TAG_TEXT
                            FROM TT_TAG
                      )
                )
            ''', (task.task_id,))
            
            c.execute('''
            INSERT INTO TASK_TAG
              (TASK_ID, TAG_ID)
              SELECT
                  ?
                  , TAG_ID
                FROM TAG
                WHERE TAG_TEXT IN (
                    SELECT TAG_TEXT
                      FROM TT_TAG
                )
              ON CONFLICT DO NOTHING
            ''', (task.task_id,))
            
            
            
            # Notes
            c.execute('''
            CREATE TEMPORARY TABLE TT_NOTE (
              NOTE_ID INTEGER
              , PINNED_IND INTEGER
            )
            ''')
            
            c.executemany('''
            INSERT INTO TT_NOTE
              (NOTE_ID, PINNED_IND)
              VALUES (?, ?)
            ''', [(n.note_id, 1) for n in task.pinned_notes] + [(n.note_id, 0) for n in task.notes])
            
            c.execute('''
            DELETE FROM TASK_NOTE
              WHERE TASK_ID = ?
                AND NOTE_ID NOT IN (
                    SELECT NOTE_ID
                      FROM TT_NOTE
                )
            ''', (task.task_id,))
            
            c.execute('''
            INSERT INTO TASK_NOTE
              (TASK_ID, NOTE_ID, PINNED_IND)
              SELECT
                  ?
                  , NOTE_ID
                  , PINNED_IND
                FROM TT_NOTE
                WHERE true
              ON CONFLICT (TASK_ID, NOTE_ID) DO UPDATE
                SET PINNED_IND = excluded.PINNED_IND
            ''', (task.task_id,))
            
            
            
            # Cleanup
            self.__cleanup(c)
            
            connection.commit()
        except Exception as e:
            connection.rollback()
            raise e
        finally:
            connection.close()
    
    
    def __cleanup(self, c):
        c.execute('''
        DELETE FROM NOTE_ATTACHMENT
          WHERE NOTE_ID NOT IN (
              SELECT NOTE_ID
                FROM TASK_NOTE
          )
        ''')
        
        c.execute('''
        DELETE FROM ATTACHMENT
          WHERE ATTACHMENT_ID NOT IN (
              SELECT ATTACHMENT_ID
                FROM NOTE_ATTACHMENT
          )
        ''')
        
        c.execute('''
        DELETE FROM NOTE
          WHERE NOTE_ID NOT IN (
              SELECT NOTE_ID
                FROM TASK_NOTE
          )
        ''')


class NoteService:
    def __init__(self, db_fname):
        self.db_fname = db_fname
    
    def create_notes(self, notes):
        '''
        notes dict[int] = TaskNote: list of TaskNotes to create by reference number
        
        Creates notes in notes, assigning permanent IDs. Updates note_id on given TaskNotes.
        '''
        
        if not notes:
            return
        
        now = datetime.now()
        connection = get_connection(self.db_fname)
        try:
            c = connection.cursor()
            
            for local_id, note in notes.items():
                c.execute('''
                INSERT INTO NOTE
                  (TEXT, MOD_TS)
                  VALUES (?, ?)
                ''', (note.text, now))
                
                c.execute('SELECT last_insert_rowid()')
                note.note_id = next(c)[0]
                
            
            c.executemany('''
            INSERT INTO NOTE_ATTACHMENT
              (NOTE_ID, ATTACHMENT_ID)
              VALUES (?, ?)
            ''', [(n.note_id, a.attachment_id) for n in notes.values() for a in n.attachment_references])
            
            connection.commit()
        except Exception as e:
            connection.rollback()
            raise e
        finally:
            connection.close()
        
    
    def update_notes(self, notes):
        '''
        notes (TaskNote[]): TaskNotes to update
        '''
        
        if not notes:
            return
        
        now = datetime.now()
        connection = get_connection(self.db_fname)
        try:
            c = connection.cursor()
            
            # Validation
            c.execute('''
            CREATE TEMPORARY TABLE TT_NOTE (
              NOTE_ID INTEGER
            )
            ''')
            
            
            c.executemany('''
            INSERT INTO TT_NOTE
              (NOTE_ID)
              VALUES (?)
            ''', [(n.note_id,) for n in notes])
            
            c.execute('''
            SELECT
                NOTE_ID
              FROM TT_NOTE
              WHERE NOTE_ID NOT IN (
                  SELECT NOTE_ID
                    FROM NOTE
              )
            ''')
            
            invalid_ids = [r[0] for r in c]
            if invalid_ids:
                raise ValueError(f'Invalid IDs in given notes: {invalid_ids}')
            
            
            # Update Note Text
            update_params = []
            for note in notes:
                update_params.append((note.text, now, note.note_id, note.text))
                
            c.executemany('''
            UPDATE NOTE
              SET TEXT = ?, MOD_TS = ?
              WHERE NOTE_ID = ?
                AND TEXT <> ?
            ''', update_params)
            
            
            # Update Note Attachments
            c.execute('''
            CREATE TEMPORARY TABLE TT_NOTE_ATT (
              NOTE_ID INTEGER
              , ATTACHMENT_ID INTEGER
            )
            ''')
            
            c.executemany('''
            INSERT INTO TT_NOTE_ATT
              (NOTE_ID, ATTACHMENT_ID)
              VALUES (?, ?)
            ''', [(n.note_id, a.attachment_id) for n in notes for a in n.attachment_references])
            
            c.execute('''
            DELETE FROM NOTE_ATTACHMENT AS t
              WHERE NOT EXISTS (
                  SELECT *
                    FROM TT_NOTE_ATT
                    WHERE NOTE_ID = t.NOTE_ID
                      AND ATTACHMENT_ID = t.ATTACHMENT_ID
              )
            ''')
            
            c.execute('''
            INSERT INTO NOTE_ATTACHMENT
              (NOTE_ID, ATTACHMENT_ID)
              SELECT
                  NOTE_ID
                  , ATTACHMENT_ID
                FROM TT_NOTE_ATT
                WHERE true
              ON CONFLICT DO NOTHING
            ''')
            
            
            connection.commit()
        except Exception as e:
            connection.rollback()
            raise e
        finally:
            connection.close()


class AttachmentService:
    def __init__(self, db_fname):
        self.db_fname = db_fname
    
    def create_attachments(self, attachments):
        '''
        attachments (dict[int] = seq[MultipartWrapper]): Attachments
        
        returns seq[AttachmentReference]
        '''
        
        result = {}
        if not attachments:
            return result
        
        now = datetime.now()
        connection = get_connection(self.db_fname)
        try:
            c = connection.cursor()
            
            for id, parts in attachments.items():
                attachment_references = []
                for part in parts:
                    with open(part.value, 'rb') as f:
                        c.execute('''
                        INSERT INTO ATTACHMENT
                          (ATTACHMENT_NM, MIME_TYPE, CONTENT, CRTN_TS)
                          VALUES (?, ?, ?, ?)
                        ''', (part.filename, part.mime_type, f.read(), now))
                        
                        c.execute('SELECT last_insert_rowid()')
                        attachment_id = next(c)[0]
                        
                        attachment_references.append(AttachmentReference(attachment_id, part.filename, part.mime_type, now))
                result[id] = attachment_references
            
            connection.commit()
        except Exception as e:
            connection.rollback()
            raise e
        finally:
            connection.close()
        
        return result
    
    
    def resolve_attachments(self, attachment_mapping):
        '''
        attachment_ids (dict[int] = seq[int]): reference numbers matched to sequences of attachment IDs to resolve
        
        returns dict[int] = seq[AttachmentReference]: resolved AttachmentReferences mapped to given reference numbers
        '''
        
        result = {}
        if not attachment_mapping:
            return result
        
        connection = get_connection(self.db_fname)
        try:
            c = connection.cursor()
            
            c.execute('''
            CREATE TEMPORARY TABLE TT_ATTACHMENT_REF (
              REF_ID INTEGER
              , ATTACHMENT_ID INTEGER
            )
            ''')
            
            c.executemany('''
            INSERT INTO TT_ATTACHMENT_REF
              (REF_ID, ATTACHMENT_ID)
              VALUES (?, ?)
            ''', [(ref_id, attachment_id) for ref_id, attachment_ids in attachment_mapping.items() for attachment_id in attachment_ids])
            
            c.execute('''
            SELECT
                r.REF_ID
                , a.ATTACHMENT_ID
                , a.ATTACHMENT_NM
                , a.MIME_TYPE
                , a.CRTN_TS
              FROM TT_ATTACHMENT_REF r
              JOIN ATTACHMENT a
                ON a.ATTACHMENT_ID = r.ATTACHMENT_ID
            ''')
            
            for r in c:
                ref_id = r['REF_ID']
                if ref_id in result:
                    attachment_references = result[ref_id]
                else:
                    attachment_references = result[ref_id] = []
                attachment_references.append(AttachmentReference(r['ATTACHMENT_ID'], r['ATTACHMENT_NM'], r['MIME_TYPE'], r['CRTN_TS']))
            
            connection.commit()
        except Exception as e:
            connection.rollback()
            raise e
        finally:
            connection.close()
        
        return result
    
    
    def fetch_attachment(self, attachment_id):
        '''
        attachment_id (int): ID of the attachment to fetch.
        
        returns Attachment: Attachment matching the given ID if it exists, otherwise None.
        '''
        
        connection = get_connection(self.db_fname)
        try:
            c = connection.cursor()
            
            c.execute('''
            SELECT
                ATTACHMENT_NM
                , MIME_TYPE
                , CONTENT
                , CRTN_TS
              FROM ATTACHMENT
              WHERE ATTACHMENT_ID = ?
            ''', (attachment_id,))
            
            r = c.fetchone()
            if not r:
                connection.commit()
                return None
            
            result = Attachment(r['ATTACHMENT_NM'], r['CONTENT'], r['MIME_TYPE'])
            
            connection.commit()
        except Exception as e:
            connection.rollback()
            raise e
        finally:
            connection.close()
        
        
        return result



class TagService:
    
    def __init__(self, db_fname):
        self.db_fname = db_fname
    
    def get_matches(self, q):
        if not q:
            return []
        
        connection = get_connection(self.db_fname)
        try:
            c = connection.cursor()
            
            c.execute('''
            SELECT
                TAG_TEXT
              FROM TAG
              WHERE CASEFOLD(TAG_TEXT) LIKE ? ESCAPE '+'
            ''', (f'%{like_escape(q)}%',))
            
            result = [r['TAG_TEXT'] for r in c]
            
            connection.commit()
        except Exception as e:
            connection.rollback()
            raise e
        finally:
            connection.close()
        
        return result




# Util
class InvalidCriteriaException(Exception):
    def __init__(self, field, operator):
        super().__init__(f'Operator {operator} is not compatible with field: {field}')
        self.field = field
        self.operator = operator

class CriteriaBuilder:
    def __init__(self):
        self.sql = []
        self.params = []
    
    def add_criteria(self, criteria):
        if isinstance(criteria, TaskSearchSimpleExpr):
            field = criteria.field
            op = criteria.op
            
            if field == TaskSearchField.NAME and isinstance(op, TaskSearchStrOp):
                self.__str_op('TASK_NM', op, criteria.value)
            elif field == TaskSearchField.DUE and isinstance(op, TaskSearchNumOp):
                self.__num_op('DUE_TS', op, criteria.value)
            else:
                raise InvalidCriteriaException(field, op)
        elif isinstance(criteria, TaskSearchIsAnyExpr):
            field = criteria.field
            params = self.params
            
            if field == TaskSearchField.STATUS:
                self.sql.append(f'STATUS_ID IN ({", ".join("?" for c in criteria.values)})')
                for val in criteria.values:
                    params.append(val.value)
                
            elif field == TaskSearchField.TAGS:
                self.sql.append(f'''
                TASK_ID IN (
                    SELECT TASK_ID
                      FROM TASK_TAG
                      WHERE TAG_ID IN (
                          SELECT TAG_ID
                            FROM TAG
                            WHERE TAG_TEXT IN ($CLAUSE$)
                      )
                )
                '''.replace('$CLAUSE$', ", ".join("?" for c in criteria.values)))
                for val in criteria.values:
                    params.append(val)
            else:
                raise InvalidCriteriaException(field, 'IS ANY')
        elif isinstance(criteria, TaskSearchExpr):
            op = criteria.op
            if op == TaskSearchLogicalOp.AND:
                sql_op = 'AND'
            elif op == TaskSearchLogicalOp.OR:
                sql_op = 'OR'
            else:
                raise ValueError(op)
                
            self.add_criteria(criteria.left_expr)
            self.sql.append(sql_op)
            self.add_criteria(criteria.right_expr)
        elif isinstance(criteria, TaskSearchGroupExpr):
            sql = self.sql
            sql.append('(')
            self.add_criteria(criteria.expr)
            sql.append(')')
    
    def __str_op(self, name, op, value):
        sql = self.sql
        params = self.params
        
        if op in (TaskSearchStrOp.STARTS_WITH, TaskSearchStrOp.CONTAINS):
            sql.append(f"CASEFOLD({name}) LIKE ? ESCAPE '+'")
            params.append(f'{"%" if op == TaskSearchStrOp.CONTAINS else ""}{like_escape(value)}%')
        elif op == TaskSearchStrOp.EQUALS:
            sql.append(f'CASEFOLD({name}) = ?')
            params.append(value.casefold())
        else:
            raise ValueError(op)
    
    def __num_op(self, name, op, value):
        if op == TaskSearchNumOp.EQ:
            sql_op = '='
        elif op == TaskSearchNumOp.GTE:
            sql_op = '>='
        elif op == TaskSearchNumOp.LTE:
            sql_op = '<='
        elif op == TaskSearchNumOp.GT:
            sql_op = '>'
        elif op == TaskSearchNumOp.LT:
            sql_op = '<'
        elif op == TaskSearchNumOp.NE:
            sql_op = '<>'
        else:
            raise ValueError(op)
        
        self.sql.append(f'{name} {sql_op} ?')
        self.params.append(value)
    
