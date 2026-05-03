from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field
from tortoise import Tortoise
from tortoise.contrib.pydantic import pydantic_model_creator

from app.models import User

Tortoise.init_models(["app.models"], "models")

Schema = pydantic_model_creator(User, name="UserRead", exclude=("hashed_password",))
Create = pydantic_model_creator(User, name="UserCreateDB", exclude_readonly=True)


class UserBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    username: str
    full_name: str | None = None
    email: EmailStr | None = None
    is_active: bool = True
    scopes: list[str] = []
    phone: str | None = None
    company_name: str | None = None


class UserCreate(UserBase):
    password: str


class OwnerCreate(BaseModel):
    """Registration payload for owner self-sign-up.

    Requires phone and email; gets DEFAULT_OWNER_SCOPES automatically.
    """

    username: str
    password: str
    full_name: str
    email: EmailStr
    phone: str = Field(..., min_length=6, max_length=30)
    company_name: str | None = Field(default=None, max_length=256)


class UserPublic(UserBase):
    id: UUID


class UserUpdate(BaseModel):
    username: str | None = None
    full_name: str | None = None
    password: str | None = None
    email: EmailStr | None = None
    is_active: bool | None = None
    phone: str | None = Field(default=None, min_length=6, max_length=30)
    company_name: str | None = Field(default=None, max_length=256)


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None
    scopes: list[str] = []


class UserScopesUpdate(BaseModel):
    scopes: list[str]
