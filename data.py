import sqlite3
from datetime import datetime
from config import config

# TODO: Make DB name configurable

class Image:
    def __init__(self,
                 id=None,
                 content_id=None,
                 filename=None,
                 orig_filename=None,
                 size=None,
                 width=None,
                 height=None,
                 url=None,
                 checksum=None,
                 version=-1,
                 thread_id=-1):
        self.id = id
        self.created = datetime.now()
        self.content_id = content_id
        self.filename = filename
        self.orig_filename = orig_filename
        self.size = size
        self.width = width
        self.height = height
        self.url = url
        self.checksum = checksum
        self.version = version
        self.thread_id = thread_id
            
class Content:
    def __init__(self,
                 id=None,
                 board=None,
                 thread_id=None,
                 page=1,
                 name=None,
                 subject=None,
                 comment=None, 
                 options=None,
                 img=None,
                 replies=None,
                 image_replies=None,
                 quotes=[]):
        self.id = id
        self.created = datetime.now()
        self.board = board
        self.thread_id = thread_id
        self.page = page
        self.name = name
        self.subject = subject
        self.comment = comment
        self.options = options
        self.img = img
        self.quotes = quotes
        self.replies = replies
        self.image_replies = image_replies
        

class Board:
    def __init__(self, 
                 path: str, 
                 name: str, 
                 description: str, 
                 threads: [Content] = []):
        self.path = path
        self.name = name
        self.description = description
        self.threads = threads


class DeletionAuth:
    def __init__(content_id,
                 image_id,
                 password_hash):
        self.content_id = content_id
        self.image_id = image_id
        self.password_hash = password_hash


