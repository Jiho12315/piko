"""기능 테스트 공용 fixture. (QApplication은 tests/conftest.py가 만든다)"""

import pytest

from piko.core.attention import AttentionCoordinator
from piko.core.feature_base import FeatureContext
from piko.core.ui_bus import UiBus
from tests.features.helpers import FakeClock, Recorder


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def context() -> FeatureContext:
    return FeatureContext(UiBus(), AttentionCoordinator())


@pytest.fixture
def recorder(context: FeatureContext) -> Recorder:
    return Recorder(context.bus)
