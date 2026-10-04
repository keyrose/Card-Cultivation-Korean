"""build/ 의 패치 파일을 게임 폴더에 설치한다. (원본은 backup/ 에 보관)

사용법: python install.py          설치
        python install.py restore  원본 복구
"""
import shutil
import sys

from common import BACKUP_DIR, BUILD_DIR, DATA_DIR


def built_files():
    return sorted(p.relative_to(BUILD_DIR).as_posix() for p in BUILD_DIR.rglob("*") if p.is_file())


def install():
    for rel in built_files():
        dst = BACKUP_DIR / rel
        if not dst.exists():  # 최초 1회 원본 백업
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(DATA_DIR / rel, dst)
            print("백업:", rel)
        shutil.copy2(BUILD_DIR / rel, DATA_DIR / rel)
        print("설치:", rel)


def restore():
    for p in sorted(BACKUP_DIR.rglob("*")):
        if p.is_file():
            rel = p.relative_to(BACKUP_DIR).as_posix()
            shutil.copy2(p, DATA_DIR / rel)
            print("복구:", rel)


if __name__ == "__main__":
    restore() if sys.argv[1:] == ["restore"] else install()
