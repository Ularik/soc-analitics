from pydantic import BaseModel
from sqlalchemy import delete, insert, select, update
from sqlalchemy.exc import IntegrityError, NoResultFound

from src.exceptions.exceptions import ObjectNotFoundException, UniqueObjIsExistException


class BaseRepository:
    model = None
    schema = None

    def __init__(self, session):
        self.session = session

    def get_filtered_objects(self, *filters, **filters_by):
        new_filters = filters_by.copy()
        limit = new_filters.pop("limit", None)
        offset = new_filters.pop("offset", None)

        query = select(self.model).filter(*filters).filter_by(**new_filters)
        if limit:
            query = query.limit(limit)
        if offset:
            query = query.offset(offset)
        result = self.session.execute(query)
        return [self.schema.model_validate(obj) for obj in result.scalars()]

    def get_objects(self):
        return self.get_filtered_objects()

    def get_one_or_none(self, **filters):
        query = select(self.model).filter_by(**filters)
        result = self.session.execute(query)
        result = result.scalars().one_or_none()
        if result:
            return self.schema.model_validate(result)

    def get_one(self, **filters):
        query = select(self.model).filter_by(**filters)
        result = self.session.execute(query)
        try:
            result = result.scalar_one()
        except NoResultFound:
            raise ObjectNotFoundException

        return self.schema.model_validate(result)

    def add_obj(self, data: BaseModel):
        query = insert(self.model).values(**data.model_dump()).returning(self.model)
        try:
            result = self.session.execute(query)
        except IntegrityError as err:
            # Универсальная проверка pgcode (23505 — Unique, 23503 — FK) для psycopg2/psycopg3
            pgcode = getattr(err.orig, "pgcode", None)
            if pgcode == "23505":
                raise UniqueObjIsExistException from err
            elif pgcode == "23503":
                raise ObjectNotFoundException from err
            else:
                raise err
        return self.schema.model_validate(result.scalar_one())

    def edit(self, data: BaseModel, exclude_unset: bool = True, **filters) -> BaseModel:
        query = (
            update(self.model)
            .filter_by(**filters)
            .values(**data.model_dump(exclude_unset=exclude_unset))
            .returning(self.model)
        )

        result = self.session.execute(query)
        try:
            return self.schema.model_validate(result.scalar_one())
        except NoResultFound:
            raise ObjectNotFoundException

    def delete(self, **filters) -> None:
        query = delete(self.model).filter_by(**filters)
        self.session.execute(query)

    def check_exist_delete(self, **filters):
        query = select(self.model).filter_by(**filters)
        result = self.session.execute(query)
        result = result.scalars().all()
        if len(result) > 0:
            self.delete(**filters)
        else:
            raise ObjectNotFoundException

    def add_bulk(self, items: list[BaseModel]):
        if items:
            query = insert(self.model).values([item.model_dump() for item in items])
            self.session.execute(query)

    def edit_bulk(self, data: dict, **filters):
        query = update(self.model).filter_by(**filters).values(**data).returning(self.model)

        result = self.session.execute(query)
        return [self.schema.model_validate(obj) for obj in result.scalars()]

    def delete_bulk(self, *args, **filters):
        query = delete(self.model).filter(*args).filter_by(**filters)
        self.session.execute(query)