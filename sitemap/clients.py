from __future__ import annotations

import json

from google.auth.transport.requests import Request as GAuthRequest
from google.oauth2 import service_account
from googleapiclient.discovery import build

_GSC_SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]


def build_gsc_client(sa_json: str) -> object:
    info = json.loads(sa_json)
    pk = info.get("private_key", "").replace("\\n", "\n")
    if not pk.endswith("\n"):
        pk += "\n"
    info["private_key"] = pk
    creds = service_account.Credentials.from_service_account_info(info, scopes=_GSC_SCOPES)
    creds.refresh(GAuthRequest())
    return build("searchconsole", "v1", credentials=creds)
