using System;
using cfg.entity;
using HarmonyLib;
using UnityGameFramework.Scripts;

namespace CardCultivationCheat;

/// <summary>모든 체력 감소는 CardFightFSMEntityLogic.DamageHealth / DamageArmorHealth 를 거친다.</summary>
[HarmonyPatch]
internal static class CombatPatches
{
    const int KillDamage = 999999;

    internal static bool IsEnemy(CardType t) => t is
        CardType.EnemyMonster or CardType.EnemyBoss or CardType.EnemyRole or CardType.NpcMonster;

    /// <summary>피해량을 치트 설정에 맞게 바꾼다.</summary>
    static void Adjust(CardFightFSMEntityLogic target, ref int num)
    {
        if (target == null || num <= 0) return;
        try
        {
            if (target.TryCast<RoleEntityLogic>() != null)
            {
                if (Plugin.GodMode.Value) num = 0;
                return;
            }
            var type = target.GetCardType();
            if (IsEnemy(type))
            {
                if (Plugin.OneHitKill.Value) num = KillDamage;
            }
            else if (Plugin.AlliesInvincible.Value)
            {
                num = 0;
            }
        }
        catch (Exception e)
        {
            Plugin.Logger.LogError(e);
        }
    }

    [HarmonyPrefix]
    [HarmonyPatch(typeof(CardFightFSMEntityLogic), nameof(CardFightFSMEntityLogic.DamageHealth), typeof(int))]
    static void DamageHealth(CardFightFSMEntityLogic __instance, ref int num) => Adjust(__instance, ref num);

    [HarmonyPrefix]
    [HarmonyPatch(typeof(CardFightFSMEntityLogic), nameof(CardFightFSMEntityLogic.DamageHealth), typeof(int), typeof(CardType))]
    static void DamageHealthTyped(CardFightFSMEntityLogic __instance, ref int num) => Adjust(__instance, ref num);

    [HarmonyPrefix]
    [HarmonyPatch(typeof(CardFightFSMEntityLogic), nameof(CardFightFSMEntityLogic.DamageArmorHealth))]
    static void DamageArmorHealth(CardFightFSMEntityLogic __instance, ref int num) => Adjust(__instance, ref num);
}
