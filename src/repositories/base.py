from pydantic import BaseModel
from src.exceptions.exceptions import ObjectNotFoundException, UniqueObjIsExistException
from asyncpg.exceptions import UniqueViolationError, ForeignKeyViolationError
from sqlalchemy import select, insert, update, delete
from sqlalchemy.exc import NoResultFound, IntegrityError

class BaseRepository:
    model = None
    schema = None

    def __init__(self, session):
        self.session = session

    async def get_filtered_objects(self, *filters, **filters_by):
        new_filters = filters_by.copy()
        limit = new_filters.pop("limit", None)
        offset = new_filters.pop("offset", None)

        query = select(self.model).filter(*filters).filter_by(**new_filters)
        if limit:
            query = query.limit(limit)
        if offset:
            query = query.offset(offset)
        result = await self.session.execute(query)
        return [self.schema.model_validate(obj) for obj in result.scalars()]

    async def get_objects(self):
        return await self.get_filtered_objects()

    async def get_one_or_none(self, **filters):
        query = select(self.model).filter_by(**filters)
        result = await self.session.execute(query)
        result = result.scalars().one_or_none()
        if result:
            return self.schema.model_validate(result)

    async def get_one(self, **filters):
        query = select(self.model).filter_by(**filters)
        result = await self.session.execute(query)
        try:
            result = result.scalar_one()
        except NoResultFound:
            raise ObjectNotFoundException

        return self.schema.model_validate(result)

    async def add_obj(self, data: BaseModel):
        query = insert(self.model).values(**data.model_dump()).returning(self.model)
        try:
            result = await self.session.execute(query)
        except IntegrityError as err:
            if isinstance(err.orig.__cause__, UniqueViolationError):
                raise UniqueObjIsExistException from err
            if isinstance(err.orig.__cause__, ForeignKeyViolationError):
                raise ObjectNotFoundException from err
            else:
                raise err
        return self.schema.model_validate(result.scalar_one())

    async def edit(self, data: BaseModel, exclude_unset: bool = True, **filters) -> BaseModel:

        query = (
            update(self.model)
            .filter_by(**filters)
            .values(**data.model_dump(exclude_unset=exclude_unset))
            .returning(self.model)
        )

        result = await self.session.execute(query)
        try:
            return self.mapper.map_to_domain_entity(result.scalar_one())
        except NoResultFound:
            raise ObjectNotFoundException

    async def delete(self, **filters) -> None:
        query = delete(self.model).filter_by(**filters)
        # print(query.compile(compile_kwargs={"literal_binds": True}))
        await self.session.execute(query)

    async def check_exist_delete(self, **filters):
        query = select(self.model).filter_by(**filters)
        result = await self.session.execute(query)
        result = result.scalars().all()
        if len(result):
            return self.delete(**filters)
        else:
            raise ObjectNotFoundException

    async def add_bulk(self, items: list[BaseModel]):
        if items:
            query = insert(self.model).values([item.model_dump() for item in items])
            await self.session.execute(query)

    async def edit_bulk(self, data: BaseModel, **filters):
        query = update(self.model).filter_by(**filters).values(**data).returning(self.model)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def delete_bulk(self, *args, **filters):
        query = delete(self.model).filter(*args).filter_by(**filters)
        print(query.compile(compile_kwargs={"literal_binds": True}))
        await self.session.execute(query)
