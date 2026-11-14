# 진행 상황

## 배포 방식 변경 — pythonw 바로가기 (완료 대기: 사용자 확인)

**한 일**
- 스마트 앱 컨트롤이 서명 없는 `Piko.exe`를 막아서, `.venv\Scripts\pythonw.exe "main.py"`를 실행하는 `Piko.lnk`로 배포한다(콘솔 없음)
- `assets/ui/piko.ico`: girl idle 첫 프레임 머리 부분으로 만든 아이콘(16~256px). `tools/make_icon.py`로 다시 만든다. 트레이 아이콘도 이것으로 바꿨다(파일이 없으면 예전 원)
- `core/shortcut.py`: PowerShell WScript.Shell로 `.lnk` 만들기·읽기(새 라이브러리 없음, 콘솔 안 뜸)
- `core/autostart.py`: 레지스트리 Run 키 → 시작 프로그램 폴더의 `Piko.lnk`. 시작할 때 예전 Run 등록이 있으면 바로가기로 옮기고 지운다. 바로가기의 pythonw나 main.py가 없어졌으면 다시 만든다
- `tools/make_shortcut.py`: 프로젝트 폴더(또는 인수로 준 폴더)에 `Piko.lnk`를 만든다
- PyInstaller 빌드(`piko.spec`)는 남겨 두었다
- 테스트를 바로가기 방식으로 바꿨다(전체 196개 통과)

**알려진 문제**
- 프로젝트 폴더나 `.venv`를 옮기면 프로젝트 폴더의 `Piko.lnk`는 다시 만들어야 한다(자동 실행 바로가기는 실행할 때 고쳐진다)
- 바로가기를 읽느라 시작할 때 PowerShell을 한 번 띄운다(자동 실행이 켜져 있을 때만, 약 0.5초)

## 8단계 — 창 축소, 스트레칭 알림, 아이콘 메뉴바 (완료 대기: 사용자 확인)

**한 일**
- 방 배경 464×232로 교체(×1). 대화창 높이 56
- `room.json`(사용자 요청으로 수정): 발끝 기준선 y=210, 이동 범위 32~432
  - 처음에는 y=150(벽과 바닥 경계)으로 해서 캐릭터가 벽 앞에 떠 보였다. 이전 방(바닥 192~288, 기준선 262 → 바닥 위에서 72.9%)과 같은 비율로 새 바닥(150~232)에 맞춰 210으로 바꿨다
  - 이동 범위는 침대~의자(173~303)에서 이전 방 비율(40~536/576)로 넓혔다. 양 끝에서 캐릭터 몸은 x=4~460. 가구와 겹치면 캐릭터가 앞에 그려진다
- 구조 변경(사용자 승인)
  - `core/attention.py`: 알림 우선순위 조율. 기능은 서로 import하지 않고 이 객체로 화면 차지를 요청한다. 높은 우선순위가 오면 낮은 쪽은 밀려난다(`on_preempted`)
  - `Feature(settings, context)`: `FeatureContext`(bus, attention). `Feature.timer_entries()`로 남은 시간을 제공하고 `FeatureRegistry.timer_entries()`가 모은다
  - `UiBus.set_character_state`는 상태 후보 목록을 받는다(캐릭터에 있는 첫 상태). `set_status_text`는 지웠다(대화창은 알림 때만)
- `features/stretch/`: 50분 → 알림 → [확인] 5분 휴식(화면 차지 유지) → 휴식 끝나면 다시 50분. [5분 뒤] 미루기. 간격·휴식은 설정 창에. 캐릭터 상태 `stretch` → 없으면 `alert`. 우선순위 20(허리 알림 10)
- 허리 알림: 스트레칭이 화면을 쓰는 중(알림·휴식)이면 알림 없이 타이머만 새로 시작. 떠 있는 허리 알림은 스트레칭이 오면 닫히고 다시 카운트. 남은 분 표시용으로 1분마다 깨던 것을 없애고 알림 시각에만 깬다
- UI: `side_bar.py`(아이콘 목록 등록), `pixel_icons.py`(코드 도트 16×16 → 32px, PNG 교체 가능), `timer_panel.py`(펼쳤을 때만 1초 갱신), `main_body.py`(가로 배치, 패널을 펼칠 때 화면 밖으로 나가면 왼쪽으로 밀고 접을 때 원위치), `theme.py`(베이지 톤). 창: 접힘 518×288, 펼침 686×288
- 테스트 27개 추가(전체 187개 통과). pytest를 `--import-mode=importlib`로 바꿨다(기능 폴더마다 같은 이름의 테스트 파일)
- 실행 확인: 패널 펼침 시 "30:00" → 2초 뒤 "29:58", 접으면 갱신 타이머 꺼짐. 스트레칭 알림 → [확인] → "휴식 중 00:29". 화면 오른쪽 끝에서 펼치면 창이 왼쪽으로 밀리고 접으면 원위치

