import base64
import subprocess
import logging
from time import sleep
from functools import lru_cache
from collections import namedtuple
from xml.etree import ElementTree
from typing import Any, Literal

from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn
from fastapi import FastAPI, File, UploadFile, HTTPException, Request, Form
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
LOGGER = logging.getLogger('uvicorn.error')
