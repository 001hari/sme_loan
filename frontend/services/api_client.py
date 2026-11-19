import os
import requests

API_BASE_URL = os.getenv(
    "FRONTEND_API_BASE_URL",
    "http://127.0.0.1:8000/api/v1",
)


class APIError(Exception):
    pass


def submit_application(payload: dict):
    try:
        response = requests.post(
            f"{API_BASE_URL}/applications", json=payload, timeout=15
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        detail = getattr(getattr(exc, "response", None), "text", str(exc))
        raise APIError(f"Could not submit application: {detail}") from exc


def fetch_applications():
    try:
        response = requests.get(f"{API_BASE_URL}/applications", timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        detail = getattr(getattr(exc, "response", None), "text", str(exc))
        raise APIError(f"Could not fetch applications: {detail}") from exc


def predict_application(application_id: str):
    try:
        response = requests.post(
            f"{API_BASE_URL}/applications/{application_id}/predict", timeout=30
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        detail = getattr(getattr(exc, "response", None), "text", str(exc))
        raise APIError(f"Could not generate prediction: {detail}") from exc
