from src.repositories.base import BaseRepository
from src.models.reports_organizations import Reports, Organization, ReportDelivery
from src.schemas.reports_schemas import ReportOutSchema, ReportCreateSchema, ReportDeliverySchema
from sqlalchemy import select, insert, Row
from sqlalchemy.orm import joinedload
from asyncpg.exceptions import NotNullViolationError
from sqlalchemy.exc import IntegrityError
from src.exceptions.exceptions import OrganizationNotFoundException

class ReportsRepository(BaseRepository):
    model = Reports
    schema = ReportOutSchema

    async def create_report(self, data: ReportCreateSchema) -> ReportCreateSchema:
        org_subquery = (
            select(Organization.id)
            .where(Organization.name_en.ilike(f"%{data.origin_name}%"))
            .scalar_subquery()
        )

        report_data = data.model_dump(exclude={'origin_name'})

        try:
            stmt = (
                insert(Reports)
                .values(**report_data, organization_id=org_subquery)
                .returning(Reports)  # Возвращает созданный ORM-объект
            )
            result = await self.session.execute(stmt)
            return result.scalar_one()
        except IntegrityError as e:
            cause = getattr(e.orig, "__cause__", e.orig)

            # Проверяем тип ошибки и имя упавшей колонки
            if isinstance(cause, NotNullViolationError):
                raise OrganizationNotFoundException
            else:
                raise e

    async def create_reports_delivery(self, data: ReportDeliverySchema):
        await self.session.execute(insert(ReportDelivery).values(**data.model_dump()))

    async def get_reports(self) -> list[ReportOutSchema]:
        result = await self.session.execute(select(self.model))
        return [ReportOutSchema.model_validate(report) for report in result.scalars()]

    async def get_report_with_report_delivery_or_none(self, report_id: int) -> Row[tuple[Reports, ReportDelivery]] | None:
        result = await self.session.execute(
            select(Reports, ReportDelivery)
            .options(
                joinedload(Reports.organization),
                joinedload(Reports.user)
            )
            .join(ReportDelivery, ReportDelivery.report_id == Reports.id)
            .where(Reports.id == report_id)
        )
        return result.first()