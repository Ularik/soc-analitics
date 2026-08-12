class NoResultException(Exception):
    detail = "Ошибка"
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class ObjectNotFoundException(NoResultException):
    detail = "Объект не найден"


class OrganizationNotFoundException(ObjectNotFoundException):
    detail = "Организация не найден"


class UniqueObjIsExistException(Exception):
    detail = 'Такой объект уже существует'