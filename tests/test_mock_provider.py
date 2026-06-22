import asyncio

from app.connectors.mock import MockProvider


def test_mock_provider_returns_unchanged_raw_payloads():
    jobs = asyncio.run(MockProvider().search(["python"], "Remote", 10))

    assert len(jobs) == 1
    assert jobs[0].provider == "mock"
    assert jobs[0].api_version == "v1"
    assert jobs[0].payload["title"] == "Python Engineer"
