#!/usr/bin/env python3

from bottle import Bottle, route, static_file, template, error, abort, request, response, redirect, cookie_encode
import html, re, os, cgi, random, enum, hashlib, logging, calendar, string, secrets
from functools import wraps
from datetime import datetime

from data import Board, Content, Image, insert_content, insert_image, select_boards, select_thread, select_threads
from util import save_image, image_dimensions
from config import config
from argon2 import PasswordHasher

logger = logging.getLogger('onchan')

# set up the logger
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler('onchan.log')
formatter = logging.Formatter('%(msg)s')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

cookie_opts = {
    # Aylmao, 4chan keeps cookies for 1 year, we'll keep a month. 
    # Clean up your messes quickly.
    'max_age': config['cookies']['max_age'],
    'path': '/',
    'httponly': True,
    'secure': request.headers.get('X-Forwarded-Proto') == 'https',
}

def log_to_logger(fn):
    '''
    Wrap a Bottle request so that a log line is emitted after it's handled.
    (This decorator can be extended to take the desired logger as a param.)
    '''
    @wraps(fn)
    def _log_to_logger(*args, **kwargs):
        request_time = datetime.now()
        actual_response = fn(*args, **kwargs)
        # modify this to log exactly what you need:
        logger.info('%s %s %s %s %s' % (request.remote_addr,
                                        request_time,
                                        request.method,
                                        request.url,
                                        response.status))
        return actual_response
    return _log_to_logger

app = Bottle()
app.install(log_to_logger)

class TemplateContext:
    def __init__(self,
                    board = None,
                    boards = None,
                    thread = None,
                    config = config,
                    reply=False,
                    catalog=False,
                    page_title=config['branding'],
                    limit = -1,
                    message = None,
                    content = None,
                    nav = 'html/components/nav.html',
                    footer = 'html/components/footer.html',
                    upload = 'html/components/upload.html',
                    replies = 'html/components/replies.html',
                    content_info = 'html/components/content/content_info.html',
                    file_info = 'html/components/content/file_info.html',
                    thread_content = 'html/components/content/thread_content.html',
                    comment_line = 'html/components/content/comment_line.html'):  
        self.board = board
        self.boards = boards
        self.thread = thread
        self.config = config
        self.nav = nav
        self.footer = footer
        self.upload = upload
        self.replies = replies
        self.comment_line = comment_line
        self.content_info = content_info
        self.file_info = file_info
        self.thread_content = thread_content
        self.reply = reply
        self.catalog = catalog
        self.page_title = page_title
        self.limit = limit
        self.message = message
        self.content = content

def merge_dicts(*args):
    result = {}
    for dictionary in args:
        result.update(dictionary)
    return result

def get_title(path=None, name=None, subject=None, extra=None):
    components = []
    if path:
        components.append(f"/{path}/")
        if subject:
                components.append(subject[:30])
        if name:
            components.append(name)
    if extra:
        components.append(extra)
    components.append(config['branding'])
    return ' - '.join(components)

def save_comment(path, name, options, comment, thread=None, subject=None):
    content = Content(
            board=f"/{path}/", 
            thread_id=thread, 
            page=1, 
            name=name, 
            options=options,
            subject=subject,
            comment=comment)
    content_id = insert_content(content)
    return content_id

def save_comment_and_file(path, data, name, options, comment, password_hash=None, thread=None, subject=None):
    content = Content(
        board=f"/{path}/", 
        thread_id=thread, 
        page=1, 
        name=name, 
        options=options,
        subject=subject,
        comment=comment)
    content_id = save_comment(path, name, options, comment, thread=thread, subject=subject)
    if data:
        success, image_id, filename, size, digest, msg = save_image(data)
        if not success:
            raise Exception(msg)
        _, ext = os.path.splitext(data.filename)
        width, height = image_dimensions(f"{config['images']['dir']}/{filename}")
        img = Image(
            id=image_id,
            content_id=content_id,
            filename=filename,
            orig_filename=data.filename,
            size=size,
            width=width,
            height=height,
            url=f"{config['images']['dir']}/{filename}",
            checksum=digest,
            # TODO: Get latest by query
            version=1
        )
        image_id = insert_image(img, thread)
    ph = PasswordHasher()
    password = ''.join([secrets.choice(string.ascii_lowercase + string.ascii_uppercase + string.digits + string.punctuation) for _ in range(32)])
    hash = ph.hash(password)
    print(password, hash)
    return content_id, image_id

