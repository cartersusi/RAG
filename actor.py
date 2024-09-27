import logging
import os

from pydantic import BaseModel
from fastapi.responses import JSONResponse
import uvicorn
from fastapi import FastAPI, Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from openai import OpenAI

from db_manage import open_db, init_db, insert_book, query_book
from pdf import Book, handle_book
from openapi import query_embedding

oakey = os.getenv('OPEN_AI_KEY')
openai_client = OpenAI(api_key=oakey)
limiter = Limiter(key_func=get_remote_address)
app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
LOGGER = logging.getLogger('-')

### ----------------------------
BOOKS = [
    'David Cherney/Linear Algebra/book.pdf',
    'KN King/C Programming - A Modern Approach - 2nd_Ed(C89, c99)/book.pdf',
    'Katherine Cox-Buday/Concurrency in Go/book.pdf',
]

books = [
    Book("David Cherney","Linear Algebra", 0, BOOKS[0]),
    Book("KN King","C Programming", 0, BOOKS[1]),
    Book("Katherine Cox-Buday","Concurrency in Go", 0, BOOKS[2]),
]

actor_reqbook = books[2]

dbpool = open_db(f"{actor_reqbook.Title}.db")
#init_db(dbpool)
### ----------------------------

@app.get("/api/upload-book/")
@limiter.limit("1/60seconds")
async def up(request: Request):
    LOGGER.info("Uploading book")
    try:
        handle_book(actor_reqbook, openai_client)
    except Exception as e:
        LOGGER.error(f"Failed to upload book: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)
    
    try:
        book_id = insert_book(dbpool, actor_reqbook)
    except Exception as e:
        LOGGER.error(f"Failed to insert book: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

    return JSONResponse(content={"book_id": book_id}, status_code=200)

class BookQuery(BaseModel):
    book_id: int
    query: str

@app.post("/api/query-book/")
@limiter.limit("1/2seconds")
async def qb(request: Request, book_query: BookQuery):
    LOGGER.info("Querying book")

    book_id = book_query.book_id
    if not book_id:
        return JSONResponse(content={"error": "Book ID parameter is required"}, status_code=400)

    query = book_query.query
    if not query:
        return JSONResponse(content={"error": "Query parameter is required"}, status_code=400)
    
    embedding = query_embedding(query, openai_client)
    if not embedding:
        return JSONResponse(content={"error": "Failed to query embedding"}, status_code=500)
    
    pages = query_book(dbpool,embedding)
    if not pages:
        return JSONResponse(content={"error": "Failed to query book"}, status_code=500)

    return JSONResponse(content={"pages": pages}, status_code=200)

if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=50051)