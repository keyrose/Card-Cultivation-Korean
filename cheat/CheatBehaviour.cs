using System;
using System.Collections.Generic;
using System.Linq;
using cfg.card;
using cfg.entity;
using UnityEngine;
using UnityGameFramework.Scripts;

namespace CardCultivationCheat;

/// <summary>F8 로 여는 IMGUI 치트 창과 매 프레임 유지형 치트.</summary>
public class CheatBehaviour : MonoBehaviour
{
    public CheatBehaviour(IntPtr ptr) : base(ptr) { }

    bool _show;
    Rect _rect = new(20, 20, 460, 620);
    int _tab;
    static readonly string[] Tabs = { "주인공", "자원", "카드 생성", "설정" };

    // 카드 생성 탭
    struct CardEntry { public int Id; public string Name; public CardType Type; public Lv Level; public string Search; }
    List<CardEntry> _cards;
    List<CardEntry> _filtered = new();
    string _search = "", _lastSearch = null;
    int _group, _lastGroup = -1;
    string _countText = "1";
    Vector2 _scroll;

    string _stoneText = "10000", _repText = "1000", _lifeText = "100";
    string _status = "";
    float _statusTime;
    float _nextTick;

    static readonly (string Label, CardType[] Types)[] Groups =
    {
        ("전체", null),
        ("재료/약초", new[] { CardType.Materials, CardType.Herb }),
        ("단약", new[] { CardType.Potion }),
        ("공법/서적", new[] { CardType.Book, CardType.Insight, CardType.Talents }),
        ("술법/스킬", new[] { CardType.Spell, CardType.Skill }),
        ("무기/법보", new[] { CardType.Weapon, CardType.WeaponSpiritual }),
        ("영수/괴뢰", new[] { CardType.SpiritBeast, CardType.Puppet, CardType.SummonCard }),
        ("아이템", new[] { CardType.ItemsKey, CardType.ItemsNormal, CardType.Blueprints, CardType.CardPack, CardType.MissionKey }),
        ("경험/영석", new[] { CardType.Exp, CardType.ExpGreatPerfection, CardType.ExpMonster, CardType.SpiritStone, CardType.Soul, CardType.Lucky, CardType.Reputation, CardType.Core, CardType.CoreGolden, CardType.CoreSoul, CardType.Energy }),
        ("적/보스", new[] { CardType.EnemyMonster, CardType.EnemyBoss, CardType.EnemyRole, CardType.NpcMonster }),
    };

    static GameMgrComponent Mgr
    {
        get { try { return GameEntry.GameMgr; } catch { return null; } }
    }

    static RoleEntityLogic Role
    {
        get { try { return Mgr?.GetRoleEntityLogic(); } catch { return null; } }
    }

    void Update()
    {
        // 게임 속도: 게임이 일시정지(0)할 때는 건드리지 않는다
        float speed = Plugin.GameSpeed.Value;
        if (!Mathf.Approximately(speed, 1f) && Time.timeScale > 0f && !Mathf.Approximately(Time.timeScale, speed))
            Time.timeScale = speed;

        if (Time.unscaledTime < _nextTick) return;
        _nextTick = Time.unscaledTime + 0.5f;
        try
        {
            var role = Role;
            if (role == null) return;
            var data = role.roleEntityData;
            if (data == null) return;
            if (Plugin.GodMode.Value && data.Health < data.HealthMax)
                role.RecoverFightHealth(data.HealthMax - data.Health);
            if (Plugin.InfiniteEnergy.Value && data.Energy < data.EnergyMax)
                role.AddRoleEnergyFull();
        }
        catch (Exception e)
        {
            Plugin.Logger.LogWarning(e.Message);
        }
    }

