"""
Central configuration, loaded from environment variables (.env).
Every other module imports from here — no module reads os.environ directly.
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # --- Groq / LLM ---
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "groq/openai/gpt-oss-120b")

    # --- Ubuntu Action Agent (autonomous -- decides and executes on the
    #     target machine itself; see app/tools/handoff_tool.py) ---
    UBUNTU_AGENT_URL: str = os.getenv("UBUNTU_AGENT_URL", "http://192.168.111.139:9100")
    UBUNTU_AGENT_API_KEY: str = os.getenv("UBUNTU_AGENT_API_KEY", "")

    # --- Neo4j ---
    NEO4J_URI: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER: str = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD: str = os.getenv("NEO4J_PASSWORD", "")

    # --- Handoff safety ---
    # Below this risk score, the incident is never even handed off to the
    # Ubuntu Action Agent. Ubuntu's own DRY_RUN (separate, in its own
    # agent.env) is what gates whether IT actually executes.
    ACTION_RISK_THRESHOLD: float = float(os.getenv("ACTION_RISK_THRESHOLD", "7"))

    # --- Webhook server ---
    WEBHOOK_HOST: str = os.getenv("WEBHOOK_HOST", "0.0.0.0")
    WEBHOOK_PORT: int = int(os.getenv("WEBHOOK_PORT", "8000"))

    def validate(self) -> list[str]:
        """Return a list of human-readable problems, empty if config looks usable."""
        problems = []
        if not self.GROQ_API_KEY:
            problems.append("GROQ_API_KEY is not set in .env")
        if not self.NEO4J_PASSWORD:
            problems.append("NEO4J_PASSWORD is not set in .env")
        if not self.UBUNTU_AGENT_API_KEY:
            problems.append("UBUNTU_AGENT_API_KEY is not set in .env")
        return problems


settings = Settings()
