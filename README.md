# onchan-nojs

`onchan` is a configurable base image-board implementation for those wanting to self-host or run their own.

## Configuration

All configuration is managed through [config.py](./config.py).

```json
{
    "branding": "<name of your image board>",
    "attribution": "<owner/responsible party to be put in footer>",
    "images": {
        "dir": "<path to hosted images>"
    },
    "db_name": "<name of SQLite DB file>.db",
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
    }
}
```

## Running

```bash
$ ./scripts/migrate.sh # Create initial schema/apply migrations from sql/
$ source venv/bin/activate
$ python3 service.py
```

## Why?

4chan sucks now, 8chan is dead. Let the best chan win. End-goal is to be configurable enough for large
distributed instances where dedicated backends, a CDN, etc. can all be configuation.

## License

Deez nuts V2