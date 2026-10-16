"""Request bodies. Responses are plain dicts built in app.serializers."""

import re
from datetime import date
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

PHONE = re.compile(r"^(?:\+91[\s-]?)?[6-9]\d{9}$")


def _phone(v: str) -> str:
    v = re.sub(r"[\s-]", "", v.strip())
    if not PHONE.match(v):
        raise ValueError("enter a 10-digit Indian mobile number")
    return v[-10:]


class SportAnswersIn(BaseModel):
    sport: str = Field(min_length=2, max_length=40)
    answers: dict[str, str]


class AthleteIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    email: EmailStr | None = None
    city: str = Field(min_length=2, max_length=60, description="city slug, e.g. bengaluru")
    recommendations_enabled: bool = True
    sports: list[SportAnswersIn] = Field(min_length=1, max_length=14)

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("name is required")
        return v

    @model_validator(mode="after")
    def unique_sports(self):
        slugs = [s.sport for s in self.sports]
        if len(slugs) != len(set(slugs)):
            raise ValueError("each sport can be added once")
        return self


class AthletePatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    email: EmailStr | None = None
    city: str | None = None
    recommendations_enabled: bool | None = None


class SaveIn(BaseModel):
    event: str


class RegistrationIn(BaseModel):
    athlete_id: str
    event: str
    category_id: int
    full_name: str = Field(min_length=2, max_length=80)
    email: EmailStr
    phone: str
    gender: Literal["female", "male", "non-binary", "prefer-not-to-say"]
    date_of_birth: date
    tshirt_size: Literal["XS", "S", "M", "L", "XL", "XXL"] | None = None
    blood_group: Literal["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"] | None = None
    emergency_name: str = Field(min_length=2, max_length=80)
    emergency_phone: str
    team_name: str | None = Field(default=None, max_length=80)
    partner_name: str | None = Field(default=None, max_length=80)
    medical_declaration: bool

    @field_validator("phone", "emergency_phone")
    @classmethod
    def valid_phone(cls, v: str) -> str:
        return _phone(v)

    @model_validator(mode="after")
    def checks(self):
        if not self.medical_declaration:
            raise ValueError("please confirm the medical declaration")
        if self.phone == self.emergency_phone:
            raise ValueError("emergency contact must be a different number")
        return self


class ReadinessIn(BaseModel):
    event: str
    category_id: int
    inputs: dict[str, str | float | int]
    athlete_id: str | None = None
