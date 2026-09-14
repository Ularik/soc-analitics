from src.db_manager.db_manager import DbManager
from src.rabbitmq.init import RabbitClient


class BaseService:

    def __init__(self, db: DbManager, rabbit_mq):
        self.db = db
        self.rmq_channel = rabbit_mq

