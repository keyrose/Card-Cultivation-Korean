using BepInEx;
using BepInEx.Configuration;
using BepInEx.Logging;
using BepInEx.Unity.IL2CPP;
using HarmonyLib;
using Il2CppInterop.Runtime.Injection;
using UnityEngine;

namespace CardCultivationCheat;

[BepInPlugin(Guid, Name, Version)]
public class Plugin : BasePlugin
{
    public const string Guid = "keyrose.cardcultivation.cheat";
    public const string Name = "Card Cultivation Cheat";
    public const string Version = "1.0.0";

    internal static ManualLogSource Logger;

    internal static ConfigEntry<KeyCode> ToggleKey;
    internal static ConfigEntry<bool> GodMode;
    internal static ConfigEntry<bool> OneHitKill;
    internal static ConfigEntry<bool> AlliesInvincible;
    internal static ConfigEntry<bool> InfiniteEnergy;
    internal static ConfigEntry<float> GameSpeed;
    internal static ConfigEntry<float> UiScale;

    public override void Load()
    {
        Logger = Log;

        ToggleKey = Config.Bind("일반", "메뉴키", KeyCode.F8, "치트 메뉴 열기/닫기 키");
        if (ToggleKey.Value == KeyCode.F1) ToggleKey.Value = KeyCode.F8; // F1 은 게임이 쓰는 키라 옛 기본값을 옮긴다
        UiScale = Config.Bind("일반", "UI배율", 0f, "치트 창 크기 배율 (0 = 화면 해상도에 맞춰 자동, 1080p 기준 1)");
        GodMode = Config.Bind("전투", "무적", false, "주인공이 피해를 받지 않음");
        AlliesInvincible = Config.Bind("전투", "아군무적", false, "주인공 외 아군 카드(영수/꼭두각시/동료 등)도 피해를 받지 않음");
        OneHitKill = Config.Bind("전투", "적즉사", false, "적에게 주는 피해가 항상 치명타");
        InfiniteEnergy = Config.Bind("수련", "에너지무한", false, "주인공 에너지를 항상 최대로 유지");
        GameSpeed = Config.Bind("일반", "게임속도", 1f, "게임 속도 배율 (1 = 기본)");

        ClassInjector.RegisterTypeInIl2Cpp<CheatBehaviour>();
        AddComponent<CheatBehaviour>();

        new Harmony(Guid).PatchAll(typeof(CombatPatches));

        Log.LogInfo($"{Name} {Version} 로드됨 - {ToggleKey.Value} 키로 메뉴를 엽니다.");
    }
}