    void OnGUI()
    {
        var e = Event.current;
        if (e != null && e.type == EventType.KeyDown && e.keyCode == Plugin.ToggleKey.Value)
        {
            _show = !_show;
            e.Use();
        }
        if (!_show) return;

        // 1080p 기준으로 그리고 화면 해상도에 맞춰 확대한다 (4K 에서 창이 너무 작아지지 않도록)
        float scale = Plugin.UiScale.Value > 0f ? Plugin.UiScale.Value : Mathf.Max(1f, Screen.height / 1080f);
        var old = GUI.matrix;
        GUI.matrix = Matrix4x4.TRS(Vector3.zero, Quaternion.identity, new Vector3(scale, scale, 1f));

        GUI.skin.label.wordWrap = true;
        // 기본 창 배경은 반투명이라 지도 위에서 글자가 잘 안 보인다 → 반투명 상자를 겹쳐 진하게 깐다
        // (GUI.DrawTexture 는 게임 빌드에서 제거되어 쓸 수 없다)
        for (int i = 0; i < 4; i++) GUI.Box(_rect, "");
        _rect = GUI.Window(0x7C17, _rect, (GUI.WindowFunction)(Action<int>)DrawWindow,
            $"Card Cultivation 치트  ({Plugin.ToggleKey.Value} 닫기)");
        // 해상도가 바뀌어도 창이 화면 밖으로 나가지 않게
        _rect.x = Mathf.Clamp(_rect.x, 0f, Mathf.Max(0f, Screen.width / scale - _rect.width));
        _rect.y = Mathf.Clamp(_rect.y, 0f, Mathf.Max(0f, Screen.height / scale - _rect.height));

        GUI.matrix = old;
    }

    void DrawWindow(int id)
    {
        try
        {
            GUILayout.BeginHorizontal();
            for (int i = 0; i < Tabs.Length; i++)
            {
                var label = i == _tab ? $"[{Tabs[i]}]" : Tabs[i];
                if (GUILayout.Button(label)) _tab = i;
            }
            GUILayout.EndHorizontal();
            GUILayout.Space(6);

            if (Mgr == null || Role == null)
            {
                GUILayout.Label("주인공을 찾지 못했습니다. 게임(세이브)을 불러온 뒤에 사용할 수 있습니다. (스토리 맨 처음에는 주인공 카드가 아직 없을 수 있습니다)");
                if (_tab == 3) DrawSettings();
            }
            else
            {
                switch (_tab)
                {
                    case 0: DrawRole(); break;
                    case 1: DrawResources(); break;
                    case 2: DrawCards(); break;
                    case 3: DrawSettings(); break;
                }
            }

            if (_status.Length > 0 && Time.unscaledTime - _statusTime < 4f)
            {
                GUILayout.FlexibleSpace();
                GUILayout.Label(_status);
            }
        }
        catch (Exception ex)
        {
            GUILayout.Label("오류: " + ex.Message);
        }
        GUI.DragWindow(new Rect(0, 0, 10000, 22));
    }

    void Status(string msg)
    {
        _status = msg;
        _statusTime = Time.unscaledTime;
        Plugin.Logger.LogInfo(msg);
    }

    void Run(string what, Action action)
    {
        try { action(); Status(what); }
        catch (Exception ex) { Status($"{what} 실패: {ex.Message}"); Plugin.Logger.LogError(ex); }
    }

