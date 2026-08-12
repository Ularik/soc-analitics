from fastapi import Request, HTTPException
from src.exceptions import exceptions


def register_exception_handlers(app):

    @app.exception_handler(exceptions.OrganizationNotFoundException)
    async def bad_room_handler(request: Request, exc: exceptions.OrganizationNotFoundException):
        raise HTTPException(status_code=400, detail=exc.detail)


    @app.exception_handler(exceptions.NoResultException)
    async def not_found_handler(request: Request, exc: exceptions.NoResultException):
        raise HTTPException(status_code=404, detail=exc.detail)
