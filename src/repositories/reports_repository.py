from src.repositories.base import BaseRepository
from src.models.models import Reports, Organization, ReportDelivery
from src.schemas.reports_schemas import ReportOutSchema, ReportCreateSchema, ReportDeliverySchema
from sqlalchemy import select, insert


class ReportsRepository(BaseRepository):
    model = Reports
    schema = ReportOutSchema

    async def create_report(self, data: ReportCreateSchema) -> ReportCreateSchema:
        org_subquery = (
            select(Organization.id)
            .where(Organization.name_en == data.origin_name)
            .scalar_subquery()
        )

        report_data = data.model_dump(exclude={'origin_name'})

        stmt = (
            insert(Reports)
            .values(**report_data, organization_id=org_subquery)
            .returning(Reports)  # Возвращает созданный ORM-объект
        )

        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def create_reports_delivery(self, data: ReportDeliverySchema):
        await self.session.execute(insert(ReportDelivery).values(**data.model_dump()))

    async def get_reports(self) -> list[ReportOutSchema]:
        result = await self.session.execute(select(self.model))
        return [ReportOutSchema.model_validate(report) for report in result.scalars()]