    // ───────────── 주인공 ─────────────
    void DrawRole()
    {
        var role = Role;
        var d = role.roleEntityData;
        GUILayout.Label($"경지: {LvName(d.Level)}");
        GUILayout.Label($"체력 {d.Health}/{d.HealthMax}   공격 {d.Attack}   방어 {d.Armor}   에너지 {d.Energy}/{d.EnergyMax}");
        GUILayout.Space(6);

        Plugin.GodMode.Value = GUILayout.Toggle(Plugin.GodMode.Value, " 무적 (주인공이 피해를 받지 않음)");
        Plugin.AlliesInvincible.Value = GUILayout.Toggle(Plugin.AlliesInvincible.Value, " 아군 무적 (영수·괴뢰·동료 등)");
        Plugin.OneHitKill.Value = GUILayout.Toggle(Plugin.OneHitKill.Value, " 적 즉사 (적에게 주는 피해 = 999999)");
        Plugin.InfiniteEnergy.Value = GUILayout.Toggle(Plugin.InfiniteEnergy.Value, " 에너지 무한");
        GUILayout.Space(6);

        GUILayout.BeginHorizontal();
        if (GUILayout.Button("체력 완전 회복"))
            Run("체력 회복", () => role.RecoverFightHealth(Math.Max(0, d.HealthMax - d.Health)));
        if (GUILayout.Button("에너지 가득"))
            Run("에너지 회복", () => role.AddRoleEnergyFull());
        GUILayout.EndHorizontal();

        GUILayout.BeginHorizontal();
        if (GUILayout.Button("최대 체력 +10"))
            Run("최대 체력 +10", () => { d.HealthMax += 10; d.Health += 10; });
        if (GUILayout.Button("공격력 +5"))
            Run("공격력 +5", () => d.Attack += 5);
        if (GUILayout.Button("방어 +10"))
            Run("방어 +10", () => d.Armor += 10);
        GUILayout.EndHorizontal();

        GUILayout.BeginHorizontal();
        if (GUILayout.Button("최대 에너지 +1"))
            Run("최대 에너지 +1", () => role.AddRoleEnergyMax(1));
        if (GUILayout.Button("신혼 +1"))
            Run("신혼 +1", () => role.ChangeSoulNum(1));
        GUILayout.EndHorizontal();

        GUILayout.Space(6);
        GUILayout.Label("수련 / 경지");
        GUILayout.BeginHorizontal();
        if (GUILayout.Button("경지 한 단계 상승"))
            Run("경지 상승", () => role.UpgradeLevel());
        GUILayout.EndHorizontal();

        GUILayout.BeginHorizontal();
        GUILayout.Label("수명 증가량", GUILayout.Width(80));
        _lifeText = GUILayout.TextField(_lifeText, GUILayout.Width(80));
        if (GUILayout.Button("수명 늘리기") && int.TryParse(_lifeText, out var life))
            Run($"수명 +{life}", () => role.AddDecAgeMaxTime(life));
        GUILayout.EndHorizontal();
    }

    // ───────────── 자원 ─────────────
    void DrawResources()
    {
        GUILayout.Label("주인공 옆에 카드로 생성됩니다. (끌어다 합치면 기존 더미에 더해집니다)");

        GUILayout.BeginHorizontal();
        GUILayout.Label("영석", GUILayout.Width(60));
        _stoneText = GUILayout.TextField(_stoneText, GUILayout.Width(100));
        if (GUILayout.Button("영석 생성") && int.TryParse(_stoneText, out var stones))
            Run($"영석 {stones} 생성", () => SpawnStack(CardType.SpiritStone, stones));
        GUILayout.EndHorizontal();

        GUILayout.BeginHorizontal();
        GUILayout.Label("명성", GUILayout.Width(60));
        _repText = GUILayout.TextField(_repText, GUILayout.Width(100));
        if (GUILayout.Button("명성 생성") && int.TryParse(_repText, out var rep))
            Run($"명성 {rep} 생성", () => SpawnStack(CardType.Reputation, rep));
        GUILayout.EndHorizontal();

        GUILayout.Space(6);
        GUILayout.BeginHorizontal();
        if (GUILayout.Button("맵의 모든 영석 더미 x10"))
            Run("영석 더미 x10", () => MultiplyStacks(10));
        GUILayout.EndHorizontal();
    }

    static CardInfo FirstCardOfType(CardType type)
    {
        var list = Mgr.GetCardInfoList();
        for (int i = 0; i < list.Count; i++)
            if (list[i].CardType == type) return list[i];
        throw new Exception($"{type} 카드 정보를 찾지 못함");
    }

    void SpawnStack(CardType type, int amount)
    {
        var data = CreateCardData(FirstCardOfType(type), 0);
        var stone = data.TryCast<SpiritStoneEntityData>();
        if (stone != null) stone.SetStoneNum(amount);
        var rep = data.TryCast<ReputationEntityData>();
        if (rep != null) rep.SetStoneNum(amount);
        Mgr.ShowEntity(data);
    }

