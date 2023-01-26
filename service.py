#!/usr/bin/env python3

from bottle import Bottle, route, static_file, template, error, abort, request, response, redirect, cookie_encode
import html, re, os, cgi, random, enum, hashlib, calendar, string, secrets
from datetime import datetime

from argon2 import PasswordHasher

from data import *
from util import save_image, image_dimensions
from log import log_to_logger
from config import config
from validations import *

class TemplateContext:
    def __init__(self,
                board = None,
                boards = None,
                thread = None,
                config = config,
                reply=False,
                catalog=False,
                page_title=config['branding'],
                error_title="Error",
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
        self.error_title = error_title

cookie_opts = {
    # Aylmao, 4chan keeps cookies for 1 year, we'll keep a month. 
    # Clean up your messes quickly.
    'max_age': config['cookies']['max_age'],
    'path': '/',
    'httponly': True,
    'secure': request.headers.get('X-Forwarded-Proto') == 'https',
}

app = Bottle()
app.install(log_to_logger)

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

# ERROR PAGES

@app.error(404)
def not_found(err):
    boards = select_boards()
    ctx = TemplateContext(
        content='html/pages/error.html', 
        boards=boards,
        page_title=get_title(extra="404: Not found"),
        error_title="Not found",
        message="Lurk moar")
    return template(
        'html/index.html', 
        ctx=ctx)

@app.error(400)
def your_bad(err):
    boards = select_boards()
    ctx = TemplateContext(
            content='html/pages/error.html', 
            boards=boards,
            page_title=get_title(extra="400: Bad request"),
            error_title="Bad request",
            message="Your bad, if a validation error - email me")
    return template(
        'html/index.html', 
        ctx=ctx)

@app.error(500)
def my_bad(err):
    boards = select_boards()
    ctx = TemplateContext(
            content='html/pages/error.html', 
            boards=boards,
            page_title=get_title(extra="500: Internal server error"),
            error_title="Internal server error",
            message="Internal server error - email me what you were doing/inputs")
    return template(
        'html/index.html', 
        ctx=ctx)

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

@app.route('/<path:re:[a-z]{1,3}>/')
def render_board(path, page=1, cookie=False):
    """ Render board into index.html """
    boards = select_boards()
    board = select_board(path, page)
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

@app.route('/<path:re:[a-z]{1,3}>/upload', method='POST')
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
        return your_bad(None)

# THREADS

@app.route('/<path:re:[a-z]{1,3}>/thread/<thread:re:[0-9]+>')
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

@app.route('/<path:re:[a-z]{1,3}>/thread/<thread:re:[0-9]+>/upload', method='POST')
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
        return your_bad(None)
 
@app.route('/<path:re:[a-z]{1,3}>/catalog')
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
        page_title=get_title(path=path, name=board.name))
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
        content='html/pages/home.html')
    return template('html/index.html', ctx=ctx)

# INFO PAGES

@app.route('/legal')
def legal():
    """ Render content into index.html """
    boards = select_boards()
    ctx = TemplateContext(
        content='html/pages/legal.html',
        boards=boards,
        page_title=get_title(extra='Legal'))
    return template('html/index.html', ctx=ctx)

@app.route('/contact')
def contact():
    """ Render content into index.html """
    boards = select_boards()
    ctx = TemplateContext(
        content='html/pages/contact.html',
        boards=boards,
        page_title=get_title(extra='Contact'))
    return template('html/index.html', ctx=ctx)

@app.route('/feedback')
def feedback():
    """ Render content into index.html """
    boards = select_boards()
    ctx = TemplateContext(
        content='html/pages/feedback.html',
        boards=boards, 
        page_title=get_title(extra='Feedback'))
    return template('html/index.html', ctx=ctx)

@app.route('/about')
def about():
    """ Render content into index.html """
    boards = select_boards()
    ctx = TemplateContext(
        content='html/pages/about.html',
        boards=boards, 
        page_title=get_title(extra='About'))
    return template('html/index.html', ctx=ctx)

@app.route('/rules')
def rules():
    """ Render content into index.html """
    boards = select_boards()
    ctx = TemplateContext(
        content='html/pages/rules.html',
        boards=boards, 
        page_title=get_title(extra='Rules'))
    return template('html/index.html', ctx=ctx)

@app.route('/faq')
def faq():
    """ Render content into index.html """
    boards = select_boards()
    ctx = TemplateContext(
        content='html/pages/faq.html',
        boards=boards, 
        page_title=get_title(extra='FAQ'))
    return template('html/index.html', ctx=ctx)

app.run(
    host=config['server']['host'], 
    port=config['server']['port'], 
    debug=config['server']['debug'], 
    reloader=config['server']['reload'])
