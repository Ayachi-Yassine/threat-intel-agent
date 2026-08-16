"""
Threat Intelligence crew: 4 reasoning agents + 1 handoff agent.
Sequential pipeline: Collection -> IOC -> Correlation -> Prediction -> Handoff.

The Action Agent no longer decides or executes the remediation itself.
It writes a clear summary and hands the incident off to the autonomous
Ubuntu Action Agent (a separate AI agent running on the target machine),
which independently investigates real system state, consults its own
playbook, decides, executes, and verifies. See
app/tools/handoff_tool.py and, on the Ubuntu side, agent_service.py's
/respond endpoint.
"""
from crewai import Agent, Task, Crew, Process, LLM

from app.settings import settings
from app.tools import store_alert_in_graph, handoff_to_ubuntu_agent

llm = LLM(model=settings.GROQ_MODEL, api_key=settings.GROQ_API_KEY)

# ---------------------------------------------------------------------------
# Agents
# ---------------------------------------------------------------------------

collection_agent = Agent(
    role="Collection Agent",
    goal="Normalize a raw Wazuh alert into a clean, structured summary.",
    backstory=(
        "You process raw security telemetry from Wazuh. You extract the "
        "essential fields (source IP, rule description, severity, agent) "
        "and discard noise."
    ),
    llm=llm,
    verbose=True,
)

ioc_agent = Agent(
    role="IOC Intelligence Agent",
    goal="Assess whether the source IP or indicators look malicious, using reasoning "
         "over known attack patterns (no external feed configured yet).",
    backstory=(
        "You are a threat intel analyst. Given an alert summary, you reason "
        "about whether the pattern matches known malicious behavior (e.g. "
        "brute force, scanning, exploitation attempts) based on the rule "
        "description and MITRE ATT&CK context."
    ),
    llm=llm,
    verbose=True,
)

correlation_agent = Agent(
    role="Campaign Correlation Agent",
    goal="Store the alert in the knowledge graph and check whether it is part of a pattern.",
    backstory=(
        "You maintain the Neo4j knowledge graph linking alerts to source "
        "IPs over time, so repeated behavior from the same source is visible."
    ),
    tools=[store_alert_in_graph],
    llm=llm,
    verbose=True,
)

prediction_agent = Agent(
    role="Threat Prediction Agent",
    goal="Assign a risk score (0-10) and recommend whether a defensive action is warranted.",
    backstory=(
        "You are the senior analyst who makes the final call. You weigh "
        "the IOC assessment and correlation history to output a risk score "
        "and a clear recommendation."
    ),
    llm=llm,
    verbose=True,
)

action_agent = Agent(
    role="Action Agent",
    goal=(
        "Write a clear, complete incident summary and hand it off to the "
        "autonomous Ubuntu Action Agent, which will independently decide "
        "and execute the actual remediation."
    ),
    backstory=(
        "You are the bridge between analysis and response. You do not "
        "decide the remediation yourself -- the Ubuntu Action Agent does "
        "that, using its own live investigation of the target machine and "
        "its own playbook. Your job is to make sure it has everything it "
        "needs: a precise summary of what happened, the source IP, the "
        "risk score, and the rule that fired. You always report exactly "
        "what the Ubuntu agent decided and did."
    ),
    tools=[handoff_to_ubuntu_agent],
    llm=llm,
    verbose=True,
)


def build_crew(raw_alert: dict) -> Crew:
    """Build a fresh Crew configured for one specific Wazuh alert payload."""
    src_ip = raw_alert.get("data", {}).get("srcip", "unknown")
    agent_id = raw_alert.get("agent", {}).get("id", "000")
    rule_desc = raw_alert.get("rule", {}).get("description", "unknown rule")
    rule_level = raw_alert.get("rule", {}).get("level", 0)
    mitre = raw_alert.get("rule", {}).get("mitre", {}).get("id", ["unknown"])
    mitre_id = mitre[0] if isinstance(mitre, list) and mitre else "unknown"
    alert_id = raw_alert.get("id", str(raw_alert.get("rule", {}).get("id", "0")))

    t1 = Task(
        description=(
            f"Summarize this raw Wazuh alert in 2-3 sentences: "
            f"source_ip={src_ip}, rule='{rule_desc}', level={rule_level}, "
            f"mitre_technique={mitre_id}, agent_id={agent_id}."
        ),
        expected_output="A short structured summary of the alert.",
        agent=collection_agent,
    )

    t2 = Task(
        description=(
            "Based on the alert summary, assess how likely this represents "
            "genuine malicious activity vs. benign/noisy traffic. Give a short "
            "verdict (Low/Medium/High likelihood) with one sentence of reasoning."
        ),
        expected_output="A likelihood verdict with brief reasoning.",
        agent=ioc_agent,
        context=[t1],
    )

    t3 = Task(
        description=(
            f"Store this alert in the knowledge graph using the store_alert_in_graph "
            f"tool with alert_id='{alert_id}', src_ip='{src_ip}', "
            f"rule_desc='{rule_desc}', mitre_technique='{mitre_id}'. "
            "Report back how many total alerts this source IP has triggered."
        ),
        expected_output="Confirmation of graph storage and the alert count for this source IP.",
        agent=correlation_agent,
        context=[t1, t2],
    )

    t4 = Task(
        description=(
            "Using the IOC likelihood assessment and the correlation history "
            "(repeated alerts from the same IP raise risk), assign a final "
            "risk_score from 0 to 10 and state it clearly as 'risk_score: X'. "
            "Then give a one-line recommendation."
        ),
        expected_output="A line containing 'risk_score: <number>' plus a recommendation.",
        agent=prediction_agent,
        context=[t1, t2, t3],
    )

    t5 = Task(
        description=(
            "Write a clear 2-3 sentence summary of this whole incident "
            "(combining the alert details and the correlation history), "
            "extract the numeric risk_score from the previous task's output "
            "(look for 'risk_score: X'), and call the handoff_to_ubuntu_agent "
            f"tool with summary=<your summary>, src_ip='{src_ip}', "
            f"risk_score=<the number>, rule_desc='{rule_desc}', "
            f"agent_id='{agent_id}'. Always call the tool -- it handles the "
            "threshold check itself. Report exactly what it returned, word "
            "for word."
        ),
        expected_output="The exact result string from the handoff_to_ubuntu_agent tool.",
        agent=action_agent,
        context=[t1, t2, t3, t4],
    )

    return Crew(
        agents=[collection_agent, ioc_agent, correlation_agent, prediction_agent, action_agent],
        tasks=[t1, t2, t3, t4, t5],
        process=Process.sequential,
        verbose=True,
        max_rpm=10,
    )
