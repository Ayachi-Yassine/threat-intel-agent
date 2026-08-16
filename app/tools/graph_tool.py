"""
Campaign Correlation storage: writes alerts into the Neo4j graph and
links repeat activity from the same source IP.
"""
from crewai.tools import tool
from neo4j import GraphDatabase

from app.settings import settings

_driver = None


def _get_driver():
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(
            settings.NEO4J_URI, auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
        )
    return _driver


def close_driver():
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None


@tool("store_alert_in_graph")
def store_alert_in_graph(alert_id: str, src_ip: str, rule_desc: str, mitre_technique: str) -> str:
    """
    Write an alert into the Neo4j knowledge graph and link it to any prior
    alerts from the same source IP, so campaigns can be traced over time.
    Args: alert_id, src_ip, rule_desc, mitre_technique (e.g. 'T1110').
    """
    driver = _get_driver()
    with driver.session() as session:
        session.run(
            """
            MERGE (ip:SourceIP {address: $src_ip})
            CREATE (a:Alert {
                id: $alert_id,
                description: $rule_desc,
                technique: $mitre_technique,
                timestamp: datetime()
            })
            MERGE (ip)-[:TRIGGERED]->(a)
            """,
            src_ip=src_ip,
            alert_id=alert_id,
            rule_desc=rule_desc,
            mitre_technique=mitre_technique,
        )

        result = session.run(
            """
            MATCH (ip:SourceIP {address: $src_ip})-[:TRIGGERED]->(a:Alert)
            RETURN count(a) AS alert_count
            """,
            src_ip=src_ip,
        )
        alert_count = result.single()["alert_count"]

    return f"Stored alert {alert_id}. Source IP {src_ip} has {alert_count} total linked alerts in the graph."
