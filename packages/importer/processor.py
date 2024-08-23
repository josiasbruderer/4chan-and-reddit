import io
import ciso8601
import csv
import datetime
import gzip
import json
import multiprocessing
import os
import random
import re
import sqlite3
import string
import tarfile
import time
import xml.etree.ElementTree as ET
from packages import databaser
from packages import logger


def get_random_string(length):
    return ''.join(random.choice(string.ascii_lowercase) for i in range(length))


def get_archive_size(input_file):
    '''
    Calculate the actual uncompressed size based on ISIZE and the compressed size.
    we will assume multiple overflows...
    '''
    compressed_size = os.stat(input_file).st_size
    with open(input_file, "rb") as f:
        # get the size of uncompressed input from last 4 bytes
        f.seek(-4, 2)
        actual_size = int.from_bytes(f.read(), "little")

    # calculate n overflows
    n = 1 + int(compressed_size > 512 * 1024 * 1024) + int(compressed_size > 1024 * 1024 * 1024) + int(compressed_size > 2048 * 1024 * 1024)

    mod_limit = n * 2 ** 32  # The 32-bit limit (2^32)

    # If the compressed size exceeds the 32-bit limit, account for overflow
    while actual_size < compressed_size:
        actual_size += mod_limit

    return compressed_size, actual_size


def get_path_info(c):
    try:
        fpath = str.split(c.path, "/")
        return re.sub(r'\D', '', fpath[3]), fpath[3]
    except:
        return None, None  # found invalid file


def identify_4chan_parent_id(body):
    try:
        return re.search("^>>([0-9]+)", body).group(1)
    except:
        return None


def parse_trash_data(data):
    if data == "N":
        return None
    return data


def parse_reddit_parent(c):
    try:
        return c["parent_id"]
    except:
        return None


def save_processed_data(processed_data, sql_write_queue):
    sql_write_queue.put(('''
    INSERT OR IGNORE INTO posts (`platform_uid`, `board_uid`, `type_uid`,
    `post_id`, `timestamp`, `thread_id`, `parent_id`, `author`, `subject`, `body`, `extras`) VALUES
    (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    ''', processed_data))


def save_thumb_data(processed_data, sql_write_queue):
    sql_write_queue.put(('''
    INSERT OR IGNORE INTO thumbs_data(`platform_uid`, `board_uid`, `image_id`, `data`)VALUES(?,?,?,?)
    ''', processed_data[1]))

    sql_write_queue.put(('''
    INSERT OR IGNORE INTO images (`platform_uid`, `board_uid`, `image_id`, `thumb_name`, `thumb_size`) VALUES (?, ?, ?, ?, ?);
    ''', processed_data[0]))


def save_image_data(processed_data, sql_write_queue):
    sql_write_queue.put(('''
    INSERT OR IGNORE INTO images_archives (`platform_uid`, `board_uid`, `group1`, `date_from`, `date_to`, `url`, `size`) VALUES 
    (?, ?, ?, ?, ?, ?, ?);
    ''', processed_data))


def error_handler(error):
    print(f'Error: {error}', flush=True)


