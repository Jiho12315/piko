# 피코 (Piko)

화면 한쪽에 항상 떠 있는 개인용 윈도우 데스크탑 마스코트입니다. 계획은 [PLAN.md](PLAN.md), 진행 상황은 [PROGRESS.md](PROGRESS.md)를 참고하세요.

## 개발 환경

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

## 실행

```powershell
.\.venv\Scripts\python.exe main.py
```

## 검사

```powershell
.\.venv\Scripts\ruff.exe format .
.\.venv\Scripts\ruff.exe check .
.\.venv\Scripts\python.exe -m pytest
```

## 배포 (바로가기)

윈도우 11 스마트 앱 컨트롤이 서명 없는 exe를 막기 때문에, 서명된 `pythonw.exe`로 `main.py`를 실행하는 바로가기로 배포합니다.

```powershell
.\.venv\Scripts\python.exe tools\make_shortcut.py            # 프로젝트 폴더에 Piko.lnk
.\.venv\Scripts\python.exe tools\make_shortcut.py <폴더>     # 다른 폴더(바탕 화면 등)에
```

`Piko.lnk`를 더블클릭하면 콘솔 창 없이 실행됩니다(피코 아이콘). 프로젝트 폴더나 `.venv`를 옮기면 바로가기를 다시 만드세요. 아이콘(`assets/ui/piko.ico`)은 캐릭터를 바꾼 뒤 `tools\make_icon.py`로 다시 만듭니다.

설정과 로그는 `%APPDATA%\Piko\`에 저장됩니다. 트레이 메뉴의 "윈도우 시작 시 실행"을 켜면 시작 프로그램 폴더(`shell:startup`)에 `Piko.lnk`가 생깁니다.

## exe 빌드 (보관용)

```powershell
.\.venv\Scripts\pyinstaller.exe piko.spec --noconfirm
```

결과는 `dist\Piko.exe`입니다. 서명이 없어 스마트 앱 컨트롤이 켜진 PC에서는 실행되지 않습니다. 버전을 올릴 때는 `piko/__init__.py`의 `__version__`, `pyproject.toml`의 `version`, `CHANGELOG.md`를 함께 고칩니다.