def create_connection(db_file=config['db_name']):
    conn = None
    try:
        conn = sqlite3.connect(db_file, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
        conn.set_trace_callback(print)
    except Error as e:
        print(e)

    return conn

def insert_image(img, thread, db_file=config['db_name'], parent=None):
    if img:
        conn = create_connection(db_file)
        conn.set_trace_callback(print)
        cur = conn.cursor()
        cur.execute(f'''INSERT INTO image(content_id, filename, orig_filename, size, width, height, checksum, version, url, thread_id)
                    VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', (
                            img.content_id,
                            img.filename,
                            img.orig_filename,
                            img.size,
                            img.width,
                            img.height,
                            img.checksum,
                            img.version,
                            img.url,
                            thread))
        conn.commit()
        return cur.lastrowid
    return None


def insert_content(content, img=None, db_file=config['db_name'], parent=None):
    conn = create_connection(db_file)
    cur = conn.cursor()
    cur.execute(f'''INSERT INTO content(created, board, thread_id, page, name, options, subject, comment)
                   VALUES(?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    content.created,
                    content.board, 
                    content.thread_id, 
                    content.page,
                    content.name,
                    content.options,
                    content.subject,
                    content.comment))
    conn.commit()
    return cur.lastrowid

def delete_image(content_id, password_hash, db_file=config['db_name']):
    conn = create_connection(db_file)
    cur = conn.cursor()
    cur.execute(f'''DELETE FROM image WHERE content_id = ? and password_hash = ?''', (content_id, password_hash))
    conn.commit()
    return cur.lastrowid

def delete_content(content_id, db_file=config['db_name']):
    conn = create_connection(db_file)
    cur = conn.cursor()
    cur.execute(f'''DELETE FROM content WHERE id = ? and password_hash = ?''', (content_id, password_hash))
    conn.commit()
    return cur.lastrowid

# TODO: Admin functionality
# def insert_board(board, db_file="onchan.db"):
#     conn = create_connection(db_file)
#     cur = conn.cursor()
#     cur.execute(f'''INSERT INTO board(path, name, description)
#                     VALUES(?, ?, ?)''', (board.path, board.name, board.description))
#     conn.commit()
# TODO: page and limit

def select_boards(db_file=config['db_name']):
    conn = create_connection(db_file)
    cur = conn.cursor()
    cur.execute(f'''SELECT * FROM board 
                    ORDER BY path ASC''')
    rows = cur.fetchall()
    boards = []
    for row in rows:
        (path, name, description) = row
        board = Board(path=path, name=name, description=description, threads=[])
        boards.append(board)
    return boards

# TODO: Optimize this nasty query. Two sorts and a double select
def select_quotes(thread, limit=100, db_file=config['db_name']):
    conn = create_connection(db_file)
    cur = conn.cursor()
    cur.execute(f'''SELECT * FROM (SELECT * FROM content 
                    LEFT JOIN image ON content.id = image.content_id 
                    WHERE content.thread_id = ? 
                    ORDER BY created DESC 
                    LIMIT ?) ORDER BY created ASC''', (thread, limit))
    rows = cur.fetchall()
    quotes = []
    for row in rows:
        (id, created, board, thread_id, page, name, options, subject, comment, _, _,
            img_id, img_created, content_id, filename, orig_filename, size, width, height, checksum, thread_id, version, url) = row
        img = Image(id=img_id,
                 content_id=content_id,
                 filename=filename,
                 orig_filename=orig_filename,
                 size=size,
                 width=width,
                 height=height,
                 url=url,
                 checksum=checksum,
                 version=version)
        quotes.append(Content(id=id, board=board, thread_id=thread_id, page=page, name=name, options=options, subject=subject, comment=comment, img=img))
    return quotes


def select_threads(path, page, limit=100, db_file=config['db_name']):
    conn = create_connection(db_file)
    cur = conn.cursor()
    cur.execute(f'''SELECT * FROM content 
                    LEFT JOIN image ON content.id = image.content_id 
                    WHERE content.thread_id IS NULL 
                    AND content.board = ? 
                    AND content.page = ?
                    ORDER BY created DESC 
                    LIMIT ?''', (f"/{path}/", page, limit))
    rows = cur.fetchall()
    threads = []
    for row in rows:
        (id, created, board, thread_id, page, name, options, subject, comment, replies, image_replies,
        img_id, img_created, content_id, filename, orig_filename, size, width, height, checksum, thread_id, version, url) = row
        img = Image(id=img_id,
                 content_id=content_id,
                 filename=filename,
                 orig_filename=orig_filename,
                 size=size,
                 width=width,
                 height=height,
                 url=url,
                 checksum=checksum,
                 version=version)
        quotes = select_quotes(id, limit=5)
        content = Content(
            id=id, 
            board=board, 
            thread_id=thread_id, 
            page=page, 
            name=name, 
            options=options,
            subject=subject, 
            comment=comment, 
            img=img, 
            quotes=quotes,
            replies=replies,
            image_replies=image_replies)
        threads.append(content)
    return threads

def select_thread(path, id, limit=100, db_file=config['db_name']):
    conn = create_connection(db_file)
    cur = conn.cursor()
    # TODO: Don't need this many conditions
    cur.execute(f'''SELECT * FROM content 
                    LEFT JOIN image ON content.id = image.content_id 
                    WHERE content.thread_id IS NULL
                    AND content.board = ?
                    AND content.id = ? LIMIT 1''', (f"/{path}/", id))
    rows = cur.fetchall()
    
    for row in rows:
        (id, created, board, thread_id, page, name, options, subject, comment, _, _,
            img_id, img_created, content_id, filename, orig_filename, size, width, height, checksum, thread_id, version, url) = row
        img = Image(id=img_id,
                 content_id=content_id,
                 filename=filename,
                 orig_filename=orig_filename,
                 size=size,
                 width=width,
                 height=height,
                 url=url,
                 checksum=checksum,
                 version=version,
                 thread_id=thread_id)
        quotes = select_quotes(id, limit=100)
        return Content(id=id, board=board, thread_id=thread_id, page=page, name=name, options=options, subject=subject, comment=comment, img=img, quotes=quotes)
