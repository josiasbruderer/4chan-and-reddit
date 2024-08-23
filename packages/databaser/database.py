import os
import sqlite3
import time


def setup_database(db_name, init_script, drop_all_data=False):
    time.sleep(0.1)
    if drop_all_data and os.path.exists(db_name):
        print("!! DATABASE WILL BE CLEARED IN 3 SECONDS !!")
        time.sleep(3)
        os.remove(db_name)

    if not os.path.exists(os.path.dirname(db_name)):
        os.makedirs(os.path.dirname(db_name), exist_ok=True)

    conn = sqlite3.connect(db_name, check_same_thread=False)
    cur = conn.cursor()

    cur.executescript(open(init_script, 'r').read())
    conn.commit()
    cur.execute("VACUUM")  # first clean up!
    conn.close()


def connect_database_ro(db_name):
    return sqlite3.connect('file:' + db_name + '?mode=ro', uri=True, check_same_thread=False, timeout=10.0)


def connect_database_rw(db_name):
    return sqlite3.connect(db_name, check_same_thread=False, timeout=10.0)


def connect_database(db_name):
    return connect_database_ro()


def queue_processor(db_name, sql_queue, sql_write_queue_priority, log):
    conn = sqlite3.connect(db_name, check_same_thread=False)
    cur = conn.cursor()
    while True:
        task = None
        if not sql_write_queue_priority.empty():
            task = sql_write_queue_priority.get()
            log.debug("priority writing to sql database! " + str(sql_write_queue_priority.qsize()) + " queued")
        elif not sql_queue.empty():
            task = sql_queue.get()
            log.debug("writing to sql database! " + str(sql_queue.qsize()) + " queued")
            if task == "STOP":
                conn.close()
                break
        else:
            time.sleep(0.1)
        if task:
            try:
                if type(task) is str:
                    cur.execute(task)
                else:
                    cur.executemany(task[0], task[1])
                conn.commit()
            except Exception as e:
                log.warning("retry because of: " + str(e))
                time.sleep(0.2)
                try:
                    if type(task) is str:
                        cur.execute(task)
                    else:
                        cur.executemany(task[0], task[1])
                    conn.commit()
                    log.debug("SQL WRITE!")
                except Exception as e:
                    log.critical(str(e))
