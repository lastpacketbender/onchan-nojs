# TODO
config = {
    "branding": "onchan",
    "attribution": "Max Headroom",
    "images": {
        "dir": "./public/img"
    },
    "data": {
        "db_name": "onchan.db",
        "migration_dir": "./sql/migration",
    },
    "server": {
        "debug": True,
        "reload": True,
        "port": 8080,
        "host": "localhost"
    },
    "info": {
        "disclaimer": "Images uploaded are the responsibility of the Poster. Comments are owned by the Poster.",
        "home": {
            "what": "It is a game. The plot is a lot like se7en. Good luck. Goodbye."
        },
        "legal": "We live in a fairy-tale land where the rules are suggestions, and idiots run the asylum. Just be legal.",
        "about": """>be me\r\n>sperg/10, GED-holding, drug-addict, and manic
>happen to be a computer wizard
>"you will do great things anon"
>family_gaslighting.wav
>realize i have no friends
>family never visits and only enjoys me when i pretend to not be mentally ill
>mfw climb to sigma 6-figure jerbs
>mfw targeted by infosec teams
>mfw psychologically tortured by infosec teams (including my own)
>life is a materialistic game
>imposter-syndrome.jpg
>mfw burning it to homelessness in a month
>mfw being successful is shittier for mental health due to fake people
>mfw most research publications are tripe


Stay true to yourselves, bros. The corporate world and /x/ made me... less than stable. 
Don't idolize education and success.
I once thought I was gifted enough to exist in the corporate world.
When an ex-DoD contractor joked about me being a 'kid from 4chan', I knew I made it to the big-leagues.
Not worth/10.

Catch me schizoposting in >>>/x/.

~Darth Thadeus
""",
        "contact": {
            "name": "Darth Thadeus",
            "email": "areyouawizard@proton.me",
            "irc": "irc://freenode.net#onchan",
        },
        "feedback": "Put it in the bin.",
        "rules": "You are the hacker known as monogamous. You are region. Forgive and forget. Expecto patronum.",
        "faq": {
            "What is this place?": "Lurk moar, it is never enough",
            "Thoughts on Jim/Ron Watkins?": "Some people take you cannot arrest an idea too far. Pricks.",
            "Who is the queen": "Still Boxxy"
        }
    },
    "cookies": {
        "key": "lolololololololololololololololololololololololololololololololololololololololololololololololol",
        "name": "onchan_pass",
        "max_age": 3600 * 24 * 30
    },
    "boards": [
        {
            "path": "/b/",
            "name": "Random",
            "description": "Don''t do it.",
            "bump_limit": 100,
            "image_limit": 50,
            "thread_limit": 100
        },
        {
            "path": "/g/",
            "name": "Technology",
            "description": "Your choice of Emacs has me quite discheesed.",
            "bump_limit": 100,
            "image_limit": 50,
            "thread_limit": 100
        },
        {
            "path": "/sci/",
            "name": "Science & Math",
            "description": "Most research is tripe, this board is no different.",
            "bump_limit": 100,
            "image_limit": 50,
            "thread_limit": 100
        },
        {
            "path": "/t/",
            "name": "Torrents",
            "description": "You wouldn't download a car, would you anon?",
            "bump_limit": 100,
            "image_limit": 50,
            "thread_limit": 100
        },
        {
            "path": "/x/",
            "name": "Paranormal",
            "description": "Meds, anon.",
            "bump_limit": 100,
            "image_limit": 50,
            "thread_limit": 100
        }
    ]
    # The current configuration is:
    #
    #  - public/ for image storage
    #  - sqlite3
    # TODO
    # IMAGE STORAGE (types: S3, public/ (for relatively small boards), ? free public service)   
        # Directory to save/pop to/from
    # DATA STORAGE (types: sqlite, standard dedicated SQL (MySQL, etc.))
    # BOARDS (path, name, description)
        # num pages
        # num per page
        # allowed file types
    # ADMINS (name, trip code)
}