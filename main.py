from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

import routes
load_dotenv()

import actions
import database


app = FastAPI()

@app.exception_handler(HTTPException)
def handle_exception(req: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content=exc.detail, headers=exc.headers)

@app.exception_handler(RequestValidationError)
def handle_validation_error(req: Request, exc: Exception):
    return JSONResponse(status_code=400, content={
        'message': 'Required values missing',
        'code': 0
    })

app.include_router(routes.router)