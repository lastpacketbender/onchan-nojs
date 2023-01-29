#!/usr/bin/env python3

import html, re, os, random, string, secrets

from bottle import Bottle, route, static_file, template, error, abort, request, response, redirect, cookie_encode, cookie_decode
from argon2 import PasswordHasher

from data import *
from util import save_image, image_dimensions
from log import log_to_logger
from config import config
from validations import *
from tasks import BackgroundFilePurge

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
                comment_line = 'html/components/content/comment_line.html',
                page = None):  
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
        self.page = page

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

def save_comment(path, name, options, comment, password_hash=None, thread=None, subject=None):
    content = Content(
            board=f"/{path}/", 
            thread_id=thread,
            name=name, 
            options=''.join(options),
            subject=subject,
            comment=comment)
    # empty var from tuple is delayed auth_id for inserting in next line as a pair
    content_id = insert_content(content)
    auth_id = None
    if password_hash:
        auth_id = insert_deletion_auth(content_id, password_hash)
    return content_id, auth_id

def save_comment_and_file(path, data, name, options, comment, password_hash, thread=None, subject=None):
    content = Content(
        board=f"/{path}/", 
        thread_id=thread, 
        name=name, 
        options=options,
        subject=subject,
        comment=comment)
    content_id, _ = save_comment(path, name, options, comment, thread=thread, subject=subject)
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
            version=1)
        # empty tuple val is delayed auth_id for inserting in next line as a pair
        image_id = insert_image(img, thread)
        auth_id = insert_deletion_auth(content_id, password_hash, image_id=image_id)
    return content_id, image_id, auth_id

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
            message=err if err else "Your bad, if a validation error - email me")
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


@app.route('/<path:re:[a-z0-9]{1,3}>/<page:int>')
def render_board_paged(path, page=1):
    """ Render board into index.html """
    boards = select_boards()
    board = select_board(path, page)
    ctx = TemplateContext(
            content='html/pages/board.html', 
            boards=boards,
            board=board,
            limit=5,
            reply=True,
            page_title=get_title(path=path, name=board.name),
            page=page)
    resp = template('html/index.html', ctx=ctx)
    return resp

@app.route('/<path:re:[a-z0-9]{1,3}>')
def render_board(path, page=1):
    redirect(f'/{path}/{page}')

@app.route('/<path:re:[a-z0-9]{1,3}>/')
def render_board_(path, page=1):
    redirect(f'/{path}/{page}')

@app.route('/<path:re:[a-z0-9]{1,3}>/delete', method='POST')
def delete_from_board(path, page=1):
    """ Render board into index.html """
    on = [x for x in request.forms.decode()]
    ids = [x for x in on if x.isdigit()]
    password_hash = request.get_cookie(config['cookies']['name'], secret=config['cookies']['key'])
    if password_hash:
        if 'delete-file-only' in on:
            delete_images(ids, password_hash)
        else:
            delete_contents(ids, password_hash)
    return redirect(f"/{path}/")

@app.route('/<path:re:[a-z0-9]{1,3}>/upload', method='POST')
def upload(path):
    name = request.forms.get('name').strip()
    subject = request.forms.get('subject').strip()
    options = request.forms.get('options').strip()
    comment = request.forms.get('comment').strip()
    data = request.files.get("file", "")
    valid_thread, message, options = validate_new_thread(name, subject, options, comment, data)   
    if valid_thread:
        password_hash = request.get_cookie(config['cookies']['name'], secret=config['cookies']['key'])
        if not password_hash:
            ph = PasswordHasher()
            password = ''.join([secrets.choice(string.ascii_lowercase + string.ascii_uppercase + string.digits + string.punctuation) for _ in range(32)])
            password_hash = ph.hash(password)
            response.set_cookie(config['cookies']['name'], password_hash, secret=config['cookies']['key'], **cookie_opts)
        content_id, image_id, auth_id = save_comment_and_file(path, data, name, ''.join(options), comment, password_hash, subject=subject)
        if "nonoko" in options:
            print("TODO: nonoko in /board/upload")
        return redirect(f"/{path}/")
    else:
        return your_bad(None)

# THREADS

@app.route('/<path:re:[a-z0-9]{1,3}>/thread/<thread:re:[0-9]+>')
def render_thread(path, thread):
    """ Render thread into index.html """
    boards = select_boards()
    board = next(filter(lambda b: f"/{path}/" == b.path, boards))
    thread = select_thread(path, thread, limit=100)
    if thread:
        ctx = TemplateContext(
            content='html/pages/thread.html',
            boards=boards,
            board=board,
            thread=thread,
            limit=100,
            page_title=get_title(path=path, name=board.name, subject=thread.subject[:30]))
        resp = template('html/index.html', ctx=ctx)
        return resp
    else:
        return not_found(None)

@app.route('/<path:re:[a-z0-9]{1,3}>/thread/<thread:re:[0-9]+>/delete', method='POST')
def delete_from_thread(path, thread):
    """ Render board into index.html """
    on = [x for x in request.forms.decode()]
    ids = [x for x in on if x.isdigit()]
    password_hash = request.get_cookie(config['cookies']['name'], secret=config['cookies']['key'])
    if password_hash:
        if 'delete-file-only' in on:
            delete_images(ids, password_hash)
        else:
            delete_contents(ids, password_hash)
    return redirect(f"/{path}/thread/{thread}") if thread not in ids else redirect(f"/{path}/")

@app.route('/<path:re:[a-z0-9]{1,3}>/thread/<thread:re:[0-9]+>/upload', method='POST')
def upload_thread(path, thread):
    name = request.forms.get('name').strip()
    options = request.forms.get('options').strip()
    comment = request.forms.get('comment').strip()
    data = request.files.get("file", "")
    valid_reply, message, options = validate_new_reply(name, options, comment, data, path, thread)
    if valid_reply:
        password_hash = request.get_cookie(config['cookies']['name'], secret=config['cookies']['key'])
        if not password_hash:
            ph = PasswordHasher()
            password = ''.join([secrets.choice(string.ascii_lowercase + string.ascii_uppercase + string.digits + string.punctuation) for _ in range(32)])
            password_hash = ph.hash(password)
            response.set_cookie(config['cookies']['name'], password_hash, secret=config['cookies']['key'], **cookie_opts)
        if data.filename != 'empty':
            content_id, image_id, auth_id = save_comment_and_file(path, data, name, options, comment, password_hash, thread=thread)
        else:
            content_id, auth_id = save_comment(path, name, options, comment, thread=thread, password_hash=password_hash)
        if "nonoko" in options:
            print("TODO: nonoko in /thread/id/upload")
        elif "sage" in options:
            sage_thread(thread)
            print("TODO: sage in /thread/id/upload")
        return redirect(f"/{path}/thread/{thread}")
    else:
        return your_bad(message)
 
@app.route('/<path:re:[a-z0-9]{1,3}>/catalog')
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

try:
    print("Checking/applying DB migrations...")
    migrate()

    # Configuration setup
    print("Reading configuration and setting up boards...")
    boards = select_boards()
    for board in config['boards']:
        if not select_board(board['path'].replace('/', ''), 1):
            print(f"Creating board {board['path']}")
            b = Board(
                board['path'], 
                board['name'], 
                board['description'], 
                board['thread_limit'], 
                board['image_limit'], 
                board['bump_limit'])
            insert_board(b)

    # t = BackgroundFilePurge()
    # t.start()
    app.run(
        server='paste',
        host=config['server']['host'], 
        port=config['server']['port'], 
        debug=config['server']['debug'], 
        reloader=config['server']['reload'])
    # t.join()
except:
    # t.join()
    print('Bye')
