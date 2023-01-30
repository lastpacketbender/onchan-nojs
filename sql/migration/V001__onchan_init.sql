PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS migration(
	version INTEGER PRIMARY KEY ASC,
	name text NOT NULL,
	hash text NOT NULL,
	UNIQUE(name, hash)
);

-- Versioned crypto for algorithm changes
CREATE TABLE IF NOT EXISTS crypto(
	id INTEGER PRIMARY KEY ASC,
	name text KEY NOT NULL,
	version INTEGER NOT NULL,
	algo text NOT NULL,
	bits INTEGER,
	UNIQUE(name)
);

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
	thread_limit INTEGER NOT NULL DEFAULT 100,
	image_limit INTEGER NOT NULL DEFAULT 50,
	bump_limit INTEGER NOT NULL DEFAULT 100,
	UNIQUE(name)
);

CREATE TABLE IF NOT EXISTS content(
	id INTEGER PRIMARY KEY ASC, 
	created DATETIME DEFAULT current_timestamp,
	board text NOT NULL,
	thread_id INTEGER,
	name text NOT NULL DEFAULT 'Anonymous', 
	options text,
	subject text,
	comment text NOT NULL,
	replies INTEGER DEFAULT 0,
	image_replies INTEGER DEFAULT 0,
	limited_at DATETIME,
	sage INTEGER DEFAULT 0,
	FOREIGN KEY(thread_id) REFERENCES content(content_id)
		ON DELETE CASCADE,
	FOREIGN KEY(board) REFERENCES board(path) 
		ON DELETE CASCADE
);

CREATE INDEX idx_content_board on content(board);
CREATE INDEX idx_content_thread_id ON content(thread_id);

CREATE TABLE IF NOT EXISTS image(
	id INTEGER PRIMARY KEY ASC,
	created DATETIME DEFAULT current_timestamp,
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
	FOREIGN KEY(thread_id) REFERENCES content(content_id)
		ON DELETE CASCADE,
	UNIQUE(content_id)
);

CREATE INDEX idx_image_thread_id ON image(thread_id);

CREATE TABLE IF NOT EXISTS deletion_auth(
	content_id INTEGER PRIMARY KEY NOT NULL,
	image_id INTEGER,
	password_hash TEXT NOT NULL,
	FOREIGN KEY(content_id) REFERENCES content(id)
		ON DELETE CASCADE,
	FOREIGN KEY(image_id) REFERENCES images(id)
		ON DELETE CASCADE
);

CREATE INDEX idx_deletion_auth_image_id ON deletion_auth(image_id);
CREATE INDEX idx_deletion_auth_password_hash ON deletion_auth(password_hash);

CREATE TABLE IF NOT EXISTS image_removal_queue(
	path TEXT PRIMARY KEY NOT NULL
);

CREATE TABLE IF NOT EXISTS quotes(
	source_id INTEGER NOT NULL,
	content_id INTEGER NOT NULL,
	FOREIGN KEY(content_id) REFERENCES content(id)
		ON DELETE CASCADE,
	FOREIGN KEY(source_id) REFERENCES content(id)
		ON DELETE CASCADE,
	PRIMARY KEY(source_id, content_id)
);

CREATE INDEX idx_quotes_thread_id ON quotes(content_id);

-- Maintain counts for replies
CREATE TRIGGER IF NOT EXISTS increment_replies_trigger
   	AFTER INSERT ON content
   	WHEN NEW.thread_id NOT NULL
BEGIN
 	UPDATE content
	SET replies = replies + 1,
		limited_at = CASE
					 WHEN content.limited_at IS NULL AND replies + sage = (SELECT bump_limit FROM board WHERE path = NEW.board) - 1
					 THEN current_timestamp 
					 ELSE content.limited_at
					 END
	WHERE content.id = NEW.thread_id;
END;

CREATE TRIGGER IF NOT EXISTS decrement_replies_trigger
	AFTER DELETE ON content
	WHEN OLD.thread_id IS NOT NULL
BEGIN
	UPDATE content 
	SET replies = replies - 1
	WHERE content.id = OLD.thread_id;
END;

-- Maintain counts for image replies
CREATE TRIGGER IF NOT EXISTS increment_image_replies_trigger
   	AFTER INSERT ON image
   	WHEN NEW.thread_id NOT NULL
BEGIN
 	UPDATE content 
 	SET image_replies = image_replies + 1
 	WHERE content.id = NEW.thread_id;
END;

CREATE TRIGGER IF NOT EXISTS decrement_image_replies_trigger
	AFTER DELETE ON image
BEGIN
	UPDATE content 
	SET image_replies = image_replies - 1
	WHERE content.id = OLD.thread_id;
	-- Insertion to image_removal_queue happens here
	INSERT INTO image_removal_queue(path) VALUES (OLD.url);
END;

-- Remove image and deletion_auth for replies
-- FIXME: Why are foreign keys not handling this?
CREATE TRIGGER IF NOT EXISTS prune_content_image_and_auth_trigger
	AFTER DELETE ON content
	WHEN (SELECT COUNT(id) FROM image WHERE content_id = OLD.id)
BEGIN
	DELETE FROM image WHERE content_id = OLD.id;
	DELETE FROM deletion_auth WHERE content_id = OLD.id;
END;

-- Remove deletion_auth and replies for a thread
-- FIXME: Why are foreign keys not handling this?
CREATE TRIGGER IF NOT EXISTS prune_children_trigger
	AFTER DELETE ON content
	WHEN OLD.thread_id IS NULL
BEGIN
	DELETE FROM deletion_auth WHERE content_id IN (SELECT id FROM content WHERE thread_id = OLD.id);
	DELETE FROM content WHERE thread_id = OLD.id;
END;

-- Roll threads when thread_limit is exceeded
CREATE TRIGGER IF NOT EXISTS roll_threads_trigger
	BEFORE INSERT ON content
	WHEN NEW.thread_id IS NULL 
	AND (SELECT CASE WHEN COUNT(*) >= (SELECT thread_limit 
									  FROM board 
									  WHERE board.path = NEW.board) 
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
