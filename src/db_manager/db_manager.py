from src.repositories.organizations_repository import OrganizationsRepository
from src.repositories.reports_repository import ReportsRepository
from src.repositories.users import UsersRepository


class DbManager:
    def __init__(self, session_factory):
        self.session_factory = session_factory

    def __enter__(self):
        self.session = self.session_factory()
        self.organizations = OrganizationsRepository(self.session)
        self.reports = ReportsRepository(self.session)
        self.users = UsersRepository(self.session)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.session.rollback()
        self.session.close()

    def save(self):
        self.session.commit()