from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from api.contract_models import (
    CaseConflictError,
    ForbiddenError,
    InvalidRequestError,
    MessageIdReusedError,
    NotFoundError,
    UnauthorizedError,
)


class ApiError(Exception):
    def __init__(self, status_code: int, body: BaseModel) -> None:
        super().__init__(status_code)
        self.status_code = status_code
        self.body = body


def unauthorized() -> ApiError:
    return ApiError(status.HTTP_401_UNAUTHORIZED, UnauthorizedError(error="unauthorized"))


def forbidden() -> ApiError:
    return ApiError(status.HTTP_403_FORBIDDEN, ForbiddenError(error="forbidden"))


def not_found() -> ApiError:
    return ApiError(status.HTTP_404_NOT_FOUND, NotFoundError(error="not_found"))


def message_id_reused() -> ApiError:
    return ApiError(status.HTTP_409_CONFLICT, MessageIdReusedError(error="message_id_reused"))


def case_already_open() -> ApiError:
    return ApiError(status.HTTP_409_CONFLICT, CaseConflictError(error="case_already_open"))


def case_ended() -> ApiError:
    return ApiError(status.HTTP_409_CONFLICT, CaseConflictError(error="case_ended"))


def case_not_appealable() -> ApiError:
    return ApiError(status.HTTP_409_CONFLICT, CaseConflictError(error="case_not_appealable"))


def invalid_body() -> ApiError:
    return ApiError(status.HTTP_422_UNPROCESSABLE_CONTENT, InvalidRequestError(error="invalid_body"))


async def _api_error(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, ApiError)
    return JSONResponse(status_code=exc.status_code, content=exc.body.model_dump())


async def _validation_error(_: Request, __: Exception) -> JSONResponse:
    error = invalid_body()
    return JSONResponse(status_code=error.status_code, content=error.body.model_dump())


def install_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ApiError, _api_error)
    app.add_exception_handler(RequestValidationError, _validation_error)
