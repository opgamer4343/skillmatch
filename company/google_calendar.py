from __future__ import annotations

import os
if os.getenv("DEBUG", "True").lower() == "true":
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

import uuid
from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


def _get_scopes():
    scopes = getattr(settings, "GOOGLE_CALENDAR_SCOPES", None) or [
        "https://www.googleapis.com/auth/calendar.events",
        "https://www.googleapis.com/auth/userinfo.email",
    ]
    return scopes


def company_google_credentials(company_profile):
    creds = Credentials(
        token=company_profile.google_access_token or None,
        refresh_token=company_profile.google_refresh_token or None,
        token_uri=company_profile.google_token_uri or "https://oauth2.googleapis.com/token",
        client_id=getattr(settings, "GOOGLE_OAUTH_CLIENT_ID", ""),
        client_secret=getattr(settings, "GOOGLE_OAUTH_CLIENT_SECRET", ""),
        scopes=_get_scopes(),
    )
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        company_profile.google_access_token = creds.token
        company_profile.google_scopes = " ".join(creds.scopes or _get_scopes())
        company_profile.save(update_fields=["google_access_token", "google_scopes", "updated_at"])
    return creds


def get_calendar_service(company_profile):
    return build("calendar", "v3", credentials=company_google_credentials(company_profile))


def _event_body(interview):
    start_dt = timezone.localtime(interview.interview_date) if timezone.is_aware(interview.interview_date) else interview.interview_date
    end_dt = start_dt + timedelta(minutes=45)
    internship = interview.application.internship
    student = interview.application.applicant
    company_name = getattr(interview.scheduled_by.company_profile, "company_name", interview.scheduled_by.get_full_name() or interview.scheduled_by.email)
    body = {
        "summary": f"Interview - {internship.title}",
        "description": f"Interview for {internship.title}\nCandidate: {student.get_full_name() or student.email}\nCompany: {company_name}\n\nNotes: {interview.notes or '-'}",
        "start": {"dateTime": start_dt.isoformat(), "timeZone": getattr(settings, "TIME_ZONE", "Asia/Kolkata")},
        "end": {"dateTime": end_dt.isoformat(), "timeZone": getattr(settings, "TIME_ZONE", "Asia/Kolkata")},
        "attendees": [{"email": student.email}],
        "conferenceData": {
            "createRequest": {
                "requestId": str(uuid.uuid4()),
                "conferenceSolutionKey": {"type": "hangoutsMeet"},
            }
        },
    }
    return body


def create_google_meet_event(interview):
    company_profile = interview.scheduled_by.company_profile
    service = get_calendar_service(company_profile)
    event = service.events().insert(
        calendarId="primary",
        body=_event_body(interview),
        conferenceDataVersion=1,
        sendUpdates="all",
    ).execute()
    meet_link = event.get("hangoutLink") or ""
    if not meet_link:
        for entry in event.get("conferenceData", {}).get("entryPoints", []):
            if entry.get("entryPointType") == "video":
                meet_link = entry.get("uri") or ""
                break
    return event.get("id"), meet_link


def update_google_meet_event(interview):
    company_profile = interview.scheduled_by.company_profile
    service = get_calendar_service(company_profile)
    event = service.events().get(calendarId="primary", eventId=interview.google_event_id).execute()
    body = _event_body(interview)
    for key, value in body.items():
        event[key] = value
    updated = service.events().update(
        calendarId="primary",
        eventId=interview.google_event_id,
        body=event,
        conferenceDataVersion=1,
        sendUpdates="all",
    ).execute()
    meet_link = updated.get("hangoutLink") or ""
    if not meet_link:
        for entry in updated.get("conferenceData", {}).get("entryPoints", []):
            if entry.get("entryPointType") == "video":
                meet_link = entry.get("uri") or ""
                break
    return updated.get("id"), meet_link


def delete_google_event(interview):
    company_profile = interview.scheduled_by.company_profile
    service = get_calendar_service(company_profile)
    return service.events().delete(calendarId="primary", eventId=interview.google_event_id, sendUpdates="all").execute()
