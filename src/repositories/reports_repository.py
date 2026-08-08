from src.repositories.base import BaseRepository
from src.models.models import Reports, Organization
from src.schemas.reports_schemas import ReportCreateSchema, ReportOutSchema

class ReportsRepository(BaseRepository):
    model = Reports
    schema = ReportOutSchema

    async def create_report(self, data: ReportCreateSchema):
        
        res = await self.session.execute()