# VALIDATIONS


def validate_file(data):
    messages = []
    supported_files = ('.bmp', '.png', '.jpg', '.jpeg', '.gif', '.tiff', '.webm')
    if data.filename != "empty":
        _, ext = os.path.splitext(data.filename)
        if not ext:
            messages.append("image required")
        elif ext and ext.lower() not in supported_files:
            messages.append("not a supported filetype")
        else:
            # File is attached and non-zero in size
            data.file.seek(0, os.SEEK_END)
            size = data.file.tell()
            data.file.seek(0, os.SEEK_SET)
            if size <= 0:
                messages.append("empty file found")
            elif size >= 1024 ** 2 * 5:
                messages.append("file larger than 5 MB limit")
    else:
        messages.append("image required")
    return True if len(messages) == 0 else False, messages

def validate_comment(comment):
    messages = []
    if not comment:
        messages.append("comment is a required field")
    else:
        if len(comment) > 2000:
            messages.append("comment is larger than 2000 character limit")
    return True if len(messages) == 0 else False, messages

def validate_new_thread(name, subject, options, comment, data):
    # TODO: length of name, subject, options
    valid_file, file_messages = validate_file(data)
    
    # if not name: Defaulted in database
    valid_comment, comment_messages = validate_comment(comment)
    
    return valid_comment and valid_file, ', '.join(file_messages + comment_messages)

def validate_new_reply(name, options, comment, data):
    # TODO: length of name, subject, options
    if data.filename != 'empty':
        valid_file, file_messages = validate_file(data)
    else:
        # Skip, images aren't required in replies
        valid_file, file_messages = True, []
    
    # if not name: Defaulted in database
    valid_comment, comment_messages = validate_comment(comment)
    
    return valid_comment and valid_file, ', '.join(file_messages + comment_messages)

# ERROR PAGES

@app.error(404)
def not_found(err):
    boards = select_boards()
    return template(
        'html/index.html', 
        config=config,
        boards=boards, 
        board=None, 
        title="404: Not found",
        message="Not found: OP is a _",
        content='html/pages/error.html',
        page_title=get_title(extra="Not found"))

@app.error(400)
def bad_request(err):
    boards = select_boards()
    return template(
        'html/index.html', 
        config=config,
        boards=boards, 
        board=None,
        title="400: Bad request",
        message="Your bad",
        content='html/pages/error.html',
        page_title=get_title(extra="Bad request"))

# STATIC FILES

@app.route('/public/<filepath:path>')
def serve_static(filepath):
    """ Serve static files/downloads (use ?download query parameter for original filename) """
    params = merge_dicts(dict(request.forms), dict(request.query.decode()))
    if 'download' not in params:
        return static_file(filepath, root='./public/')
    else:
        return static_file(filepath, root='./public/', download=params['download'], ctx=TemplateContext())

## BOARDS

@app.route('/<path>/')
def render_board(path, cookie=False):
    """ Render board into index.html """
    boards = select_boards()
    threads = select_threads(path=path, page=1)
    board = next(filter(lambda b: b.path == f"/{path}/", boards))
    board.threads = threads
    ctx = TemplateContext(
            content='html/pages/board.html', 
            boards=boards,
            board=board,
            limit=5,
            reply=True,
            page_title=get_title(path=path, name=board.name))
    resp = template('html/index.html', ctx=ctx)
    if cookie:
        password = ''.join([secrets.choice(string.ascii_lowercase + string.ascii_uppercase + string.digits + string.punctuation) for x in range(32)])
        # TODO: Maybe store on the fly keys instead
        encoded = cookie_encode(password, config['cookies']['key'])
        response.set_cookie(config['cookies']['name'], encoded, secret=config['cookies']['key'], **cookie_opts)
    return resp

@app.route('/<path>/upload', method='POST')
def upload(path):
    name = request.forms.get('name')
    subject = request.forms.get('subject')
    options = request.forms.get('options')
    comment = request.forms.get('comment')
    data = request.files.get("file", "")
    valid_thread, message = validate_new_thread(name, subject, options, comment, data)
    
    if valid_thread:
        ph = PasswordHasher()
        password_hash = ph.hash('test')
        ph.verify(password_hash, 'test')
        ph.check_needs_rehash(password_hash)
        content_id, image_id = save_comment_and_file(path, data, name, options, comment, password_hash, subject=subject)
        return render_board(path, cookie=True)
    else:
        return bad_request(None)

