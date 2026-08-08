from src.repositories.base import BaseRepository
from src.models.models import Organization
from src.schemas.organizations_schema import OrganizationSchema

from sqlalchemy import select


class OrganizationsRepository(BaseRepository):
    model = Organization
    schema = OrganizationSchema

    async def get_origins(self) -> list[OrganizationSchema]:
        res = await self.session.execute(select(self.model))
        return [self.schema.model_validate(org) for org in res.scalars()]