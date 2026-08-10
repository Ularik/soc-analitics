from src.repositories.base import BaseRepository
from src.models.models import Organization
from src.schemas.organizations_schema import OrganizationSchema, OrganizationCreateSchema

from sqlalchemy import select, insert


class OrganizationsRepository(BaseRepository):
    model = Organization
    schema = OrganizationSchema

    async def get_origins(self) -> list[OrganizationSchema]:
        res = await self.session.execute(select(self.model))
        return [self.schema.model_validate(org) for org in res.scalars()]

    async def post_origin(self, body: OrganizationCreateSchema) -> OrganizationCreateSchema:
        query = (
            insert(self.model)
                 .values(**body.model_dump())
                 .returning(self.model)
        )

        res = await self.session.execute(query)
        return res.scalar_one()