"""Text helper; no font files are redistributed."""
from pathlib import Path
from pico2d import load_font

_cache = {}
_CANDIDATES = [
    r'C:\Windows\Fonts\malgun.ttf',
    r'C:\Windows\Fonts\gulim.ttc',
    '/usr/share/fonts/truetype/nanum/NanumGothic.ttf',
    '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
]


def font(size=18):
    if size not in _cache:
        path = next((p for p in _CANDIDATES if Path(p).exists()), None)
        if path is None:
            raise RuntimeError('한글 글꼴을 찾지 못했습니다. ui.py의 _CANDIDATES를 수정하세요.')
        _cache[size] = load_font(path, size)
    return _cache[size]


def text(x, y, string, size=18, color=(255, 255, 255)):
    font(size).draw(x, y, str(string), color)
