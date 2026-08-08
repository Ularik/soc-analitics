from src.repositories.organizations_repository import OrganizationsRepository
from src.repositories.reports_repository import ReportsRepository


class DbManager:
    def __init__(self, session_factory):
        self.session_factory = session_factory

    async def __aenter__(self):
        self.session = self.session_factory()
        self.organizations = OrganizationsRepository(self.session)
        self.reports = ReportsRepository(self.session)
        return self

    async def __aexit__(self, *args):
        await self.session.rollback()
        await self.session.close()

    async def save(self):
        await self.session.commit()