from google.auth import default as auth_default
from google.oauth2 import service_account
from google.cloud.ces_v1 import (
    AgentServiceClient,
    RunSessionRequest,
    RunSessionResponse,
    SessionConfig,
    SessionInput,
    SessionServiceClient,
)
import json
import uuid
from typing import Optional
from config import CESConfig

class CESClient:
    """Wrapper around the CES (Conversational Agents) Session API."""

    def __init__(self, config: CESConfig):
        self.config = config

        credentials = self._load_credentials(
            config.credentials_file, config.credentials_json
        )

        api_endpoint = f"https://ces.googleapis.com"

        self._sessions_client = SessionServiceClient(
            credentials=credentials,
            transport="rest",
            client_options={"api_endpoint": api_endpoint},
        )
        self._agent_client = AgentServiceClient(
            credentials=credentials,
            transport="rest",
            client_options={"api_endpoint": api_endpoint},
        )

    @staticmethod
    def _load_credentials(
        credentials_file: Optional[str], credentials_json: Optional[str]
    ):
        if credentials_json:
            info = json.loads(credentials_json)
            return service_account.Credentials.from_service_account_info(info)
        if credentials_file:
            return service_account.Credentials.from_service_account_file(
                credentials_file
            )
        credentials, _ = auth_default()
        return credentials

    def run_session_text(
        self,
        text: str,
        session_id: Optional[str] = None,
    ) -> RunSessionResponse:
        """Send a text message to the agent and return the full response."""
        session_id = session_id or str(uuid.uuid4())
        session_path = self.config.session_path(session_id)

        request = RunSessionRequest(
            config=SessionConfig(session=session_path),
            inputs=[SessionInput(text=text)],
        )

        return self._sessions_client.run_session(request=request)

    def get_app_info(self) -> dict:
        """Retrieve basic info about the connected app."""
        app = self._agent_client.get_app(name=self.config.app_path)
        return {
            "display_name": app.display_name,
            "description": getattr(app, "description", ""),
        }

    @staticmethod
    def extract_response_text(response: RunSessionResponse) -> list[str]:
        """Pull plain-text messages from a RunSessionResponse."""
        messages: list[str] = []
        for output in response.outputs:
            if output.text:
                messages.append(output.text)
        return messages
