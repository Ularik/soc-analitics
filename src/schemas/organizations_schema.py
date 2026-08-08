from pydantic import BaseModel, Field, ConfigDict


class OrganizationSchema(BaseModel):
    id: int
    name_en: str
    name_ru: str

    model_config = ConfigDict(from_attributes=True)