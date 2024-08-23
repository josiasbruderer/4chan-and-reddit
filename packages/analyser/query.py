import random
import string

from tabulate import tabulate


def randomString(N=8):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=N))


QUERIES = {
    "test": {
        "h": ['test'],
        "q": '''SELECT :test as test;'''
    },
    "counts_per_board": {
        "h": ['board', 'platform', 'count_posts'],
        "q": {
            'pre': '''CREATE TEMPORARY TABLE [tmp_table_name] AS
SELECT board_uid, platform_uid, count() as count_posts FROM posts
GROUP BY board_uid, platform_uid
ORDER BY count_posts DESC;''',
            'query': '''SELECT b.name, p.name, t.count_posts FROM [tmp_table_name] as t
JOIN boards as b on t.board_uid = b.uid
JOIN platforms as p on t.platform_uid = p.uid;''',
            'post': '''DROP TABLE IF EXISTS [tmp_table_name];'''
          }
    },
    "counts_per_platform": {
      "h": ['platform', 'count_posts'],
      "q": '''SELECT p.name, v.count_posts from (
SELECT platform_uid, count() as count_posts FROM posts
GROUP BY platform_uid ) v
join platforms as p ON p.uid = v.platform_uid'''
    },
    "fts_body_count_by_platform": {
        "h": ['count'],
        "q": {
            'pre': '''CREATE TEMPORARY TABLE [tmp_table_name] AS
SELECT DISTINCT meta.*, round(bm25(fts_idx),3) as rank, subject, extras, highlight(fts_idx, 1, '<span class="fts_match">', '</span>') body from fts_idx
JOIN v_all_posts_meta as meta on meta.uid = fts_idx.ROWID
WHERE `fts_idx`.body MATCH :keyword
ORDER BY rank;''',
            'query': '''SELECT count() as count_posts from [tmp_table_name] as t
WHERE t.platform = :platform;''',
            'digg_query': '''SELECT * from [tmp_table_name] as t
WHERE t.platform = :platform;''',
            'post': '''DROP TABLE IF EXISTS [tmp_table_name];'''}
    },
    "create_sample": {
        "h": [],
        "q": '''CREATE TEMPORARY TABLE [sample_table_name] AS
SELECT uid from posts WHERE platform_uid = (SELECT uid FROM platforms WHERE name = :platform)
ORDER BY RANDOM() LIMIT (SELECT count() FROM v_all_posts_meta WHERE platform = concat('q_', :platform));'''
    },
    "create_sample_v2": {
        "h": [],
        "q": '''CREATE TEMPORARY TABLE [sample_table_name] AS
SELECT uid from posts WHERE platform_uid = (SELECT uid FROM platforms WHERE name = :platform)
ORDER BY RANDOM() LIMIT (SELECT count() FROM v_all_posts_meta WHERE platform = :platform) / 100;'''
    },
    "delete_sample": {
      "h": [],
      "q": '''DROP TABLE IF EXISTS [sample_table_name];'''
    },
    "dump_sample": {
      "h": ['uid'],
      "q": '''SELECT uid FROM [sample_table_name];'''
    },
    "dump_sample2": {
      "h": ['uid', 'post_id', 'timestamp', 'thread_id', 'thread_uid', 'parent_id', 'parent_uid', 'author', 'subject', 'body', 'extras', 'board', 'platform', 'post_type'],
      "q": '''SELECT * FROM v_all_posts WHERE uid in (SELECT uid FROM [sample_table_name]);'''
    },
    "fts_body_count_in_sample": {
        "h": ['count'],
        "q": {
            'pre': '''CREATE TEMPORARY TABLE [tmp_table_name] AS
SELECT DISTINCT meta.*, round(bm25(fts_idx),3) as rank, subject, extras, highlight(fts_idx, 1, '<span class="fts_match">', '</span>') body from fts_idx
JOIN v_all_posts_meta as meta on meta.uid = fts_idx.ROWID
WHERE `fts_idx`.body MATCH :keyword
ORDER BY rank;''',
            'query': '''SELECT count() from [tmp_table_name] as v
INNER JOIN [sample_table_name] as t ON v.uid = t.uid;''',
            'digg_query': '''SELECT * from [tmp_table_name] as v
INNER JOIN [sample_table_name] as t ON v.uid = t.uid;''',
            'post': '''DROP TABLE IF EXISTS [tmp_table_name];'''
        }
    },
    "meta_posts_per_day": {
        "h": ['date', 'count_4chan', 'count_q_4chan', 'count_sample_4chan', 'count_reddit', 'count_q_reddit', 'count_sample_reddit'],
        "q": '''SELECT
    t1.date AS date,
    COALESCE(t1.count_posts, 0) AS count_4chan,
    COALESCE(t2.count_posts, 0) AS count_q_4chan,
    COALESCE(t3.count_posts, 0) AS count_sample_4chan,
    COALESCE(t4.count_posts, 0) AS count_reddit,
    COALESCE(t5.count_posts, 0) AS count_q_reddit,
    COALESCE(t6.count_posts, 0) AS count_sample_reddit
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
     WHERE v.uid IN (select * from [sample_table_name0])
     GROUP BY date) t3
ON t1.date = t3.date
LEFT JOIN
    (SELECT strftime('%Y-%m-%d', v.timestamp) as date, count() AS count_posts
     FROM v_all_posts_meta as v
     WHERE v.platform = 'reddit'
     GROUP BY date) t4
ON t1.date = t4.date
LEFT JOIN
     (SELECT strftime('%Y-%m-%d', v.timestamp) as date, count() AS count_posts
     FROM v_all_posts_meta as v
     WHERE v.platform = 'q_reddit'
     GROUP BY date) t5
ON t1.date = t5.date
LEFT JOIN
    (SELECT strftime('%Y-%m-%d', v.timestamp) as date, count() AS count_posts
     FROM v_all_posts_meta as v
     WHERE v.uid IN (select * from [sample_table_name1])
     GROUP BY date) t6
ON t1.date = t6.date
ORDER BY t1.date;'''
    }
}


