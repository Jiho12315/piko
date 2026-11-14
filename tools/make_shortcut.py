"""피코 실행 바로가기(Piko.lnk)를 프로젝트 폴더에 만든다.

pythonw.exe로 main.py를 실행하므로 콘솔 창이 뜨지 않는다. 바탕 화면이나 시작 메뉴에 두려면
만들어진 Piko.lnk를 복사하거나, 폴더를 인수로 준다.
사용법: .\\.venv\\Scripts\\python.exe tools\\make_shortcut.py [만들 폴더]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from piko.core import autostart, paths, shortcut  # noqa: E402


def main() -> None:
    """바로가기를 만든다."""
    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else paths.entry_script().parent
    link = autostart.launch_shortcut()
    path = folder / autostart.SHORTCUT_NAME
    shortcut.create(path, link)
    print(f"바로가기 생성: {path}\n  → {link.target} {link.arguments}")  # noqa: T201


if __name__ == "__main__":
    main()
