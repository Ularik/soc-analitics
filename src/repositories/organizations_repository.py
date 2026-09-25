from src.repositories.base import BaseRepository
from src.models.reports_organizations import Organization
from src.schemas.organizations_schema import OrganizationSchema, OrganizationCreateSchema

from sqlalchemy import select, insert


class OrganizationsRepository(BaseRepository):
    model = Organization
    schema = OrganizationSchema

    def get_origins(self) -> list[OrganizationSchema]:
        res = self.session.execute(select(self.model))
        return [self.schema.model_validate(org) for org in res.scalars()]

    def post_origin(self, body: OrganizationCreateSchema) -> OrganizationCreateSchema:
        query = (
            insert(self.model)
                 .values(**body.model_dump())
                 .returning(self.model)
        )

        res = self.session.execute(query)
        return res.scalar_one()