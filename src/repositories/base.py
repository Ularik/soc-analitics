

class BaseRepository:
    model = None
    schema = None

    def __init__(self, session):
        self.session = session