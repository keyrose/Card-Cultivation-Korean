"""build/ 의 패치 파일을 게임 폴더에 설치한다. (원본은 backup/ 에 보관)

사용법: python install.py          설치
        python install.py restore  원본 복구
"""
import shutil
import sys

from common import BACKUP_DIR, BUILD_DIR, DATA_DIR, PATCHED_FILES


def backup():
    for rel in PATCHED_FILES:
        dst = BACKUP_DIR / rel
        if not dst.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(DATA_DIR / rel, dst)
            print("백업:", rel)


def install():
    backup()
    for rel in PATCHED_FILES:
        src = BUILD_DIR / rel
        if src.exists():
            shutil.copy2(src, DATA_DIR / rel)
            print("설치:", rel)


def restore():
    for rel in PATCHED_FILES:
        src = BACKUP_DIR / rel
        if src.exists():
            shutil.copy2(src, DATA_DIR / rel)
            print("복구:", rel)


if __name__ == "__main__":
    restore() if sys.argv[1:] == ["restore"] else install()
