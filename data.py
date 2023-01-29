import sqlite3, os, hashlib
from datetime import datetime
from config import config

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
        self.created = datetime.utcnow()
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
                 name=None,
                 subject=None,
                 comment=None, 
                 options=None,
                 img=None,
                 replies=None,
                 image_replies=None,
                 quotes=[],
                 sage=0):
        self.id = id
        self.created = datetime.utcnow()
        self.board = board
        self.thread_id = thread_id
        self.name = name
        self.subject = subject
        self.comment = comment
        self.options = options
        self.img = img
        self.quotes = quotes
        self.replies = replies
        self.image_replies = image_replies
        self.sage = sage
        

class Board:
    def __init__(self, 
                 path: str, 
                 name: str, 
                 description: str, 
                 threads: [Content] = [],
                 thread_limit: int = 100,
                 image_limit: int = 50,
                 bump_limit: int = 100):
        self.path = path
        self.name = name
        self.description = description
        self.threads = threads
        self.thread_limit = thread_limit
        self.image_limit = image_limit
        self.bump_limit = bump_limit


class DeletionAuth:
    def __init__(content_id,
                 image_id,
                 password_hash):
        self.content_id = content_id
        self.image_id = image_id
        self.password_hash = password_hash

def select_migration_table_exists(db_file=config['data']['db_name']):
    conn = create_connection(db_file)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='migration'")
    rows = cur.fetchall()
    conn.close()
    if rows and rows[0][0] == 'migration':
        return True
    return False

def insert_migration(name, hash, db_file=config['data']['db_name']):
    conn = create_connection(db_file)
    cur = conn.cursor()
    cur.execute("INSERT INTO migration(name, hash) VALUES (?, ?)", (name, hash))
    conn.commit()
    conn.close()
    return cur.lastrowid

def migrate(db_file=config['data']['db_name']):
    migration_table_exists = select_migration_table_exists()
    dir = os.fsencode(config['data']['migration_dir'])
    if migration_table_exists:
        conn = create_connection(db_file)
        cur = conn.cursor()
        cur.execute("SELECT * FROM migration")
        rows = cur.fetchall()
        conn.close()
        migration_files = os.listdir(dir)
        file_checksums = [(f, c) for _, f, c in rows]
        files = [f for f, _ in file_checksums]
        for file in migration_files:
            filename = os.fsdecode(file)
            with open(f"{dir.decode()}/{filename}") as migration_file:
                migration = migration_file.read()
            m = hashlib.sha512()
            m.update(migration.encode('utf-8'))
            lookup = (filename, m.hexdigest())
            if lookup not in file_checksums:
                if lookup[1] not in [x[1] for x in file_checksums]:
                    print("Migration file found with different checksum")
                    exit(1)
                print(f"Applying {filename}...")
                conn = create_connection(db_file)
                cur = conn.cursor()
                cur.executescript(migration)
                conn.commit()
                conn.close()
            else:
                print(f"Migration {filename} already applied, skipping...")
    else:
        for file in os.listdir(dir):
            filename = os.fsdecode(file)
            with open(f"{dir.decode()}/{filename}") as migration_file:
                migration = migration_file.read()
            print(f"Applying {filename}...")
            conn = create_connection(db_file)
            cur = conn.cursor()
            cur.executescript(migration)
            conn.commit()
            conn.close()
            m = hashlib.sha512()
            m.update(migration.encode('utf-8'))
            insert_migration(filename, m.hexdigest())

            

def insert_board(board, db_file=config['data']['db_name']):
    conn = create_connection(db_file)
    cur = conn.cursor()
    cur.execute(f'''INSERT INTO board(path, name, description, thread_limit, image_limit, bump_limit)
                    VALUES(?, ?, ?, ?, ?, ?)''', (board.path, board.name, board.description, board.thread_limit, board.image_limit, board.bump_limit))
    conn.commit()
    conn.close()
    return cur.lastrowid

