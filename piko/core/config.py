"""설정 로드/저장(JSON). 섹션 단위로 기본값과 저장값을 합쳐서 돌려준다."""

import json
import logging
import os
from pathlib import Path
from typing import Any

CONFIG_ENCODING = "utf-8"
CORRUPT_SUFFIX = ".corrupt"
TEMP_SUFFIX = ".tmp"
JSON_INDENT = 2

logger = logging.getLogger(__name__)


class ConfigStore:
    """JSON 파일 하나에 섹션별 설정을 보관한다. 예: {"window": {...}, "posture": {...}}."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._data: dict[str, dict[str, Any]] = {}

    @property
    def path(self) -> Path:
        """설정 파일 경로."""
        return self._path

    def load(self) -> None:
        """파일에서 읽는다. 없으면 빈 설정, 깨졌으면 백업해 두고 빈 설정으로 시작한다."""
        if not self._path.exists():
            self._data = {}
            return
        try:
            raw = json.loads(self._path.read_text(encoding=CONFIG_ENCODING))
            if not isinstance(raw, dict):
                raise ValueError("최상위 값이 객체가 아님")
        except (OSError, ValueError) as exc:
            backup = self._path.with_name(self._path.name + CORRUPT_SUFFIX)
            logger.warning("설정 파일을 읽지 못해 기본값을 씁니다(%s). 백업: %s", exc, backup)
            os.replace(self._path, backup)
            self._data = {}
            return
        self._data = {k: v for k, v in raw.items() if isinstance(v, dict)}

    def save(self) -> None:
        """임시 파일에 쓴 뒤 교체해서 저장 중 꺼져도 파일이 깨지지 않게 한다."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_name(self._path.name + TEMP_SUFFIX)
        text = json.dumps(self._data, ensure_ascii=False, indent=JSON_INDENT)
        tmp.write_text(text, encoding=CONFIG_ENCODING)
        os.replace(tmp, self._path)

    def section(self, name: str, defaults: dict[str, Any]) -> dict[str, Any]:
        """기본값 위에 저장값을 덮어쓴 섹션 사본을 반환한다. 모르는 키는 버린다."""
        stored = self._data.get(name, {})
        return {key: stored.get(key, value) for key, value in defaults.items()}

    def set_section(self, name: str, values: dict[str, Any]) -> None:
        """섹션 값을 교체한다. 파일에 쓰려면 save()를 호출한다."""
        self._data[name] = dict(values)
