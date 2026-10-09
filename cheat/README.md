# Card Cultivation 치트 (BepInEx 6 IL2CPP 플러그인)

게임 안에서 **F8** 로 여는 치트 창. 창 크기는 화면 해상도에 맞춰 자동으로 커지고, 설정 탭에서 바꿀 수 있다.

| 탭 | 기능 |
|---|---|
| 주인공 | 무적, 아군 무적, 적 즉사, 에너지 무한, 체력/에너지 회복, 최대 체력·공격·방어·최대 에너지·신혼 증가, 경지 상승, 수명 증가 |
| 자원 | 영석/명성 카드 생성(수량 지정), 맵의 영석 더미 x10 |
| 카드 생성 | 전체 카드 표에서 이름/ID 검색, 종류별 필터, 원하는 개수만큼 주인공 옆에 생성 |
| 설정 | 게임 속도 x0.5 ~ x10 |

토글 상태와 메뉴 키는 `BepInEx/config/keyrose.cardcultivation.cheat.cfg` 에 저장된다.

## 설치
한글 패치 설치 프로그램에서 **4번(한글 패치 + 치트 메뉴)** 을 고르면 BepInEx(6.0.0-be.788)와 함께 자동으로 설치된다.
릴리스용 DLL 은 같은 be.788 을 설치한 게임 폴더를 기준으로 빌드한다 (`tools/installer.py` 의 `BEPINEX_*`).
GitHub 릴리스의 6.0.0-pre.2 는 이 게임(IL2CPP 메타데이터 v31)을 지원하지 않아 쓸 수 없다.
직접 설치하려면:
1. [BepInEx 6 bleeding edge #788](https://builds.bepinex.dev/projects/bepinex_be) 의 `BepInEx-Unity.IL2CPP-win-x64-6.0.0-be.788+5b766a3.zip` 을 게임 폴더에 압축 해제
2. 게임을 한 번 실행해 `BepInEx/interop` 생성 (첫 실행은 몇 분 걸림)
3. `CardCultivationCheat.dll` 을 `BepInEx/plugins/` 에 넣기

제거: `BepInEx/plugins/CardCultivationCheat.dll` 삭제 (BepInEx 자체를 지우려면 `winhttp.dll`, `doorstop_config.ini`, `BepInEx/`, `dotnet/` 삭제).
치트 사용 전 `%USERPROFILE%\AppData\LocalLow\DarkIndex\CardCultivation\SaveRecord` 백업 권장.

## 빌드
.NET 6+ SDK 필요. 게임 폴더가 기본 경로가 아니면 `-p:GameDir=...` 지정.
```bash
dotnet build -c Release
```
빌드 후 자동으로 게임의 `BepInEx/plugins` 에 복사된다 (`-p:Deploy=false` 로 끔).

## 구조
- `Plugin.cs` 진입점, 설정, Harmony 패치 등록
- `CombatPatches.cs` `CardFightFSMEntityLogic.DamageHealth/DamageArmorHealth` 프리픽스로 무적/즉사
- `CheatBehaviour.cs` IMGUI 창, 카드 생성(`CardInfoHelper.CreateBaseEntityData` → `GameMgr.ShowEntity`), 유지형 치트
