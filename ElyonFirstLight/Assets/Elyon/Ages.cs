using System.Collections.Generic;

namespace Elyon
{
    public enum AgeId
    {
        FirstFamily = 0,
        Camps = 1,
        Farming = 2,
        MetalTowns = 3,
        Cities = 4,
        RoadsAndLetters = 5,
        Mills = 6,
    }

    public enum DivineAct
    {
        TurnYears,
        Bless,
        Heal,
        SetFruit,
        Calm,
        SendGame,
        RaiseShelter,
        SendRain,
        BlessField,
        GiftOre,
        Mend,
        Proclaim,
        GrantHarvest,
        WithholdHarvest,
        OpenRoad,
        KindleLesson,
        TurnMill,
        RestMill,
    }

    public struct AgeFacts
    {
        public int year;
        public int population;
        public int childrenBorn;
        public float meals;
        public float wood;
        public float ore;
        public float knowledge;
        public float faith;
        public int tents;
        public int houses;
        public int fields;
        public int metalTools;
        public int settlements;
        public bool smithy;
        public bool hall;
        public bool temple;
        public bool road;
        public bool letters;
        public bool mill;
    }

    /// <summary>
    /// What must be true in the world before the next age can begin.
    /// </summary>
    public static class Ages
    {
        public static string Name(AgeId age)
        {
            switch (age)
            {
                case AgeId.FirstFamily: return "First family";
                case AgeId.Camps: return "Camps";
                case AgeId.Farming: return "Farming";
                case AgeId.MetalTowns: return "Metal and towns";
                case AgeId.Cities: return "Cities and empires";
                case AgeId.RoadsAndLetters: return "Roads and letters";
                default: return "Mills";
            }
        }

        public static string Living(AgeId age)
        {
            switch (age)
            {
                case AgeId.FirstFamily:
                    return "Adam and Eve live at the fire. They gather fruit and wood, and a child can be born into their care.";
                case AgeId.Camps:
                    return "The household camps east of the lake, hunts, and sleeps in lean-tos.";
                case AgeId.Farming:
                    return "Fields and houses feed them. Grain is the meal, and hoes are cut from wood.";
                case AgeId.MetalTowns:
                    return "Ore, a smithy, and hammers. The camp becomes a town on the ridge.";
                case AgeId.Cities:
                    return "A hall, a temple, and a second hold. Law and worship sit in the city.";
                case AgeId.RoadsAndLetters:
                    return "A road joins the holds. Someone teaches, and a house keeps letters.";
                default:
                    return "A mill multiplies the harvest. The same families keep house.";
            }
        }

        public static string Hand(AgeId age)
        {
            switch (age)
            {
                case AgeId.FirstFamily:
                    return "You may bless, heal, set fruit, calm a fear, and turn the years.";
                case AgeId.Camps:
                    return "You may also send game and raise a shelter from their wood.";
                case AgeId.Farming:
                    return "You may send rain and bless a field.";
                case AgeId.MetalTowns:
                    return "You may gift ore and mend a body at the smithy.";
                case AgeId.Cities:
                    return "You may proclaim a law, grant a harvest, or withhold one.";
                case AgeId.RoadsAndLetters:
                    return "You may open the road and kindle a lesson.";
                default:
                    return "You may turn the mill or let it rest.";
            }
        }

        public static string Label(DivineAct act)
        {
            switch (act)
            {
                case DivineAct.TurnYears: return "The years turn";
                case DivineAct.Bless: return "Bless";
                case DivineAct.Heal: return "Heal";
                case DivineAct.SetFruit: return "Set fruit";
                case DivineAct.Calm: return "Calm";
                case DivineAct.SendGame: return "Send game";
                case DivineAct.RaiseShelter: return "Raise a shelter";
                case DivineAct.SendRain: return "Send rain";
                case DivineAct.BlessField: return "Bless the field";
                case DivineAct.GiftOre: return "Gift ore";
                case DivineAct.Mend: return "Mend";
                case DivineAct.Proclaim: return "Proclaim a law";
                case DivineAct.GrantHarvest: return "Grant the harvest";
                case DivineAct.WithholdHarvest: return "Withhold the harvest";
                case DivineAct.OpenRoad: return "Open the road";
                case DivineAct.KindleLesson: return "Kindle a lesson";
                case DivineAct.TurnMill: return "Turn the mill";
                default: return "Let the mill rest";
            }
        }