def create_connection(db_file=config['data']['db_name']):
    conn = None
    try:
        conn = sqlite3.connect(db_file, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
        conn.set_trace_callback(print)
    except Error as e:
        print(e)

    return conn

def insert_image(img, thread, db_file=config['data']['db_name']):
    if img:
        conn = create_connection(db_file)
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
        conn.close()
        return cur.lastrowid
    return None


def insert_content(content, db_file=config['data']['db_name']):
    conn = create_connection(db_file)
    cur = conn.cursor()
    cur.execute(f'''INSERT INTO content(created, board, thread_id, name, options, subject, comment)
                   VALUES(?, ?, ?, ?, ?, ?, ?)''', (
                        content.created,
                        content.board, 
                        content.thread_id, 
                        content.name,
                        content.options,
                        content.subject,
                        content.comment))
    conn.commit()
    conn.close()
    return cur.lastrowid

def insert_deletion_auth(content_id, password_hash, image_id=None, db_file=config['data']['db_name']):
    conn = create_connection(db_file)
    cur = conn.cursor()
    cur.execute(f'''INSERT INTO deletion_auth(content_id, image_id, password_hash)
                   VALUES(?, ?, ?)''', (
                        content_id,
                        image_id,
                        password_hash))
    conn.commit()
    conn.close()
    return cur.lastrowid

def select_images(ids, db_file=config['data']['db_name']):
    conn = create_connection(db_file)
    cur = conn.cursor()
    cur.execute(f'''SELECT url FROM image WHERE id IN ({','.join(ids)})''')
    rows = cur.fetchall()
    conn.close()
    return [i[0] for i in rows]

def delete_images(ids, password_hash, db_file=config['data']['db_name']):
    conn = create_connection(db_file)
    cur = conn.cursor()
    cur.execute(f'''DELETE FROM image 
                    WHERE content_id IN ({','.join(ids)}) 
                    AND (SELECT password_hash 
                         FROM deletion_auth 
                         WHERE content_id IN ({','.join(ids)})) = \'{password_hash}\'''')
    conn.commit()
    conn.close()
    for url in select_images(ids):
        if os.path.isfile(image):
            os.remove(image)
            print("%s purged" % image)
        else:
            # If it fails, inform the user.
            print("%s file not found for removal, skipping..." % image)
    return cur.lastrowid

def delete_contents(ids, password_hash, db_file=config['data']['db_name']):
    conn = create_connection(db_file)
    cur = conn.cursor()
    cur.execute(f'''DELETE FROM content 
                    WHERE id IN ({','.join(ids)}) 
                    AND (SELECT password_hash FROM deletion_auth WHERE content_id IN ({','.join(ids)})) = ?''', (password_hash,))
    conn.commit()
    conn.close()
    return cur.lastrowid

def select_boards(db_file=config['data']['db_name']):
    conn = create_connection(db_file)
    cur = conn.cursor()
    cur.execute(f'''SELECT * FROM board 
                    ORDER BY path ASC''')
    rows = cur.fetchall()
    conn.close()
    boards = []
    for row in rows:
        (path, name, description, thread_limit, image_limit, bump_limit) = row
        board = Board(
            path=path, 
            name=name, 
            description=description, 
            threads=[],
            thread_limit=thread_limit,
            image_limit=image_limit,
            bump_limit=bump_limit)
        boards.append(board)
    return boards

def select_board(path, page, db_file=config['data']['db_name']):
    conn = create_connection(db_file)
    cur = conn.cursor()
    cur.execute(f'''SELECT * FROM board 
                    WHERE path = ? LIMIT 1''', (f'/{path}/',))
    rows = cur.fetchall()
    conn.close()
    boards = []
    for row in rows:
        (path2, name, description, thread_limit, image_limit, bump_limit) = row
        board = Board(
            path=path2, 
            name=name, 
            description=description, 
            threads=select_threads(path, page, limit=10),
            thread_limit=thread_limit,
            image_limit=image_limit,
            bump_limit=bump_limit)
        return board
    return None

# TODO: Optimize this nasty query. Two sorts and a double select
def select_quotes(thread, limit=100, db_file=config['data']['db_name']):
    conn = create_connection(db_file)
    cur = conn.cursor()
    cur.execute(f'''SELECT * FROM (SELECT * FROM content 
                    LEFT JOIN image ON content.id = image.content_id 
                    WHERE content.thread_id = ? 
                    ORDER BY created DESC 
                    LIMIT ?) ORDER BY created ASC''', (thread, limit))
    rows = cur.fetchall()
    conn.close()
    quotes = []
    for row in rows:
        (id, created, board, thread_id, name, options, subject, comment, _, _, _, _,
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
        quotes.append(Content(id=id, board=board, thread_id=thread_id, name=name, options=options, subject=subject, comment=comment, img=img))
    return quotes

def count_threads(path, db_file=config['data']['db_name']):
    conn = create_connection(db_file)
    cur = conn.cursor()
    cur.execute(f'''SELECT COUNT(*) FROM content WHERE thread_id IS NULL AND board = ?''', (path,))
    rows = cur.fetchall()
    conn.close()
    return rows[0][0]

def select_threads(path, page, limit=100, db_file=config['data']['db_name']):
    conn = create_connection(db_file)
    cur = conn.cursor()
    cur.execute(f'''SELECT * FROM content c1
                    LEFT JOIN image ON c1.id = image.content_id 
                    WHERE c1.thread_id IS NULL 
                    AND c1.board = ? 
                    ORDER BY COALESCE(
                        (SELECT MAX(c2.created) FROM content c2 WHERE c2.thread_id = c1.id AND c1.limited_at >= c2.created),
                        c1.limited_at,
                        (SELECT MAX(c2.created) FROM content c2 WHERE c2.thread_id = c1.id),
                        c1.created) DESC
                    LIMIT ? OFFSET ?''', (f"/{path}/", limit, (page - 1) * 10))
    rows = cur.fetchall()
    conn.close()
    threads = []
    for row in rows:
        (id, created, board, thread_id, name, options, subject, comment, replies, image_replies, limited_at, sage,
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
            name=name, 
            options=options,
            subject=subject, 
            comment=comment, 
            img=img, 
            quotes=quotes,
            replies=replies,
            image_replies=image_replies,
            sage=sage)
        threads.append(content)
    return threads

def select_thread(path, id, limit=100, db_file=config['data']['db_name']):
    conn = create_connection(db_file)
    cur = conn.cursor()
    # TODO: Don't need this many conditions
    cur.execute(f'''SELECT * FROM content 
                    LEFT JOIN image ON content.id = image.content_id 
                    WHERE content.thread_id IS NULL
                    AND content.board = ?
                    AND content.id = ? LIMIT 1''', (f"/{path}/", id))
    rows = cur.fetchall()
    conn.close()
    for row in rows:
        (id, created, board, thread_id, name, options, subject, comment, replies, image_replies, limited_at, sage,
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
        quotes = select_quotes(id, limit=limit)
        return Content(id=id, 
                        board=board, 
                        thread_id=thread_id, 
                        name=name, 
                        options=options, 
                        subject=subject, 
                        comment=comment, 
                        img=img, 
                        quotes=quotes,
                        replies=replies,
                        image_replies=image_replies,
                        sage=sage)

def count_image_removal_queue(db_file=config['data']['db_name']):
    conn = create_connection(db_file)
    cur = conn.cursor()
    cur.execute(f'''SELECT COUNT(*) FROM image_removal_queue''')
    rows = cur.fetchall()
    conn.close()
    return rows[0][0]

def select_image_removal_queue(db_file=config['data']['db_name']):
    conn = create_connection(db_file)
    cur = conn.cursor()
    # TODO: Don't need this many conditions
    cur.execute(f'''SELECT * FROM image_removal_queue''')
    rows = cur.fetchall()
    conn.close()
    return [r[0] for r in rows]

def clear_image_removal_queue(db_file=config['data']['db_name']):
    conn = create_connection(db_file)
    cur = conn.cursor()
    # TODO: Don't need this many conditions
    cur.execute(f'''DELETE FROM image_removal_queue''')
    conn.commit()
    conn.close()

def sage_thread(id, db_file=config['data']['db_name']):
    conn = create_connection(db_file)
    cur = conn.cursor()
    # TODO: Don't need this many conditions
    cur.execute(f'''UPDATE content SET sage = sage + 1 WHERE id = ?''', (id,))
    conn.commit()
    conn.close()