# THREADS

@app.route('/<path>/thread/<thread>')
def render_thread(path, thread, cookie=False):
    """ Render thread into index.html """
    boards = select_boards()
    board = next(filter(lambda b: f"/{path}/" == b.path, boards))
    thread = select_thread(path, thread, limit=100)
    ctx = TemplateContext(
        content='html/pages/thread.html',
        boards=boards,
        board=board,
        thread=thread,
        limit=100,
        page_title=get_title(path=path, name=board.name, subject=thread.subject[:30]))
    if thread:
        resp = template('html/index.html', ctx=ctx)
        if cookie:
            password = ''.join([secrets.choice(string.ascii_lowercase + string.ascii_uppercase + string.digits + string.punctuation) for x in range(32)])
            response.set_cookie(config['cookies']['name'], password, secret=config['cookies']['key'], **cookie_opts)
        return resp
    else:
        return not_found(None)

@app.route('/<path>/thread/<thread>/upload', method='POST')
def upload_thread(path, thread):
    name = request.forms.get('name')
    options = request.forms.get('options')
    comment = request.forms.get('comment')
    data = request.files.get("file", "")
    valid_reply, message = validate_new_reply(name, options, comment, data)
    if valid_reply:
        if data.filename != 'empty':
            content_id, image_id = save_comment_and_file(path, data, name, options, comment, thread=thread)
        else:
            content_id = save_comment(path, name, options, comment, thread=thread)
        return render_thread(path, thread, cookie=True)
    else:
        return bad_request(None)
 
@app.route('/<path>/catalog')
def render_catalog(path):
    """ Render board catalog into index.html """
    boards = select_boards()
    threads = select_threads(path=path, page=1)
    board = next(filter(lambda b: b.path == f"/{path}/", boards))
    board.threads = threads
    ctx = TemplateContext(
        content='html/pages/catalog.html',
        config=config,
        boards=boards,
        board=board,
        catalog=True,
        page_title=get_title(path=path, name=board.name)
    )
    return template(
        'html/index.html',  
        ctx=ctx)

## HOME

@app.route('/')
def landing():
    """ Render content into index.html """
    boards = select_boards()
    ctx = TemplateContext(
        boards=boards, 
        content='html/pages/home.html'
    )
    return template('html/index.html', ctx=ctx)

# AUXILARY PAGES

@app.route('/legal')
def legal():
    """ Render content into index.html """
    boards = select_boards()
    ctx = TemplateContext(
        content='html/pages/legal.html',
        boards=boards,
        page_title=get_title(extra='Legal')
    )
    return template('html/index.html', ctx=ctx)

@app.route('/contact')
def contact():
    """ Render content into index.html """
    boards = select_boards()
    ctx = TemplateContext(
        content='html/pages/contact.html',
        boards=boards,
        page_title=get_title(extra='Contact')
    )
    return template('html/index.html', ctx=ctx)

@app.route('/feedback')
def feedback():
    """ Render content into index.html """
    boards = select_boards()
    ctx = TemplateContext(
        content='html/pages/feedback.html',
        boards=boards, 
        page_title=get_title(extra='Feedback')
    )
    return template('html/index.html', ctx=ctx)

@app.route('/about')
def about():
    """ Render content into index.html """
    boards = select_boards()
    ctx = TemplateContext(
        content='html/pages/about.html',
        boards=boards, 
        page_title=get_title(extra='About')
    )
    return template('html/index.html', ctx=ctx)

@app.route('/rules')
def rules():
    """ Render content into index.html """
    boards = select_boards()
    ctx = TemplateContext(
        content='html/pages/rules.html',
        boards=boards, 
        page_title=get_title(extra='Rules')
    )
    return template('html/index.html', ctx=ctx)

@app.route('/faq')
def faq():
    """ Render content into index.html """
    boards = select_boards()
    ctx = TemplateContext(
        content='html/pages/faq.html',
        boards=boards, 
        page_title=get_title(extra='FAQ')
    )
    return template('html/index.html', ctx=ctx)

app.run(
    host=config['server']['host'], 
    port=config['server']['port'], 
    debug=config['server']['debug'], 
    reloader=config['server']['reload'])