**남은 일**
- exe 다시 빌드·배포(0.3.0)
- 메뉴바·패널은 배율을 따르지 않는다(지금 기본 배율 1에서만 확인)

**알려진 문제**
- 확인 중 고친 것: 패널을 처음 펼칠 때 줄이 한 박자 늦게 보이던 문제(새 라벨을 바로 표시하도록 수정)

## 7단계 — 실제 도트 그림 교체 (완료)

**한 일**
- 방 배경 `incoming/background_576x288.png` → `rooms/bedroom/background.png`. `room.json`: 576×288, 바닥선 y=262, 이동 범위 40~536, 기본 배율 1
- 캐릭터 `characters/girl`(PixelLab GIF 4개): 프레임 분리, 떨어진 잡티 제거(idle 2번째 프레임 1px), 발끝 정렬(alert 1px, walk 최대 3px), 공통 영역으로 여백 자르기 → 57×109. idle 4, alert 4, walk_right 6, walk_left 6장. 모두 5fps(GIF 200ms)
- 방향별 폴더 지원: `<상태>_left`/`<상태>_right`. 한쪽만 있으면 반전해서 쓴다. `character.json`의 `front_facing_states`(정면 그림)는 왼쪽을 볼 때도 반전하지 않는다(머리핀이 틀어지지 않게)
- 대화창 크기를 고해상 규격으로 바꿨다(×1에서 576×72)
- **버그 수정:** 자동 실행 경로 갱신이 "실행 위치가 다르면" 덮어쓰던 것을 "등록된 실행 파일이 없을 때만" 고치도록 바꿨다. 개발용 실행이 설치한 exe의 자동 실행 등록을 덮어쓰는 문제가 있었다
- 테스트 14개 추가(전체 151개 통과)
- **걷기 끊김 개선:** 50ms 고정 갱신(실제로는 윈도우 타이머 때문에 61~64ms, 2~3px씩 들쭉날쭉)을 "그릴 x가 1px 바뀌는 시각에 깨어나기"로 바꿨다. 정밀 타이머(`PreciseTimer`)와 ns 단위 경과 시간을 쓴다. 측정 결과 26~29ms마다 정확히 1px씩 움직인다. 다시 그리기는 캐릭터 주변 영역만 한다. 테스트 9개 추가(전체 160개)

- 0.2.0 exe를 빌드해 사용자 폴더(`%USERPROFILE%\Piko\Piko.exe`)에 배포했다(사용자가 걷기 상태를 확인함)

**남은 일**
- 필요하면 걷기 FPS를 5에서 8~10으로 올린다(`character.json`만 수정)

**알려진 문제**
- `penguin`, `test_slime`은 예전 192×96 방 기준이라 새 방에서는 아주 작게 보인다
- (해결됨) 사용자 PC의 자동 실행 등록이 개발용 명령으로 바뀌었던 문제: 구버전 exe 실행으로 복구됨

## 6단계 — 배포 (완료)

**한 일**
- `piko.spec`: PyInstaller 단일 exe(`dist\Piko.exe`, 46MB, 콘솔 창 없음, assets 포함). 개발용 의존성에 `pyinstaller` 추가
- `core/autostart.py`: `HKCU\...\Run`의 `Piko` 값으로 자동 실행 등록과 해제(`winreg`). exe면 exe 경로, 소스면 `pythonw.exe main.py`를 등록한다. 시작할 때 등록된 경로가 지금과 다르면(exe를 옮긴 경우) 고친다
- 트레이에 체크 메뉴 "윈도우 시작 시 실행". 실패하면 경고 창을 띄우고 체크를 실제 상태로 되돌린다
- `__version__ = "0.1.0"`, 시작 로그에 버전을 남긴다. `CHANGELOG.md` 작성
- 테스트 5개 추가(전체 137개 통과). 레지스트리 테스트는 전용 테스트 키를 쓰고 지운다

