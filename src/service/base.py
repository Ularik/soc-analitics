from src.db_manager.db_manager import DbManager

class BaseService:
    def __init__(self, db: DbManager):
        self.db = db