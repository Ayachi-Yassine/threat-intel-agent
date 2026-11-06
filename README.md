# SentinelX Intelligence

**AI-assisted threat intelligence, alert correlation, risk assessment, and incident handoff.**

SentinelX is a lab-oriented, multi-agent security operations project. This repository contains the **intelligence and orchestration component**: it receives Wazuh alerts, runs a sequential CrewAI analysis pipeline, stores alert relationships in Neo4j, estimates incident risk, and can hand qualifying incidents to the companion SentinelX Responder service.

> **Project status:** experimental / educational. The current IOC assessment is LLM reasoning over alert context and known attack patterns; no external threat-intelligence feed or reputation API is configured. Risk scores and model verdicts are analyst-assistance signals, not ground truth.

## What it does

- **Alert intake:** FastAPI exposes a `POST /wazuh-alerts` webhook for Wazuh alert payloads.
- **Normalization:** a Collection Agent extracts key alert details such as source IP, rule description, severity, agent ID, and MITRE ATT&CK technique.
- **IOC assessment:** an IOC Intelligence Agent reasons about whether the observed pattern appears malicious. It does not currently query an external IOC feed.
- **Campaign context:** a Correlation Agent writes alert and source-IP relationships to Neo4j and retrieves the number of linked alerts for that source.
- **Risk assessment:** a Prediction Agent produces a 0–10 risk score and a recommendation.
- **Response handoff:** an Action Agent prepares an incident summary. The handoff tool checks `ACTION_RISK_THRESHOLD` before sending the summary to the separate Ubuntu responder, which performs its own host reconnaissance and decision process.

## Architecture

```text
Wazuh Manager
    |
    | POST /wazuh-alerts
    v
FastAPI webhook (app/main.py)
    |
    v
CrewAI sequential workflow
    |
    +--> Collection Agent
    |
    +--> IOC Intelligence Agent
    |      LLM reasoning; no external IOC feed configured
    |
    +--> Campaign Correlation Agent
    |      Neo4j graph storage and source-IP alert count
    |
    +--> Threat Prediction Agent
    |      risk score (0-10) and recommendation
    |
    +--> Action / Handoff Agent
           |
           | if risk_score >= ACTION_RISK_THRESHOLD
           v
       SentinelX Responder (/respond)
           |
           +--> independent live host reconnaissance
           +--> local playbook + Groq decision
           +--> dry-run or action execution (responder-side controls)
```

The two services perform **separate reasoning stages**. SentinelX Intelligence evaluates the Wazuh alert and graph context. SentinelX Responder independently inspects the target host before deciding whether and how to respond.

## Repository layout

```text
app/
  main.py                 FastAPI webhook and health endpoint
  settings.py             environment-based configuration
  agents/crew.py          five-agent sequential CrewAI workflow
  tools/
    graph_tool.py         Neo4j alert storage and correlation
    handoff_tool.py       threshold check and responder HTTP handoff
config/
  wazuh_manager_integration.xml
scripts/
  setup.bat
  run_server.bat
tests/
  test_local.py           local fake-alert pipeline exercise
.env.example
requirements.txt
```

The companion response service is maintained in [SentinelX Responder](https://github.com/Ayachi-Yassine/responder-agent-v3). The repository is currently named `responder-agent-v3`; the SentinelX name is the proposed shared project identity.

## Technology

- Python
- FastAPI and Uvicorn
- CrewAI
- Groq-hosted LLM
- Neo4j
- Requests
- Wazuh alert integration

## Configuration

Create a local `.env` file from `.env.example`. At minimum, configure:

| Variable | Purpose |
|---|---|
| `GROQ_API_KEY` | API key used by the CrewAI LLM |
| `NEO4J_URI` | Neo4j Bolt endpoint |
| `NEO4J_USER` | Neo4j username |
| `NEO4J_PASSWORD` | Neo4j password |
| `UBUNTU_AGENT_URL` | Base URL of the companion responder |
| `UBUNTU_AGENT_API_KEY` | Shared API key expected by the responder |
| `ACTION_RISK_THRESHOLD` | Minimum risk score required for handoff (default: 7) |
| `WEBHOOK_HOST` | Webhook bind address (default: `0.0.0.0`) |
| `WEBHOOK_PORT` | Webhook port (default: `8000`) |

Never commit a populated `.env`, API keys, passwords, or real incident data. Use `.env.example` only for placeholder values.

## Run locally

The repository includes Windows helper scripts:

```powershell
scripts\setup.bat
scripts\run_server.bat
```

After configuration, run the local fake-alert exercise:

```powershell
python -m tests.test_local
```

The webhook health endpoint is:

```text
http://localhost:8000/health
```

The local test exercises the CrewAI pipeline without requiring a live Wazuh alert. A successful run still depends on valid Groq and Neo4j configuration. If the responder is contacted, keep its own `DRY_RUN=true` setting enabled during testing.

## Wazuh integration

The example integration block is in `config/wazuh_manager_integration.xml`. Review and adapt it to the actual Wazuh deployment and webhook address before adding it to the manager configuration. Restart/reload Wazuh only after validating the configuration.

## Security boundaries and current limitations

This project is a prototype and should be run only in a controlled lab until the following areas are hardened:

- **Webhook authentication:** the current `/wazuh-alerts` route does not show request authentication. Restrict network access to trusted Wazuh infrastructure or add an authenticated integration before exposing it beyond an isolated lab.
- **LLM output is not authoritative:** model-generated IOC assessments and risk scores can be wrong. Validate consequential decisions with deterministic checks and analyst review.
- **No external IOC enrichment yet:** the IOC agent reasons from the alert and its prompt; it does not currently query VirusTotal, OTX, MISP, or another threat-intelligence provider.
- **Responder trust boundary:** the handoff uses an API key and HTTP request. Use a protected network path and consider TLS, key rotation, request authentication, and replay protection.
- **Neo4j lifecycle and resilience:** the graph driver is lazily initialized. Add application lifecycle cleanup, retries, and explicit database health checks before production use.
- **Observability:** current logging is basic application logging. Durable incident journaling, structured event records, distributed tracing, and end-to-end correlation IDs remain improvement areas.
- **Testing:** `tests/test_local.py` is a manual local exercise, not evidence of comprehensive automated unit, integration, or security test coverage.

## Roadmap

- Add authenticated Wazuh webhook intake and request validation.
- Integrate one or more external IOC enrichment providers.
- Add structured incident records, durable journaling, and correlation IDs across both services.
- Add distributed tracing and metrics for agent stages, graph operations, and response handoff.
- Expand automated tests with mocked LLM, Neo4j, and responder dependencies.
- Add analyst review gates and deterministic policy checks for high-impact actions.

## Disclaimer

SentinelX is an educational security automation project. It is not a substitute for a production SIEM/SOAR platform, and it must not be connected to production systems without a security review, strict access controls, and tested rollback procedures.