**알려진 문제**
- 피코를 두 개 실행하는 것을 막지 않는다. 자동 실행 중에 exe를 또 누르면 두 개가 뜬다
- 단일 exe라 실행할 때마다 임시 폴더에 풀어서 시작에 2~4초 걸린다
- exe 아이콘은 기본 아이콘이다(그림 확정 후 교체)

## 5단계 — 설정 저장 (완료)

**한 일**
- `core/settings_schema.py`: 설정 항목 설명(`SettingField`: 키, 이름, 종류 int/float/bool, 범위, 단위)과 `normalize_value()`(범위 자르기, 정수로 떨어지는 실수는 정수로)
- `Feature.title`, `Feature.settings_fields()` 추가. 허리 알림은 간격(0.5~240분), 미루기(0.5~60분), 알림음. `FeatureRegistry.settings_sections()`와 `apply_settings()`(그 기능만 다시 시작)
- `ui/settings_dialog.py`: 스키마를 보고 입력칸을 만든다. 트레이 메뉴 "설정…"으로 연다. 항상 맨 위에 뜨고, 중복으로 열리지 않는다
- 배율 즉시 적용: `ui/piko_view.py`(방 장면 + 대화창 묶음)가 새 배율로 다시 만들면서 캐릭터 위치, 알림 상태, 대화창 내용을 옮긴다. 창은 오른쪽 아래 모서리를 유지하고 화면 밖으로 나가면 안으로 밀어 넣는다
- 창 위치: 드래그가 끝날 때마다 `config.json`의 `window`에 바로 저장한다. 시작할 때 저장된 위치가 어느 화면에든 48px 이상 보이면 그 위치를, 아니면(모니터 분리 등) 기본 위치를 쓴다
- 트레이 메뉴 항목 추가는 같은 id면 문구만 바꾼다(기능 재시작 대비). 기능을 멈출 때 알림 중이었으면 알림을 닫는다
- 테스트 25개 추가(전체 132개 통과)

**알려진 문제**
- 설정 창의 최솟값보다 작은 값(예: 테스트용 0.05분)이 설정 파일에 있으면, 설정 창에서 [저장]할 때 최솟값으로 바뀐다

## 4단계 — 허리 알림 기능 (완료)

**한 일**
- `core/ui_bus.py`: 기능과 화면 사이의 범용 신호 묶음(`set_character_state`, `show_dialog`, `clear_dialog`, `set_status_text`, `add_tray_action`, `set_tray_action_text`, `dialog_button_clicked`, `tray_action_triggered`). `DialogButton`도 여기로 옮겼다
- `Feature(settings, bus)`, `FeatureRegistry(config, bus)`로 바꿨다. 기능 설정 섹션을 config.json에 써 두어 키가 보인다
- `features/posture/`
  - `settings.py`: 간격 30분, 미루기 5분, 소리 끔. 잘못된 값은 로그를 남기고 기본값을 쓴다. 소수 분(0.5 등)도 허용
  - `scheduler.py`: 대기/알림/일시정지 상태 기계(Qt 없음, 시각 주입)
  - `feature.py`: 단발 QTimer 하나로 알림 시각이나 남은 분 표시가 바뀌는 시각에만 깨어난다. 알림이 오면 캐릭터를 `alert` 상태로 바꾸고 대화창에 "허리 펴세요!"와 [확인] [N분 뒤]를 띄운다. 소리 옵션은 `winsound`를 쓴다
- 대화창은 평소에 "다음 허리 펴기까지 N분"(일시정지 중에는 "허리 알림 일시정지 중")을 작게 보여 준다
- 트레이: 기능이 메뉴 항목을 추가할 수 있게 했다("허리 알림 일시정지/재개"). 임시 "테스트: 대화창" 메뉴는 지웠다
- 테스트 37개 추가(전체 107개 통과)

