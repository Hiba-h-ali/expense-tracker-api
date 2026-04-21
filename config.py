import os
from dataclasses import dataclass, field
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


@dataclass
class CESConfig:
    project_id: str
    app_id: str
    location: str
    credentials_file: Optional[str] = field(default=None)
    credentials_json: Optional[str] = field(default=None)

    @property
    def app_path(self) -> str:
        return (
            f"projects/{self.project_id}/locations/{self.location}"
            f"/apps/{self.app_id}"
        )

    def session_path(self, session_id: str) -> str:
        return f"{self.app_path}/sessions/{session_id}"

    @classmethod
    def from_env(cls) -> "CESConfig":
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT_ID")
        app_id = os.getenv("CES_APP_ID")
        location = os.getenv("CES_LOCATION", "us-central1")
        credentials_file = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        credentials_json = os.getenv("GOOGLE_CREDENTIALS_JSON")

        if not project_id:
            raise ValueError("GOOGLE_CLOUD_PROJECT_ID is not set")
        if not app_id:
            raise ValueError("CES_APP_ID is not set")

        return cls(
            project_id=project_id,
            app_id=app_id,
            location=location,
            credentials_file=credentials_file,
            credentials_json=credentials_json,
        )


@dataclass
class AuthConfig:
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 30
    refresh_token_days: int = 14

    @classmethod
    def from_env(cls) -> "AuthConfig":
        return cls(
            jwt_secret=os.getenv(
                "JWT_SECRET",
                "dev-insecure-change-me-at-least-32-bytes",
            ),
            jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
            access_token_minutes=int(os.getenv("ACCESS_TOKEN_MINUTES", "30")),
            refresh_token_days=int(os.getenv("REFRESH_TOKEN_DAYS", "14")),
        )