    static void MultiplyStacks(int mul)
    {
        var list = Mgr.GetCurMapEntityList();
        int n = 0;
        for (int i = 0; i < list.Count; i++)
        {
            var stone = list[i]?.TryCast<SpiritStoneEntityLogic>();
            if (stone == null) continue;
            var num = stone.spiritStoneEntityData?.StoneNum ?? 0;
            if (num > 0) { stone.AddStoneNum(num * (mul - 1)); n++; }
        }
        if (n == 0) throw new Exception("맵에 영석 더미가 없음");
    }

    // ───────────── 카드 생성 ─────────────
    void LoadCards()
    {
        var list = Mgr.GetCardInfoList();
        _cards = new List<CardEntry>(list.Count);
        for (int i = 0; i < list.Count; i++)
        {
            var c = list[i];
            if (c == null) continue;
            var name = c.Name ?? "";
            _cards.Add(new CardEntry
            {
                Id = c.Id, Name = name, Type = c.CardType, Level = c.Level,
                Search = (c.Id + " " + name).ToLowerInvariant(),
            });
        }
        _lastSearch = null;
    }

    void DrawCards()
    {
        if (_cards == null || _cards.Count == 0) LoadCards();

        GUILayout.BeginHorizontal();
        GUILayout.Label("검색", GUILayout.Width(40));
        _search = GUILayout.TextField(_search ?? "");
        GUILayout.Label("개수", GUILayout.Width(35));
        _countText = GUILayout.TextField(_countText, GUILayout.Width(40));
        GUILayout.EndHorizontal();

        for (int row = 0; row < Groups.Length; row += 5)
        {
            GUILayout.BeginHorizontal();
            for (int i = row; i < Math.Min(row + 5, Groups.Length); i++)
                if (GUILayout.Button(i == _group ? $"[{Groups[i].Label}]" : Groups[i].Label)) _group = i;
            GUILayout.EndHorizontal();
        }

        if (_search != _lastSearch || _group != _lastGroup)
        {
            _lastSearch = _search;
            _lastGroup = _group;
            var q = _search.Trim().ToLowerInvariant();
            var types = Groups[_group].Types;
            _filtered = _cards
                .Where(c => (types == null || types.Contains(c.Type)) && (q.Length == 0 || c.Search.Contains(q)))
                .Take(300)
                .ToList();
            _scroll = Vector2.zero;
        }

        GUILayout.Label($"{_filtered.Count}개 표시 (최대 300, 전체 {_cards.Count}) · 이름 또는 ID로 검색");
        _scroll = GUILayout.BeginScrollView(_scroll);
        foreach (var c in _filtered)
        {
            GUILayout.BeginHorizontal();
            GUILayout.Label($"{c.Id}  {c.Name}  <color=#9ab>{TypeName(c.Type)} {LvName(c.Level)}</color>");
            if (GUILayout.Button("생성", GUILayout.Width(50)))
            {
                int count = int.TryParse(_countText, out var n) ? Math.Clamp(n, 1, 50) : 1;
                var entry = c;
                Run($"{entry.Name} x{count} 생성", () =>
                {
                    var info = Mgr.GetCardInfo(entry.Id);
                    for (int i = 0; i < count; i++)
                        Mgr.ShowEntity(CreateCardData(info, i));
                });
            }
            GUILayout.EndHorizontal();
        }
        GUILayout.EndScrollView();
    }

    static readonly System.Random Rng = new();

    /// <summary>주인공 카드 근처에 놓일 카드 데이터를 만든다.</summary>
    static BaseEntityData CreateCardData(CardInfo info, int index)
    {
        var role = Role;
        var pos = role.transform.position;
        // 주인공 오른쪽에 조금씩 흩어 놓는다
        pos += new Vector3(2.5f + (index % 5) * 0.4f + (float)Rng.NextDouble() * 0.3f, 0f,
                           -((index / 5) * 0.6f) - (float)Rng.NextDouble() * 0.3f);
        var data = CardInfoHelper.CreateBaseEntityData(info, role.MapId, pos, null, null);
        if (data == null) throw new Exception($"카드 {info.Id} 데이터 생성 실패");
        return data;
    }

