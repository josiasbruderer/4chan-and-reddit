CREATE TABLE IF NOT EXISTS platforms (
    uid INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(32) NOT NULL UNIQUE,
    archive VARCHAR(32)
);

INSERT OR IGNORE INTO platforms (`uid`, `name`, `archive`) VALUES
    (1, '4chan', '4plebs'),
    (2, 'reddit', 'redarcs'),
    (3, 'q_4chan', 'hagen-et-al'),
    (4, 'q_reddit', 'hagen-et-al');

CREATE TABLE IF NOT EXISTS boards (
    uid INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(64) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS types (
    uid INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(32) NOT NULL UNIQUE
);

INSERT OR IGNORE INTO types (`uid`, `name`) VALUES (1, 'thread'), (2, 'comment'), (3, 'submission');

CREATE TABLE IF NOT EXISTS posts (
    uid INTEGER PRIMARY KEY AUTOINCREMENT,
    platform_uid INTEGER NOT NULL,
    board_uid INTEGER NOT NULL,
    type_uid INTEGER NOT NULL,
    post_id VARCHAR(64) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    thread_id VARCHAR(64) DEFAULT NULL,
    parent_id VARCHAR(64) DEFAULT NULL,
    parent_uid INTEGER DEFAULT NULL,
    thread_uid INTEGER DEFAULT NULL,
    author VARCHAR(255) DEFAULT NULL,
    subject TEXT DEFAULT NULL,
    body TEXT DEFAULT NULL,
    extras TEXT DEFAULT NULL,
    added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(platform_uid) REFERENCES platforms(uid),
    FOREIGN KEY(board_uid) REFERENCES boards(uid),
    FOREIGN KEY(type_uid) REFERENCES types(uid),
    FOREIGN KEY(parent_uid) REFERENCES posts(uid),
    FOREIGN KEY(thread_uid) REFERENCES posts(uid),
    UNIQUE(platform_uid, board_uid, type_uid, post_id, timestamp)
);

-- Add index for platform
CREATE INDEX IF NOT EXISTS idx_posts_platform ON posts(platform_uid);

-- Add index for board
CREATE INDEX IF NOT EXISTS idx_posts_board ON posts(board_uid);

-- FTS index to speed up full text search
CREATE VIRTUAL TABLE IF NOT EXISTS fts_idx USING fts5(subject, body, extras, content='posts', content_rowid='uid');

-- Triggers to keep the FTS index up to date.
CREATE TRIGGER IF NOT EXISTS tbl_ai AFTER INSERT ON posts BEGIN
  INSERT INTO fts_idx(rowid, subject, body, extras) VALUES (new.uid, new.subject, new.body, new.extras);
END;
CREATE TRIGGER IF NOT EXISTS tbl_ad AFTER DELETE ON posts BEGIN
  INSERT INTO fts_idx(fts_idx, rowid, subject, body, extras) VALUES('delete', old.uid, old.subject, old.body, old.extras);
END;
CREATE TRIGGER IF NOT EXISTS tbl_au AFTER UPDATE ON posts BEGIN
  INSERT INTO fts_idx(fts_idx, rowid, subject, body, extras) VALUES('delete', old.uid, old.subject, old.body, old.extras);
  INSERT INTO fts_idx(rowid, subject, body, extras) VALUES (new.uid, new.subject, new.body, new.extras);
END;

CREATE VIEW IF NOT EXISTS v_all_posts AS
    SELECT `posts`.`uid`,`posts`.`post_id`,`posts`.`timestamp`,`posts`.
    `thread_id`,`posts`.`thread_uid`,`posts`.`parent_id`,`posts`.`parent_uid`,
    `posts`.`author`,`fts_idx`.`subject`,`fts_idx`.`body`,`fts_idx`.`extras`,
    `boards`.name as 'board', `platforms`.name as 'platform', `types`.name as 'post_type' FROM posts
    JOIN boards ON posts.board_uid = boards.uid
    JOIN platforms ON posts.platform_uid = platforms.uid
    JOIN types ON posts.type_uid = types.uid
    JOIN fts_idx ON `posts`.uid = fts_idx.ROWID;


CREATE VIEW IF NOT EXISTS v_all_posts_meta AS
    SELECT `posts`.`uid`,`posts`.`post_id`,`posts`.`timestamp`,`posts`.
    `thread_id`,`posts`.`thread_uid`,`posts`.`parent_id`,`posts`.`parent_uid`,
    `posts`.`author`,
    `boards`.name as 'board', `platforms`.name as 'platform', `types`.name as 'post_type' FROM posts
    JOIN boards ON posts.board_uid = boards.uid
    JOIN platforms ON posts.platform_uid = platforms.uid
    JOIN types ON posts.type_uid = types.uid;

CREATE VIEW IF NOT EXISTS v_reddit AS
    SELECT * FROM v_all_posts
    WHERE platform = 'reddit';

CREATE VIEW IF NOT EXISTS v_fourchan AS
    SELECT * FROM v_all_posts
    WHERE platform = '4chan';

CREATE VIEW IF NOT EXISTS v_q_reddit AS
    SELECT * FROM v_all_posts
    WHERE platform = 'q_reddit';

CREATE VIEW IF NOT EXISTS v_q_fourchan AS
    SELECT * FROM v_all_posts
    WHERE platform = 'q_4chan';

CREATE VIEW IF NOT EXISTS v_reddit_meta AS
    SELECT * FROM v_all_posts_meta
    WHERE platform = 'reddit';

CREATE VIEW IF NOT EXISTS v_fourchan_meta AS
    SELECT * FROM v_all_posts_meta
    WHERE platform = '4chan';

CREATE VIEW IF NOT EXISTS v_q_reddit_meta AS
    SELECT * FROM v_all_posts_meta
    WHERE platform = 'q_reddit';

CREATE VIEW IF NOT EXISTS v_q_fourchan_meta AS
    SELECT * FROM v_all_posts_meta
    WHERE platform = 'q_4chan';