        public static bool Allows(AgeId age, DivineAct act)
        {
            switch (act)
            {
                case DivineAct.TurnYears:
                case DivineAct.Bless:
                case DivineAct.Heal:
                case DivineAct.SetFruit:
                case DivineAct.Calm:
                    return true;
                case DivineAct.SendGame:
                case DivineAct.RaiseShelter:
                    return age >= AgeId.Camps;
                case DivineAct.SendRain:
                case DivineAct.BlessField:
                    return age >= AgeId.Farming;
                case DivineAct.GiftOre:
                case DivineAct.Mend:
                    return age >= AgeId.MetalTowns;
                case DivineAct.Proclaim:
                case DivineAct.GrantHarvest:
                case DivineAct.WithholdHarvest:
                    return age >= AgeId.Cities;
                case DivineAct.OpenRoad:
                case DivineAct.KindleLesson:
                    return age >= AgeId.RoadsAndLetters;
                case DivineAct.TurnMill:
                case DivineAct.RestMill:
                    return age >= AgeId.Mills;
                default:
                    return false;
            }
        }

        public static bool ReadyForNext(AgeId age, AgeFacts facts)
        {
            switch (age)
            {
                case AgeId.FirstFamily:
                    return facts.year >= 4
                        && facts.childrenBorn >= 1
                        && facts.wood >= 6f
                        && facts.meals >= 8f
                        && facts.faith >= 15f;
                case AgeId.Camps:
                    return facts.year >= 10
                        && facts.population >= 5
                        && facts.tents >= 2
                        && facts.meals >= 8f;
                case AgeId.Farming:
                    return facts.year >= 18
                        && facts.fields >= 2
                        && facts.houses >= 1
                        && facts.population >= 8;
                case AgeId.MetalTowns:
                    return facts.year >= 26
                        && facts.smithy
                        && facts.metalTools >= 1
                        && facts.population >= 10
                        && facts.faith >= 25f;
                case AgeId.Cities:
                    return facts.year >= 38
                        && facts.hall
                        && facts.temple
                        && facts.population >= 12
                        && facts.faith >= 30f;
                case AgeId.RoadsAndLetters:
                    return facts.year >= 52
                        && facts.road
                        && facts.letters
                        && facts.knowledge >= 8f
                        && facts.settlements >= 2;
                default:
                    return false;
            }
        }

        public static string StillNeeded(AgeId age, AgeFacts facts)
        {
            if (age == AgeId.Mills)
            {
                return "Mills is the latest age. Kin, work, and the mill carry on. The years still turn.";
            }

            var missing = new List<string>();
            switch (age)
            {
                case AgeId.FirstFamily:
                    if (facts.year < 4) missing.Add("year " + facts.year + "/4");
                    if (facts.childrenBorn < 1) missing.Add("a child born");
                    if (facts.wood < 6f) missing.Add("wood " + (int)facts.wood + "/6");
                    if (facts.meals < 8f) missing.Add("meals " + (int)facts.meals + "/8");
                    if (facts.faith < 15f) missing.Add("faith " + (int)facts.faith + "/15");
                    return Need("Camps", missing);
                case AgeId.Camps:
                    if (facts.year < 10) missing.Add("year " + facts.year + "/10");
                    if (facts.population < 5) missing.Add("people " + facts.population + "/5");
                    if (facts.tents < 2) missing.Add("lean-tos " + facts.tents + "/2");
                    if (facts.meals < 8f) missing.Add("meals " + (int)facts.meals + "/8");
                    return Need("Farming", missing);
                case AgeId.Farming:
                    if (facts.year < 18) missing.Add("year " + facts.year + "/18");
                    if (facts.fields < 2) missing.Add("fields " + facts.fields + "/2");
                    if (facts.houses < 1) missing.Add("a house");
                    if (facts.population < 8) missing.Add("people " + facts.population + "/8");
                    return Need("Metal and towns", missing);
                case AgeId.MetalTowns:
                    if (facts.year < 26) missing.Add("year " + facts.year + "/26");
                    if (!facts.smithy) missing.Add("a smithy");
                    if (facts.metalTools < 1) missing.Add("a hammer");
                    if (facts.population < 10) missing.Add("people " + facts.population + "/10");
                    if (facts.faith < 25f) missing.Add("faith " + (int)facts.faith + "/25");
                    return Need("Cities and empires", missing);
                case AgeId.Cities:
                    if (facts.year < 38) missing.Add("year " + facts.year + "/38");
                    if (!facts.hall) missing.Add("a hall");
                    if (!facts.temple) missing.Add("a temple");
                    if (facts.population < 12) missing.Add("people " + facts.population + "/12");
                    if (facts.faith < 30f) missing.Add("faith " + (int)facts.faith + "/30");
                    return Need("Roads and letters", missing);
                default:
                    if (facts.year < 52) missing.Add("year " + facts.year + "/52");
                    if (!facts.road) missing.Add("an open road");
                    if (!facts.letters) missing.Add("a house of letters");
                    if (facts.knowledge < 8f) missing.Add("learning " + (int)facts.knowledge + "/8");
                    if (facts.settlements < 2) missing.Add("two holds");
                    return Need("Mills", missing);
            }
        }

        static string Need(string next, List<string> missing)
        {
            if (missing.Count == 0) return next + " can begin.";
            return next + " still needs " + string.Join(", ", missing) + ".";
        }
    }
}
