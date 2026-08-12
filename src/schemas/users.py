from pydantic import BaseModel, Field, ConfigDict


class UsersRequestSchema(BaseModel):
    email: str
    username: str
    password: str


class UserLoginSchema(BaseModel):
    username: str
    password: str


class UserAddSchema(BaseModel):
    email: str
    username: str
    hashed_password: bytes


class UserOutSchema(BaseModel):
    id: int
    email: str
    username: str

    model_config = ConfigDict(from_attributes=True)


class UserHashedPswdSchema(UserAddSchema):
    id: int

    model_config = ConfigDict(from_attributes=True)
