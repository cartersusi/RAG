import sqlite3
import time
from sqlite_vec import serialize_float32, load as load_vec
from queue import Queue
from threading import Lock

from server import LOGGER
from pdf import Book
from fnutil import clean_string

class SQLiteConnectionPool:
    def __init__(self, database, max_connections=10):
        self.database = database
        self.max_connections = max_connections
        self.connections = Queue(maxsize=max_connections)
        self.lock = Lock()

    def get_connection(self):
        if self.connections.empty():
            conn = sqlite3.connect(self.database)
            conn.enable_load_extension(True)
            load_vec(conn)
            conn.enable_load_extension(False)
            return conn
        else:
            return self.connections.get()

    def return_connection(self, connection):
        if self.connections.qsize() < self.max_connections:
            self.connections.put(connection)
        else:
            connection.close()

    def execute_query(self, query, params=None):
        connection = self.get_connection()
        try:
            with connection:
                cursor = connection.cursor()
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                return cursor.fetchall()
        finally:
            self.return_connection(connection)

def open_db(dbpath):
    pool = SQLiteConnectionPool(dbpath, max_connections=10)
    return pool

def init_db(db):
    db.execute_query("CREATE TABLE IF NOT EXISTS book (title TEXT NOT NULL, author TEXT NOT NULL, publication_year INTEGER, upload_date TEXT);")
    db.execute_query("CREATE VIRTUAL TABLE embeddings USING vec0(embedding float[1536])")
    db.execute_query("CREATE TABLE IF NOT EXISTS pages (content TEXT);")

def insert_book(db, b: Book):
    try:
        upload_date = time.strftime("%Y-%m-%d %H:%M:%S")
        db.execute_query("""
            INSERT INTO book (title, author, publication_year, upload_date)
            VALUES (?, ?, ?, ?);
        """, (b.Title, b.Author, b.PubYear, upload_date))

        pages = b.Pages
        LOGGER.debug(f"Inserting {len(pages)} pages")

        for p in pages:
            db.execute_query("""
                INSERT INTO pages(rowid, content)
                VALUES (?, ?);
            """, (p.PageNum, p.Content))

            db.execute_query("""
                INSERT INTO embeddings(rowid, embedding)
                VALUES (?, ?);
            """, (p.PageNum, serialize_float32(p.Embedding)))

        return True
    except Exception as e:
        LOGGER.error(f"An error occurred: {e}")
        return False

def query_book(db, qe, k=5):
    start = time.time()
    try:
        results = db.execute_query("""
                SELECT
                    e.rowid AS page_num,
                    p.content,
                    distance
                FROM embeddings e
                JOIN pages p ON e.rowid = p.rowid
                WHERE e.embedding MATCH ?
                AND k = ?
                ORDER BY distance ASC
            """, (serialize_float32(qe), k))

        LOGGER.info(f"Query took {(time.time() - start) * 1000} ms")
        ret = {}
        for result in results:
            #ret[result[0]] = result[1] # maybe remove clean_string if text is to be displayed on frontend
            ret[result[0]] = clean_string(result[1])

        return ret
    except Exception as e:
        LOGGER.error(f"An error occurred: {e}")
        ret = {
            "error": "Not able to query book"
        }
        return ret
        
