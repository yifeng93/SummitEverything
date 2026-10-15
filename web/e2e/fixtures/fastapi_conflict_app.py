"""FastAPI test app with deterministic synthetic conflict output."""

import os

from summit_everything.api.app import create_app as create_summit_app
from summit_everything.intake.review import IntakeReviewService
from summit_everything.integrations.feishu.provider import FeishuConfig
from summit_everything.integrations.llm import FakeLLM


def create_app():
    return create_summit_app(
        session_token=os.environ.get("SUMMIT_SESSION_TOKEN"),
        feishu_config=FeishuConfig(
            redirect_uri=(
                f"http://127.0.0.1:{os.environ.get('SUMMIT_WEB_PORT', '5174')}"
                "/api/v1/integrations/feishu/callback"
            ),
            allowed_origins=(
                f"http://127.0.0.1:{os.environ.get('SUMMIT_WEB_PORT', '5174')}",
                f"http://127.0.0.1:{os.environ.get('SUMMIT_API_PORT', '8794')}",
            ),
        ),
        review_service=IntakeReviewService(FakeLLM(scenario="conflict")),
    )
