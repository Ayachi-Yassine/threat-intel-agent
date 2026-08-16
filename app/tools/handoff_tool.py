"""
The Action Agent's tool. Instead of deciding an action itself, this
hands off a summary of the incident to the autonomous Ubuntu Action
Agent, which independently investigates the machine's real state,
consults its own playbook, decides the action, executes it, and
verifies the result. This tool's job is: (1) a cheap early exit if
risk is below threshold (no point waking Ubuntu's agent for noise),
and (2) making the handoff call and returning Ubuntu's full verdict.
"""
import requests
from crewai.tools import tool

from app.settings import settings


@tool("handoff_to_ubuntu_agent")
def handoff_to_ubuntu_agent(summary: str, src_ip: str, risk_score: float, rule_desc: str, agent_id: str) -> str:
    """
    Hand off this incident to the autonomous Ubuntu Action Agent. Write a
    clear, complete `summary` of what happened -- the Ubuntu agent will
    use it alongside its own live investigation of the machine to decide
    what to do. You do not choose the action yourself; that decision is
    made independently by the Ubuntu agent. Always pass risk_score (0-10)
    -- if it's below the configured threshold, this tool returns early
    without contacting Ubuntu at all. Args: summary (a few sentences
    describing the incident), src_ip, risk_score, rule_desc, agent_id.
    """
    if risk_score < settings.ACTION_RISK_THRESHOLD:
        return (
            f"No handoff made. risk_score={risk_score} is below threshold "
            f"({settings.ACTION_RISK_THRESHOLD})."
        )

    try:
        resp = requests.post(
            f"{settings.UBUNTU_AGENT_URL}/respond",
            headers={"X-API-Key": settings.UBUNTU_AGENT_API_KEY},
            json={
                "summary": summary,
                "src_ip": src_ip,
                "risk_score": risk_score,
                "rule_desc": rule_desc,
                "agent_id": agent_id,
            },
            timeout=45,  # Ubuntu does its own recon + LLM call, give it room
        )
    except requests.exceptions.RequestException as e:
        return f"Could not reach the Ubuntu Action Agent: {e}"

    if resp.status_code >= 400:
        return f"Ubuntu Action Agent error {resp.status_code}: {resp.text}"

    data = resp.json()
    decision = data.get("decision", {})
    status = data.get("status")

    if status == "dry_run":
        return data.get("message", str(data))

    exec_result = data.get("execution_result", {})
    return (
        f"Ubuntu agent decided action='{decision.get('action')}' "
        f"(reasoning: {decision.get('reasoning')}). "
        f"Execution result: {exec_result}"
    )
