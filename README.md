# onchan-nojs

`onchan` is a configurable base image-board for those wanting to self-host or run their own. This is a mishmash of things I miss from imageboards of yesterday and features from 4chan X.

## Features

This is a bare-bones image board with some thing stolen from 4chan X (albeit without JavaScript - so no live updates). In the future I'll make connectors for CDN/infrastructure to host images and write ANSI SQL for DBs other than SQLite. 

The goal was a very small instance that can be run on an inexpensive VPS with zero extra infrastructure. It's meant to be as disposable as it's content.

* No CDN, S3, or special cloud services needed to host images. This implementation puts them in `public/img` and rolls them out when the thread expires. As long as you have enough storage for ~5MB * thread limit * image limit - you will be able to host without special infrastructure.
* Cat emotes are there for those who know. `:k:` = head, `:o:` = body, `:t:` = trousers. Only use if you add lots of `:o:` on newlines. Long cat is long.
* Post/image deletion works the same as 4chan. I store a cookie when you post that is is your password for deletion. If you clear cookies, you lose the ability to delete your posts.
* Catalog view - display images and a short summary/reply counts in a more concise way.
* Reply tracking - if a reply is quoted (`>>1` for example), it will show its references similar to 4chan X.
* Greentext
* Cross-board linking `>>>/b/` for example
* Default posting functionality from a board is akin to old 4chan. (return to index after posting)
* Using `nonoko` within an open thread's reply options will jump back to the index after replying
* You may `sage` threads. The number of thread replies + `sage` will stop bumping the thread if it exceeds the bump limit defined in config for the board. Stop bumping low quality in half the time.
* You may use nonoko in addition to sage with `nonokosage` to go back to the index from a thread.
* I also allow you to `sage` your own thread on its initial post, just because. Throw it in options you masochist.

## In progress

* Trip codes
* Secure trip codes
* Capcodes

## Configuration

All configuration is managed through [config.py](./config.py).

```python
config = {
    "branding": "<name of your image board>",
    "attribution": "<owner/responsible party to be put in footer>",
    "images": {
        "dir": "<path to hosted images>"
    },
    "data": {
        "db_name": "<name of SQLite DB file>.db",
        "migration_dir": "<name of directory with SQL migrations>",
        "purge_delay": 30
    },
    "server": {
        "debug": True,
        "reload": True,
        "port": 8080,
        "host": "localhost"
    },
    "info": {
        "disclaimer": "<footer disclaimer about posts/comments of users>",
        "home": {
            "what": "<what is your image board/site>"
        },
        "legal": "<legal disclaimer injected into /legal (html/pages/legal.html)",
        "about": "<about the image board/site (supports emotes, greentext, links, etc)>",
        "contact": {
            "name": "<contact name>",
            "email": "<contact email>",
            "irc": "irc://<server>#<channel>",
        },
        "feedback": "<information to give feedback>",
        "rules": "<site-wide rules>",
        "faq": {
            "<question>": "<answer>",
            ...
        }
    },
    "cookies": {
        "key": "<secret for encrypting/decrypting cookies>",
        "name": "<cookie name for post/image deletion>",
        "max_age": 3600 * 24 * 30
    },
    "boards": [
        {
            "path": "<path in URL>",
            "name": "<name of board>",
            "description": "<board description>",
            "thread_limit": 100,
            "image_limit": 50,
            "bump_limit": 100
        }
        ...
    ]
}
```

## Running

```bash
$ source venv/bin/activate
$ python3 service.py
```

## Scripts

* [scripts/destroy.sh](./scripts/destroy.sh) - destroy database and remove public/img
* [scripts/migrate.sh](./scripts/migrate.sh) - now defunct due to migrations being handled at startup

## Why?

4chan sucks now, 8chan is dead. Let the best chan win. End-goal is to be configurable enough for large
distributed instances where dedicated backends, a CDN, etc. can all be configuation.

## License

Deez nuts V2