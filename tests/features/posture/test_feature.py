"""허리 알림 기능이 버스로 올바른 요청을 보내는지 테스트(가짜 시계, 화면 없음)."""

from collections.abc import Iterator

import pytest

from piko.core.feature_base import FeatureContext, TimerEntry
from piko.core.ui_bus import DialogButton
from piko.features.posture.feature import (
    BUTTON_OK_ID,
    BUTTON_SNOOZE_ID,
    TEXT_ALERT,
    TEXT_TRAY_PAUSE,
    TEXT_TRAY_RESUME,
    TRAY_PAUSE_ID,
    PostureFeature,
)
from piko.features.posture.scheduler import PosturePhase
from tests.features.helpers import FakeClock, Recorder


@pytest.fixture
def feature(context: FeatureContext, clock: FakeClock) -> Iterator[PostureFeature]:
    settings = {"interval_min": 1, "snooze_min": 0.5, "sound": False}
    feat = PostureFeature(settings, context, clock=clock)
    feat.start()
    yield feat
    feat.stop()


def fire(feature: PostureFeature, clock: FakeClock, at: float) -> None:
    """시계를 옮기고 타이머가 울린 것처럼 처리한다."""
    clock.now = at
    feature._on_timer()


def test_start_signals(context: FeatureContext, clock: FakeClock, recorder: Recorder) -> None:
    feat = PostureFeature({"interval_min": 1}, context, clock=clock)
    feat.start()
    assert recorder.last("tray_add") == (TRAY_PAUSE_ID, TEXT_TRAY_PAUSE)
    assert feat._timer.interval() == 60_000  # 알림 시각에만 깨어난다
    feat.stop()


def test_timer_entries(feature: PostureFeature, clock: FakeClock) -> None:
    clock.now = 1015
    assert feature.timer_entries() == [TimerEntry("허리 알림", 45, "")]
    fire(feature, clock, 1060)
    assert feature.timer_entries() == [TimerEntry("허리 알림", None, "알림 중")]


def test_alert_when_due(feature: PostureFeature, clock: FakeClock, recorder: Recorder) -> None:
    fire(feature, clock, 1000 + 59)
    assert "dialog" not in recorder.kinds()
    fire(feature, clock, 1000 + 60)
    assert recorder.last("state") == ["alert"]
    text, buttons = recorder.last("dialog")
    assert text == TEXT_ALERT
    assert buttons == [
        DialogButton(BUTTON_OK_ID, "확인"),
        DialogButton(BUTTON_SNOOZE_ID, "0.5분 뒤"),
    ]
    assert feature.attention.holder == "posture"


def test_ok_restarts_and_releases(
    feature: PostureFeature, context: FeatureContext, clock: FakeClock, recorder: Recorder
) -> None:
    fire(feature, clock, 1060)
    clock.now = 1070
    context.bus.dialog_button_clicked.emit(BUTTON_OK_ID)
    assert recorder.last("clear") is None
    assert recorder.last("state") is None
    assert feature.scheduler.remaining(1070) == 60
    assert context.attention.holder is None


def test_snooze_alerts_again(
    feature: PostureFeature, context: FeatureContext, clock: FakeClock, recorder: Recorder
) -> None:
    fire(feature, clock, 1060)
    clock.now = 1070
    context.bus.dialog_button_clicked.emit(BUTTON_SNOOZE_ID)
    assert feature.scheduler.remaining(1070) == 30
    fire(feature, clock, 1100)
    assert feature.scheduler.phase == PosturePhase.ALERTING
    assert recorder.dialogs() == [TEXT_ALERT, TEXT_ALERT]


def test_other_button_ids_are_ignored(
    feature: PostureFeature, context: FeatureContext, clock: FakeClock
) -> None:
    fire(feature, clock, 1060)
    context.bus.dialog_button_clicked.emit("other.ok")
    assert feature.scheduler.phase == PosturePhase.ALERTING


def test_pause_and_resume_from_tray(
    feature: PostureFeature, context: FeatureContext, clock: FakeClock, recorder: Recorder
) -> None:
    clock.now = 1020
    context.bus.tray_action_triggered.emit(TRAY_PAUSE_ID)
    assert feature.scheduler.phase == PosturePhase.PAUSED
    assert recorder.last("tray_text") == (TRAY_PAUSE_ID, TEXT_TRAY_RESUME)
    assert feature.timer_entries() == [TimerEntry("허리 알림", 40, "일시정지")]
    assert not feature._timer.isActive()

    fire(feature, clock, 5000)  # 멈춘 동안에는 알림 없음
    assert "dialog" not in recorder.kinds()

    clock.now = 5000
    context.bus.tray_action_triggered.emit(TRAY_PAUSE_ID)
    assert recorder.last("tray_text") == (TRAY_PAUSE_ID, TEXT_TRAY_PAUSE)
    assert feature.scheduler.remaining(5000) == 40
    fire(feature, clock, 5040)
    assert feature.scheduler.phase == PosturePhase.ALERTING


def test_pause_while_alerting_closes_dialog_and_releases(
    feature: PostureFeature, context: FeatureContext, clock: FakeClock, recorder: Recorder
) -> None:
    fire(feature, clock, 1060)
    context.bus.tray_action_triggered.emit(TRAY_PAUSE_ID)
    assert recorder.last("clear") is None
    assert recorder.last("state") is None
    assert context.attention.holder is None


def test_skips_alert_when_higher_priority_holds_attention(
    feature: PostureFeature, context: FeatureContext, clock: FakeClock, recorder: Recorder
) -> None:
    context.attention.register("higher", 99, lambda: None)
    assert context.attention.try_acquire("higher")
    fire(feature, clock, 1060)
    assert "dialog" not in recorder.kinds()  # 알림을 띄우지 않고
    assert feature.scheduler.phase == PosturePhase.COUNTING
    assert feature.scheduler.remaining(1060) == 60  # 타이머만 새로 시작


def test_preempted_alert_closes_and_restarts(
    feature: PostureFeature, context: FeatureContext, clock: FakeClock, recorder: Recorder
) -> None:
    fire(feature, clock, 1060)
    context.attention.register("higher", 99, lambda: None)
    clock.now = 1065
    assert context.attention.try_acquire("higher")
    assert recorder.last("clear") is None
    assert feature.scheduler.phase == PosturePhase.COUNTING
    assert feature.scheduler.remaining(1065) == 60
    assert context.attention.holder == "higher"  # 밀려난 쪽이 차지를 풀어 버리지 않는다