    // ───────────── 설정 ─────────────
    void DrawSettings()
    {
        GUILayout.Label($"게임 속도: x{Plugin.GameSpeed.Value:0.#}");
        GUILayout.BeginHorizontal();
        foreach (var s in new[] { 0.5f, 1f, 2f, 3f, 5f, 10f })
            if (GUILayout.Button($"x{s:0.#}"))
            {
                Plugin.GameSpeed.Value = s;
                if (Time.timeScale > 0f) Time.timeScale = s;
            }
        GUILayout.EndHorizontal();
        GUILayout.Space(10);
        var ui = Plugin.UiScale.Value;
        GUILayout.Label($"창 크기: {(ui > 0f ? $"x{ui:0.##}" : "자동 (해상도에 맞춤)")}");
        GUILayout.BeginHorizontal();
        if (GUILayout.Button("자동")) Plugin.UiScale.Value = 0f;
        foreach (var s in new[] { 1f, 1.5f, 2f, 2.5f, 3f })
            if (GUILayout.Button($"x{s:0.#}")) Plugin.UiScale.Value = s;
        GUILayout.EndHorizontal();
        GUILayout.Space(10);
        GUILayout.Label($"메뉴 키: {Plugin.ToggleKey.Value}  (BepInEx/config/{Plugin.Guid}.cfg 에서 변경)");
        GUILayout.Label("토글 설정은 자동 저장됩니다. 카드 목록이 비어 있으면 아래 버튼을 누르세요.");
        if (Mgr != null && GUILayout.Button("카드 목록 다시 읽기"))
            Run("카드 목록 갱신", LoadCards);
    }

    // ───────────── 이름표 ─────────────
    static string LvName(Lv lv) => lv switch
    {
        Lv.None => "",
        Lv.Human => "범인",
        Lv.QiRefingEarly => "연기 초기",
        Lv.QiRefingMiddle => "연기 중기",
        Lv.QiRefing => "연기 후기",
        Lv.FoundationEstablishmentEarly => "축기 초기",
        Lv.FoundationEstablishmentMiddle => "축기 중기",
        Lv.FoundationEstablishment => "축기 후기",
        Lv.CoreFormationEarly => "결단 초기",
        Lv.CoreFormation => "결단 후기",
        Lv.NascentSoulEarly => "원영 초기",
        Lv.NascentSoul => "원영 후기",
        Lv.SpiritTransformation => "화신",
        Lv.VoidRefining => "연허",
        Lv.BodyIntegration => "합체",
        Lv.GreatAscension => "대승",
        Lv.Special => "특수",
        _ => lv.ToString(),
    };

    static string TypeName(CardType t) => t switch
    {
        CardType.Materials => "재료",
        CardType.Herb => "약초",
        CardType.Potion => "단약",
        CardType.Book => "서적",
        CardType.Insight => "깨달음",
        CardType.Talents => "재능",
        CardType.Spell => "술법",
        CardType.Skill => "스킬",
        CardType.Weapon => "무기",
        CardType.WeaponSpiritual => "법보",
        CardType.SpiritBeast => "영수",
        CardType.Puppet => "괴뢰",
        CardType.SummonCard => "소환",
        CardType.ItemsKey => "핵심 아이템",
        CardType.ItemsNormal => "아이템",
        CardType.Blueprints => "도면",
        CardType.CardPack => "카드팩",
        CardType.Exp => "수련 경험",
        CardType.SpiritStone => "영석",
        CardType.Reputation => "명성",
        CardType.EnemyMonster => "요수",
        CardType.EnemyBoss => "보스",
        CardType.EnemyRole => "적 수사",
        _ => t.ToString(),
    };
}
