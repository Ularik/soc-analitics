import re
from sqlalchemy import Row, insert, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from src.exceptions.exceptions import OrganizationNotFoundException
from src.models.reports_organizations import Organization, ReportDelivery, Reports
from src.repositories.base import BaseRepository
from src.schemas.reports_schemas import (
    ReportCreateSchema,
    ReportDeliverySchema,
    ReportOutSchema,
)


class ReportsRepository(BaseRepository):
    model = Reports
    schema = ReportOutSchema

    def create_report(self, data: ReportCreateSchema) -> ReportOutSchema:
        # 1. Очищаем origin_name от расширений и спецсимволов
        clean_name = re.sub(r"[\(\)_-]", " ", data.origin_name).strip()

        # Извлекаем слова длиной > 2 символов (чтобы отсечь мусор)
        tokens = [token for token in clean_name.split() if len(token) > 2]

        org_id = None
        if tokens:
            # Вариант А: Ищем по первому базовому слову или по нескольким первым токенам через OR
            conditions = [
                Organization.name_en.ilike(f"%{token}%") for token in tokens[:2]
            ]

            stmt_org = select(Organization.id).where(or_(*conditions)).limit(1)
            org_id = self.session.scalar(stmt_org)

        # 2. Если организация всё еще не найдена — сразу выбрасываем исключение
        if not org_id:
            raise OrganizationNotFoundException

        report_data = data.model_dump(exclude={"origin_name"})

        try:
            stmt = (
                insert(self.model)
                .values(**report_data, organization_id=org_id)
                .returning(self.model)  # Возвращает созданный ORM-объект
            )
            result = self.session.execute(stmt)
            return ReportOutSchema.model_validate(result.scalar_one())
        except IntegrityError as e:
            raise e

    def create_reports_delivery(self, data: ReportDeliverySchema):
        self.session.execute(insert(ReportDelivery).values(**data.model_dump()))

    def get_reports(self) -> list[ReportOutSchema]:
        result = self.session.execute(select(self.model))
        return [ReportOutSchema.model_validate(report) for report in result.scalars()]

    def get_report_with_report_delivery_or_none(
        self, report_id: int
    ) -> Row[tuple[Reports, ReportDelivery]] | None:
        result = self.session.execute(
            select(Reports, ReportDelivery)
            .options(
                joinedload(Reports.organization),
                joinedload(Reports.user)
            )
            .join(ReportDelivery, ReportDelivery.report_id == Reports.id)
            .where(Reports.id == report_id)
        )
        return result.first()