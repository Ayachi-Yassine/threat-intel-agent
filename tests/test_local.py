"""
Run this to test the whole pipeline WITHOUT waiting for a real Wazuh alert.

Usage:
    python -m tests.test_local
"""
from app.settings import settings
from app.agents import build_crew

FAKE_ALERT = {
    "id": "1690000000.654321",
    "agent": {"id": "002", "name": "yassine-VMware-Virtual-Platform"},
    "rule": {
        "id": 5720,
        "level": 12,
        "description": (
            "sshd: 50 authentication failures from the same source IP "
            "within 60 seconds, followed by a successful login — "
            "classic brute-force-then-access pattern."
        ),
        "mitre": {"id": ["T1110", "T1078"]},
    },
    "data": {"srcip": "185.220.101.47"},  # looks like a real routable IP, not a test range
}


def main():
    problems = settings.validate()
    if problems:
        print("Config problems found before running:")
        for p in problems:
            print(f"  - {p}")
        print("Fix your .env file and try again.\n")
        return

    crew = build_crew(FAKE_ALERT)
    result = crew.kickoff()

    print("\n\n=== FINAL RESULT ===")
    print(result)


if __name__ == "__main__":
    main()
