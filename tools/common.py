"""경로 및 게임 .dat(XOR 암호화된 UnityFS 번들) 입출력 공용 함수."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GAME_DIR = Path(os.environ.get(
    "CC_GAME_DIR", r"C:\Program Files (x86)\Steam\steamapps\common\Card Cultivation"))
DATA_DIR = GAME_DIR / "CardCultivation_Data"
SA_DIR = DATA_DIR / "StreamingAssets"

BACKUP_DIR = ROOT / "backup"     # 원본 게임 파일 (git 제외)
BUILD_DIR = ROOT / "build"       # 빌드 결과 (git 제외)
SOURCE_DIR = ROOT / "source"     # 추출한 원문
TRANS_DIR = ROOT / "translation"  # 한국어 번역

KR_FONT = str(ROOT / "tools" / "fonts" / "NotoSerifKR-VF.ttf")  # SIL OFL
KR_FONT_WEIGHT = 500

# 한국어로 교체할 언어 열 (tbtextmapper: key, zh-Hans, zh-Hant, en, ru)
LANG_COLUMNS = ["ChineseSimplified", "ChineseTraditional", "English", "Russian"]
TARGET_LANG = "English"
KOREAN_LABEL = "한국어"


MAGIC = b"UnityFS\0"


def original(rel: str) -> Path:
    """백업이 있으면 백업(=원본)을, 없으면 게임 폴더의 파일을 돌려준다."""
    b = BACKUP_DIR / rel
    return b if b.exists() else DATA_DIR / rel


def derive_key(enc: bytes) -> bytes:
    k = bytes(a ^ b for a, b in zip(enc[:4], MAGIC[:4]))
    if k != bytes(a ^ b for a, b in zip(enc[4:8], MAGIC[4:8])):
        raise ValueError("4바이트 반복 XOR 키를 찾지 못함")
    return k


def xor(data: bytes, key: bytes) -> bytes:
    n = len(data)
    rep = (key * (n // 4 + 1))[:n]
    return (int.from_bytes(data, "little") ^ int.from_bytes(rep, "little")).to_bytes(n, "little")


def read_dat(path) -> tuple[bytes, bytes]:
    """암호화된 .dat → (복호화된 번들, 키)"""
    d = Path(path).read_bytes()
    key = derive_key(d)
    return xor(d, key), key
