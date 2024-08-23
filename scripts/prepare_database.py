# use this script to create the database
import os
import sqlite3

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

db_name = os.path.join(ROOT_DIR, "db", "data.db")
init_script = os.path.join(ROOT_DIR, "scripts", "create_database.sql")
drop_all_data = False

## do not edit after this line!

if drop_all_data and os.path.exists(db_name):
    os.remove(db_name)

# Establish a connection and create a table
def setup_database(database_name):
    conn = sqlite3.connect(database_name)
    cur = conn.cursor()

    cur.executescript(open(init_script, 'r').read())
    conn.commit()
    cur.execute("VACUUM")  # first clean up!
    conn.close()


setup_database(db_name)