class querymanager:
    def __init__(self):
        '''nothing'''

    def get(self, name=None):
        if not name:
            return QUERIES.keys()
        if name in QUERIES:
            return QUERIES[name]['h'], QUERIES[name]['q']
        return False

    def query_sample(self, conn, name, data=None, sample_name=None, format=None, traceable=False, deepdigg=False):
        if not sample_name:
            sample_name = "sample_" + randomString()
        if data is None:
            data = []
        cur = conn.cursor()
        q = self.get(name)
        tmp_data = None
        tmp_digg = None

        if not q:
            return False, 'unknown query'

        try:
            if name == "create_sample" or name == "create_sample_v2":
                cur.execute(q[1].replace('[sample_table_name]', sample_name), data)
                return sample_name
            if name == "delete_sample":
                cur.execute(q[1].replace('[sample_table_name]', sample_name), data)
                return True
            if name == "meta_posts_per_day":
                tmp_data = cur.execute(q[1].replace('[sample_table_name0]', sample_name[0]).replace('[sample_table_name1]', sample_name[1]), data).fetchall()
                return q[0], tmp_data
            if type(q[1]) is str:
                tmp_data = cur.execute(q[1].replace('[sample_table_name]', sample_name), data).fetchall()
            if type(q[1]) is dict:
                tmp_table_name = "tmp_" + randomString()
                cur.execute(q[1]["pre"].replace('[tmp_table_name]', tmp_table_name).replace('[sample_table_name]', sample_name), data)
                tmp_data = cur.execute(q[1]["query"].replace('[tmp_table_name]', tmp_table_name).replace('[sample_table_name]', sample_name), data).fetchall()
                if deepdigg:
                    tmp_digg = cur.execute(q[1]["digg_query"].replace('[tmp_table_name]', tmp_table_name).replace('[sample_table_name]', sample_name), data).fetchall()
                cur.execute(q[1]["post"].replace('[tmp_table_name]', tmp_table_name).replace('[sample_table_name]', sample_name), data)
        except Exception as e:
            return False, str(e)

        if format == "table":
            tbl = self.format_table(tmp_data, q[0])
            if traceable:
                return tbl + '\n> Parameters: ' + str(data) + '\n> Query: ' + str(q[1])
            return tbl

        if format == "single":
            if traceable:
                print('\n> Parameters: ' + str(data) + '\n> Query: ' + str(q[1]))

            if deepdigg:
                return tmp_data[0][0], tmp_digg

            return tmp_data[0][0]

        if traceable and deepdigg:
            return q[0], tmp_data, q[1], data, tmp_digg

        if traceable:
            return q[0], tmp_data, q[1], data

        if deepdigg:
            return q[0], tmp_data, tmp_digg

        return q[0], tmp_data


    def query(self, conn, name, data=None, format=None, traceable=False, deepdigg=False):
        if data is None:
            data = []
        cur = conn.cursor()
        q = self.get(name)
        tmp_data = None
        tmp_digg = None

        if not q:
            return False, 'unknown query'

        try:
            if type(q[1]) is str:
                tmp_data = cur.execute(q[1], data).fetchall()
            if type(q[1]) is dict:
                tmp_table_name = "tmp_" + randomString()
                cur.execute(q[1]["pre"].replace('[tmp_table_name]', tmp_table_name), data)
                tmp_data = cur.execute(q[1]["query"].replace('[tmp_table_name]', tmp_table_name), data).fetchall()
                if deepdigg:
                    tmp_digg = cur.execute(q[1]["digg_query"].replace('[tmp_table_name]', tmp_table_name), data).fetchall()
                cur.execute(q[1]["post"].replace('[tmp_table_name]', tmp_table_name), data)
        except Exception as e:
            return False, str(e)

        if format == "table":
            tbl = self.format_table(tmp_data, q[0])
            if traceable:
                return tbl + '\n> Parameters: ' + str(data) + '\n> Query: ' + str(q[1])
            return tbl

        if format == "single":
            if traceable:
                print('\n> Parameters: ' + str(data) + '\n> Query: ' + str(q[1]))

            if deepdigg:
                return tmp_data[0][0], tmp_digg

            return tmp_data[0][0]

        if traceable and deepdigg:
            return q[0], tmp_data, q[1], data, tmp_digg

        if traceable:
            return q[0], tmp_data, q[1], data

        if deepdigg:
            return q[0], tmp_data, tmp_digg

        return q[0], tmp_data

    def format_table(self, data, headers):
        return tabulate(data, headers, tablefmt='orgtbl')
