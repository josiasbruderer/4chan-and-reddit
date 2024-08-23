CREATE TABLE IF NOT EXISTS platforms (
    uid INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(32) NOT NULL,
    archive VARCHAR(32)
);

INSERT OR IGNORE INTO platforms (`uid`, `name`, `archive`) VALUES
    (1, '4chan', '4plebs'),
    (2, 'reddit', 'redarcs'),
    (3, 'q_4chan', 'hagen-et-al'),
    (4, 'q_reddit', 'hagen-et-al');

CREATE TABLE IF NOT EXISTS boards (
    uid INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(64) NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS boards_name ON boards(name);

CREATE TABLE IF NOT EXISTS images_archives (
    uid INTEGER PRIMARY KEY AUTOINCREMENT,
    platform_uid INTEGER NOT NULL,
    board_uid INTEGER NOT NULL,
    group1 INTEGER DEFAULT NULL,
    date_from TIMESTAMP DEFAULT NULL,
    date_to TIMESTAMP DEFAULT NULL,
    url VARCHAR(255) NOT NULL,
    size INTEGER NOT NULL,
    FOREIGN KEY(platform_uid) REFERENCES platforms(uid),
    FOREIGN KEY(board_uid) REFERENCES boards(uid)
);

CREATE UNIQUE INDEX IF NOT EXISTS images_archives_uuid ON images_archives(platform_uid, board_uid, group1);


CREATE TABLE IF NOT EXISTS images_data (
    platform_uid INTEGER NOT NULL,
    board_uid INTEGER NOT NULL,
    image_id INTEGER,
    data BLOB DEFAULT NULL,
    FOREIGN KEY(platform_uid) REFERENCES platforms(uid),
    FOREIGN KEY(board_uid) REFERENCES boards(uid),
    PRIMARY KEY (platform_uid, board_uid, image_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS images_data_uuid ON images_data(platform_uid, board_uid, image_id);

CREATE TABLE IF NOT EXISTS thumbs_data (
    platform_uid INTEGER NOT NULL,
    board_uid INTEGER NOT NULL,
    image_id INTEGER,
    data BLOB DEFAULT NULL,
    FOREIGN KEY(platform_uid) REFERENCES platforms(uid),
    FOREIGN KEY(board_uid) REFERENCES boards(uid),
    PRIMARY KEY (platform_uid, board_uid, image_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS thumbs_data_uuid ON thumbs_data(platform_uid, board_uid, image_id);

CREATE TABLE IF NOT EXISTS images (
    uid INTEGER PRIMARY KEY  AUTOINCREMENT,
    platform_uid INTEGER NOT NULL,
    board_uid INTEGER NOT NULL,
    image_id INTEGER,
    image_name VARCHAR(64) DEFAULT NULL,
    image_size INT DEFAULT NULL,
    thumb_name VARCHAR(64) DEFAULT NULL,
    thumb_size INT DEFAULT NULL,
    added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated TIMESTAMP DEFAULT NULL,
    FOREIGN KEY(platform_uid) REFERENCES platforms(uid),
    FOREIGN KEY(board_uid) REFERENCES boards(uid)
);

CREATE UNIQUE INDEX IF NOT EXISTS images_uuid ON images(platform_uid, board_uid, image_id);

CREATE VIEW IF NOT EXISTS v_all_images_meta AS
    SELECT `images`.*, `platforms`.name as platform, `boards`.name as board FROM `images`
    JOIN `platforms` ON `images`.platform_uid = `platforms`.uid
    JOIN `boards` ON `images`.board_uid = `boards`.uid;

CREATE VIEW IF NOT EXISTS v_all_images AS
    SELECT `images`.*, `platforms`.name as platform, `boards`.name as board, `images_data`.data as image_data, `thumbs_data`.data as thumb_data FROM `images`
    JOIN `platforms` ON `images`.platform_uid = `platforms`.uid
    JOIN `boards` ON `images`.board_uid = `boards`.uid
    LEFT JOIN `thumbs_data` ON `images`.platform_uid = `thumbs_data`.platform_uid AND `images`.board_uid = `thumbs_data`.board_uid AND `images`.image_id = `thumbs_data`.image_id
    LEFT JOIN `images_data` ON `images`.platform_uid = `images_data`.platform_uid AND `images`.board_uid = `images_data`.board_uid AND `images`.image_id = `images_data`.image_id;

CREATE VIEW IF NOT EXISTS v_all_images_archives AS
    SELECT `images_archives`.*, `images_archives`.size / 1024 / 1024 / 1024 as size_gb FROM images_archives