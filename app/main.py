"""
Webhook receiver for Wazuh alerts.
Point Wazuh's <hook_url> at http://<this-host>:8000/wazuh-alerts
"""
import logging
from fastapi import FastAPI, Request
import uvicorn

from app.settings import settings
from app.agents import build_crew

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("threat-intel")

app = FastAPI(title="Threat Intel Agent Webhook")


@app.get("/health")
def health():
    problems = settings.validate()
    return {"status": "ok" if not problems else "misconfigured", "problems": problems}


@app.post("/wazuh-alerts")
async def receive_alert(request: Request):
    payload = await request.json()
    logger.info("Received alert: %s", payload.get("rule", {}).get("description"))

    crew = build_crew(payload)
    result = crew.kickoff()

    logger.info("Crew result: %s", result)
    return {"status": "processed", "result": str(result)}


def run():
    uvicorn.run("app.main:app", host=settings.WEBHOOK_HOST, port=settings.WEBHOOK_PORT, reload=False)


if __name__ == "__main__":
    run()
