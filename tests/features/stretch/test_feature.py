"""스트레칭 알림 기능 테스트(가짜 시계, 화면 없음). 허리 알림과 겹치는 경우도 확인한다."""

from collections.abc import Iterator

import pytest

from piko.core.feature_base import FeatureContext, TimerEntry
from piko.core.ui_bus import DialogButton
from piko.features.posture.feature import TEXT_ALERT as POSTURE_ALERT
from piko.features.posture.feature import PostureFeature
from piko.features.posture.scheduler import PosturePhase
from piko.features.stretch.feature import (
    BUTTON_OK_ID,
    BUTTON_SNOOZE_ID,
    TEXT_ALERT,
    StretchFeature,
)
from piko.features.stretch.scheduler import StretchPhase
from tests.features.helpers import FakeClock, Recorder

# 간격 1분, 휴식 0.5분(30초), 미루기 5분(고정)
SETTINGS = {"interval_min": 1, "rest_min": 0.5}


@pytest.fixture
def stretch(context: FeatureContext, clock: FakeClock) -> Iterator[StretchFeature]:
    feat = StretchFeature(dict(SETTINGS), context, clock=clock)
    feat.start()
    yield feat
    feat.stop()


def fire(feature: StretchFeature | PostureFeature, clock: FakeClock, at: float) -> None:
    clock.now = at
    feature._on_timer()


def test_alert_uses_stretch_state_with_alert_fallback(
    stretch: StretchFeature, clock: FakeClock, recorder: Recorder
) -> None:
    fire(stretch, clock, 1060)
    assert recorder.last("state") == ["stretch", "alert"]
    text, buttons = recorder.last("dialog")
    assert text == TEXT_ALERT == "스트레칭할 시간!"
    assert buttons == [DialogButton(BUTTON_OK_ID, "확인"), DialogButton(BUTTON_SNOOZE_ID, "5분 뒤")]


def test_ok_starts_rest_then_counts_again(
    stretch: StretchFeature, context: FeatureContext, clock: FakeClock, recorder: Recorder
) -> None:
    fire(stretch, clock, 1060)
    clock.now = 1070
    context.bus.dialog_button_clicked.emit(BUTTON_OK_ID)
    assert recorder.last("clear") is None
    assert recorder.last("state") is None  # 휴식 중에는 다시 돌아다닌다
    assert stretch.scheduler.phase == StretchPhase.RESTING
    clock.now = 1080
    assert stretch.timer_entries() == [TimerEntry("스트레칭", 20, "휴식 중")]
    assert context.attention.holder == "stretch"  # 휴식이 끝날 때까지 차지

    fire(stretch, clock, 1100)  # 휴식 30초 끝
    assert stretch.scheduler.phase == StretchPhase.COUNTING
    assert stretch.timer_entries() == [TimerEntry("스트레칭", 60, "")]
    assert context.attention.holder is None


def test_snooze_alerts_again_after_five_minutes(
    stretch: StretchFeature, context: FeatureContext, clock: FakeClock, recorder: Recorder
) -> None:
    fire(stretch, clock, 1060)
    clock.now = 1070
    context.bus.dialog_button_clicked.emit(BUTTON_SNOOZE_ID)
    assert context.attention.holder is None
    assert stretch.scheduler.remaining(1070) == 300
    fire(stretch, clock, 1370)
    assert recorder.dialogs() == [TEXT_ALERT, TEXT_ALERT]


def test_alerting_timer_entry(stretch: StretchFeature, clock: FakeClock) -> None:
    fire(stretch, clock, 1060)
    assert stretch.timer_entries() == [TimerEntry("스트레칭", None, "알림 중")]


# --- 허리 알림과 겹칠 때 ---


@pytest.fixture
def posture(context: FeatureContext, clock: FakeClock) -> Iterator[PostureFeature]:
    feat = PostureFeature({"interval_min": 1.5, "snooze_min": 5}, context, clock=clock)
    feat.start()
    yield feat
    feat.stop()


def test_posture_skipped_while_stretch_alert_is_shown(
    stretch: StretchFeature, posture: PostureFeature, clock: FakeClock, recorder: Recorder
) -> None:
    fire(stretch, clock, 1060)  # 스트레칭 알림(응답 안 함)
    fire(posture, clock, 1090)  # 허리 알림 시각
    assert recorder.dialogs() == [TEXT_ALERT]  # 허리 알림은 띄우지 않음
    assert posture.scheduler.phase == PosturePhase.COUNTING
    assert posture.scheduler.remaining(1090) == 90  # 타이머만 새로 시작


def test_posture_skipped_while_resting(
    stretch: StretchFeature,
    posture: PostureFeature,
    context: FeatureContext,
    clock: FakeClock,
    recorder: Recorder,
) -> None:
    fire(stretch, clock, 1060)
    clock.now = 1061
    context.bus.dialog_button_clicked.emit(BUTTON_OK_ID)  # 휴식 시작(30초)
    fire(posture, clock, 1090)  # 휴식 중 허리 알림 시각
    assert recorder.dialogs() == [TEXT_ALERT]
    assert posture.scheduler.remaining(1090) == 90
    fire(stretch, clock, 1091)  # 휴식 끝
    fire(posture, clock, 1180)  # 이제는 허리 알림이 뜬다
    assert recorder.dialogs() == [TEXT_ALERT, POSTURE_ALERT]


def test_stretch_replaces_visible_posture_alert(
    stretch: StretchFeature,
    posture: PostureFeature,
    context: FeatureContext,
    clock: FakeClock,
    recorder: Recorder,
) -> None:
    stretch.scheduler._due_at = 1200  # 허리 알림이 먼저 오도록
    fire(posture, clock, 1090)
    assert recorder.dialogs() == [POSTURE_ALERT]
    fire(stretch, clock, 1200)
    assert recorder.dialogs() == [POSTURE_ALERT, TEXT_ALERT]
    assert posture.scheduler.phase == PosturePhase.COUNTING  # 허리 알림은 닫히고 다시 카운트
    assert context.attention.holder == "stretch"
    # 마지막 대화창 요청은 스트레칭 것이다(허리 알림의 닫기가 뒤에 오지 않는다)
    kinds = recorder.kinds()
    assert kinds[-1] == "dialog" and kinds[-2] == "state"
