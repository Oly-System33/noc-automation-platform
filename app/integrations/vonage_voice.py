import os
import time
import uuid

import jwt
import requests
from dotenv import load_dotenv


class VonageVoiceClient:

    def __init__(self):
        load_dotenv()

        self.application_id = os.getenv("VONAGE_APPLICATION_ID")
        self.private_key_path = os.getenv("VONAGE_PRIVATE_KEY_PATH")
        self.from_number = os.getenv("VONAGE_FROM_NUMBER")
        self.public_base_url = os.getenv("PUBLIC_BASE_URL")
        self.api_base_url = os.getenv(
            "VONAGE_API_BASE_URL",
            "https://api.nexmo.com/v1/calls"
        )

        self._validate_config()

    def _validate_config(self):
        missing = [
            name
            for name, value in {
                "VONAGE_APPLICATION_ID": self.application_id,
                "VONAGE_PRIVATE_KEY_PATH": self.private_key_path,
                "VONAGE_FROM_NUMBER": self.from_number,
                "PUBLIC_BASE_URL": self.public_base_url,
            }.items()
            if not value
        ]

        if missing:
            raise ValueError(
                "Missing Vonage environment variables: "
                + ", ".join(missing)
            )

        if not os.path.exists(self.private_key_path):
            raise ValueError("Vonage private key file was not found")

    def create_call(self, phone, event_id):
        base_url = self.public_base_url.rstrip("/")
        payload = {
            "to": [
                {
                    "type": "phone",
                    "number": self._normalize_vonage_number(phone),
                }
            ],
            "from": {
                "type": "phone",
                "number": self._normalize_vonage_number(self.from_number),
            },
            "answer_url": [
                f"{base_url}/vonage/answer?event_id={event_id}"
            ],
            "event_url": [
                f"{base_url}/vonage/event?event_id={event_id}"
            ],
        }

        response = requests.post(
            self.api_base_url,
            json=payload,
            headers={
                "Authorization": f"Bearer {self._build_jwt()}",
                "Content-Type": "application/json",
            },
            timeout=10
        )

        try:
            raw_response = response.json()
        except ValueError:
            raw_response = {"response_text": response.text}

        if response.status_code >= 400:
            raise RuntimeError(
                "Vonage call creation failed "
                f"with status {response.status_code}: {raw_response}"
            )

        return {
            "uuid": raw_response.get("uuid"),
            "status": raw_response.get("status"),
            "raw": raw_response,
        }

    def _build_jwt(self):
        now = int(time.time())

        with open(self.private_key_path, "rb") as private_key_file:
            private_key = private_key_file.read()

        return jwt.encode(
            {
                "application_id": self.application_id,
                "iat": now,
                "exp": now + 3600,
                "jti": str(uuid.uuid4()),
            },
            private_key,
            algorithm="RS256"
        )

    def _normalize_vonage_number(self, phone):
        phone = str(phone).strip()

        if phone.endswith(".0"):
            phone = phone[:-2]

        return (
            phone.replace("+", "")
            .replace(" ", "")
            .replace("-", "")
        )
