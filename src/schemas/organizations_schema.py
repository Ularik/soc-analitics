from pydantic import BaseModel, ConfigDict


class OrganizationCreateSchema(BaseModel):
    name_en: str
    name_ru: str


class OrganizationSchema(OrganizationCreateSchema):
    id: int

    model_config = ConfigDict(from_attributes=True)