**알려진 문제**
- `time.monotonic` 기준이라 PC가 절전에서 깨어나면 그동안의 시간도 흐른 것으로 쳐서 곧바로 알림이 뜰 수 있다

## 3.5단계 — 방 장면 (완료)

**한 일**
- `core/asset_loader.py`: `characters/<id>/character.json`, `rooms/<id>/room.json`을 읽고 검증한다. PNG 크기는 헤더로 확인하고, 상태는 폴더 이름으로 인식한다(idle·walk·alert는 필수). 고른 캐릭터나 방이 규격에 안 맞으면 로그를 남기고 다른 폴더로 대체하며, 하나도 없으면 오류 창을 띄우고 종료한다
- 설정 `config.json`의 `appearance` 섹션(`character`, `room`, `scale`). null이면 폴더 이름 순 첫 번째와 방의 기본 배율을 쓴다
- `ui/wander.py`: 쉬기(2~6초) → 범위 안 임의 x로 걷기 → 쉬기를 반복한다. x만 바뀐다. 멈춤/재개 가능
- `ui/scene_view.py`: 배경 → 캐릭터 순서로 그린다. 위치는 원본 1px 격자에 맞추고, 걸을 때만 50ms마다 갱신한다. 쉬는 동안에는 쉬기가 끝날 때 한 번만 깨어난다
- `ui/character_view.py`: 위젯 대신 `CharacterAnimator`로 바꿨다. 프레임을 배율만큼 미리 확대해 두고 좌우 반전본도 함께 만든다
- `ui/dialog_box.py`: 방 아래 대화창(문구 + 버튼, 버튼은 포커스를 받지 않음). `ui/pixel_art.py`: nearest-neighbor 확대
- 창은 내용물 크기에 맞춘다(×3에서 576×360). 투명 배경은 껐다
- `assets/characters/test_slime`(40×40, 눈이 오른쪽): 교체와 반전 확인용 임시 캐릭터
- 트레이 임시 메뉴를 "테스트: 대화창"으로 바꿨다(4단계에서 제거)
- 테스트 48개 추가(전체 70개 통과). 유휴 CPU는 5초 측정에서 펭귄 1.9%, 슬라임 0%(한 코어 기준, 걷기 포함)

**알려진 문제**
- 펭귄 그림이 정면이라 좌우 반전이 눈에 보이지 않는다(코드상 반전은 됨. 슬라임으로 확인)

## 3단계 — 피코 표시 (완료)

- 상태별 프레임 루프 재생, `set_state()`. 3.5단계에서 방 장면 구조로 확장됨

## 2단계 — 위젯 창 (완료)

**한 일**
- `ui/widget_window.py`: 테두리 없음, 투명 배경, 항상 맨 위, 작업표시줄 미표시(`Tool`), 포커스 뺏지 않음. 기본 위치는 주 화면 작업 영역 우측 하단(여백 16px). 왼쪽 드래그로 이동하고 끝나면 `moved` 시그널을 보낸다(5단계 위치 저장용). 지금은 임시로 주황색 원을 그린다
- `ui/tray.py`: 임시 원 아이콘, 메뉴 [숨기기/보이기] [종료], 아이콘 왼쪽 클릭으로 토글. 동작은 시그널로만 알린다
- `app.py`에서 창과 트레이를 연결. 창을 숨겨도 앱은 트레이에 남는다
- 위치 계산 단위 테스트 2개 추가(전체 16개 통과)

## 1단계 — 환경 준비 (완료)

**한 일**
- `.venv` 생성(Python 3.14.6), `pyproject.toml`로 PySide6·ruff·pytest 설치(`pip install -e ".[dev]"`)
- 폴더 뼈대: `piko/core`, `piko/ui`, `piko/features`, `assets/idle`, `assets/alert`, `tests/`, `docs/`
- `core/paths.py`(assets·APPDATA 경로), `core/logging_setup.py`(파일+콘솔 로그, 미처리 예외 기록), `core/config.py`(섹션별 JSON 설정), `core/feature_base.py`(`Feature` ABC + `FeatureRegistry`)
- `piko/app.py`가 앱을 조립하고 `main.py`는 진입점만 담당. 지금은 임시 빈 창을 띄운다
- 테스트 14개(paths, config, feature_base), `ruff check` 통과

