PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS crypto(
	id INTEGER PRIMARY KEY ASC,
	name text KEY NOT NULL,
	version INTEGER NOT NULL,
	algo text NOT NULL,
	bits INTEGER,
	UNIQUE(name)
);

-- Version control for future crypto migrations, not that these should change soon
--  - file_checksum is obviously for files
--  - hash_password is for trip codes, argon2i is slow to break if a table gets dumped
INSERT OR IGNORE INTO crypto(id, name, version, algo, bits) 
VALUES 
(
	0,
	'file_checksum',
	1,
	'sha',
	512
),
(
	1,
	'hash_password',
	1,
	'argon2i',
	-1
);

CREATE TABLE IF NOT EXISTS board(
	path text PRIMARY KEY NOT NULL,
	name text UNIQUE NOT NULL,
	description text,
	UNIQUE(name)
);

INSERT OR IGNORE INTO board(path, name, description)
VALUES
(
	'/b/',
	'Random',
	'Don''t do it.'
),
(
	'/g/',
	'Technology',
	'Your choice of Emacs has me quite discheesed.'
),
(
	'/lit/',
	'Literature',
	'This place is /lit/'
),
(
	'/sci/',
	'Science & Math',
	'Most research is tripe, this board is no different'
),
(
	'/t/', 
	'Torrents', 
	'You wouldn''t download a car, would you anon?'
),
(
	'/x/',
	'Paranormal',
	'Meds, anon.'
);

CREATE TABLE IF NOT EXISTS content(
	id INTEGER PRIMARY KEY ASC, 
	created text DEFAULT current_timestamp,
	board text NOT NULL,
	thread_id INTEGER,
	page INTEGER NOT NULL,
	name text NOT NULL DEFAULT 'Anonymous', 
	options text,
	subject text,
	comment text NOT NULL,
	replies INTEGER DEFAULT 0,
	image_replies INTEGER DEFAULT 0,
	FOREIGN KEY(thread_id) REFERENCES content(content_id),
	FOREIGN KEY(board) REFERENCES board(path) 
		ON DELETE CASCADE
	-- UNIQUE(comment)
);

CREATE TABLE IF NOT EXISTS image(
	id INTEGER PRIMARY KEY ASC,
	created text DEFAULT current_timestamp,
	content_id INTEGER NOT NULL,
	filename text NOT NULL, 
	orig_filename text NOT NULL,
	size INTEGER NOT NULL,
	width INTEGER NOT NULL, 
	height INTEGER NOT NULL, 
	checksum text NOT NULL,
	thread_id INTEGER,
	version INTEGER NOT NULL,
	url text NOT NULL,
	FOREIGN KEY(content_id) REFERENCES content(content_id)
		ON DELETE CASCADE,
	FOREIGN KEY(version) REFERENCES crypto(id)
		ON DELETE CASCADE,
	FOREIGN KEY(thread_id) REFERENCES content(content_id),
	UNIQUE(content_id)
);

CREATE TABLE IF NOT EXISTS deletion_auth(
	content_id INTEGER PRIMARY KEY NOT NULL,
	image_id INTEGER,
	pass TEXT NOT NULL,
	FOREIGN KEY(content_id) REFERENCES content(id)
		ON DELETE CASCADE,
	FOREIGN KEY(image_id) REFERENCES images(id)
		ON DELETE CASCADE
);

-- Table to track database migrations versions, these include:
-- 
--- schema changes
--- stored procedure additions/deletions/modifications
--- configuration data
--- admin controlled data such as boards, configurations, site information updates
---		- it's fine to read these in from a config file, but live changes 
---     - are better than dark-deploying an instance and swapping DNS with
---     - teardown of the old.
--- 
-- TODO: Track version/see if this migration file can be hashed
CREATE TABLE IF NOT EXISTS migration(
	id INTEGER PRIMARY KEY ASC,
	name text NOT NULL,
	UNIQUE(name)
);

-- Maintain counts for replies
CREATE TRIGGER IF NOT EXISTS content_omission_trigger
   	BEFORE INSERT ON content
   	WHEN NEW.thread_id NOT NULL
BEGIN
 	UPDATE content SET replies = replies + 1
	WHERE content.id = NEW.thread_id;
END;

-- Maintain counts for image replies
CREATE TRIGGER IF NOT EXISTS image_omission_trigger
   	BEFORE INSERT ON image
   	WHEN NEW.thread_id NOT NULL
BEGIN
 	UPDATE content 
 	SET image_replies = image_replies + 1
 	WHERE content.id = NEW.thread_id;
END;

-- Roll threads past 100 for each board after insertion
CREATE TRIGGER IF NOT EXISTS roll_threads_trigger
	AFTER INSERT ON content
	WHEN (SELECT
			CASE WHEN COUNT(*) > 100 
			THEN 1 
			ELSE 0 
			END 
		  FROM (SELECT id 
		  		FROM content 
				WHERE board = NEW.board 
				AND thread_id IS NULL))
BEGIN
	DELETE FROM content
	WHERE created = (SELECT MIN(created) 
						FROM content 
						WHERE board = NEW.board 
						AND thread_id IS NULL);
END;

-- Maintain rolling queue for threads
-- CREATE TRIGGER IF NOT EXISTS roll_threads
-- 	BEFORE INSERT ON content
-- BEGIN
-- 	-- if num posts < board per page * pages
-- 	--   delete oldest if not stickied and add to image deletion queue
-- END;

INSERT OR IGNORE INTO migration(name) VALUES ('V001__onchan_init.sql');
