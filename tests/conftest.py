import pytest


def pytest_addoption(parser):
    parser.addoption("--live", action="store_true", default=False, help="also hit the Anthropic API")


@pytest.fixture
def live(request):
    return request.config.getoption("--live")
