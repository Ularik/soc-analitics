from src.repositories.base import BaseRepository
from src.models.reports_organizations import Reports, Organization, ReportDelivery
from src.schemas.reports_schemas import ReportOutSchema, ReportCreateSchema, ReportDeliverySchema
from sqlalchemy import select, insert, Row, or_
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import IntegrityError
from src.exceptions.exceptions import OrganizationNotFoundException
import re

class ReportsRepository(BaseRepository):
    model = Reports
    schema = ReportOutSchema

    async def create_report(self, data: ReportCreateSchema) -> ReportCreateSchema:
        # 1. Очищаем origin_name от расширений и спецсимволов
        clean_name = re.sub(r'[\(\)_-]', ' ', data.origin_name).strip()

        # Извлекаем слова длиной > 2 символов (чтобы отсечь мусор)
        tokens = [token for token in clean_name.split() if len(token) > 2]

        org_id = None
        if tokens:
            # Вариант А: Ищем по первому базовому слову (например, 'President')
            # или по нескольким первым токенам через AND/OR
            conditions = [Organization.name_en.ilike(f"%{token}%") for token in tokens[:2]]

            stmt_org = select(Organization.id).where(or_(*conditions)).limit(1)
            org_id = await self.session.scalar(stmt_org)

        # 2. Если организация все еще не найдена — сразу выбрасываем исключение
        if not org_id:
            raise OrganizationNotFoundException

        report_data = data.model_dump(exclude={'origin_name'})

        try:
            stmt = (
                insert(Reports)
                .values(**report_data, organization_id=org_id)
                .returning(Reports)  # Возвращает созданный ORM-объект
            )
            result = await self.session.execute(stmt)
            return self.schema.model.validate(result.scalar_one())
        except IntegrityError as e:
            # cause = getattr(e.orig, "__cause__", e.orig)
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