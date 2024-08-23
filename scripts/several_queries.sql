SELECT count(`v_all_images_meta`.image_id) FROM v_all_images_meta
JOIN boards on v_all_images_meta.board_uid = boards.uid
where boards.name = '/pol/';



SELECT
    strftime('%Y-%m-%d %H:%M:%S', datetime(min(`v_all_images_meta`.image_id)/1000, 'unixepoch')) AS first,
    strftime('%Y-%m-%d %H:%M:%S', datetime(max(`v_all_images_meta`.image_id)/1000, 'unixepoch')) AS last
FROM v_all_images_meta
JOIN boards on v_all_images_meta.board_uid = boards.uid
where boards.name = '/pol/';



SELECT
    strftime('%Y-%m-%d', datetime(`v_all_images_meta`.image_id/1000, 'unixepoch')) AS date,
    count(`v_all_images_meta`.image_id) AS count_per_day
FROM v_all_images_meta
JOIN boards ON v_all_images_meta.board_uid = boards.uid
WHERE boards.name = '/pol/'
GROUP BY date ORDER BY date;



-- this is the fastest way:
CREATE TEMPORARY TABLE TEMP_dihw AS
SELECT *  FROM v_all_posts as v
  WHERE v.body MATCH 'whitepill*';

SELECT * from TEMP_dihw as t
JOIN fts_idx ON fts_idx.ROWID = t.uid
WHERE t.platform = '4chan';

DROP TABLE IF EXISTS TEMP_dihw;




CREATE TEMPORARY TABLE TEMP_dihw AS
SELECT meta.*, round(bm25(fts_idx),3) as rank, subject, extras, highlight(fts_idx, 1, '<span class="fts_match">', '</span>') body from fts_idx
    JOIN v_all_posts_meta as meta on meta.uid = fts_idx.ROWID
    WHERE `fts_idx`.body MATCH 'whitepill*'
    ORDER BY rank;

SELECT count() from TEMP_dihw;

DROP TABLE IF EXISTS TEMP_dihw;





CREATE TEMPORARY TABLE TEMP_asdf AS
SELECT board_uid, platform_uid, count() as count_posts FROM posts
GROUP BY board_uid, platform_uid
ORDER BY count_posts DESC;

SELECT b.name, p.name, t.count_posts FROM TEMP_asdf as t
JOIN boards as b on t.board_uid = b.uid
JOIN platforms as p on t.platform_uid = p.uid;

DROP TABLE IF EXISTS TEMP_asdf;






SELECT
    t1.date AS date,
    COALESCE(t1.count_posts, 0) AS count_4chan,
    COALESCE(t2.count_posts, 0) AS count_q_4chan,
    COALESCE(t3.count_posts, 0) AS count_reddit,
    COALESCE(t4.count_posts, 0) AS count_q_reddit,
    COALESCE(t5.count_posts, 0) AS count_sample1,
    COALESCE(t6.count_posts, 0) AS count_sample2
FROM
    (SELECT strftime('%Y-%m-%d', v.timestamp) as date, count() AS count_posts
     FROM v_all_posts_meta as v
     WHERE v.platform = '4chan'
     GROUP BY date) t1
LEFT JOIN
    (SELECT strftime('%Y-%m-%d', v.timestamp) as date, count() AS count_posts
     FROM v_all_posts_meta as v
     WHERE v.platform = 'q_4chan'
     GROUP BY date) t2
ON t1.date = t2.date
LEFT JOIN
    (SELECT strftime('%Y-%m-%d', v.timestamp) as date, count() AS count_posts
     FROM v_all_posts_meta as v
     WHERE v.platform = 'reddit'
     GROUP BY date) t3
ON t1.date = t3.date
LEFT JOIN
    (SELECT strftime('%Y-%m-%d', v.timestamp) as date, count() AS count_posts
     FROM v_all_posts_meta as v
     WHERE v.platform = 'q_reddit'
     GROUP BY date) t4
ON t1.date = t4.date
LEFT JOIN
    (SELECT strftime('%Y-%m-%d', v.timestamp) as date, count() AS count_posts
     FROM v_all_posts_meta as v
     WHERE v.uid IN (select * from tmp_asdfa)
     GROUP BY date) t5
ON t1.date = t5.date
LEFT JOIN
    (SELECT strftime('%Y-%m-%d', v.timestamp) as date, count() AS count_posts
     FROM v_all_posts_meta as v
     WHERE v.uid IN (select * from tmp_asdfa)
     GROUP BY date) t6
ON t1.date = t6.date
ORDER BY t1.date;
