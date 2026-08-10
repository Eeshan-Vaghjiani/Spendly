"""Marshmallow request validation."""

from __future__ import annotations

from marshmallow import Schema, ValidationError, fields, validate, validates_schema


def validate_strong_password(value: str) -> None:
    """Keep the client and API password rules aligned."""
    missing: list[str] = []
    if not any(character.isupper() for character in value):
        missing.append("an uppercase letter")
    if not any(character.islower() for character in value):
        missing.append("a lowercase letter")
    if not any(character.isdigit() for character in value):
        missing.append("a number")
    if not any(not character.isalnum() and not character.isspace() for character in value):
        missing.append("a symbol")
    if any(character.isspace() for character in value):
        missing.append("no spaces")
    if missing:
        raise ValidationError("Password must include " + ", ".join(missing) + ".")


class RegisterSchema(Schema):
    email = fields.Email(required=True, validate=validate.Length(max=255))
    password = fields.String(
        required=True,
        load_only=True,
        validate=[validate.Length(min=10, max=128), validate_strong_password],
    )
    display_name = fields.String(
        required=True, validate=validate.Length(min=1, max=100)
    )
    accepted_terms = fields.Boolean(
        required=True, validate=validate.Equal(True)
    )
    accepted_privacy = fields.Boolean(
        required=True, validate=validate.Equal(True)
    )
    model_training_opt_in = fields.Boolean(load_default=False)


class ConsentSchema(Schema):
    accepted_terms = fields.Boolean(
        required=True, validate=validate.Equal(True)
    )
    accepted_privacy = fields.Boolean(
        required=True, validate=validate.Equal(True)
    )
    model_training_opt_in = fields.Boolean(load_default=False)


class LoginSchema(Schema):
    email = fields.Email(required=True)
    password = fields.String(required=True, load_only=True)


class GoogleLoginSchema(Schema):
    id_token = fields.String(
        required=True,
        load_only=True,
        validate=validate.Length(min=20, max=8192),
    )


class TransactionSchema(Schema):
    transaction_timestamp = fields.DateTime(required=True)
    amount = fields.Float(
        required=True, validate=validate.Range(min=0, min_inclusive=False)
    )
    category = fields.String(
        required=True, validate=validate.Length(min=1, max=80)
    )
    transaction_type = fields.String(
        required=True, validate=validate.OneOf(["expense", "income"])
    )
    merchant = fields.String(
        load_default=None, allow_none=True, validate=validate.Length(max=120)
    )
    is_recurring = fields.Boolean(load_default=False)


class BudgetSchema(Schema):
    period_start = fields.Date(required=True)
    period_end = fields.Date(required=True)
    category = fields.String(
        required=True, validate=validate.Length(min=1, max=80)
    )
    amount = fields.Float(
        required=True, validate=validate.Range(min=0, min_inclusive=False)
    )

    @validates_schema
    def validate_dates(self, data: dict[str, object], **kwargs: object) -> None:
        del kwargs
        if data["period_end"] < data["period_start"]:
            raise ValidationError(
                {"period_end": ["period_end must be on or after period_start."]}
            )
