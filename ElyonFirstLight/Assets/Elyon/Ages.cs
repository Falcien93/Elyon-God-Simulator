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
        Industry = 7,
        ElectricLight = 8,
        Present = 9,
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
        SetEngine,
        BankEngine,
        KindleLamps,
        DarkenLamps,
        BlessPresent,
        KeepCommons,
        BlessPact,
        WithholdPact,
        StopRaid,
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
        public bool engine;
        public bool lights;
        public float drive;
        public float power;
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
                case AgeId.Mills: return "Mills";
                case AgeId.Industry: return "Industry and engines";
                case AgeId.ElectricLight: return "Electricity and cities of light";
                default: return "The present";
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
                case AgeId.Mills:
                    return "A mill multiplies the harvest. The same families keep house.";
                case AgeId.Industry:
                    return "An engine burns wood and ore-work into drive. Fields turn faster, and someone keeps the engine.";
                case AgeId.ElectricLight:
                    return "Drive becomes power. Lamps are strung over the city, and the night is no longer only the fire.";
                default:
                    return "The same houses keep a press and a commons. Lamps, the mill, and the engine still run.";
            }
        }

        public static string Voice(AgeId age)
        {
            switch (age)
            {
                case AgeId.FirstFamily:
                    return "Speak simply of the fire, the fruit, and the two of you. You do not know fields, mills, or lamps.";
                case AgeId.Camps:
                    return "Speak of the camp, the hunt, the lean-to, and the night beyond the fire.";
                case AgeId.Farming:
                    return "Speak of the field, the rain, the hoe, and the house.";
                case AgeId.MetalTowns:
                    return "Speak of ore, the hammer, the smithy, and the ridge.";
                case AgeId.Cities:
                    return "Speak of the hall, the temple, the law, and the other hold.";
                case AgeId.RoadsAndLetters:
                    return "Speak of the road, the letters, and what was taught.";
                case AgeId.Mills:
                    return "Speak of the mill, the grain, and the turning stone.";
                case AgeId.Industry:
                    return "Speak of the engine, the wood it drinks, the drive, and the smoke. Do not talk as a gatherer at the first fire.";
                case AgeId.ElectricLight:
                    return "Speak of the lamps, the night, and power. A dark lamp is a thing you fear.";
                default:
                    return "Speak of the press, the commons, and the lamps still burning. You remember older ages, and you live in this one.";
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
                    return "You may proclaim a law, grant a harvest, or withhold one. You may bless a pact, withhold it, or stop a raid.";
                case AgeId.RoadsAndLetters:
                    return "You may open the road and kindle a lesson.";
                case AgeId.Mills:
                    return "You may turn the mill or let it rest.";
                case AgeId.Industry:
                    return "You may set the engine or bank it. A banked engine does no work.";
                case AgeId.ElectricLight:
                    return "You may kindle the lamps or darken them. Dark lamps cost faith and raise fear.";
                default:
                    return "You may bless the present or keep a commons between the holds.";
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
                case DivineAct.RestMill: return "Let the mill rest";
                case DivineAct.SetEngine: return "Set the engine";
                case DivineAct.BankEngine: return "Bank the engine";
                case DivineAct.KindleLamps: return "Kindle the lamps";
                case DivineAct.DarkenLamps: return "Darken the lamps";
                case DivineAct.BlessPresent: return "Bless the present";
                case DivineAct.KeepCommons: return "Keep the commons";
                case DivineAct.BlessPact: return "Bless the pact";
                case DivineAct.WithholdPact: return "Withhold the pact";
                case DivineAct.StopRaid: return "Stop the raid";
                default: return "Keep the commons";
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
                case DivineAct.BlessPact:
                case DivineAct.WithholdPact:
                case DivineAct.StopRaid:
                    return age >= AgeId.Cities;
                case DivineAct.OpenRoad:
                case DivineAct.KindleLesson:
                    return age >= AgeId.RoadsAndLetters;
                case DivineAct.TurnMill:
                case DivineAct.RestMill:
                    return age >= AgeId.Mills;
                case DivineAct.SetEngine:
                case DivineAct.BankEngine:
                    return age >= AgeId.Industry;
                case DivineAct.KindleLamps:
                case DivineAct.DarkenLamps:
                    return age >= AgeId.ElectricLight;
                case DivineAct.BlessPresent:
                case DivineAct.KeepCommons:
                    return age >= AgeId.Present;
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
                case AgeId.Mills:
                    return facts.year >= 64
                        && facts.mill
                        && facts.engine
                        && facts.knowledge >= 12f;
                case AgeId.Industry:
                    return facts.year >= 78
                        && facts.engine
                        && facts.drive >= 6f
                        && facts.knowledge >= 16f;
                case AgeId.ElectricLight:
                    return facts.year >= 92
                        && facts.lights
                        && facts.power >= 8f
                        && facts.faith >= 20f;
                default:
                    return false;
            }
        }

        public static string StillNeeded(AgeId age, AgeFacts facts)
        {
            if (age == AgeId.Present)
            {
                return "The present is the latest age. Kin, work, lamps, and the commons carry on. The years still turn.";
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
                case AgeId.RoadsAndLetters:
                    if (facts.year < 52) missing.Add("year " + facts.year + "/52");
                    if (!facts.road) missing.Add("an open road");
                    if (!facts.letters) missing.Add("a house of letters");
                    if (facts.knowledge < 8f) missing.Add("learning " + (int)facts.knowledge + "/8");
                    if (facts.settlements < 2) missing.Add("two holds");
                    return Need("Mills", missing);
                case AgeId.Mills:
                    if (facts.year < 64) missing.Add("year " + facts.year + "/64");
                    if (!facts.mill) missing.Add("a mill");
                    if (!facts.engine) missing.Add("an engine house");
                    if (facts.knowledge < 12f) missing.Add("learning " + (int)facts.knowledge + "/12");
                    return Need("Industry and engines", missing);
                case AgeId.Industry:
                    if (facts.year < 78) missing.Add("year " + facts.year + "/78");
                    if (!facts.engine) missing.Add("an engine house");
                    if (facts.drive < 6f) missing.Add("drive " + (int)facts.drive + "/6");
                    if (facts.knowledge < 16f) missing.Add("learning " + (int)facts.knowledge + "/16");
                    return Need("Electricity and cities of light", missing);
                default:
                    if (facts.year < 92) missing.Add("year " + facts.year + "/92");
                    if (!facts.lights) missing.Add("lamps over the city");
                    if (facts.power < 8f) missing.Add("power " + (int)facts.power + "/8");
                    if (facts.faith < 20f) missing.Add("faith " + (int)facts.faith + "/20");
                    return Need("The present", missing);
            }
        }

        static string Need(string next, List<string> missing)
        {
            if (missing.Count == 0) return next + " can begin.";
            return next + " still needs " + string.Join(", ", missing) + ".";
        }
    }
}