class Processor:
    def __init__(self, db_name, chunk_size=32000, num_workers=8, date_range=None, log_file=None, download_prefix=None):
        self.db_name = db_name
        self.chunk_size = chunk_size
        self.num_workers = num_workers
        self.date_range = {
            'start': time.mktime(ciso8601.parse_datetime(date_range["start"]).timetuple()),
            'end': time.mktime(ciso8601.parse_datetime(date_range["end"]).timetuple())
        } if date_range and "start" in date_range and "end" in date_range else None
        self.log_file = log_file
        self.download_prefix = download_prefix

        self.input_file = None
        self.input_file_size = None
        self.input_file_size_uncompressed = None
        self.mode = None
        self.current_file = None
        self.total_files = None
        self.meta_cache = {}

        self.logg = logger.setup(__name__, self.log_file, logger.DEBUG)


    def debug(self, message):
        self.logg.debug(message)


    def start_import(self, input_file, mode, total_files=0, current_file=0):
        self.input_file = input_file
        self.input_file_size, self.input_file_size_uncompressed = get_archive_size(input_file)
        self.mode = mode
        self.total_files = total_files
        self.current_file = current_file
        
        self.logg.info(f'processing {self.input_file}')

        manager = multiprocessing.Manager()

        log_queue = manager.Queue()
        log_process = multiprocessing.Process(target=logger.queue_processor, args=(log_queue, self.logg))
        log_process.start()

        sql_write_queue = manager.Queue()
        sql_write_queue_priority = manager.Queue()
        sql_write_process = multiprocessing.Process(target=databaser.queue_processor,
                                                         args=(self.db_name, sql_write_queue, sql_write_queue_priority, self.logg))
        sql_write_process.start()

        if self.mode.startswith("q_"):
            """hagen-et-al datasets can be imported as csv - they ain't that big"""
            chunk = []
            with gzip.open(self.input_file, 'rt') as f:
                reader = csv.reader(f, delimiter=',', quotechar="\"")
                for row in reader:
                    if row[0] == "thread_id" or row[2] == "subreddit":
                        continue  # skip header column
                    chunk.append(row)
            processed_data = self.process_chunk(chunk, log_queue, sql_write_queue_priority)
            save_processed_data(processed_data, sql_write_queue)

        if self.mode == "reddit_submissions" or self.mode == "reddit_comments" or self.mode == "4chan":
            with multiprocessing.Pool(self.num_workers) as pool:
                with gzip.open(self.input_file, 'rt') as f:
                    for chunk in self.read_in_chunks(f):
                        pool.apply_async(
                            self.process_and_save,
                            (chunk, log_queue, sql_write_queue, sql_write_queue_priority),
                            error_callback=error_handler)
                pool.close()
                pool.join()

        if self.mode == "4chan_images":
            scope = os.path.basename(self.input_file).replace('_files.xml', '')
            root = ET.parse(self.input_file).getroot()
            data = []
            for child in root:
                if child.attrib.get('name').endswith(".tar.gz"):
                    platform = self.get_meta_id("platforms", self.mode.rstrip("_images"), sql_write_queue_priority)
                    board, grp = child.attrib.get('name').removesuffix('.tar.gz').split('-')
                    board = self.get_meta_id("boards", "/" + board + "/", sql_write_queue_priority)
                    d_from = int(grp) * 1000000
                    d_to = ((int(grp) + 1) * 1000000) - 1
                    url = self.download_prefix + scope + "/" + child.attrib.get('name')
                    size = child.find("size").text
                    data.append((platform, board, grp, d_from, d_to, url, size))
            save_image_data(data, sql_write_queue)
            print(f'\r100% processed reading of file {self.current_file} from {self.total_files}', end='\n')

        if self.mode == "4chan_thumbs":
            with multiprocessing.Pool(self.num_workers) as pool:
                threads = []
                with tarfile.open(self.input_file, 'r:gz') as tar:
                    for chunk in self.read_in_chunks(tar):
                        pool.apply_async(
                             self.process_and_save,
                             (chunk, log_queue, sql_write_queue, sql_write_queue_priority,),
                             error_callback=error_handler)
                pool.close()
                pool.join()

        # Signal the logging process to stop
        log_queue.put("STOP")
        log_process.join()
        log_process.close()

        # Signal the logging process to stop
        sql_write_queue.put("STOP")
        sql_write_process.join()
        sql_write_process.close()

    def read_in_chunks(self, file_object):
        """Lazy function (generator) to read a file piece by piece."""
        i = 0
        data = []
        lineoverflow = ""
        read_sofar = 0
        for obj in file_object:
            progress = round(read_sofar / self.input_file_size_uncompressed * 100, 2)
            print(f'\r{progress}% processed reading of file {self.current_file} from {self.total_files}', end='')

            if type(file_object) is io.TextIOWrapper:
                read_sofar += len(obj)
                obj = lineoverflow + obj
                if str.endswith(obj, "\\\n"):
                    lineoverflow = obj
                    continue

            if type(file_object) is tarfile.TarFile:
                read_sofar = obj.offset_data
                path_info = get_path_info(obj)[0]
                if obj.type != tarfile.REGTYPE or path_info is None or not self.in_date_range(int(path_info) / 1000):
                    continue

            lineoverflow = ""
            data.append(obj)
            i += 1
            if i == self.chunk_size:
                yield data
                i = 0
                data = []
        yield data  # yield last chunk no matter how small it is

    def process_and_save(self, chunk, log_queue, sql_write_queue, sql_write_queue_priority):
        chunk_id = get_random_string(6)
        processed_data = None
        try:
            processed_data = self.process_chunk(chunk, log_queue, sql_write_queue_priority)
            if processed_data and len(processed_data) > 0:
                if type(processed_data) is tuple: # thumbnail process always return tuple
                    chunk_length = len(processed_data[0])
                    chunk_size = round(sum(row[4] for row in processed_data[0]) / 1024 / 1024)
                    chunk_from = datetime.datetime.fromtimestamp(round(int(processed_data[0][0][2])/1000), datetime.UTC).isoformat()
                    chunk_to = datetime.datetime.fromtimestamp(round(int(processed_data[0][-1][2])/1000), datetime.UTC).isoformat()
                else:
                    chunk_length = len(processed_data)
                    chunk_size = round(sum(len(row[9] if row[9] else '') for row in processed_data) / 1024 / 1024)
                    chunk_from = processed_data[0][4].isoformat()
                    chunk_to = processed_data[-1][4].isoformat()
                log_queue.put(f'INFO chunk {chunk_id}: {chunk_length} records, {chunk_size} MB, reaching from {chunk_from} to {chunk_to}')
                if type(processed_data) is tuple:  # thumbnail process always return tuple
                    save_thumb_data(processed_data, sql_write_queue)
                else:
                    save_processed_data(processed_data, sql_write_queue)
        except Exception as e:
            print(e)
            log_queue.put(f"ERROR {chunk_id} -> " + str(e))
            log_queue.put(f"DEBUG chunk -> {str(chunk)[0:3200]}")
            log_queue.put(f"DEBUG processed_data -> {str(processed_data)[0:3200]}")

    def process_chunk(self, chunk, log_queue, sql_write_queue_priority):
        # we need following columns for comments data:
        # platform_uid, board_uid, type_uid,
        # post_id, timestamp,
        # thread_id, parent_id,
        # author, subject, body
        # extras
        processed_data = None
        try:
            if self.mode == "q_4chan":
                platform = self.get_meta_id("platforms", self.mode, sql_write_queue_priority)
                board = self.get_meta_id("boards", "/pol/", sql_write_queue_priority)
                post_type = self.get_meta_id("types", "comment", sql_write_queue_priority)
                if self.date_range:
                    chunk = [c for c in chunk if self.in_date_range(c[5])]
                if chunk:
                    processed_data = [(platform, board, post_type,
                        c[1], datetime.datetime.fromtimestamp(int(c[5]), datetime.UTC),
                        c[0], identify_4chan_parent_id(c[4]),
                        c[2], c[3], c[4], None) for c in chunk]

            elif self.mode == "q_reddit":
                platform = self.get_meta_id("platforms", self.mode, sql_write_queue_priority)
                post_type = self.get_meta_id("types", "comment", sql_write_queue_priority)
                if self.date_range:
                    chunk = [c for c in chunk if self.in_date_range(c[4])]
                if chunk:
                    processed_data = [(platform, self.get_meta_id("boards", "r/" + c[2], sql_write_queue_priority), post_type,
                        c[0], datetime.datetime.fromtimestamp(int(c[4]), datetime.UTC),
                        None, c[1],
                        None, None, c[3], None) for c in chunk]

            elif self.mode == "reddit_submissions":
                platform = self.get_meta_id("platforms", "reddit", sql_write_queue_priority)
                post_type = self.get_meta_id("types", "submission", sql_write_queue_priority)
                chunk = [json.loads(c) for c in chunk]
                if self.date_range:
                    chunk = [c for c in chunk if self.in_date_range(c["created_utc"])]
                if chunk:
                    processed_data = [(platform, self.get_meta_id("boards", "r/" + c["subreddit"], sql_write_queue_priority), post_type,
                        c["id"], datetime.datetime.fromtimestamp(int(c["created_utc"]), datetime.UTC),
                        None, parse_reddit_parent(c),
                        c["author"], c["title"], None,
                        json.dumps({'media': c["media"], 'thumbnail': c["thumbnail"], 'url': c["url"]})) for c in chunk]

            elif self.mode == "reddit_comments":
                platform = self.get_meta_id("platforms", "reddit", sql_write_queue_priority)
                post_type = self.get_meta_id("types", "comment", sql_write_queue_priority)
                chunk = [json.loads(c) for c in chunk]
                if self.date_range:
                    chunk = [c for c in chunk if self.in_date_range(c["created_utc"])]
                if chunk:
                    processed_data = [(platform, self.get_meta_id("boards", "r/" + c["subreddit"], sql_write_queue_priority), post_type,
                        c["id"], datetime.datetime.fromtimestamp(int(c["created_utc"]), datetime.UTC),
                        c["link_id"], c["parent_id"],
                        c["author"], None, c["body"], None) for c in chunk]

            elif self.mode == "4chan":
                platform = self.get_meta_id("platforms", "4chan", sql_write_queue_priority)
                board = self.get_meta_id("boards", "/" + re.search("/([a-zA-Z0-9]+)(_[0-9]+)?.csv(.gz)?", self.input_file).group(1) + "/",
                                         sql_write_queue_priority)
                post_type = self.get_meta_id("types", "comment", sql_write_queue_priority)
                chunk = [c for c in chunk if str.startswith(c, '"')]  # fix for broken data
                chunk_processed = []
                for c in csv.reader(chunk, delimiter=',', quotechar='"', escapechar='\\'):
                    try:
                        if not self.date_range or self.in_date_range(c[4]):
                            chunk_processed.append(
                                (platform, board, post_type,
                                 c[0], datetime.datetime.fromtimestamp(int(c[4]), datetime.UTC),
                                 c[2], identify_4chan_parent_id(c[22]),
                                 c[19], c[21], c[22],
                                 json.dumps({'thumbnail': parse_trash_data(c[14])}) if parse_trash_data(c[14]) else None)
                            )
                    except Exception as e:
                        log_queue.put("WARNING invalid data found!")
                        log_queue.put(f"WARNING {e}")
                        log_queue.put(f"WARNING {c}")
                processed_data = chunk_processed

            elif self.mode == "4chan_thumbs":
                # we need following columns:
                # platform_uid, board_uid, group1, group2, filename, size, data
                with tarfile.open(self.input_file, 'r:gz') as tar:
                    try:
                        platform = self.get_meta_id("platforms", self.mode.rstrip("_thumbs"), sql_write_queue_priority)
                        board = self.get_meta_id("boards", "/" + str.split(os.path.basename(self.input_file), "_")[0] + "/", sql_write_queue_priority)
                        chunk_meta = [(platform, board, *get_path_info(c), c.size) for c in chunk]
                        chunk_data = [(platform, board, get_path_info(c)[0], tar.extractfile(c).read()) for c in chunk]
                        chunk_meta = [c for c in chunk_meta if c[2] is not None]
                        chunk_data = [c for c in chunk_data if c[2] is not None]
                    except Exception as e:
                        raise e
                    return chunk_meta, chunk_data

            else:
                raise NotImplementedError("mode not implemented: " + self.mode)

        except Exception as e:
            log_queue.put("WARNING unknown error!")
            log_queue.put(f"WARNING {e}")
        return processed_data

    def in_date_range(self, c):
        if self.date_range is None:
            return True
        elif self.date_range["start"] <= int(c) <= self.date_range["end"]:
            return True
        else:
            return False

    def get_meta_id(self, table, meta, sql_write_queue_priority):
        try:
            return self.meta_cache[table][meta]
        except Exception as e:
            meta_id = None
            while not meta_id:
                try:
                    conn = sqlite3.connect('file:' + self.db_name + '?mode=ro', uri=True, check_same_thread=False, timeout=10.0)
                    meta_id = conn.execute("SELECT `uid` FROM " + table + " WHERE `name` = '" + meta + "';").fetchone()
                    conn.close()
                    if meta_id:
                        meta_id = meta_id[0]
                        break
                    else:
                        sql_write_queue_priority.put(("INSERT OR IGNORE INTO " + table + " (`name`) VALUES ('" + meta + "');"))
                    time.sleep(0.1)
                except Exception as e:
                    '''just retry...'''
            self.cache_meta(table, meta, meta_id)
            return meta_id

    def cache_meta(self, table, board, value):
        if table not in self.meta_cache:
            self.meta_cache[table] = {}

        if board not in self.meta_cache[table]:
            self.meta_cache[table][board] = {}

        self.meta_cache[table][board] = value





