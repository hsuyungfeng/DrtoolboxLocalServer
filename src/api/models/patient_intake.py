"""
Pydantic validation models for patient intake forms and related operations.

Implements D-01 (form fields) and D-02 (validation logic) from phase 3 requirements.
Supports:
  - PatientIntakeRequest: main intake form submission
  - PatientDemographics: dashboard view of patient info
  - AppointmentRequest: appointment booking/editing
  - LineUserMapping: LINE user to patient mapping
"""

from pydantic import BaseModel, Field, field_validator, EmailStr
from datetime import date
from typing import Optional
import re


class PatientIntakeRequest(BaseModel):
    """
    Main patient intake form model.

    Lean form per D-01: name, phone, email, dob, chief_complaint,
    medications, allergies, appointment_type.
    """

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Patient full name"
    )
    phone: str = Field(
        ...,
        description="Phone number in Taiwan format (09XX-XXX-XXX or 09XXXXXXXX)"
    )
    email: EmailStr = Field(
        ...,
        description="Patient email address"
    )
    dob: date = Field(
        ...,
        description="Date of birth (must be in the past)"
    )
    chief_complaint: str = Field(
        ...,
        max_length=500,
        description="Chief complaint or reason for visit"
    )
    medications: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Current medications (optional)"
    )
    allergies: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Known allergies (optional)"
    )
    appointment_date: date = Field(
        ...,
        description="Requested appointment date (must be today or later)"
    )
    appointment_type: str = Field(
        ...,
        description="Type of appointment (e.g., 'initial', 'follow-up', 'consultation')"
    )

    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        """
        Validate Taiwan phone format.
        Accepts: 09XX-XXX-XXX, 09XXXXXXXX, 09XX-XXXX-XXX
        """
        # Remove all dashes for validation
        clean_phone = v.replace('-', '')

        # Must start with 09 and have exactly 10 digits
        if not re.match(r'^09\d{8}$', clean_phone):
            raise ValueError(
                'Phone must be in Taiwan format (e.g., 0912-345-678 or 09123456789)'
            )

        return v

    @field_validator('dob')
    @classmethod
    def validate_dob(cls, v: date) -> date:
        """Validate that DOB is in the past (not today or future)."""
        if v >= date.today():
            raise ValueError('Date of birth must be in the past')
        return v

    @field_validator('appointment_date')
    @classmethod
    def validate_appointment_date(cls, v: date) -> date:
        """Validate that appointment date is today or in the future."""
        if v < date.today():
            raise ValueError('Appointment date must be today or in the future')
        return v

    @field_validator('chief_complaint')
    @classmethod
    def validate_chief_complaint(cls, v: str) -> str:
        """Validate chief complaint is not empty and within length limits."""
        if not v or not v.strip():
            raise ValueError('Chief complaint cannot be empty')
        return v.strip()

    class Config:
        json_schema_extra = {
            "example": {
                "name": "王小明",
                "phone": "0912-345-678",
                "email": "wang@example.com",
                "dob": "1990-01-15",
                "chief_complaint": "頭痛和疲勞",
                "medications": "阿斯匹靈",
                "allergies": "青黴素",
                "appointment_date": "2026-05-20",
                "appointment_type": "initial"
            }
        }


class PatientDemographics(BaseModel):
    """
    Patient demographics subset for dashboard display.

    Minimal patient information for viewing in the dashboard.
    """

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Patient full name"
    )
    phone: str = Field(
        ...,
        description="Patient phone number"
    )
    email: str = Field(
        ...,
        description="Patient email address"
    )
    dob: date = Field(
        ...,
        description="Patient date of birth"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "name": "王小明",
                "phone": "0912-345-678",
                "email": "wang@example.com",
                "dob": "1990-01-15"
            }
        }


class AppointmentRequest(BaseModel):
    """
    Appointment booking or editing request.

    Used for scheduling or rescheduling appointments.
    """

    appointment_date: date = Field(
        ...,
        description="Requested appointment date"
    )
    appointment_type: str = Field(
        ...,
        description="Type of appointment (e.g., 'initial', 'follow-up', 'consultation')"
    )
    notes: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Additional notes for appointment"
    )

    @field_validator('appointment_date')
    @classmethod
    def validate_appointment_date(cls, v: date) -> date:
        """Validate that appointment date is today or in the future."""
        if v < date.today():
            raise ValueError('Appointment date must be today or in the future')
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "appointment_date": "2026-05-20",
                "appointment_type": "follow-up",
                "notes": "跟進頭痛症狀"
            }
        }


class LineUserMapping(BaseModel):
    """
    Maps a LINE user ID to a patient record.

    Used for linking LINE users to patient database entries.
    """

    line_user_id: str = Field(
        ...,
        min_length=1,
        description="LINE user ID from LINE messaging API"
    )
    patient_id: int = Field(
        ...,
        gt=0,
        description="Patient ID in the patient database"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "line_user_id": "U1234567890abcdef1234567890abcdef",
                "patient_id": 12345
            }
        }
