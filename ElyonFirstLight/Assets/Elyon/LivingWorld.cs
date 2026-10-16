using System;
using System.Collections.Generic;
using System.IO;
using UnityEngine;
using UnityEngine.Rendering.HighDefinition;

namespace Elyon
{
    /// <summary>
    /// One population, carried by needs, kin, work, food, shelter, tools, and belief.
    /// Ages change when those facts are true. They are not a menu.
    /// </summary>
    public class LivingWorld : MonoBehaviour
    {
        public const int PopulationCap = 18;
        public const string RecordName = "elyon-first-light.json";

        static readonly string[] Names =
        {
            "Miriam", "Lior", "Hannah", "Noam", "Ruth", "Amos", "Leah", "Jonah",
            "Caleb", "Dinah", "Eli", "Naomi", "Tamar", "Oren", "Yael", "Boaz",
            "Tova", "Itai", "Serah", "Hanan",
        };

        static readonly string[] HerdNames =
        {
            "Carmel", "Sharon", "Gilead", "Bashan", "Nebo", "Hermon",
        };

        static readonly string[] FishNames =
        {
            "Kinneret", "Kishon", "Arnon", "Yarkon", "Zered", "Jabbok",
        };

        readonly List<Person> people = new List<Person>();
        readonly List<Settlement> settlements = new List<Settlement>();
        readonly List<string> log = new List<string>();
        readonly List<string> ageBook = new List<string>();
        readonly List<string> eventBook = new List<string>();
        readonly List<string> recentBook = new List<string>();

        GardenWorld garden;
        GardenDirector director;
        Transform built;
        AgeId age = AgeId.FirstFamily;
        int year = 1;
        int childrenBorn;
        int nextId = 3;
        int nameCursor;
        int jobStamp = -1;
        float knowledge;
        bool roadOpen;
        bool charter;
        bool pact;
        bool pactWithheld;
        bool raidStopped;
        string dealLine = "";
        string bornLine = "";
        string lostLine = "";
        string gardenLine = "Adam and Eve woke at the garden fire.";
        string pactLine = "";
        string raidLine = "";
        string woundLine = "";
        string nameDraft = "";
        float followTimer;
        bool visualsDirty = true;
        string loadedTimeNote = "";

        int shownTents;
        int shownHouses;
        int shownFields;
        bool shownSmithy;
        bool shownHall;
        bool shownTemple;
        bool shownPalisade;
        bool shownLetters;
        bool shownMill;
        bool shownEngine;
        bool shownLamps;
        bool shownPress;
        bool shownRoad;
        bool shownEastFire;
        bool shownFarFire;
        readonly List<string> raisedMarks = new List<string>();

        Material woodMat;
        Material clothMat;
        Material grainMat;
        Material stoneMat;
        Material roofMat;

        public int Year => year;
        public AgeId Age => age;
        public string AgeName => Ages.Name(age);
        public string LastEvent => log.Count == 0 ? "" : log[log.Count - 1];
        public IReadOnlyList<Person> People => people;

        public void Begin(GardenWorld world, Transform root, GardenDirector owner)
        {
            garden = world;
            director = owner;
            built = new GameObject("Raised").transform;
            built.SetParent(root, false);
            CacheMaterials();

            var eden = new Settlement
            {
                id = "eden",
                placeName = "the fire",
                hearthX = world.Fire.x,
                hearthZ = world.Fire.z,
            };
            settlements.Add(eden);
            RegisterFounders(eden);

            if (!TryLoad())
            {
                Note("Adam and Eve are awake at the fire.");
                RememberAge();
                AssignJobs();
                RefreshKin();
            }

            if (director != null) director.dayNumber = year;
        }

        public void Tick(float delta, float timeOfDay, bool newDay)
        {
            foreach (var person in people)
            {
                if (!person.alive) continue;
                person.scarce = HomeOf(person).Meals < 1f;
            }

            AssignJobs();
            UpdateFollowers(delta);
            for (int i = 0; i < people.Count; i++)
            {
                if (people[i].alive) people[i].Tick(timeOfDay, delta);
            }

            float span = director != null && director.daySeconds > 1f ? director.daySeconds : 180f;
            ApplyLabor(delta / span, true);
            if (newDay) CloseYear(false);
            if (visualsDirty) EnsureVisuals();
        }

        public bool TryServeMeal(Person person)
        {
            Settlement home = HomeOf(person);
            return home != null && home.TakeMeal(1f);
        }

        public bool TryServeWater(Person person)
        {
            Settlement home = HomeOf(person);
            return home != null && home.TakeWater(1f);
        }

        public bool HasBed(Person person)
        {
            if (person == null || !person.alive) return false;
            if (age == AgeId.FirstFamily) return true;
            Settlement home = HomeOf(person);
            if (home == null) return false;
            int beds = home.tents * 2 + home.houses * 3 + (home.hall ? 4 : 0);
            if (beds <= 0) return false;
            int before = 0;
            int score = BedScore(person);
            foreach (var other in people)
            {
                if (!other.alive || other == person || other.settlementId != home.id) continue;
                int otherScore = BedScore(other);
                if (otherScore > score || (otherScore == score && string.CompareOrdinal(other.personId, person.personId) < 0))
                {
                    before++;
                }
            }

            return before < beds;
        }

        public void Act(DivineAct act)
        {
            if (!Ages.Allows(age, act)) return;
            Settlement home = TargetSettlement();
            if (home == null)
            {
                Note("There is no hearth.");
                return;
            }
            Person person = TargetPerson();
            switch (act)
            {
                case DivineAct.TurnYears:
                    ApplyLabor(1f, false);
                    CloseYear(true);
                    return;
                case DivineAct.Bless:
                    if (person == null) { Note("No one is here to bless."); break; }
                    person.ApplyTrust(6);
                    person.favor += 6;
                    person.blessedHouse = true;
                    Person blessedWith = Find(person.partnerId);
                    if (blessedWith != null && blessedWith.alive)
                    {
                        blessedWith.favor += 4;
                        blessedWith.blessedHouse = true;
                    }
                    home.faith = Mathf.Clamp(home.faith + 2f, 0f, 100f);
                    Note(person.personName + " is blessed. Their house may bear this year, and they will not be the one to leave.");
                    break;
                case DivineAct.Heal:
                    if (person == null) { Note("No one is here to heal."); break; }
                    person.body.fever = 0f;
                    person.body.bleeding = 0f;
                    home.faith = Mathf.Clamp(home.faith + 2f, 0f, 100f);
                    Note(person.personName + " is healed.");
                    break;
                case DivineAct.SetFruit:
                    float mealsBefore = home.Meals;
                    home.fruit += 6f;
                    if (person != null) person.body.hunger = Mathf.Max(0f, person.body.hunger - 10f);
                    Note(mealsBefore < 8f && home.Meals >= 8f
                        ? "Fruit is set at " + home.placeName + ". The stores can spare a birth."
                        : "Fruit is set at " + home.placeName + ".");
                    break;
                case DivineAct.Calm:
                    if (person == null) { Note("No one is here to calm."); break; }
                    person.body.fear = Mathf.Max(0f, person.body.fear - 24f);
                    home.faith = Mathf.Clamp(home.faith + 1f, 0f, 100f);
                    Note(person.personName + " grows quieter.");
                    break;
                case DivineAct.SendGame:
                    home.meat += 6f;
                    Note("Game is sent to " + home.placeName + ".");
                    break;
                case DivineAct.KeepHerd:
                    KeepTheHerd(home);
                    break;
                case DivineAct.RaiseShelter:
                    if (home.wood < 4f)
                    {
                        Note("A shelter needs 4 wood. They have " + (int)home.wood + ".");
                        break;
                    }
                    home.wood -= 4f;
                    home.tents++;
                    visualsDirty = true;
                    Note("You raise a lean-to at " + home.placeName + ".");
                    break;
                case DivineAct.SendRain:
                    SendTheRain(home);
                    break;
                case DivineAct.SendDrought:
                    DryTheGround(home);
                    break;
                case DivineAct.SendFlood:
                    SendTheFlood(home);
                    break;
                case DivineAct.BlessField:
                    if (home.fields < 1)
                    {
                        Note("There is no field to bless.");
                        break;
                    }
                    home.grain += 5f + home.fields;
                    home.faith = Mathf.Clamp(home.faith + 2f, 0f, 100f);
                    Note("The field is blessed. Grain comes in.");
                    break;
                case DivineAct.GiftOre:
                    home.ore += 3f;
                    Note("Ore is set down for the smiths.");
                    break;
                case DivineAct.Mend:
                    if (!home.smithy)
                    {
                        Note("The smithy is not raised, so no one can be mended there.");
                        break;
                    }
                    if (person == null) { Note("No one is here to mend."); break; }
                    person.body.bleeding = 0f;
                    person.body.fatigue = Mathf.Max(0f, person.body.fatigue - 15f);
                    Note(person.personName + " is mended at the smithy.");
                    break;
                case DivineAct.Proclaim:
                    if (!home.hall)
                    {
                        Note("They have no hall to hear a law.");
                        break;
                    }
                    home.faith = Mathf.Clamp(home.faith + 6f, 0f, 100f);
                    home.lawKept = true;
                    CalmMembers(home, 10f);
                    TouchWork();
                    dealLine = "A commandment is kept in " + home.placeName + ". They work, and they are less afraid.";
                    Note(dealLine);
                    break;
                case DivineAct.GrantHarvest:
                    home.grain += 8f;
                    home.faith = Mathf.Clamp(home.faith + 5f, 0f, 100f);
                    Note("The harvest is granted to " + home.placeName + ".");
                    break;
                case DivineAct.WithholdHarvest:
                    home.grain *= 0.5f;
                    home.faith = Mathf.Max(0f, home.faith - 8f);
                    home.dread = true;
                    MarkDarkYear(home);
                    foreach (var member in people)
                    {
                        if (member.alive && member.settlementId == home.id)
                        {
                            member.body.fear = Mathf.Min(100f, member.body.fear + 6f);
                            member.body.grief = Mathf.Min(100f, member.body.grief + 4f);
                        }
                    }
                    Note("The harvest is withheld. Faith falls. Unless a house was blessed, no child is born here, and someone may leave.");
                    break;
                case DivineAct.OpenRoad:
                    if (roadOpen)
                    {
                        Note("The road is already open.");
                        break;
                    }
                    if (home.wood < 6f)
                    {
                        Note("The road needs 6 wood. They have " + (int)home.wood + ".");
                        break;
                    }
                    home.wood -= 6f;
                    roadOpen = true;
                    visualsDirty = true;
                    Note("The road opens between the holds.");
                    break;
                case DivineAct.KindleLesson:
                    knowledge += 4f;
                    home.faith = Mathf.Clamp(home.faith + 1f, 0f, 100f);
                    Note("A lesson is kindled. Learning is now " + (int)knowledge + ".");
                    break;
                case DivineAct.TurnMill:
                    if (!AnyMill())
                    {
                        Note("There is no mill to turn.");
                        break;
                    }
                    SetMills(true);
                    TouchWork();
                    Note("The mill turns. Harvest labor grows.");
                    break;
                case DivineAct.RestMill:
                    if (!AnyMill())
                    {
                        Note("There is no mill to rest.");
                        break;
                    }
                    SetMills(false);
                    foreach (var member in people)
                    {
                        if (member.alive && member.labor == Labor.Farm)
                        {
                            member.body.fatigue = Mathf.Max(0f, member.body.fatigue - 8f);
                        }
                    }
                    Note("The mill rests. The farmers breathe.");
                    TouchWork();
                    break;
                case DivineAct.SetEngine:
                    if (!home.engine)
                    {
                        Note("There is no engine house to set.");
                        break;
                    }
                    if (home.wood < 4f)
                    {
                        Note("Setting the engine needs 4 wood. They have " + (int)home.wood + ".");
                        break;
                    }
                    home.wood -= 4f;
                    home.engineOn = true;
                    home.drive += 2f;
                    visualsDirty = true;
                    Note("The engine is set. It drinks wood and makes drive.");
                    TouchWork();
                    break;
                case DivineAct.BankEngine:
                    if (!home.engine)
                    {
                        Note("There is no engine to bank.");
                        break;
                    }
                    if (!home.engineOn)
                    {
                        Note("The engine is already banked.");
                        break;
                    }
                    home.engineOn = false;
                    Note("The engine is banked. Drive stops, the fields lose its help, and no other hold can copy it while it is cold.");
                    TouchWork();
                    break;
                case DivineAct.KindleLamps:
                    if (home.power < 4f)
                    {
                        Note("The lamps need 4 power. The city has " + (int)home.power + ".");
                        break;
                    }
                    home.power -= 4f;
                    home.lights = true;
                    visualsDirty = true;
                    Note("Lamps kindle over " + home.placeName + ".");
                    TouchWork();
                    break;
                case DivineAct.DarkenLamps:
                    if (!home.lights)
                    {
                        Note("The lamps are already dark.");
                        break;
                    }
                    home.lights = false;
                    home.dread = true;
                    MarkDarkYear(home);
                    home.faith = Mathf.Max(0f, home.faith - 3f);
                    foreach (var member in people)
                    {
                        if (member.alive && member.settlementId == home.id)
                        {
                            member.body.fear = Mathf.Min(100f, member.body.fear + 6f);
                            member.body.grief = Mathf.Min(100f, member.body.grief + 4f);
                        }
                    }
                    Note("The lamps go dark. Faith falls. Unless a house was blessed, no child is born here, and someone may leave.");
                    TouchWork();
                    break;
                case DivineAct.BlessPresent:
                    charter = true;
                    home.faith = Mathf.Clamp(home.faith + 3f, 0f, 100f);
                    foreach (var member in people)
                    {
                        if (!member.alive) continue;
                        member.body.fear = Mathf.Max(0f, member.body.fear - 8f);
                        member.ApplyTrust(2);
                    }
                    foreach (var hold in settlements) hold.dread = false;
                    Note("The present is blessed. Fear eases, and the west quarter may be planted.");
                    break;
                case DivineAct.KeepCommons:
                    Settlement other = OtherHold(home);
                    if (other == null)
                    {
                        Note("There is one hearth. The commons is already the whole house.");
                        break;
                    }
                    Settlement giver = home.Meals >= other.Meals ? home : other;
                    Settlement taker = giver == home ? other : home;
                    float takerBefore = taker.Meals;
                    float giverBefore = giver.Meals;
                    ShareMeals(home, other, 0.1f);
                    string moved = "A tenth of the richer store moves to the poorer hold.";
                    if (takerBefore < 8f && taker.Meals >= 8f) moved += " " + taker.placeName + " can spare a birth.";
                    if (giverBefore >= 8f && giver.Meals < 8f) moved += " " + giver.placeName + " can no longer spare one.";
                    Note(moved);
                    break;
                case DivineAct.BlessPact:
                    BlessPact(home);
                    break;
                case DivineAct.WithholdPact:
                    WithholdPact(home);
                    break;
                case DivineAct.StopRaid:
                    StopTheRaid(home);
                    break;
            }

            RefreshKin();
            Save();
        }

        void CloseYear(bool fromGod)
        {
            ConsumeYear();
            TendWild();
            AgeBodies();
            Mishaps();
            Deaths();
            Strife();
            Departures();
            FounderHolds();
            Newcomer();
            Births();
            if (Ages.ReadyForNext(age, Facts())) Advance();
            Craft();
            BuildPlaces();
            if (Ages.ReadyForNext(age, Facts())) Advance();
            Trade();
            KeepLaw();
            KeepRite();
            foreach (var person in people) person.arrived = false;
            year++;
            if (director != null) director.dayNumber = year;
            foreach (var person in people) person.spokenWork = false;
            jobStamp = -1;
            AssignJobs();
            RefreshKin();
            visualsDirty = true;
            foreach (var hold in settlements)
            {
                hold.dread = false;
                hold.raided = false;
                hold.willRaid = false;
                hold.sky = Sky.Clear;
            }
            pactWithheld = false;
            foreach (var person in people)
            {
                person.blessedHouse = false;
                person.favor = Mathf.Max(0, person.favor - 2);
            }
            if (fromGod && (log.Count == 0 || !log[log.Count - 1].StartsWith("Year " + (year - 1), StringComparison.Ordinal)))
            {
                Note("Year " + (year - 1) + " turns. " + Ages.Name(age) + ". " + SeasonName() + " opens.");
                Chronicle(LastEvent);
                string book = ChronicleText();
                foreach (var person in people) person.chronicle = book;
            }
            Save();
        }

        void ConsumeYear()
        {
            foreach (var settlement in settlements)
            {
                float catchment = 4f + settlement.tents * 1.5f + settlement.houses * 3f + (settlement.hall ? 4f : 0f);
                settlement.water = Mathf.Min(48f, settlement.water + catchment);
            }

            for (int i = 0; i < people.Count; i++)
            {
                Person person = people[i];
                if (!person.alive) continue;
                Settlement home = HomeOf(person);
                float meal = person.body.age < 14f ? 0.55f : 0.8f;
                if (home.TakeMeal(meal))
                {
                    person.body.hunger = Mathf.Max(0f, person.body.hunger - 8f);
                    person.body.grief = Mathf.Max(0f, person.body.grief - 3f);
                    person.body.fear = Mathf.Max(0f, person.body.fear - 2f);
                }
                else
                {
                    person.body.hunger = Mathf.Min(100f, person.body.hunger + 14f);
                    home.faith = Mathf.Max(0f, home.faith - 1f);
                }

                if (home.TakeWater(0.5f)) person.body.thirst = Mathf.Max(0f, person.body.thirst - 8f);
                else person.body.thirst = Mathf.Min(100f, person.body.thirst + 12f);

                bool bed = HasBed(person);
                if (bed) person.body.fatigue = Mathf.Max(0f, person.body.fatigue - 12f);
                if (SeasonNow() == Season.Winter && !home.TakeMeal(person.body.age < 14f ? 0.15f : 0.25f))
                {
                    person.body.hunger = Mathf.Min(100f, person.body.hunger + 4f);
                }
                if (home.lights && bed) person.body.fatigue = Mathf.Max(0f, person.body.fatigue - 6f);
                if (home.lights) person.body.fear = Mathf.Max(0f, person.body.fear - 3f);
                if (!bed && age != AgeId.FirstFamily) person.body.fever = Mathf.Min(100f, person.body.fever + 8f);
                else if (person.body.hunger < 75f) person.body.fever = Mathf.Max(0f, person.body.fever - 10f);
            }
        }

        void AgeBodies()
        {
            for (int i = 0; i < people.Count; i++)
            {
                if (!people[i].alive) continue;
                people[i].ApplyAge(people[i].body.age + 1f);
            }
        }

        void Mishaps()
        {
            foreach (var person in people)
            {
                if (!person.alive) continue;
                bool risky = person.labor == Labor.Hunt || person.labor == Labor.Smith;
                if (risky && person.body.fatigue > 68f && person.body.bleeding < 8f)
                {
                    person.body.bleeding += 14f;
                    Note(person.personName + " is cut, and bleeding.");
                }
            }
        }

        void Deaths()
        {
            int aliveAdults = 0;
            foreach (var person in people)
            {
                if (person.alive && person.body.age >= 14f) aliveAdults++;
            }

            var dying = new List<Person>();
            foreach (var person in people)
            {
                if (!person.alive) continue;
                bool old = person.body.age >= 76f;
                bool starved = person.body.hunger >= 98f && person.body.Strength < 15f && aliveAdults > 2;
                bool bled = person.body.bleeding >= 90f;
                if (old || starved || bled) dying.Add(person);
            }

            foreach (var person in dying)
            {
                Settlement hearth = HomeOf(person);
                string place = hearth != null ? hearth.placeName : "the valley";
                person.Die();
                Grieve(person);
                Note(person.personName + " dies. The house grieves.");
                KeepBook(ref lostLine, person.personName + " is lost from " + place + ".");
                KeepBook(ref woundLine, person.personName + " dies in " + Ages.Name(age) + ", and the line grieves.");
                Chronicle(person.personName + " dies in " + Ages.Name(age) + ", and the line grieves.");
            }
        }

        void Grieve(Person dead)
        {
            foreach (var person in people)
            {
                if (!person.alive || person == dead) continue;
                bool kin = person.personId == dead.partnerId
                    || person.personId == dead.motherId
                    || person.personId == dead.fatherId
                    || person.motherId == dead.personId
                    || person.fatherId == dead.personId
                    || person.partnerId == dead.personId;
                if (!kin) continue;
                person.body.grief = Mathf.Min(100f, person.body.grief + 22f);
                HomeOf(person).faith = Mathf.Max(0f, HomeOf(person).faith - 2f);
                person.Remember(dead.personName + " is gone.");
            }
        }

        void Newcomer()
        {
            if (AliveCount() >= PopulationCap) return;
            Person lone = null;
            foreach (var person in people)
            {
                if (!person.alive || person.arrived || person.body.age < 18f) continue;
                Person partner = Find(person.partnerId);
                if (partner != null && partner.alive) continue;
                if (lone == null || person.body.age > lone.body.age) lone = person;
            }

            if (lone == null) return;
            Settlement home = HomeOf(lone);
            if (home.Meals < 8f) return;
            string name = NextName();
            var spot = Dry(home.Hearth + new Vector3(2.4f, 0f, 1.6f));
            Person arrived = Spawn(name, !lone.eveShape, 22f, spot, home);
            arrived.arrived = true;
            arrived.partnerId = lone.personId;
            lone.partnerId = arrived.personId;
            arrived.bornInto = Ages.Name(age);
            Note(name + " comes to " + home.placeName + " and keeps house with " + lone.personName + ".");
            lone.Remember(name + " keeps house with me.");
            arrived.Remember("I keep house with " + lone.personName + ".");
        }

        void Births()
        {
            if (AliveCount() >= PopulationCap) return;
            foreach (var home in settlements)
            {
                if (home.abandoned || Members(home) <= 0) continue;
                Person one;
                Person two;
                if (!PickParents(home, out one, out two))
                {
                    if (home.dread) Note("No child is born at " + home.placeName + ". The year is dark.");
                    continue;
                }
                if (home.dread && !one.blessedHouse && !two.blessedHouse)
                {
                    Note("No child is born at " + home.placeName + ". The dark holds, and no house was blessed.");
                    continue;
                }
                bool houseBlessed = one.blessedHouse || two.blessedHouse;
                if (SeasonNow() == Season.Winter && !houseBlessed)
                {
                    Note("No child is born at " + home.placeName + ". The cold holds, and no house was blessed.");
                    continue;
                }
                if (home.sky == Sky.Drought && !houseBlessed)
                {
                    Note("No child is born at " + home.placeName + ". The ground is dry, and no house was blessed.");
                    continue;
                }
                if (home.sky == Sky.Flood && !houseBlessed)
                {
                    Note("No child is born at " + home.placeName + ". The flood is over the ground, and no house was blessed.");
                    continue;
                }
                if (home.Meals < 8f || !home.TakeMeal(2f))
                {
                    Note("No child is born at " + home.placeName + ". The stores cannot spare a meal.");
                    continue;
                }
                string name = NextName();
                bool eveShape = childrenBorn % 2 == 0;
                Person child = Spawn(name, eveShape, 0f, Dry(home.Hearth), home);
                child.motherId = one.eveShape ? one.personId : two.personId;
                child.fatherId = one.eveShape ? two.personId : one.personId;
                if (child.motherId == child.fatherId)
                {
                    child.motherId = one.personId;
                    child.fatherId = two.personId;
                }
                child.bornInto = Ages.Name(age);
                childrenBorn++;
                one.body.child = true;
                two.body.child = true;
                string line = name + " is born into the house of " + one.personName + " and " + two.personName + " in " + child.bornInto + ".";
                Note(line);
                Chronicle(line);
                KeepBook(ref bornLine, line);
                one.Remember(line);
                two.Remember(line);
                if (AliveCount() >= PopulationCap) return;
            }
        }

        bool PickParents(Settlement home, out Person one, out Person two)
        {
            one = null;
            two = null;
            int best = int.MinValue;
            foreach (var person in people)
            {
                if (!CanBear(person, home)) continue;
                Person partner = Find(person.partnerId);
                if (!CanBear(partner, home)) continue;
                if (string.CompareOrdinal(person.personId, partner.personId) > 0) continue;
                if (HasInfant(person, partner)) continue;
                int score = person.favor + partner.favor;
                if (person.blessedHouse || partner.blessedHouse) score += 100;
                if (one != null && score < best) continue;
                if (one != null && score == best && string.CompareOrdinal(person.personId, one.personId) > 0) continue;
                best = score;
                one = person;
                two = partner;
            }
            return one != null && two != null;
        }

        bool CanBear(Person person, Settlement home)
        {
            if (person == null || !person.alive || person.arrived) return false;
            if (person.settlementId != home.id) return false;
            if (person.body.age < 18f || person.body.age > 50f) return false;
            if (person.body.Strength < 35f) return false;
            return true;
        }

        void Departures()
        {
            foreach (var hold in settlements)
            {
                if (hold.abandoned || Members(hold) <= 0) continue;
                if (hold.pactStay && !hold.dread && !hold.raided) continue;
                float grief = MeanGrief(hold);
                bool pressure = hold.dread || hold.faith < 12f || (grief >= 50f && hold.Meals < 6f) || hold.raided;
                if (!pressure) continue;
                SendAway(hold, "I left " + hold.placeName + ".");
            }
        }

        bool SendAway(Settlement hold, string memory)
        {
            Person leaver = PickLeaver(hold);
            if (leaver == null) return false;
            Settlement dest = BestHold(hold);
            if (dest == null)
            {
                Note(leaver.personName + " wants to leave " + hold.placeName + ", and there is no other hearth.");
                return false;
            }
            SetHome(leaver, dest, true);
            leaver.Remember(memory);
            Note(leaver.personName + " leaves " + hold.placeName + " for " + dest.placeName + ".");
            return true;
        }

        Person PickLeaver(Settlement hold)
        {
            Person worst = null;
            foreach (var person in people)
            {
                if (!person.alive || person.settlementId != hold.id) continue;
                if (person.body.age < 18f) continue;
                if (person.personId == "adam" || person.personId == "eve") continue;
                if (person.blessedHouse || person.favor >= 4) continue;
                if (worst == null || person.trust < worst.trust) worst = person;
            }
            return worst;
        }

        void FounderHolds()
        {
            int living = LivingHolds();
            foreach (var hold in settlements)
            {
                if (hold.abandoned || Members(hold) <= 0) continue;
                float grief = MeanGrief(hold);
                bool hunger = hold.Meals < 2f && hold.faith < 14f;
                bool sorrow = grief >= 58f && hold.faith < 18f && hold.Meals < 8f;
                if (!hunger && !sorrow) continue;
                if (living <= 1)
                {
                    Note(hold.placeName + " is failing, and it is the last hearth.");
                    continue;
                }
                Settlement dest = BestHold(hold);
                if (dest == null)
                {
                    Note(hold.placeName + " is failing, and no hearth can take the people.");
                    continue;
                }
                var movers = new List<Person>();
                foreach (var person in people)
                {
                    if (person.alive && person.settlementId == hold.id) movers.Add(person);
                }
                foreach (var person in movers)
                {
                    SetHome(person, dest, true);
                    person.Remember(hold.placeName + " foundered.");
                }
                dest.fruit += hold.fruit;
                dest.meat += hold.meat;
                dest.grain += hold.grain;
                dest.wood += hold.wood * 0.5f;
                dest.ore += hold.ore;
                dest.fish += hold.fish;
                dest.herd = Mathf.Min(6, dest.herd + hold.herd);
                if (dest.herd > 0 && string.IsNullOrEmpty(dest.herdName) && !string.IsNullOrEmpty(hold.herdName))
                {
                    dest.herdName = hold.herdName;
                    hold.herdName = "";
                }
                if (dest.fish >= 1f && string.IsNullOrEmpty(dest.fishName) && !string.IsNullOrEmpty(hold.fishName))
                {
                    dest.fishName = hold.fishName;
                    hold.fishName = "";
                }
                hold.fruit = 0f;
                hold.meat = 0f;
                hold.grain = 0f;
                hold.wood *= 0.5f;
                hold.ore = 0f;
                hold.fish = 0f;
                hold.herd = 0;
                hold.sky = Sky.Clear;
                hold.abandoned = true;
                hold.engineOn = false;
                hold.millOn = false;
                hold.lights = false;
                living--;
                string why = hunger ? "the food and the faith are gone" : "grief and thin faith empty it";
                Note(hold.placeName + " founders (" + why + "). The people go to " + dest.placeName + ".");
            }
        }

        float MeanGrief(Settlement hold)
        {
            float sum = 0f;
            int count = 0;
            foreach (var person in people)
            {
                if (!person.alive || person.settlementId != hold.id) continue;
                sum += person.body.grief;
                count++;
            }
            return count == 0 ? 0f : sum / count;
        }

        int LivingHolds()
        {
            int count = 0;
            foreach (var hold in settlements)
            {
                if (!hold.abandoned && Members(hold) > 0) count++;
            }
            return count;
        }

        Settlement BestHold(Settlement except)
        {
            Settlement best = null;
            foreach (var hold in settlements)
            {
                if (hold == except || hold.abandoned) continue;
                if (best == null || hold.Meals > best.Meals) best = hold;
            }
            return best;
        }

        void Advance()
        {
            age = (AgeId)((int)age + 1);
            switch (age)
            {
                case AgeId.Camps:
                    Settlement east = EnsureEast();
                    RelocateAll(east);
                    Note("The family leaves the garden fire and raises a camp on the eastern meadow.");
                    gardenLine = "Adam and Eve woke at the garden fire. The family left the garden fire and raised a camp on the eastern meadow.";
                    break;
                case AgeId.Farming:
                    Note("They break ground. Fields will feed the houses.");
                    break;
                case AgeId.MetalTowns:
                    Settlement town = MainHome();
                    if (town == null) break;
                    town.ore += 3f;
                    town.placeName = "the town by the ridge";
                    Note("Ore shows in the ridge. The camp becomes a town.");
                    break;
                case AgeId.Cities:
                    Settlement city = MainHome();
                    if (city == null) break;
                    city.placeName = "the city";
                    Note("The town is a city. A second hold can be planted.");
                    break;
                case AgeId.RoadsAndLetters:
                    Note("The holds look toward each other. Someone must teach, and a road must be kept.");
                    break;
                case AgeId.Mills:
                    Note("They can raise a mill. The harvest can be multiplied.");
                    break;
                case AgeId.Industry:
                    Note("An engine house can burn wood into drive. Someone must keep it.");
                    break;
                case AgeId.ElectricLight:
                    Note("Drive can become power, and lamps can be strung over the city.");
                    break;
                case AgeId.Present:
                    Note("The present keeps the press, the lamps, and the commons.");
                    break;
            }

            string lived = Ages.Living(age);
            RememberAge();
            foreach (var person in people)
            {
                if (person.alive) person.Remember(lived);
            }

            jobStamp = -1;
        }

        void RaiseShelter(Settlement home)
        {
            if (age >= AgeId.Camps)
            {
                int want = Mathf.Clamp(Mathf.Max(1, Members(home) / 2), 1, 6);
                while (home.tents < want && home.wood >= 4f)
                {
                    home.wood -= 4f;
                    home.tents++;
                    Note("A lean-to goes up at " + home.placeName + ".");
                }
            }

            if (age >= AgeId.Farming)
            {
                while (home.fields < 3 && home.wood >= 2f)
                {
                    home.wood -= 2f;
                    home.fields++;
                    Note("They mark a field at " + home.placeName + ".");
                }

                int houses = Mathf.Clamp(Mathf.Max(1, Members(home) / 3), 1, 4);
                while (home.houses < houses && home.wood >= 6f)
                {
                    home.wood -= 6f;
                    home.houses++;
                    Note("A house stands at " + home.placeName + ".");
                }
            }
        }

        static int AxeLast(Person person)
        {
            return person.tool == ToolKind.Axe ? 1 : 0;
        }

        bool HoldHas(Person person, System.Predicate<Settlement> test)
        {
            Settlement hold = HomeOf(person);
            return hold != null && test(hold);
        }

        void Craft()
        {
            if (age >= AgeId.Farming)
            {
                Settlement home = MainHome();
                if (home == null) return;
                int hoes = CountTools(ToolKind.Hoe);
                int want = Mathf.Max(1, home.fields);
                while (hoes < want && home.wood >= 2f)
                {
                    Person farmer = FindWorker(Labor.Farm, ToolKind.Hands) ?? FindAdultWith(ToolKind.Hands);
                    if (farmer == null) break;
                    home.wood -= 2f;
                    farmer.tool = ToolKind.Hoe;
                    farmer.toolWear = 0f;
                    hoes++;
                    Note(farmer.personName + " keeps a hoe.");
                }
            }

            if (age >= AgeId.MetalTowns)
            {
                Settlement home = MainHome();
                if (home == null) return;
                int hammers = CountTools(ToolKind.Hammer);
                while (hammers < 2 && home.ore >= 2f && home.wood >= 1f)
                {
                    Person smith = FindWorker(Labor.Smith, ToolKind.Hands) ?? FindWorker(Labor.Smith, ToolKind.Hoe);
                    if (smith == null || smith.tool == ToolKind.Axe) break;
                    home.ore -= 2f;
                    home.wood -= 1f;
                    smith.tool = ToolKind.Hammer;
                    smith.toolWear = 0f;
                    home.metalTools++;
                    hammers++;
                    Note(smith.personName + " lifts a hammer.");
                }
            }
        }

        void BuildPlaces()
        {
            foreach (var place in settlements)
            {
                if (Members(place) == 0) continue;
                RaiseShelter(place);
            }

            Settlement home = MainHome();
            if (home == null) return;

            if (age >= AgeId.MetalTowns && !home.smithy && home.wood >= 5f && home.ore >= 1f)
            {
                home.wood -= 5f;
                home.ore -= 1f;
                home.smithy = true;
                Note("The smithy is lit.");
            }

            if (age >= AgeId.MetalTowns && home.smithy && !home.palisade && home.wood >= 8f)
            {
                home.wood -= 8f;
                home.palisade = true;
                Note("A palisade rings the town.");
            }

            if (age >= AgeId.Cities && !home.hall && home.wood >= 8f)
            {
                home.wood -= 8f;
                home.hall = true;
                Note("The hall is raised.");
            }

            if (age >= AgeId.Cities && home.hall && !home.temple && home.wood >= 6f && home.faith >= 25f)
            {
                home.wood -= 6f;
                home.temple = true;
                Note("A temple is raised. Belief has a house.");
            }

            if (age >= AgeId.Cities) PlantHolds(home);

            if (age >= AgeId.RoadsAndLetters && !home.letters && knowledge >= 4f && home.wood >= 5f)
            {
                home.wood -= 5f;
                home.letters = true;
                Note("A house of letters is kept.");
            }

            if (age >= AgeId.RoadsAndLetters && !roadOpen && home.letters && knowledge >= 8f && settlements.Count >= 2)
            {
                float roadCost = home.lawKept ? 4f : 6f;
                if (home.wood >= roadCost)
                {
                    home.wood -= roadCost;
                    roadOpen = true;
                    Note(home.lawKept
                        ? "The commandment keeps the road. It opens for less wood."
                        : "The people open the road.");
                }
            }

            if (age >= AgeId.Mills && !home.mill && home.wood >= 8f && home.grain >= 4f)
            {
                home.wood -= 8f;
                home.grain -= 4f;
                home.mill = true;
                home.millOn = true;
                Note("The mill is raised and set turning.");
            }

            if (age >= AgeId.Mills && home.mill && !home.engine && knowledge >= 12f && home.wood >= 10f && home.ore >= 2f)
            {
                home.wood -= 10f;
                home.ore -= 2f;
                home.engine = true;
                home.engineOn = true;
                Note("An engine house is raised beside the mill.");
            }

            if (age >= AgeId.ElectricLight && home.engine && home.engineOn && !home.dread && !home.lights && home.power >= 6f && home.wood >= 4f)
            {
                home.wood -= 4f;
                home.lights = true;
                Note("Lamps are strung over " + home.placeName + ".");
            }

            if (age >= AgeId.Present && home.letters && !home.press && home.wood >= 6f)
            {
                home.wood -= 6f;
                home.press = true;
                Note("A press is kept in the house of letters.");
            }

            RaiseSisterWorks(home);

            visualsDirty = true;
        }

        void RaiseSisterWorks(Settlement home)
        {
            if (!roadOpen || home == null) return;
            foreach (var hold in settlements)
            {
                if (hold == home || hold.abandoned || Members(hold) <= 0) continue;
                if (age >= AgeId.Mills && home.mill && home.millOn && !hold.mill && hold.wood >= 8f && hold.grain >= 4f)
                {
                    hold.wood -= 8f;
                    hold.grain -= 4f;
                    hold.mill = true;
                    hold.millOn = true;
                    Note("A mill is raised at " + hold.placeName + ".");
                }
                if (age >= AgeId.Industry && home.engine && home.engineOn && !hold.engine && hold.wood >= 8f)
                {
                    hold.wood -= 8f;
                    hold.engine = true;
                    hold.engineOn = true;
                    Note("An engine house is raised at " + hold.placeName + ".");
                }
                if (age >= AgeId.ElectricLight && home.lights && hold.engine && hold.engineOn && !hold.dread && !hold.lights && hold.power >= 6f && hold.wood >= 4f)
                {
                    hold.wood -= 4f;
                    hold.lights = true;
                    Note("Lamps are strung over " + hold.placeName + ".");
                }
            }
        }

        void PlantHolds(Settlement home)
        {
            TryPlant(home, "far", "the far hold", 38f, 74f, true, 6, 10f, 20f);
            TryPlant(home, "north", "the north hold", 118f, 168f, age >= AgeId.Mills && roadOpen, 5, 16f, 26f);
            TryPlant(home, "west", "the west quarter", 22f, 150f, age >= AgeId.ElectricLight && charter, 4, 18f, 24f);
        }

        void TryPlant(Settlement from, string id, string placeName, float x, float z, bool allowed, int minMembers, float mealNeed, float faithNeed)
        {
            if (!allowed || from == null) return;
            Settlement source = from.Meals >= mealNeed && from.faith >= faithNeed && Members(from) >= minMembers
                ? from
                : BestHold(null);
            if (source == null || source.abandoned) return;
            if (source.Meals < mealNeed || source.faith < faithNeed || Members(source) < minMembers) return;
            Person mover = PickPlanter(source);
            if (mover == null) return;
            Settlement existing = FindSettlement(id);
            if (existing != null && !existing.abandoned) return;
            if (existing != null)
            {
                if (!existing.abandoned) return;
                if (mover == null || !mover.blessedHouse) return;
                existing.abandoned = false;
                existing.millOn = existing.mill;
                existing.engineOn = existing.engine;
                float gift = source.grain * 0.12f;
                source.grain -= gift;
                existing.grain += gift;
                MoveHousehold(mover, existing);
                Note(mover.personName + " leads a house back to " + existing.placeName + ".");
                return;
            }
            var planted = new Settlement
            {
                id = id,
                placeName = placeName,
                hearthX = x,
                hearthZ = z,
                fruit = 0f,
                water = 8f,
                wood = 0f,
                faith = source.faith,
            };
            planted.grain = source.grain * 0.2f;
            source.grain -= planted.grain;
            planted.fruit = source.fruit * 0.2f;
            source.fruit -= planted.fruit;
            if (source.wood >= 6f)
            {
                source.wood -= 6f;
                planted.wood = 2f;
                planted.tents = 1;
                planted.fields = age >= AgeId.Farming ? 1 : 0;
            }
            settlements.Add(planted);
            MoveHousehold(mover, planted);
            Note(mover.personName + " plants " + placeName + " and carries a share of the food.");
            KeepBook(ref woundLine, mover.personName + " planted " + placeName + ".");
        }

        Person PickPlanter(Settlement from)
        {
            Person best = null;
            int bestScore = int.MinValue;
            foreach (var person in people)
            {
                if (!person.alive || person.settlementId != from.id) continue;
                if (person.personId == "adam" || person.personId == "eve") continue;
                if (person.body.age < 18f || string.IsNullOrEmpty(person.partnerId)) continue;
                Person partner = Find(person.partnerId);
                if (partner == null || !partner.alive || partner.settlementId != from.id) continue;
                int score = person.favor * 10 - Mathf.RoundToInt(person.body.age);
                if (person.blessedHouse) score += 50;
                if (best == null || score > bestScore)
                {
                    best = person;
                    bestScore = score;
                }
            }
            return best;
        }

        void Strife()
        {
            if (LivingHolds() < 2) return;
            Settlement attacker = null;
            Settlement peacemaker = null;
            foreach (var hold in settlements)
            {
                if (hold.abandoned || Members(hold) <= 0) continue;
                bool hungry = SeenMeals(hold) < 4f && hold.faith < 22f;
                bool grieving = MeanGrief(hold) >= 55f && hold.Meals < (hold.sky == Sky.Drought ? 10f : 8f);
                bool vowed = hold.willRaid && !hold.lawKept && !hold.pactStay;
                if (!hungry && !grieving && !vowed) continue;
                if (!vowed && (hold.lawKept || hold.pactStay))
                {
                    if (peacemaker == null) peacemaker = hold;
                    continue;
                }
                bool attackerVowed = attacker != null && attacker.willRaid && !attacker.lawKept && !attacker.pactStay;
                if (attacker == null || (vowed && !attackerVowed) || (vowed == attackerVowed && hold.Meals < attacker.Meals))
                {
                    attacker = hold;
                }
            }
            if (attacker == null)
            {
                if (peacemaker != null)
                {
                    Settlement other = OtherHold(peacemaker);
                    if (other != null)
                    {
                        dealLine = peacemaker.placeName + " is thin and keeps the peace with " + other.placeName + ".";
                        Note(dealLine);
                        CalmMembers(peacemaker, 4f);
                        other.faith = Mathf.Clamp(other.faith + 1f, 0f, 100f);
                    }
                }
                raidStopped = false;
                return;
            }
            Settlement victim = BestHold(attacker);
            if (victim == null)
            {
                raidStopped = false;
                return;
            }
            if (raidStopped)
            {
                raidStopped = false;
                attacker.faith = Mathf.Clamp(attacker.faith + 1f, 0f, 100f);
                victim.faith = Mathf.Clamp(victim.faith + 2f, 0f, 100f);
                CalmMembers(victim, 6f);
                dealLine = "Elyon stops the raid from " + attacker.placeName + ". " + victim.placeName + " keeps its stores, and its people stay.";
                Note(dealLine);
                Chronicle(dealLine);
                return;
            }
            float grain = Mathf.Min(victim.grain * 0.22f, 8f);
            float wood = Mathf.Min(victim.wood * 0.3f, 4f);
            float fish = Mathf.Min(victim.fish * 0.3f, 3f);
            bool herdTaken = victim.herd > 0;
            if (grain < 0.4f && wood < 0.4f && fish < 0.4f && !herdTaken)
            {
                dealLine = attacker.placeName + " wanted to raid " + victim.placeName + ", and there was nothing to carry.";
                Note(dealLine);
                return;
            }
            victim.grain = Mathf.Max(0f, victim.grain - grain);
            attacker.grain += grain;
            victim.wood = Mathf.Max(0f, victim.wood - wood);
            attacker.wood += wood;
            victim.fish = Mathf.Max(0f, victim.fish - fish);
            attacker.fish = Mathf.Min(12f, attacker.fish + fish);
            if (herdTaken)
            {
                victim.herd--;
                attacker.herd = Mathf.Min(6, attacker.herd + 1);
            }
            bool tool = StealTool(victim, attacker);
            victim.raided = true;
            victim.dread = true;
            MarkDarkYear(victim);
            victim.faith = Mathf.Max(0f, victim.faith - 4f);
            attacker.faith = Mathf.Max(0f, attacker.faith - 2f);
            string memory = attacker.placeName + " raided " + victim.placeName + ".";
            KeepBook(ref raidLine, memory);
            foreach (var member in people)
            {
                if (!member.alive) continue;
                if (member.settlementId == victim.id)
                {
                    member.body.fear = Mathf.Min(100f, member.body.fear + 10f);
                    member.body.grief = Mathf.Min(100f, member.body.grief + 3f);
                    member.Remember(memory);
                }
                else if (member.settlementId == attacker.id)
                {
                    member.body.fear = Mathf.Min(100f, member.body.fear + 4f);
                    member.Remember(memory);
                }
            }
            string carried = tool ? "grain, wood, and a tool" : "grain and wood";
            if (fish >= 0.4f) carried += string.IsNullOrEmpty(victim.fishName) ? ", and fish" : ", and " + victim.fishName;
            if (herdTaken) carried += ", and a head of " + (string.IsNullOrEmpty(victim.herdName) ? "the herd" : victim.herdName);
            string cause = "";
            if (attacker.sky == Sky.Drought && attacker.Meals >= 4f)
            {
                cause = " The drought made " + attacker.placeName + " look hungry.";
            }
            else if (SeasonNow() == Season.Winter && attacker.Meals >= 4f && SeenMeals(attacker) < 4f)
            {
                cause = " The cold made " + attacker.placeName + " look hungry.";
            }
            dealLine = attacker.placeName + " raids " + victim.placeName + " and carries " + carried + "." + cause;
            Note(dealLine + " " + victim.placeName + " may not build this year, and someone may leave.");
            Chronicle(dealLine);
        }

        void BlessPact(Settlement home)
        {
            Settlement other = OtherHold(home);
            if (other == null)
            {
                Note("There is one hearth. A pact needs two.");
                return;
            }
            pact = true;
            pactWithheld = false;
            home.pactStay = true;
            other.pactStay = true;
            home.faith = Mathf.Clamp(home.faith + 2f, 0f, 100f);
            other.faith = Mathf.Clamp(other.faith + 2f, 0f, 100f);
            CalmMembers(home, 6f);
            CalmMembers(other, 6f);
            dealLine = "A pact holds between " + home.placeName + " and " + other.placeName + ".";
            KeepBook(ref pactLine, dealLine);
            Note(dealLine + " They may send grain, wood, and tools, and their people stay.");
            Chronicle(dealLine);
        }

        void WithholdPact(Settlement home)
        {
            Settlement other = OtherHold(home);
            if (other == null)
            {
                Note("There is one hearth. There is no pact to withhold.");
                return;
            }
            pact = false;
            pactWithheld = true;
            home.pactStay = false;
            other.pactStay = false;
            home.faith = Mathf.Max(0f, home.faith - 3f);
            other.faith = Mathf.Max(0f, other.faith - 2f);
            foreach (var member in people)
            {
                if (!member.alive) continue;
                if (member.settlementId != home.id && member.settlementId != other.id) continue;
                member.body.fear = Mathf.Min(100f, member.body.fear + 4f);
            }
            dealLine = "The pact is withheld between " + home.placeName + " and " + other.placeName + ".";
            KeepBook(ref pactLine, dealLine);
            Note(dealLine + " No grain, wood, or tools move, and someone may leave.");
            Chronicle(dealLine);
            Settlement poorer = home.Meals <= other.Meals ? home : other;
            SendAway(poorer, "The pact was withheld.");
        }

        void StopTheRaid(Settlement home)
        {
            if (OtherHold(home) == null)
            {
                Note("There is one hearth. No raid can be stopped.");
                return;
            }
            raidStopped = true;
            dealLine = "Elyon has said a raid will not land.";
            CalmMembers(home, 4f);
            Note(dealLine + " The stores stay where they are, and the people of " + home.placeName + " stay.");
        }

        void Trade()
        {
            if (LivingHolds() < 2) return;
            if (pactWithheld)
            {
                dealLine = "The pact is withheld. Nothing is sent between the holds.";
                Note(dealLine);
                return;
            }
            if (!roadOpen && !pact) return;
            Settlement grainRich = null;
            Settlement grainPoor = null;
            foreach (var hold in settlements)
            {
                if (hold.abandoned || Members(hold) <= 0) continue;
                if (grainRich == null || hold.grain > grainRich.grain) grainRich = hold;
                if (grainPoor == null || hold.grain < grainPoor.grain) grainPoor = hold;
            }
            if (grainRich == null || grainPoor == null || grainRich == grainPoor) return;
            float share = pact ? 0.18f : 0.1f;
            float grainSent = grainRich.grain * share;
            if (grainSent < 0.5f) return;
            grainRich.grain -= grainSent;
            grainPoor.grain += grainSent;
            string back = "";
            if (grainPoor.wood >= 3f && grainPoor.wood > grainRich.wood + 1f)
            {
                float wood = Mathf.Min(grainPoor.wood * (pact ? 0.35f : 0.15f), pact ? 5f : 2f);
                if (wood >= 1f)
                {
                    grainPoor.wood -= wood;
                    grainRich.wood += wood;
                    back = " " + grainPoor.placeName + " sends wood back.";
                }
            }
            else if (SendTool(grainPoor, grainRich))
            {
                back = " A tool goes back to " + grainRich.placeName + ".";
            }
            else if (grainRich.wood >= 4f)
            {
                float wood = Mathf.Min(grainRich.wood * (pact ? 0.25f : 0.08f), pact ? 4f : 1.5f);
                if (wood >= 1f)
                {
                    grainRich.wood -= wood;
                    grainPoor.wood += wood;
                    back = " Wood goes with the grain, so " + grainPoor.placeName + " can build.";
                }
            }
            string line = grainRich.placeName + " sends grain to " + grainPoor.placeName + "." + back;
            if (pact) line = "Under the pact, " + line;
            dealLine = line;
            if (pact)
            {
                grainRich.faith = Mathf.Clamp(grainRich.faith + 1f, 0f, 100f);
                grainPoor.faith = Mathf.Clamp(grainPoor.faith + 1f, 0f, 100f);
            }
            Note(line);
        }

        bool StealTool(Settlement from, Settlement to)
        {
            return MoveTool(from, to, 1);
        }

        bool SendTool(Settlement from, Settlement to)
        {
            return MoveTool(from, to, 2);
        }

        bool MoveTool(Settlement from, Settlement to, int minKeep)
        {
            if (from == null || to == null) return false;
            Person donor = null;
            int ofKind = 0;
            foreach (var person in people)
            {
                if (!person.alive || person.settlementId != from.id) continue;
                if (person.tool == ToolKind.Hands) continue;
                ofKind++;
                if (donor == null || person.toolWear > donor.toolWear) donor = person;
            }
            if (donor == null || ofKind < minKeep) return false;
            Person receiver = null;
            foreach (var person in people)
            {
                if (!person.alive || person.settlementId != to.id || person.body.age < 14f) continue;
                if (person.tool != ToolKind.Hands) continue;
                receiver = person;
                break;
            }
            if (receiver == null) return false;
            receiver.tool = donor.tool;
            receiver.toolWear = donor.toolWear;
            donor.tool = ToolKind.Hands;
            donor.toolWear = 0f;
            return true;
        }

        void ApplyLabor(float years, bool onlyWhileWorking)
        {
            if (years <= 0f) return;
            for (int i = 0; i < people.Count; i++)
            {
                Person person = people[i];
                if (!person.alive || person.body.age < 8f || person.labor == Labor.Follow) continue;
                if (onlyWhileWorking && !person.Working) continue;
                Settlement home = HomeOf(person);
                if (home == null) continue;
                float effort = person.body.Strength / 100f * ToolFactor(person) * (home.faith < 15f ? 0.75f : 1f) * years;
                if (person.body.age < 14f) effort *= 0.45f;
                switch (person.labor)
                {
                    case Labor.Gather:
                        float gather = LandLabor(home, Labor.Gather);
                        if (age >= AgeId.Industry && home.engineOn)
                        {
                            home.wood += 4.2f * effort;
                            home.fruit += 4f * effort * gather;
                            home.drive += 0.35f * effort;
                        }
                        else
                        {
                            home.wood += 3.2f * effort;
                            home.fruit += 8.2f * effort * gather;
                        }
                        break;
                    case Labor.Hunt:
                        float hunt = LandLabor(home, Labor.Hunt);
                        float kept = home.herd > 0 ? 0.7f * home.herd : 0f;
                        home.meat += (8.5f + kept) * effort * hunt;
                        home.wood += 0.35f * effort;
                        break;
                    case Labor.Farm:
                        float mill = home.mill && home.millOn ? 1.8f : 1f;
                        float engine = home.engine && home.engineOn && home.drive > 0f ? 1.3f : 1f;
                        float field = home.fields > 0 ? 1f : 0.35f;
                        float night = age >= AgeId.ElectricLight && !home.lights ? 0.85f : 1f;
                        float law = home.lawKept ? 1.12f : 1f;
                        float season = LandLabor(home, Labor.Farm);
                        home.grain += 9f * effort * mill * engine * field * night * law * season;
                        if (home.lawKept) person.body.fear = Mathf.Max(0f, person.body.fear - 2f * years);
                        break;
                    case Labor.Smith:
                        home.ore += 1.4f * effort;
                        MendTools(home, 22f * effort);
                        break;
                    case Labor.Tend:
                        home.faith = Mathf.Clamp(home.faith + 3.5f * effort, 0f, 100f);
                        break;
                    case Labor.Teach:
                        knowledge += (age >= AgeId.Present ? 2.2f : 1.6f) * effort;
                        break;
                    case Labor.Guard:
                        person.body.fear = Mathf.Max(0f, person.body.fear - 8f * effort);
                        break;
                    case Labor.Engine:
                        float fuel = Mathf.Min(home.wood, 0.4f * effort);
                        if (home.engineOn && fuel > 0.05f)
                        {
                            home.wood -= fuel;
                            home.drive += 3.4f * effort;
                            person.body.fatigue = Mathf.Min(100f, person.body.fatigue + 6f * years);
                        }
                        break;
                    case Labor.Wire:
                        if (home.engineOn && home.drive > 0.05f)
                        {
                            float take = Mathf.Min(home.drive, 1.2f * effort);
                            home.drive -= take;
                            home.power += take * 5f;
                        }
                        if (home.lights) person.body.fear = Mathf.Max(0f, person.body.fear - 3f * years);
                        else person.body.fear = Mathf.Min(100f, person.body.fear + 4f * years);
                        break;
                    case Labor.Keep:
                        knowledge += (home.press ? 3.2f : 2.4f) * effort;
                        home.faith = Mathf.Clamp(home.faith + 0.4f * effort, 0f, 100f);
                        break;
                }

                if (person.tool != ToolKind.Hands)
                {
                    person.toolWear = Mathf.Min(40f, person.toolWear + 5f * years);
                }
            }
        }

        void TouchWork()
        {
            jobStamp = -1;
            AssignJobs();
        }

        void AssignJobs()
        {
            int stamp = ((int)age * 1000) + year * 10 + AliveCount();
            if (stamp == jobStamp) return;
            jobStamp = stamp;
            var adults = new List<Person>();
            foreach (var person in people)
            {
                if (person.alive && person.body.age >= 14f) adults.Add(person);
            }

            adults.Sort((a, b) => AxeLast(a).CompareTo(AxeLast(b)));
            Settlement home = MainHome();
            if (home == null) return;
            int farmers = age >= AgeId.Farming ? Mathf.Clamp(adults.Count / 2, 1, 8) : 0;
            int smiths = age >= AgeId.MetalTowns ? 1 : 0;
            int tenders = age >= AgeId.Cities && home.temple ? 1 : 0;
            int teachers = age >= AgeId.RoadsAndLetters ? 1 : 0;
            int guards = age >= AgeId.Cities ? 1 : 0;
            int hunters = age == AgeId.Camps ? 1 : 0;
            int engineers = 0;
            int wirers = 0;
            if (age >= AgeId.Industry)
            {
                foreach (var hold in settlements)
                {
                    if (!hold.engine || Members(hold) <= 0) continue;
                    engineers++;
                    if (age >= AgeId.ElectricLight) wirers++;
                }
            }
            int keepers = age >= AgeId.Present ? 1 : 0;
            int specialists = smiths + tenders + teachers + guards + hunters + engineers + wirers + keepers;
            if (farmers + specialists >= adults.Count)
            {
                farmers = Mathf.Max(0, adults.Count - specialists);
            }

            foreach (var person in adults)
            {
                if (person.spokenWork)
                {
                    SetDuty(person, person.spokenLabor);
                    continue;
                }
                Labor labor = Labor.Gather;
                if (smiths > 0) { labor = Labor.Smith; smiths--; }
                else if (tenders > 0) { labor = Labor.Tend; tenders--; }
                else if (teachers > 0) { labor = Labor.Teach; teachers--; }
                else if (guards > 0 && !HoldHas(person, place => place.lawKept)) { labor = Labor.Guard; guards--; }
                else if (engineers > 0 && HoldHas(person, s => s.engine)) { labor = Labor.Engine; engineers--; }
                else if (wirers > 0 && HoldHas(person, s => s.engine)) { labor = Labor.Wire; wirers--; }
                else if (keepers > 0) { labor = Labor.Keep; keepers--; }
                else if (farmers > 0 && age >= AgeId.Farming) { labor = Labor.Farm; farmers--; }
                else if (hunters > 0) { labor = Labor.Hunt; hunters--; }
                SetDuty(person, labor);
            }

            foreach (var person in people)
            {
                if (!person.alive || person.body.age >= 14f) continue;
                if (person.spokenWork)
                {
                    SetDuty(person, person.spokenLabor);
                    continue;
                }
                if (person.body.age < 8f)
                {
                    person.labor = Labor.Follow;
                    person.workTree = null;
                    person.hasDuty = true;
                    person.dutyLabel = "staying near the house";
                    Person parent = Find(person.motherId) ?? Find(person.fatherId);
                    Settlement hearth = HomeOf(person);
                    person.dutyTarget = parent != null
                        ? parent.transform.position
                        : hearth != null ? Dry(hearth.Hearth) : person.transform.position;
                }
                else if (person.body.age >= 8f)
                {
                    Labor young = Labor.Gather;
                    if (age >= AgeId.Present) young = Labor.Keep;
                    else if (age >= AgeId.ElectricLight && HoldHas(person, s => s.engine)) young = Labor.Wire;
                    else if (age >= AgeId.Industry && HoldHas(person, s => s.engine)) young = Labor.Engine;
                    else if (age >= AgeId.Farming) young = Labor.Farm;
                    SetDuty(person, young);
                }
            }
        }

        public void ApplySpoken(Person person, string act)
        {
            if (person == null || !person.alive) return;
            string token = (act ?? "").Trim().ToLowerInvariant();
            if (token == "keep peace" || token == "keeppeace" || token == "keep_peace") token = "peace";
            if (token.Length == 0 || token == "none") return;
            Settlement hold = HomeOf(person);
            if (hold == null) return;
            switch (token)
            {
                case "work":
                    if (person.body.age < 8f)
                    {
                        Note(person.personName + " is too young to take up the work.");
                        return;
                    }
                    Labor labor = LaborFor(person);
                    person.spokenWork = true;
                    person.spokenLabor = labor;
                    SetDuty(person, labor);
                    Note(person.personName + " takes up " + person.dutyLabel + ".");
                    break;
                case "stay":
                    person.blessedHouse = true;
                    person.favor += 4;
                    Note(person.personName + " stays in " + hold.placeName + ".");
                    break;
                case "leave":
                    if (person.body.age < 18f)
                    {
                        Note(person.personName + " is too young to leave " + hold.placeName + ".");
                        return;
                    }
                    Settlement dest = OtherHold(hold);
                    if (dest == null)
                    {
                        Note(person.personName + " cannot leave. There is no other hearth.");
                        return;
                    }
                    person.spokenWork = false;
                    SetHome(person, dest, true);
                    person.Remember("I left " + hold.placeName + ".");
                    Note(person.personName + " leaves " + hold.placeName + " for " + dest.placeName + ".");
                    jobStamp = -1;
                    break;
                case "peace":
                    hold.lawKept = true;
                    hold.pactStay = true;
                    hold.willRaid = false;
                    CalmMembers(hold, 4f);
                    dealLine = person.personName + " keeps the peace in " + hold.placeName + ".";
                    Note(dealLine + " The fields are worked harder, fear eases, and this hold will not raid.");
                    jobStamp = -1;
                    break;
                case "raid":
                    if (LivingHolds() < 2 || OtherHold(hold) == null)
                    {
                        Note(person.personName + " speaks of a raid, and there is only one hearth.");
                        return;
                    }
                    hold.willRaid = true;
                    hold.lawKept = false;
                    hold.pactStay = false;
                    dealLine = person.personName + " says " + hold.placeName + " will raid.";
                    Note(dealLine + " At the year's end grain, wood, and a spare tool may be carried off.");
                    jobStamp = -1;
                    break;
                case "rain":
                    SendTheRain(hold);
                    break;
                case "drought":
                    DryTheGround(hold);
                    break;
                case "herd":
                    KeepTheHerd(hold);
                    break;
                default:
                    return;
            }
            if (jobStamp < 0) AssignJobs();
            RefreshKin();
        }

        Labor LaborFor(Person person)
        {
            Settlement hold = HomeOf(person);
            if (person.body.age < 8f) return Labor.Follow;
            if (age >= AgeId.Present && hold != null && hold.press) return Labor.Keep;
            if (age >= AgeId.ElectricLight && hold != null && hold.engine) return Labor.Wire;
            if (age >= AgeId.Industry && hold != null && hold.engine) return Labor.Engine;
            if (age >= AgeId.RoadsAndLetters && hold != null && hold.letters) return Labor.Teach;
            if (age >= AgeId.Cities && hold != null && hold.temple) return Labor.Tend;
            if (age >= AgeId.MetalTowns && person.tool == ToolKind.Hammer) return Labor.Smith;
            if (age >= AgeId.Farming && hold != null && hold.fields > 0) return Labor.Farm;
            if (age == AgeId.Camps) return Labor.Hunt;
            return Labor.Gather;
        }

        void SetDuty(Person person, Labor labor)
        {
            person.labor = labor;
            Settlement home = HomeOf(person);
            if (home == null) return;
            Vector3 site = Dry(home.Hearth);
            Transform tree = null;
            string label = WorkPhrase(labor, home, person) + LandPhrase(labor, home);
            switch (labor)
            {
                case Labor.Gather:
                    tree = NearestTree(home.Hearth);
                    site = tree != null ? tree.position : site;
                    break;
                case Labor.Hunt:
                    site = Dry(home.Hearth + new Vector3(7f, 0f, 5f));
                    break;
                case Labor.Farm:
                    site = FieldPoint(home, IndexOfLabor(person, Labor.Farm));
                    break;
                case Labor.Smith:
                    site = Ridge();
                    break;
                case Labor.Tend:
                    site = Dry(home.Hearth + new Vector3(0f, 0f, 5f));
                    break;
                case Labor.Teach:
                    site = Dry(home.Hearth + new Vector3(4f, 0f, -2f));
                    break;
                case Labor.Guard:
                    site = Dry(home.Hearth + new Vector3(-3f, 0f, -2f));
                    break;
                case Labor.Engine:
                    site = Dry(home.Hearth + new Vector3(8f, 0f, -4f));
                    break;
                case Labor.Wire:
                    site = Dry(home.Hearth + new Vector3(3f, 0f, 7f));
                    break;
                case Labor.Keep:
                    site = Dry(home.Hearth + new Vector3(5f, 0f, -2f));
                    break;
            }

            person.workTree = labor == Labor.Gather && person.tool == ToolKind.Axe ? tree : null;
            person.hasDuty = true;
            person.dutyTarget = site;
            person.dutyLabel = label;
            if (person.alive) person.Retarget();
        }

        string WorkPhrase(Labor labor, Settlement home, Person person)
        {
            switch (labor)
            {
                case Labor.Gather:
                    if (age >= AgeId.Present) return "gathering for the commons";
                    if (age >= AgeId.Industry) return home.engineOn ? "hauling wood to the engine" : "gathering while the engine is banked";
                    if (age >= AgeId.MetalTowns) return "cutting timber for the town";
                    if (age >= AgeId.Camps) return "gathering for the camp";
                    return person.tool == ToolKind.Axe ? "cutting wood at a tree" : "gathering fruit and wood";
                case Labor.Hunt:
                    return "hunting out from the camp";
                case Labor.Farm:
                    if (age >= AgeId.Present) return "keeping the common field";
                    if (age >= AgeId.ElectricLight) return home.lights ? "working the field under the lamps" : "working a field in the dark";
                    if (age >= AgeId.Industry) return home.engineOn ? "driving the field from the engine" : "tending a field while the engine is banked";
                    if (age >= AgeId.Mills) return home.millOn ? "feeding grain to the mill" : "tending a field while the mill rests";
                    return "tending a field";
                case Labor.Smith:
                    if (age >= AgeId.Industry) return "mending tools for the engine house";
                    return "working the smithy";
                case Labor.Tend:
                    if (age >= AgeId.Present) return "keeping the rite for the living holds";
                    return "tending the temple";
                case Labor.Teach:
                    if (age >= AgeId.Present) return "setting type at the press";
                    return "teaching in the house of letters";
                case Labor.Guard:
                    if (age >= AgeId.ElectricLight) return home.lights ? "watching the lamps" : "watching a dark street";
                    return "keeping watch by the hall";
                case Labor.Engine:
                    if (!home.engine) return "waiting on an engine house";
                    return home.engineOn ? "keeping the engine" : "standing by a banked engine";
                case Labor.Wire:
                    if (!home.lights) return "drawing power in the dark";
                    return "drawing power for the lamps";
                case Labor.Keep:
                    return "keeping the press and the commons";
                default:
                    return "following a parent";
            }
        }

        void UpdateFollowers(float delta)
        {
            followTimer -= delta;
            if (followTimer > 0f) return;
            followTimer = 1.5f;
            foreach (var person in people)
            {
                if (!person.alive || person.labor != Labor.Follow) continue;
                Person parent = Find(person.motherId) ?? Find(person.fatherId);
                if (parent == null) continue;
                if (Vector3.Distance(person.dutyTarget, parent.transform.position) < 3f) continue;
                person.dutyTarget = parent.transform.position;
                person.Retarget();
            }
        }

        void RegisterFounders(Settlement eden)
        {
            garden.Adam.personId = "adam";
            garden.Eve.personId = "eve";
            garden.Adam.partnerId = "eve";
            garden.Eve.partnerId = "adam";
            garden.Adam.eveShape = false;
            garden.Eve.eveShape = true;
            garden.Adam.tool = ToolKind.Axe;
            garden.Eve.tool = ToolKind.Hands;
            people.Add(garden.Adam);
            people.Add(garden.Eve);
            SetHome(garden.Adam, eden, false);
            SetHome(garden.Eve, eden, false);
            garden.Adam.bornInto = Ages.Name(AgeId.FirstFamily);
            garden.Eve.bornInto = Ages.Name(AgeId.FirstFamily);
            garden.Adam.givenName = true;
            garden.Eve.givenName = true;
            garden.Adam.home = this;
            garden.Eve.home = this;
        }

        Person Spawn(string personName, bool eveShape, float years, Vector3 spot, Settlement home)
        {
            var go = new GameObject(personName);
            go.transform.SetParent(built.parent, false);
            var person = go.AddComponent<Person>();
            person.who = "house";
            person.personName = personName;
            person.personId = "p" + nextId++;
            person.eveShape = eveShape;
            person.home = this;
            person.body.hunger = years < 3f ? 20f : 35f;
            person.body.thirst = 24f;
            person.body.fatigue = 8f;
            float scale = years >= 16f ? 1f : Mathf.Lerp(0.42f, 1f, years / 16f);
            HumanForm.Attach(person, eveShape, scale);
            person.ApplyAge(years);
            Vector3 hearth = Dry(home.Hearth);
            person.BindDay(hearth, Dry(hearth + new Vector3(1.1f, 0f, 0.2f)), Dry(hearth + new Vector3(0.2f, 0f, 1.15f)), null, Dry(spot));
            person.body.age = years;
            people.Add(person);
            SetHome(person, home, false);
            jobStamp = -1;
            return person;
        }

        void SetHome(Person person, Settlement settlement, bool walk)
        {
            person.settlementId = settlement.id;
            person.homeName = settlement.placeName;
            Vector3 hearth = Dry(settlement.Hearth);
            person.fire = hearth;
            person.pot = Dry(hearth + new Vector3(1.1f, 0f, 0.2f));
            person.cup = Dry(hearth + new Vector3(0.2f, 0f, 1.15f));
            int seat = 0;
            foreach (var other in people)
            {
                if (other.settlementId == settlement.id) seat++;
            }
            person.seat = Dry(hearth + new Vector3(-1.6f + (seat % 4) * 0.85f, 0f, -1.3f));
            if (walk && person.alive) person.Retarget();
        }

        void MoveHousehold(Person person, Settlement dest)
        {
            SetHome(person, dest, true);
            Person partner = Find(person.partnerId);
            if (partner != null && partner.alive) SetHome(partner, dest, true);
            foreach (var child in people)
            {
                if (!child.alive) continue;
                if (child.motherId == person.personId || child.fatherId == person.personId
                    || (partner != null && (child.motherId == partner.personId || child.fatherId == partner.personId)))
                {
                    if (child.body.age < 18f) SetHome(child, dest, true);
                }
            }
        }

        void RelocateAll(Settlement dest)
        {
            foreach (var settlement in settlements)
            {
                if (settlement != dest) dest.Receive(settlement);
            }
            foreach (var person in people)
            {
                if (person.alive) SetHome(person, dest, true);
            }
        }

        Settlement EnsureEast()
        {
            Settlement east = FindSettlement("east");
            if (east != null) return east;
            east = new Settlement
            {
                id = "east",
                placeName = "the eastern camp",
                hearthX = 168f,
                hearthZ = 118f,
                fruit = 0f,
                water = 0f,
                wood = 0f,
                faith = 36f,
            };
            settlements.Add(east);
            return east;
        }

        void RefreshKin()
        {
            string ageName = Ages.Name(age);
            foreach (var person in people)
            {
                bool infant = false;
                if (person.body.age >= 14f)
                {
                    foreach (var child in people)
                    {
                        if (!child.alive || child.body.age >= 3f) continue;
                        if (child.motherId == person.personId || child.fatherId == person.personId) infant = true;
                    }
                    person.body.child = infant;
                }

                person.ageName = ageName;
                person.ageVoice = Ages.Voice(age) + " " + Ages.Between(age);
                if (!string.IsNullOrEmpty(dealLine)) person.ageVoice += " Between the holds: " + dealLine;
                Settlement kinHome = HomeOf(person);
                if (kinHome != null) person.homeName = kinHome.placeName;
                person.holdFacts = HoldFacts(kinHome);
                person.kinLine = KinLine(person);
                person.lineMemory = FamilyMemory();
                person.chronicle = ChronicleText();
                person.worldLine = LastEvent;
            }
        }

        string KinLine(Person person)
        {
            string line;
            if (person.personId == "adam") line = "the first man, of the garden fire";
            else if (person.personId == "eve") line = "the first woman, of the garden fire";
            else line = HouseLine(person);
            return WithHouse(person, line);
        }

        string HouseLine(Person person)
        {
            Person mother = Find(person.motherId);
            Person father = Find(person.fatherId);
            string born = BirthAge(person);
            if (mother == null && father == null)
            {
                Person partner = Find(person.partnerId);
                string house = partner != null ? partner.personName : person.homeName;
                return "came to the house of " + house + ", of the line of Eve and Adam" + born;
            }

            string line = mother != null && father != null
                ? "child of " + mother.personName + " and " + father.personName
                : "child of " + (mother != null ? mother.personName : father.personName);
            bool garden = (mother != null && IsRoot(mother)) || (father != null && IsRoot(father));
            var elders = new List<string>();
            var seen = new HashSet<string>();
            seen.Add(person.personId);
            if (mother != null) seen.Add(mother.personId);
            if (father != null) seen.Add(father.personId);
            WalkElders(mother, elders, seen, ref garden, 0);
            WalkElders(father, elders, seen, ref garden, 0);
            if (garden) line += ", of the line of Eve and Adam";
            if (elders.Count > 0) line += ", through " + string.Join(", ", elders);
            return line + born;
        }

        static bool IsRoot(Person person)
        {
            return person.personId == "adam" || person.personId == "eve";
        }

        static string BirthAge(Person person)
        {
            if (string.IsNullOrEmpty(person.bornInto)) return "";
            if (string.IsNullOrEmpty(person.motherId) && string.IsNullOrEmpty(person.fatherId))
                return ", in the age of " + person.bornInto;
            return ", born in " + person.bornInto;
        }

        void WalkElders(Person node, List<string> elders, HashSet<string> seen, ref bool garden, int depth)
        {
            if (node == null || depth > 6) return;
            TakeElder(Find(node.motherId), elders, seen, ref garden, depth);
            TakeElder(Find(node.fatherId), elders, seen, ref garden, depth);
        }

        void TakeElder(Person elder, List<string> elders, HashSet<string> seen, ref bool garden, int depth)
        {
            if (elder == null) return;
            if (IsRoot(elder))
            {
                garden = true;
                return;
            }
            if (!seen.Add(elder.personId)) return;
            if (elders.Count < 4) elders.Add(elder.personName);
            WalkElders(elder, elders, seen, ref garden, depth + 1);
        }

        string WithHouse(Person person, string line)
        {
            Person partner = Find(person.partnerId);
            if (partner != null)
            {
                line += partner.alive
                    ? ", keeping house with " + partner.personName
                    : ", of the house of " + partner.personName;
            }
            string children = "";
            foreach (var child in people)
            {
                if (!child.alive) continue;
                if (child.motherId != person.personId && child.fatherId != person.personId) continue;
                if (children.Length > 0) children += ", ";
                children += child.personName;
            }
            if (children.Length > 0) line += ", children: " + children;
            return line;
        }

        public string FamilyMemory()
        {
            string garden = string.IsNullOrEmpty(gardenLine)
                ? "Adam and Eve woke at the garden fire."
                : gardenLine.Trim();
            string pact = Tail(pactLine, 110);
            string raid = Tail(raidLine, 90);
            string wound = Tail(woundLine, 150);
            string memory = garden;
            if (pact.Length > 0) memory += " " + pact;
            if (raid.Length > 0) memory += " " + raid;
            if (wound.Length > 0) memory += " " + wound;
            return memory;
        }

        static string Tail(string book, int cap)
        {
            if (string.IsNullOrEmpty(book)) return "";
            string trimmed = book.Trim();
            if (trimmed.Length <= cap) return trimmed;
            string cut = trimmed.Substring(trimmed.Length - cap).Trim();
            int dot = cut.IndexOf(". ", System.StringComparison.Ordinal);
            if (dot >= 0 && dot + 2 < cut.Length) return cut.Substring(dot + 2).Trim();
            int space = cut.IndexOf(' ');
            if (space >= 0 && space < 24) return cut.Substring(space + 1).Trim();
            return cut;
        }

        void RememberAge()
        {
            string line = "The age of " + Ages.Name(age) + " begins.";
            for (int i = 0; i < ageBook.Count; i++)
            {
                if (ageBook[i] == line) return;
            }
            ageBook.Add(line);
        }

        void Chronicle(string line)
        {
            if (string.IsNullOrWhiteSpace(line)) return;
            string trimmed = line.Trim();
            if (trimmed.StartsWith("Year ", StringComparison.Ordinal))
            {
                KeepLine(recentBook, trimmed, 8);
                return;
            }
            KeepLine(eventBook, trimmed, 64);
        }

        static void KeepLine(List<string> book, string line, int cap)
        {
            if (book.Count > 0 && book[book.Count - 1] == line) return;
            book.Add(line);
            if (book.Count > cap) book.RemoveAt(0);
        }

        public string ChronicleText()
        {
            string text = string.IsNullOrEmpty(gardenLine)
                ? "Adam and Eve woke at the garden fire."
                : gardenLine.Trim();
            for (int i = 0; i < ageBook.Count; i++) text += " " + ageBook[i];
            for (int i = 0; i < eventBook.Count; i++) text += " " + eventBook[i];
            for (int i = 0; i < recentBook.Count; i++) text += " " + recentBook[i];
            return text;
        }

        void MarkDarkYear(Settlement home)
        {
            if (home == null) return;
            KeepBook(ref woundLine, "A dark year at " + home.placeName + ".");
        }

        string HoldFacts(Settlement hold)
        {
            if (hold == null) return "";
            string law = hold.lawKept ? "The commandment is kept here." : "No commandment is kept here.";
            string bond;
            if (pactWithheld) bond = "The pact is withheld.";
            else if (pact) bond = "A pact holds.";
            else bond = "There is no pact.";
            string strife = "";
            if (hold.willRaid) strife += " This hold will raid.";
            if (hold.raided) strife += " This hold was raided.";
            string between = string.IsNullOrEmpty(dealLine) ? "" : " " + dealLine;
            string born = string.IsNullOrEmpty(bornLine) ? "" : " Born: " + bornLine;
            string lost = string.IsNullOrEmpty(lostLine) ? "" : " Lost: " + lostLine;
            return "Stores in " + hold.placeName
                + ": meals " + Mathf.RoundToInt(hold.Meals)
                + ", grain " + Mathf.RoundToInt(hold.grain)
                + ", wood " + Mathf.RoundToInt(hold.wood)
                + ", faith " + Mathf.RoundToInt(hold.faith)
                + ". The season is " + SeasonName()
                + ". The sky is " + SkyName(hold.sky)
                + ". " + HerdFact(hold)
                + ". " + FishFact(hold)
                + ". " + law + " " + bond + strife + between + born + lost;
        }

        void KeepBook(ref string book, string line)
        {
            if (string.IsNullOrWhiteSpace(line)) return;
            string next = string.IsNullOrEmpty(book) ? line.Trim() : (book + " " + line.Trim()).Trim();
            if (next.Length > 240) next = next.Substring(next.Length - 240).Trim();
            book = next;
        }

        Season SeasonNow()
        {
            return (Season)((Mathf.Max(1, year) - 1) % 4);
        }

        string SeasonName()
        {
            switch (SeasonNow())
            {
                case Season.Spring: return "Spring";
                case Season.Summer: return "Summer";
                case Season.Autumn: return "Autumn";
                default: return "Winter";
            }
        }

        static string SkyName(Sky sky)
        {
            switch (sky)
            {
                case Sky.Rain: return "rain";
                case Sky.Drought: return "drought";
                case Sky.Flood: return "flood";
                default: return "clear";
            }
        }

        float SeenMeals(Settlement hold)
        {
            float seen = hold.Meals;
            if (SeasonNow() == Season.Winter) seen -= 2f;
            if (hold.sky == Sky.Drought) seen -= 3f;
            return seen;
        }

        float LandLabor(Settlement home, Labor labor)
        {
            float season = 1f;
            switch (SeasonNow())
            {
                case Season.Spring:
                    if (labor == Labor.Farm) season = 1.08f;
                    break;
                case Season.Summer:
                    if (labor == Labor.Farm) season = 0.92f;
                    else if (labor == Labor.Gather) season = 1.12f;
                    else if (labor == Labor.Hunt) season = 1.08f;
                    break;
                case Season.Autumn:
                    if (labor == Labor.Farm) season = 1.2f;
                    else if (labor == Labor.Gather) season = 1.06f;
                    break;
                default:
                    if (labor == Labor.Farm) season = 0.72f;
                    else if (labor == Labor.Gather) season = 0.8f;
                    else if (labor == Labor.Hunt) season = 0.75f;
                    break;
            }
            float sky = 1f;
            if (home.sky == Sky.Rain && labor == Labor.Farm) sky = 1.28f;
            else if (home.sky == Sky.Rain && labor == Labor.Gather) sky = 1.1f;
            else if (home.sky == Sky.Drought && (labor == Labor.Farm || labor == Labor.Gather || labor == Labor.Hunt)) sky = 0.5f;
            else if (home.sky == Sky.Flood && labor == Labor.Farm) sky = 0.55f;
            else if (home.sky == Sky.Flood && labor == Labor.Hunt) sky = 0.8f;
            return season * sky;
        }

        string LandPhrase(Labor labor, Settlement home)
        {
            bool outdoors = labor == Labor.Farm || labor == Labor.Gather || labor == Labor.Hunt;
            if (home.sky == Sky.Drought && outdoors) return " on dry ground";
            if (home.sky == Sky.Flood && (labor == Labor.Farm || labor == Labor.Gather)) return " in the flood";
            if (home.sky == Sky.Rain && labor == Labor.Farm) return " in the rain";
            if (SeasonNow() == Season.Winter && outdoors) return " in the cold";
            if (SeasonNow() == Season.Autumn && labor == Labor.Farm) return " at the harvest";
            if (home.herd > 0 && labor == Labor.Hunt)
                return string.IsNullOrEmpty(home.herdName) ? " with the herd" : " with " + home.herdName;
            return "";
        }

        void TendWild()
        {
            Season season = SeasonNow();
            foreach (var hold in settlements)
            {
                if (hold.abandoned || Members(hold) <= 0) continue;
                if (hold.sky == Sky.Drought)
                {
                    hold.fish = 0f;
                    hold.water *= 0.5f;
                    if (hold.herd > 0)
                    {
                        hold.herd--;
                        Note("Drought takes a head from " + HerdCalled(hold) + " at " + hold.placeName + ".");
                    }
                }
                else if (season == Season.Winter)
                {
                    if (hold.fish >= 1f) hold.fish -= 1f;
                    if (hold.wood > 0.5f) hold.wood -= 0.4f;
                    if (hold.herd > 0)
                    {
                        float feed = hold.herd * 0.4f;
                        if (hold.grain >= feed) hold.grain -= feed;
                        else
                        {
                            hold.herd--;
                            Note("Winter takes a head from " + HerdCalled(hold) + " at " + hold.placeName + ". The stores could not feed them.");
                        }
                    }
                }
                else if ((season == Season.Summer || season == Season.Autumn) && hold.herd > 0 && hold.herd < 6 && hold.Meals >= 6f && hold.sky != Sky.Flood)
                {
                    hold.herd++;
                    Note(HerdCalled(hold) + " at " + hold.placeName + " grows. They keep " + hold.herd + " head.");
                }
            }
        }

        void SendTheRain(Settlement home)
        {
            home.sky = Sky.Rain;
            home.water += 12f;
            if (home.fields > 0) home.grain += 4f;
            else home.fruit += 2f;
            home.fish = Mathf.Min(12f, home.fish + 3f);
            home.faith = Mathf.Clamp(home.faith + 2f, 0f, 100f);
            Note(home.fields > 0
                ? "Rain falls on the fields at " + home.placeName + ". The nets take " + FishCalled(home) + "."
                : "Rain fills the stores at " + home.placeName + ". The nets take " + FishCalled(home) + ".");
            Chronicle(LastEvent);
            TouchWork();
        }

        void DryTheGround(Settlement home)
        {
            home.sky = Sky.Drought;
            home.water = Mathf.Max(0f, home.water - 10f);
            home.grain *= 0.7f;
            home.fruit *= 0.8f;
            home.fish = 0f;
            home.faith = Mathf.Max(0f, home.faith - 2f);
            if (home.herd > 0)
            {
                home.herd--;
                Note("The drought thins " + HerdCalled(home) + " at " + home.placeName + ".");
                Chronicle(LastEvent);
            }
            foreach (var member in people)
            {
                if (member.alive && member.settlementId == home.id)
                {
                    member.body.fear = Mathf.Min(100f, member.body.fear + 3f);
                }
            }
            string fishGone = string.IsNullOrEmpty(home.fishName) ? "The fish are gone." : home.fishName + " is gone from the nets.";
            Note("Drought lies on " + home.placeName + ". " + fishGone + " Unless a house was blessed, no child is born, and a thin hold may raid.");
            Chronicle(LastEvent);
            TouchWork();
        }

        void SendTheFlood(Settlement home)
        {
            home.sky = Sky.Flood;
            home.water += 8f;
            home.grain = Mathf.Max(0f, home.grain - 4f);
            home.wood = Mathf.Max(0f, home.wood - 2f);
            home.fish *= 0.5f;
            home.faith = Mathf.Max(0f, home.faith - 2f);
            if (home.herd > 0)
            {
                home.herd--;
                Note("The flood scatters a head of " + HerdCalled(home) + " at " + home.placeName + ".");
                Chronicle(LastEvent);
            }
            foreach (var member in people)
            {
                if (member.alive && member.settlementId == home.id)
                {
                    member.body.fear = Mathf.Min(100f, member.body.fear + 4f);
                }
            }
            Note("A flood runs through " + home.placeName + ". Grain and wood are carried off. Unless a house was blessed, no child is born.");
            Chronicle(LastEvent);
            TouchWork();
        }

        void KeepTheHerd(Settlement home)
        {
            if (home.sky == Sky.Drought)
            {
                Note("The ground is dry at " + home.placeName + ". " + HerdCalled(home) + " will not stay.");
                return;
            }
            if (home.sky == Sky.Flood)
            {
                Note("The flood is on " + home.placeName + ". " + HerdCalled(home) + " will not stay.");
                return;
            }
            int before = home.herd;
            home.herd = Mathf.Min(6, home.herd + 2);
            if (home.herd == before)
            {
                Note(HerdCalled(home) + " at " + home.placeName + " is already as large as the grass will hold.");
                return;
            }
            home.meat += 1f;
            Note(string.IsNullOrEmpty(home.herdName)
                ? home.placeName + " keeps a herd. " + home.herd + " head."
                : home.placeName + " keeps " + home.herdName + ". " + home.herd + " head.");
            Chronicle(LastEvent);
            TouchWork();
        }

        AgeFacts Facts()
        {
            var facts = new AgeFacts
            {
                year = year,
                childrenBorn = childrenBorn,
                knowledge = knowledge,
                road = roadOpen,
            };
            int livingSettlements = 0;
            float faithWeight = 0f;
            foreach (var settlement in settlements)
            {
                if (settlement.abandoned) continue;
                int members = Members(settlement);
                if (members > 0)
                {
                    livingSettlements++;
                    facts.faith += settlement.faith * members;
                    faithWeight += members;
                }
                facts.meals += settlement.Meals;
                facts.wood += settlement.wood;
                facts.ore += settlement.ore;
                facts.tents += settlement.tents;
                facts.houses += settlement.houses;
                facts.fields += settlement.fields;
                facts.metalTools += settlement.metalTools;
                facts.smithy |= settlement.smithy;
                facts.hall |= settlement.hall;
                facts.temple |= settlement.temple;
                facts.letters |= settlement.letters;
                facts.mill |= settlement.mill;
                facts.engine |= settlement.engine;
                facts.lights |= settlement.lights;
                facts.drive += settlement.drive;
                facts.power += settlement.power;
            }
            facts.population = AliveCount();
            facts.settlements = livingSettlements;
            facts.faith = faithWeight > 0f ? facts.faith / faithWeight : 0f;
            return facts;
        }

        public string StockLine()
        {
            AgeFacts facts = Facts();
            string line = "meals " + (int)facts.meals
                + "   wood " + (int)facts.wood
                + "   water " + (int)TotalWater()
                + "   faith " + (int)facts.faith;
            if (age >= AgeId.Farming) line += "   grain " + (int)TotalGrain();
            if (age >= AgeId.MetalTowns) line += "   ore " + (int)facts.ore;
            if (age >= AgeId.RoadsAndLetters) line += "   learning " + (int)knowledge;
            if (age >= AgeId.Industry) line += "   drive " + (int)facts.drive;
            if (age >= AgeId.ElectricLight) line += "   power " + (int)facts.power;
            line += "   holds " + LivingHolds();
            int empty = 0;
            foreach (var hold in settlements)
            {
                if (hold.abandoned) empty++;
            }
            if (empty > 0) line += "   empty " + empty;
            int herd = 0;
            float fish = 0f;
            bool rain = false;
            bool drought = false;
            bool flood = false;
            foreach (var hold in settlements)
            {
                if (hold.abandoned) continue;
                herd += hold.herd;
                fish += hold.fish;
                if (hold.sky == Sky.Rain) rain = true;
                if (hold.sky == Sky.Drought) drought = true;
                if (hold.sky == Sky.Flood) flood = true;
            }
            if (herd > 0) line += "   herd " + herd + NamedStock(true);
            if (fish >= 1f) line += "   fish " + (int)fish + NamedStock(false);
            if (drought) line += "   drought";
            else if (flood) line += "   flood";
            else if (rain) line += "   rain";
            if (LivingHolds() > 1)
            {
                if (pactWithheld) line += "   pact withheld";
                else if (pact) line += "   pact";
                if (raidStopped) line += "   raid stopped";
            }
            foreach (var hold in settlements)
            {
                if (hold.lawKept && !hold.abandoned)
                {
                    line += "   law";
                    break;
                }
            }
            foreach (var hold in settlements)
            {
                if (hold.willRaid && !hold.abandoned && Members(hold) > 0)
                {
                    line += "   will raid";
                    break;
                }
            }
            return line;
        }

        void EnsureVisuals()
        {
            visualsDirty = false;
            Settlement east = FindSettlement("east");
            Settlement far = FindSettlement("far");
            Settlement main = MainHome();
            if (east != null && !shownEastFire)
            {
                shownEastFire = true;
                PlaceHearth(east.Hearth, "Camp fire");
            }
            if (far != null && !shownFarFire)
            {
                shownFarFire = true;
                PlaceHearth(far.Hearth, "Hold fire");
            }
            foreach (var hold in settlements)
            {
                if (hold.abandoned) continue;
                if (hold.id == "eden" || hold.id == "east" || hold.id == "far") continue;
                string hearthKey = hold.id + ":hearth";
                MarkWork(hearthKey, () => PlaceHearth(hold.Hearth, hold.placeName));
            }

            Settlement tentsHome = east ?? main;
            while (shownTents < tentsHome.tents)
            {
                PlaceLeanTo(tentsHome.Hearth + new Vector3(2.2f + shownTents * 1.8f, 0f, 1.5f), shownTents);
                shownTents++;
            }
            while (shownFields < main.fields)
            {
                PlaceField(FieldPoint(main, shownFields));
                shownFields++;
            }
            while (shownHouses < main.houses)
            {
                PlaceHouse(main.Hearth + new Vector3(-2.4f - shownHouses * 2.2f, 0f, 2.2f), "House");
                shownHouses++;
            }
            if (main.smithy && !shownSmithy)
            {
                shownSmithy = true;
                PlaceSmithy(Ridge());
            }
            if (main.palisade && !shownPalisade)
            {
                shownPalisade = true;
                PlacePalisade(main.Hearth);
            }
            if (main.hall && !shownHall)
            {
                shownHall = true;
                PlaceHouse(main.Hearth + new Vector3(0f, 0f, 6f), "Hall");
            }
            if (main.temple && !shownTemple)
            {
                shownTemple = true;
                PlaceTemple(main.Hearth + new Vector3(0f, 0f, 9f));
            }
            if (main.letters && !shownLetters)
            {
                shownLetters = true;
                PlaceHouse(main.Hearth + new Vector3(5f, 0f, -2f), "Letters");
            }
            if (main.mill && !shownMill)
            {
                shownMill = true;
                PlaceMill(main.Hearth + new Vector3(6f, 0f, 4f));
            }
            if (main.engine && !shownEngine)
            {
                shownEngine = true;
                PlaceEngine(main.Hearth + new Vector3(8f, 0f, -4f));
            }
            if (main.lights && !shownLamps)
            {
                shownLamps = true;
                PlaceLamps(main.Hearth);
            }
            if (main.press && !shownPress)
            {
                shownPress = true;
                PlacePress(main.Hearth + new Vector3(5f, 0f, -4.2f));
            }
            foreach (var hold in settlements)
            {
                if (hold == main) continue;
                if (hold.mill) MarkWork(hold.id + ":mill", () => PlaceMill(hold.Hearth + new Vector3(6f, 0f, 4f)));
                if (hold.engine) MarkWork(hold.id + ":engine", () => PlaceEngine(hold.Hearth + new Vector3(8f, 0f, -4f)));
                if (hold.lights) MarkWork(hold.id + ":lamps", () => PlaceLamps(hold.Hearth));
            }
            if (roadOpen && !shownRoad && far != null)
            {
                shownRoad = true;
                PlaceRoad(main.Hearth, far.Hearth);
            }
        }

        void MarkWork(string key, System.Action place)
        {
            if (raisedMarks.Contains(key)) return;
            raisedMarks.Add(key);
            place();
        }

        void CacheMaterials()
        {
            woodMat = GardenBuilder.Lit(new Color(0.35f, 0.22f, 0.12f), 0.28f, null, Vector2.one);
            clothMat = GardenBuilder.Lit(new Color(0.62f, 0.48f, 0.32f), 0.2f, null, Vector2.one);
            grainMat = GardenBuilder.Lit(new Color(0.45f, 0.42f, 0.16f), 0.12f, null, Vector2.one);
            stoneMat = GardenBuilder.Lit(new Color(0.45f, 0.44f, 0.4f), 0.18f, null, Vector2.one);
            roofMat = GardenBuilder.Lit(new Color(0.42f, 0.28f, 0.18f), 0.22f, null, Vector2.one);
        }

        void PlaceHearth(Vector3 spot, string name)
        {
            var go = new GameObject(name);
            go.transform.SetParent(built, false);
            go.transform.position = Dry(spot);
            var meshGo = new GameObject("Logs");
            meshGo.transform.SetParent(go.transform, false);
            meshGo.AddComponent<MeshFilter>().sharedMesh = GardenMeshes.Trunk(0.8f, 0.1f, 2);
            meshGo.AddComponent<MeshRenderer>().sharedMaterial = woodMat;
            var lightGo = new GameObject("Light");
            lightGo.transform.SetParent(go.transform, false);
            lightGo.transform.localPosition = new Vector3(0f, 1f, 0f);
            var light = lightGo.AddComponent<Light>();
            light.type = LightType.Point;
            light.color = new Color(1f, 0.62f, 0.28f);
            light.range = 8f;
            light.intensity = 1200f;
            lightGo.AddComponent<HDAdditionalLightData>().SetIntensity(1200f, LightUnit.Lumen);
        }

        void PlaceLeanTo(Vector3 spot, int salt)
        {
            var root = new GameObject("Lean-to");
            root.transform.SetParent(built, false);
            root.transform.position = Dry(spot);
            for (int i = 0; i < 3; i++)
            {
                var pole = new GameObject("Pole");
                pole.transform.SetParent(root.transform, false);
                pole.transform.localRotation = Quaternion.Euler(28f, i * 40f, 18f);
                pole.AddComponent<MeshFilter>().sharedMesh = GardenMeshes.Trunk(1.6f, 0.05f, salt + i);
                pole.AddComponent<MeshRenderer>().sharedMaterial = i == 2 ? clothMat : woodMat;
            }
        }

        void PlaceHouse(Vector3 spot, string name)
        {
            var root = new GameObject(name);
            root.transform.SetParent(built, false);
            root.transform.position = Dry(spot);
            for (int i = 0; i < 4; i++)
            {
                var post = new GameObject("Post");
                post.transform.SetParent(root.transform, false);
                post.transform.localPosition = new Vector3(i < 2 ? -0.8f : 0.8f, 0f, i % 2 == 0 ? -0.6f : 0.6f);
                post.AddComponent<MeshFilter>().sharedMesh = GardenMeshes.Trunk(1.5f, 0.06f, i);
                post.AddComponent<MeshRenderer>().sharedMaterial = woodMat;
            }
            var roof = new GameObject("Roof");
            roof.transform.SetParent(root.transform, false);
            roof.transform.localPosition = new Vector3(0f, 1.45f, 0f);
            roof.transform.localScale = new Vector3(0.22f, 1f, 0.18f);
            roof.AddComponent<MeshFilter>().sharedMesh = GardenMeshes.Ellipse(8f, 8f, 10);
            roof.AddComponent<MeshRenderer>().sharedMaterial = roofMat;
        }

        void PlaceField(Vector3 spot)
        {
            var go = new GameObject("Field");
            go.transform.SetParent(built, false);
            go.transform.position = Dry(spot) + Vector3.up * 0.05f;
            go.transform.localScale = new Vector3(0.35f, 1f, 0.28f);
            go.AddComponent<MeshFilter>().sharedMesh = GardenMeshes.Ellipse(8f, 8f, 14);
            go.AddComponent<MeshRenderer>().sharedMaterial = grainMat;
        }

        void PlaceSmithy(Vector3 spot)
        {
            var root = new GameObject("Smithy");
            root.transform.SetParent(built, false);
            root.transform.position = Dry(spot);
            var stone = new GameObject("Anvil");
            stone.transform.SetParent(root.transform, false);
            stone.AddComponent<MeshFilter>().sharedMesh = GardenMeshes.Boulder(6);
            stone.AddComponent<MeshRenderer>().sharedMaterial = stoneMat;
            var chimney = new GameObject("Chimney");
            chimney.transform.SetParent(root.transform, false);
            chimney.transform.localPosition = new Vector3(0.4f, 0f, 0.2f);
            chimney.AddComponent<MeshFilter>().sharedMesh = GardenMeshes.Trunk(2.2f, 0.12f, 5);
            chimney.AddComponent<MeshRenderer>().sharedMaterial = stoneMat;
        }

        void PlacePalisade(Vector3 center)
        {
            var root = new GameObject("Palisade");
            root.transform.SetParent(built, false);
            for (int i = 0; i < 12; i++)
            {
                float a = i / 12f * Mathf.PI * 2f;
                var post = new GameObject("Stake");
                post.transform.SetParent(root.transform, false);
                post.transform.position = Dry(center + new Vector3(Mathf.Cos(a) * 7f, 0f, Mathf.Sin(a) * 5.5f));
                post.AddComponent<MeshFilter>().sharedMesh = GardenMeshes.Trunk(1.8f, 0.05f, i);
                post.AddComponent<MeshRenderer>().sharedMaterial = woodMat;
            }
        }

        void PlaceTemple(Vector3 spot)
        {
            var root = new GameObject("Temple");
            root.transform.SetParent(built, false);
            root.transform.position = Dry(spot);
            for (int i = 0; i < 6; i++)
            {
                float a = i / 6f * Mathf.PI * 2f;
                var post = new GameObject("Pillar");
                post.transform.SetParent(root.transform, false);
                post.transform.localPosition = new Vector3(Mathf.Cos(a) * 1.4f, 0f, Mathf.Sin(a) * 1.4f);
                post.AddComponent<MeshFilter>().sharedMesh = GardenMeshes.Trunk(2.4f, 0.07f, i + 2);
                post.AddComponent<MeshRenderer>().sharedMaterial = stoneMat;
            }
        }

        void PlaceMill(Vector3 spot)
        {
            var root = new GameObject("Mill");
            root.transform.SetParent(built, false);
            root.transform.position = Dry(spot);
            var tower = new GameObject("Tower");
            tower.transform.SetParent(root.transform, false);
            tower.AddComponent<MeshFilter>().sharedMesh = GardenMeshes.Trunk(3.2f, 0.28f, 4);
            tower.AddComponent<MeshRenderer>().sharedMaterial = stoneMat;
            var wheel = new GameObject("Wheel");
            wheel.transform.SetParent(root.transform, false);
            wheel.transform.localPosition = new Vector3(0.9f, 1.2f, 0f);
            wheel.transform.localRotation = Quaternion.Euler(0f, 0f, 90f);
            wheel.transform.localScale = new Vector3(0.12f, 1f, 0.12f);
            wheel.AddComponent<MeshFilter>().sharedMesh = GardenMeshes.Ellipse(8f, 8f, 12);
            wheel.AddComponent<MeshRenderer>().sharedMaterial = woodMat;
        }

        void PlaceEngine(Vector3 spot)
        {
            var root = new GameObject("Engine");
            root.transform.SetParent(built, false);
            root.transform.position = Dry(spot);
            var house = new GameObject("House");
            house.transform.SetParent(root.transform, false);
            house.AddComponent<MeshFilter>().sharedMesh = GardenMeshes.Trunk(2.2f, 0.7f, 11);
            house.AddComponent<MeshRenderer>().sharedMaterial = stoneMat;
            var stack = new GameObject("Stack");
            stack.transform.SetParent(root.transform, false);
            stack.transform.localPosition = new Vector3(0.4f, 2.1f, 0f);
            stack.AddComponent<MeshFilter>().sharedMesh = GardenMeshes.Trunk(1.6f, 0.12f, 12);
            stack.AddComponent<MeshRenderer>().sharedMaterial = stoneMat;
            var wheel = new GameObject("Flywheel");
            wheel.transform.SetParent(root.transform, false);
            wheel.transform.localPosition = new Vector3(1.2f, 1.1f, 0f);
            wheel.transform.localRotation = Quaternion.Euler(0f, 0f, 90f);
            wheel.transform.localScale = new Vector3(0.1f, 0.7f, 0.1f);
            wheel.AddComponent<MeshFilter>().sharedMesh = GardenMeshes.Ellipse(8f, 8f, 12);
            wheel.AddComponent<MeshRenderer>().sharedMaterial = woodMat;
        }

        void PlaceLamps(Vector3 hearth)
        {
            for (int i = 0; i < 4; i++)
            {
                float ang = i * Mathf.PI * 0.5f;
                var pole = new GameObject("Lamp");
                pole.transform.SetParent(built, false);
                pole.transform.position = Dry(hearth + new Vector3(Mathf.Cos(ang) * 6f, 0f, Mathf.Sin(ang) * 6f));
                var post = new GameObject("Post");
                post.transform.SetParent(pole.transform, false);
                post.AddComponent<MeshFilter>().sharedMesh = GardenMeshes.Trunk(3.2f, 0.06f, 20 + i);
                post.AddComponent<MeshRenderer>().sharedMaterial = woodMat;
                var lamp = new GameObject("LampLight");
                lamp.transform.SetParent(pole.transform, false);
                lamp.transform.localPosition = new Vector3(0f, 3.2f, 0f);
                var light = lamp.AddComponent<Light>();
                light.type = LightType.Point;
                light.color = new Color(0.85f, 0.92f, 1f);
                light.range = 14f;
                light.intensity = 900f;
                lamp.AddComponent<HDAdditionalLightData>().SetIntensity(900f, LightUnit.Lumen);
            }
        }

        void PlacePress(Vector3 spot)
        {
            var root = new GameObject("Press");
            root.transform.SetParent(built, false);
            root.transform.position = Dry(spot);
            var table = new GameObject("Table");
            table.transform.SetParent(root.transform, false);
            table.transform.localPosition = new Vector3(0f, 0.7f, 0f);
            table.transform.localScale = new Vector3(1.4f, 0.12f, 0.8f);
            table.AddComponent<MeshFilter>().sharedMesh = GardenMeshes.Boulder(3);
            table.AddComponent<MeshRenderer>().sharedMaterial = woodMat;
            var screw = new GameObject("Screw");
            screw.transform.SetParent(root.transform, false);
            screw.transform.localPosition = new Vector3(0f, 0.2f, 0f);
            screw.AddComponent<MeshFilter>().sharedMesh = GardenMeshes.Trunk(1.5f, 0.08f, 21);
            screw.AddComponent<MeshRenderer>().sharedMaterial = stoneMat;
        }

        void PlaceRoad(Vector3 from, Vector3 to)
        {
            var root = new GameObject("Road");
            root.transform.SetParent(built, false);
            Vector3 a = Dry(from);
            Vector3 b = Dry(to);
            var mesh = GardenMeshes.Ellipse(2.2f, 1.2f, 8);
            for (int i = 1; i < 10; i++)
            {
                Vector3 spot = Vector3.Lerp(a, b, i / 10f);
                var stone = new GameObject("Stone");
                stone.transform.SetParent(root.transform, false);
                stone.transform.position = Dry(spot) + Vector3.up * 0.04f;
                stone.AddComponent<MeshFilter>().sharedMesh = mesh;
                stone.AddComponent<MeshRenderer>().sharedMaterial = stoneMat;
            }
        }

        Vector3 FieldPoint(Settlement home, int index)
        {
            Vector3[] offsets =
            {
                new Vector3(4f, 0f, 6f),
                new Vector3(8f, 0f, 2f),
                new Vector3(-2f, 0f, 8f),
            };
            Vector3 offset = offsets[Mathf.Abs(index) % offsets.Length];
            return Dry(home.Hearth + offset);
        }

        Vector3 Ridge()
        {
            return Dry(new Vector3(176f, 0f, 132f));
        }

        Transform NearestTree(Vector3 hint)
        {
            Transform best = null;
            float bestDistance = float.PositiveInfinity;
            if (garden == null) return null;
            foreach (var tree in garden.Trees)
            {
                if (tree == null) continue;
                if (tree.name.Contains("Life") || tree.name.Contains("Knowledge")) continue;
                float distance = Vector3.Distance(tree.position, hint);
                if (distance < bestDistance)
                {
                    bestDistance = distance;
                    best = tree;
                }
            }
            return best;
        }

        Settlement MainHome()
        {
            if (settlements.Count == 0) return null;
            Settlement best = settlements[0];
            int bestCount = -1;
            foreach (var settlement in settlements)
            {
                int count = Members(settlement);
                if (count > bestCount)
                {
                    bestCount = count;
                    best = settlement;
                }
            }
            return best;
        }

        Settlement HomeOf(Person person)
        {
            Settlement found = FindSettlement(person.settlementId);
            return found ?? MainHome();
        }

        Settlement FindSettlement(string id)
        {
            foreach (var settlement in settlements)
            {
                if (settlement.id == id) return settlement;
            }
            return null;
        }

        Person Find(string id)
        {
            if (string.IsNullOrEmpty(id)) return null;
            foreach (var person in people)
            {
                if (person.personId == id) return person;
            }
            return null;
        }

        int Members(Settlement settlement)
        {
            int count = 0;
            foreach (var person in people)
            {
                if (person.alive && person.settlementId == settlement.id) count++;
            }
            return count;
        }

        int AliveCount()
        {
            int count = 0;
            foreach (var person in people)
            {
                if (person.alive) count++;
            }
            return count;
        }

        bool HasInfant(Person one, Person two)
        {
            foreach (var child in people)
            {
                if (!child.alive || child.body.age >= 3f) continue;
                bool theirs = child.motherId == one.personId || child.fatherId == one.personId
                    || child.motherId == two.personId || child.fatherId == two.personId;
                if (theirs) return true;
            }
            return false;
        }

        int CountTools(ToolKind tool)
        {
            int count = 0;
            foreach (var person in people)
            {
                if (person.alive && person.tool == tool) count++;
            }
            return count;
        }

        Person FindWorker(Labor labor, ToolKind tool)
        {
            foreach (var person in people)
            {
                if (person.alive && person.labor == labor && person.tool == tool) return person;
            }
            return null;
        }

        Person FindAdultWith(ToolKind tool)
        {
            foreach (var person in people)
            {
                if (person.alive && person.body.age >= 14f && person.tool == tool) return person;
            }
            return null;
        }

        int IndexOfLabor(Person person, Labor labor)
        {
            int index = 0;
            foreach (var other in people)
            {
                if (other == person) return index;
                if (other.alive && other.labor == labor) index++;
            }
            return index;
        }

        static int BedScore(Person person)
        {
            if (person.body.age < 3f) return 3;
            if (person.body.child) return 2;
            if (person.body.age >= 14f) return 1;
            return 0;
        }

        static float ToolFactor(Person person)
        {
            float factor = 1f;
            if (person.tool == ToolKind.Axe && person.labor == Labor.Gather) factor = 1.35f;
            else if (person.tool == ToolKind.Hoe && person.labor == Labor.Farm) factor = 1.45f;
            else if (person.tool == ToolKind.Hammer && person.labor == Labor.Smith) factor = 1.35f;
            if (person.tool != ToolKind.Hands)
            {
                factor *= Mathf.Lerp(1f, 0.72f, Mathf.Clamp01(person.toolWear / 40f));
            }
            return factor;
        }

        void MendTools(Settlement home, float amount)
        {
            Person worst = null;
            foreach (var person in people)
            {
                if (!person.alive || person.settlementId != home.id || person.tool == ToolKind.Hands) continue;
                if (worst == null || person.toolWear > worst.toolWear) worst = person;
            }
            if (worst != null) worst.toolWear = Mathf.Max(0f, worst.toolWear - amount);
        }

        void KeepLaw()
        {
            foreach (var home in settlements)
            {
                if (!home.lawKept || home.abandoned || Members(home) <= 0) continue;
                if (home.faith < 12f || home.dread)
                {
                    home.lawKept = false;
                    foreach (var member in people)
                    {
                        if (!member.alive || member.settlementId != home.id) continue;
                        member.body.fear = Mathf.Min(100f, member.body.fear + 8f);
                    }
                    dealLine = "The commandment breaks in " + home.placeName + ". Fear returns, and the work is no longer kept.";
                    Note(dealLine);
                    continue;
                }
                CalmMembers(home, 6f);
                dealLine = "The commandment is kept in " + home.placeName + ". The fields are worked, and fear stays low.";
            }
        }

        void KeepRite()
        {
            foreach (var home in settlements)
            {
                if (!home.temple || home.faith < 28f || !home.TakeMeal(1f)) continue;
                int eased = 0;
                foreach (var person in people)
                {
                    if (!person.alive || person.settlementId != home.id || person.body.grief < 1f) continue;
                    person.body.grief = Mathf.Max(0f, person.body.grief - 6f);
                    eased++;
                }
                if (eased > 0)
                {
                    Note("A temple rite in " + home.placeName + " eases grief. It costs a meal.");
                }
            }
        }

        Person TargetPerson()
        {
            if (director != null && director.selected != null && director.selected.alive) return director.selected;
            foreach (var person in people)
            {
                if (person.alive) return person;
            }
            return null;
        }

        Settlement TargetSettlement()
        {
            Person person = TargetPerson();
            return person != null ? HomeOf(person) : MainHome();
        }

        void CalmMembers(Settlement home, float amount)
        {
            foreach (var person in people)
            {
                if (person.alive && person.settlementId == home.id)
                {
                    person.body.fear = Mathf.Max(0f, person.body.fear - amount);
                }
            }
        }

        bool AnyMill()
        {
            foreach (var settlement in settlements)
            {
                if (settlement.mill) return true;
            }
            return false;
        }

        void SetMills(bool turning)
        {
            foreach (var settlement in settlements) settlement.millOn = turning;
        }

        Settlement OtherHold(Settlement home)
        {
            Settlement found = null;
            foreach (var settlement in settlements)
            {
                if (settlement == home || Members(settlement) <= 0) continue;
                found = settlement;
                if (settlement.id == "far") return settlement;
            }
            return found;
        }

        static void ShareMeals(Settlement a, Settlement b, float fraction)
        {
            Settlement rich = a.Meals >= b.Meals ? a : b;
            Settlement poor = rich == a ? b : a;
            float fruit = rich.fruit * fraction;
            float meat = rich.meat * fraction;
            float grain = rich.grain * fraction;
            rich.fruit -= fruit;
            rich.meat -= meat;
            rich.grain -= grain;
            poor.fruit += fruit;
            poor.meat += meat;
            poor.grain += grain;
        }

        float TotalWater()
        {
            float total = 0f;
            foreach (var settlement in settlements) total += settlement.water;
            return total;
        }

        float TotalGrain()
        {
            float total = 0f;
            foreach (var settlement in settlements) total += settlement.grain;
            return total;
        }

        string NextName()
        {
            for (int i = 0; i < Names.Length; i++)
            {
                string candidate = Names[(nameCursor + i) % Names.Length];
                if (!NameTaken(candidate))
                {
                    nameCursor = (nameCursor + i + 1) % Names.Length;
                    return candidate;
                }
            }
            return "Young one " + nextId;
        }

        string NextWildName(string[] pool)
        {
            for (int i = 0; i < pool.Length; i++)
            {
                if (!NameTaken(pool[i])) return pool[i];
            }
            return "";
        }

        bool NameUsed(string personName)
        {
            foreach (var person in people)
            {
                if (string.Equals(person.personName, personName, StringComparison.OrdinalIgnoreCase)) return true;
            }
            return false;
        }

        bool NameTaken(string name)
        {
            if (string.IsNullOrEmpty(name) || NameUsed(name)) return true;
            foreach (var hold in settlements)
            {
                if (string.Equals(hold.herdName, name, StringComparison.OrdinalIgnoreCase)) return true;
                if (string.Equals(hold.fishName, name, StringComparison.OrdinalIgnoreCase)) return true;
            }
            return false;
        }

        static string CleanName(string raw)
        {
            if (string.IsNullOrWhiteSpace(raw)) return "";
            var chars = new List<char>();
            foreach (char c in raw.Trim())
            {
                if (char.IsLetter(c) || c == ' ' || c == '\'' || c == '-') chars.Add(c);
                if (chars.Count >= 24) break;
            }
            string name = new string(chars.ToArray()).Trim();
            while (name.Contains("  ")) name = name.Replace("  ", " ");
            if (name.Length < 2) return "";
            return name;
        }

        string ChosenName(System.Func<string> fallback)
        {
            string typed = CleanName(nameDraft);
            if (string.IsNullOrEmpty(typed)) return fallback != null ? fallback() : "";
            if (NameTaken(typed) || IsKey(typed)) return "";
            return typed;
        }

        static bool IsKey(string name)
        {
            string key = GrokSpeech.LoadKey();
            if (string.IsNullOrEmpty(key)) return false;
            string trimmed = key.Trim();
            if (string.Equals(trimmed, name, StringComparison.Ordinal)) return true;
            return name.Length > 8 && trimmed.IndexOf(name, StringComparison.Ordinal) >= 0;
        }

        void GivePersonName(Person person)
        {
            if (person == null || !person.alive || person.givenName) return;
            string name = ChosenName(NextName);
            if (string.IsNullOrEmpty(name))
            {
                Note("That is not a name this valley can keep.");
                return;
            }
            string before = person.personName;
            person.personName = name;
            person.givenName = true;
            person.gameObject.name = name;
            var label = person.GetComponentInChildren<TextMesh>();
            if (label != null) label.text = name;
            nameDraft = "";
            Note("Elyon names " + before + " as " + name + ".");
            Chronicle(LastEvent);
            RefreshKin();
            Save();
        }

        void GiveHerdName(Settlement hold)
        {
            if (hold == null || hold.herd <= 0 || !string.IsNullOrEmpty(hold.herdName)) return;
            string name = ChosenName(() => NextWildName(HerdNames));
            if (string.IsNullOrEmpty(name))
            {
                Note("That is not a name this valley can keep.");
                return;
            }
            hold.herdName = name;
            nameDraft = "";
            Note("Elyon names the herd at " + hold.placeName + ": " + name + ".");
            Chronicle(LastEvent);
            RefreshKin();
            Save();
        }

        void GiveFishName(Settlement hold)
        {
            if (hold == null || hold.fish < 1f || !string.IsNullOrEmpty(hold.fishName)) return;
            string name = ChosenName(() => NextWildName(FishNames));
            if (string.IsNullOrEmpty(name))
            {
                Note("That is not a name this valley can keep.");
                return;
            }
            hold.fishName = name;
            nameDraft = "";
            Note("Elyon names the fish at " + hold.placeName + ": " + name + ".");
            Chronicle(LastEvent);
            RefreshKin();
            Save();
        }

        public string LivingNames(Person person)
        {
            Settlement hold = person == null ? null : HomeOf(person);
            string line = "";
            if (hold != null && !string.IsNullOrEmpty(hold.herdName))
            {
                line = hold.herd > 0
                    ? hold.herdName + " is the herd"
                    : hold.herdName + " is the herd, and they are not on the grass";
            }
            if (hold != null && !string.IsNullOrEmpty(hold.fishName))
            {
                string fish = hold.fish >= 1f
                    ? hold.fishName + " are the fish"
                    : hold.fishName + " are the fish, and the nets are empty";
                line = string.IsNullOrEmpty(line) ? fish : line + ". " + fish;
            }
            return line;
        }

        static string HerdCalled(Settlement hold)
        {
            return hold != null && !string.IsNullOrEmpty(hold.herdName) ? hold.herdName : "the herd";
        }

        static string FishCalled(Settlement hold)
        {
            return hold != null && !string.IsNullOrEmpty(hold.fishName) ? hold.fishName : "the fish";
        }

        static string HerdFact(Settlement hold)
        {
            if (string.IsNullOrEmpty(hold.herdName)) return "Herd " + hold.herd;
            return hold.herdName + " " + hold.herd;
        }

        static string FishFact(Settlement hold)
        {
            if (string.IsNullOrEmpty(hold.fishName)) return "Fish " + Mathf.RoundToInt(hold.fish);
            return hold.fishName + " " + Mathf.RoundToInt(hold.fish);
        }

        string NamedStock(bool herd)
        {
            string names = "";
            foreach (var hold in settlements)
            {
                if (hold.abandoned) continue;
                string name = herd ? hold.herdName : hold.fishName;
                if (string.IsNullOrEmpty(name)) continue;
                if (herd && hold.herd <= 0) continue;
                if (!herd && hold.fish < 1f) continue;
                if (names.Length > 0) names += ", ";
                names += name;
            }
            return names.Length == 0 ? "" : " (" + names + ")";
        }

        static Vector3 Dry(Vector3 point)
        {
            point.x = Mathf.Clamp(point.x, 2f, GardenMap.WorldSize - 2f);
            point.z = Mathf.Clamp(point.z, 2f, GardenMap.WorldSize - 2f);
            if (GardenMap.InWater(point.x, point.z))
            {
                Vector3 away = point - new Vector3(GardenMap.LakeX, 0f, GardenMap.LakeZ);
                away.y = 0f;
                if (away.sqrMagnitude < 0.01f) away = Vector3.right;
                for (int i = 0; i < 16 && GardenMap.InWater(point.x, point.z); i++)
                {
                    point += away.normalized * 3f;
                }
            }
            return GardenMap.OnLand(point);
        }

        void Note(string line)
        {
            if (string.IsNullOrWhiteSpace(line)) return;
            log.Add(line.Trim());
            if (log.Count > 12) log.RemoveAt(0);
            foreach (var person in people) person.worldLine = log[log.Count - 1];
        }

        public void Save()
        {
            try
            {
                var record = new ChronicleRecord
                {
                    version = 3,
                    year = year,
                    age = (int)age,
                    dayTime = director != null ? director.timeOfDay : 0.1f,
                    childrenBorn = childrenBorn,
                    knowledge = knowledge,
                    road = roadOpen,
                    charter = charter,
                    pact = pact,
                    pactWithheld = pactWithheld,
                    raidStopped = raidStopped,
                    deal = dealLine,
                    born = bornLine,
                    lost = lostLine,
                    gardenMemory = gardenLine,
                    pactMemory = pactLine,
                    raidMemory = raidLine,
                    wound = woundLine,
                    chronicleAges = ageBook.ToArray(),
                    chronicleEvents = eventBook.ToArray(),
                    chronicleRecent = recentBook.ToArray(),
                    nextId = nextId,
                    nameCursor = nameCursor,
                    settlements = new SettlementRecord[settlements.Count],
                    people = new PersonRecord[people.Count],
                    lines = log.ToArray(),
                };
                for (int i = 0; i < settlements.Count; i++) record.settlements[i] = SettlementRecord.From(settlements[i]);
                for (int i = 0; i < people.Count; i++) record.people[i] = PersonRecord.From(people[i]);
                File.WriteAllText(RecordPath(), JsonUtility.ToJson(record));
            }
            catch (Exception error)
            {
                Debug.LogWarning("Could not write the garden record: " + error.Message);
            }
        }

        bool TryLoad()
        {
            try
            {
                string path = RecordPath();
                if (!File.Exists(path)) return false;
                var record = JsonUtility.FromJson<ChronicleRecord>(File.ReadAllText(path));
                if (record == null || record.version < 2 || record.people == null || record.settlements == null) return false;
                var loaded = new List<Settlement>();
                foreach (var saved in record.settlements)
                {
                    if (saved != null && !string.IsNullOrEmpty(saved.id)) loaded.Add(saved.ToSettlement());
                }
                if (loaded.Count == 0) return false;
                var previous = new List<Settlement>(settlements);
                year = Mathf.Max(1, record.year);
                age = (AgeId)Mathf.Clamp(record.age, 0, (int)AgeId.Present);
                childrenBorn = record.childrenBorn;
                knowledge = record.knowledge;
                roadOpen = record.road;
                charter = record.charter;
                pact = record.pact;
                pactWithheld = record.pactWithheld;
                raidStopped = record.raidStopped;
                dealLine = record.deal ?? "";
                bornLine = record.born ?? "";
                lostLine = record.lost ?? "";
                gardenLine = record.gardenMemory ?? "";
                pactLine = record.pactMemory ?? "";
                raidLine = record.raidMemory ?? "";
                woundLine = record.wound ?? "";
                if (string.IsNullOrEmpty(gardenLine))
                {
                    gardenLine = age >= AgeId.Camps
                        ? "Adam and Eve woke at the garden fire. The family left the garden fire and raised a camp on the eastern meadow."
                        : "Adam and Eve woke at the garden fire.";
                }
                ageBook.Clear();
                if (record.chronicleAges != null)
                {
                    foreach (var line in record.chronicleAges)
                    {
                        if (!string.IsNullOrWhiteSpace(line)) ageBook.Add(line);
                    }
                }
                if (ageBook.Count == 0) RememberAge();
                eventBook.Clear();
                recentBook.Clear();
                if (record.chronicleEvents != null)
                {
                    foreach (var line in record.chronicleEvents)
                    {
                        if (string.IsNullOrWhiteSpace(line)) continue;
                        string trimmed = line.Trim();
                        if (trimmed.StartsWith("Year ", StringComparison.Ordinal)) KeepLine(recentBook, trimmed, 8);
                        else eventBook.Add(trimmed);
                    }
                }
                if (record.chronicleRecent != null)
                {
                    foreach (var line in record.chronicleRecent)
                    {
                        if (!string.IsNullOrWhiteSpace(line)) KeepLine(recentBook, line.Trim(), 8);
                    }
                }
                nextId = Mathf.Max(3, record.nextId);
                nameCursor = record.nameCursor;
                settlements.Clear();
                settlements.AddRange(loaded);
                try
                {
                    if (director != null) director.timeOfDay = record.dayTime;
                    foreach (var saved in record.people)
                    {
                        if (saved == null || string.IsNullOrEmpty(saved.id)) continue;
                        Person existing = Find(saved.id);
                        if (existing == null)
                        {
                            Settlement home = FindSettlement(saved.settlement) ?? MainHome();
                            if (home == null) throw new InvalidOperationException("A saved person has no hearth.");
                            existing = Spawn(string.IsNullOrEmpty(saved.personName) ? "Someone" : saved.personName, saved.eveShape, saved.age, new Vector3(saved.x, 0f, saved.z), home);
                            existing.personId = saved.id;
                        }
                        saved.Apply(existing);
                        if (!existing.alive) existing.Die();
                    }
                }
                catch (Exception spawnError)
                {
                    settlements.Clear();
                    settlements.AddRange(previous);
                    Debug.LogWarning("Could not read the garden record: " + spawnError.Message);
                    return false;
                }
                log.Clear();
                if (record.lines != null)
                {
                    foreach (var line in record.lines)
                    {
                        if (!string.IsNullOrWhiteSpace(line)) log.Add(line);
                    }
                }
                jobStamp = -1;
                AssignJobs();
                RefreshKin();
                visualsDirty = true;
                EnsureVisuals();
                return true;
            }
            catch (Exception error)
            {
                Debug.LogWarning("Could not read the garden record: " + error.Message);
                return false;
            }
        }

        static string RecordPath()
        {
            return Path.Combine(Application.persistentDataPath, RecordName);
        }

        void OnGUI()
        {
            var area = new Rect(Screen.width - 336f, 16f, 320f, Screen.height - 32f);
            GUILayout.BeginArea(area);
            GUI.color = new Color(0.96f, 0.9f, 0.75f);
            GUILayout.Label(Ages.Name(age) + "  ·  year " + year + "  ·  " + SeasonName());
            GUILayout.Label(Ages.Living(age));
            GUILayout.Label(Ages.Hand(age));
            GUILayout.Label(StockLine());
            GUILayout.Label(Ages.StillNeeded(age, Facts()));
            GUILayout.Space(6f);
            foreach (DivineAct act in ActOrder)
            {
                if (!Ages.Allows(age, act)) continue;
                if (GUILayout.Button(Ages.Label(act), GUILayout.Height(24f))) Act(act);
            }
            GUILayout.Space(6f);
            GUILayout.Label("A name for what is still unnamed");
            GUI.SetNextControlName("elyon-name");
            nameDraft = GUILayout.TextField(nameDraft, 24, GUILayout.Height(22f));
            Person namedPerson = TargetPerson();
            Settlement namedHome = TargetSettlement();
            if (namedPerson != null && !namedPerson.givenName && GUILayout.Button("Name " + namedPerson.personName, GUILayout.Height(22f)))
                GivePersonName(namedPerson);
            if (namedHome != null && age >= AgeId.Camps && namedHome.herd > 0 && string.IsNullOrEmpty(namedHome.herdName)
                && GUILayout.Button("Name the herd", GUILayout.Height(22f)))
                GiveHerdName(namedHome);
            if (namedHome != null && age >= AgeId.Farming && namedHome.fish >= 1f && string.IsNullOrEmpty(namedHome.fishName)
                && GUILayout.Button("Name the fish", GUILayout.Height(22f)))
                GiveFishName(namedHome);
            GUILayout.Space(8f);
            GUILayout.Label("Chronicle");
            int start = Mathf.Max(0, log.Count - 5);
            for (int i = start; i < log.Count; i++) GUILayout.Label(log[i]);
            if (!string.IsNullOrEmpty(loadedTimeNote)) GUILayout.Label(loadedTimeNote);
            GUILayout.EndArea();
        }

        static readonly DivineAct[] ActOrder =
        {
            DivineAct.TurnYears,
            DivineAct.Bless,
            DivineAct.Heal,
            DivineAct.SetFruit,
            DivineAct.Calm,
            DivineAct.SendGame,
            DivineAct.KeepHerd,
            DivineAct.RaiseShelter,
            DivineAct.SendRain,
            DivineAct.SendDrought,
            DivineAct.SendFlood,
            DivineAct.BlessField,
            DivineAct.GiftOre,
            DivineAct.Mend,
            DivineAct.Proclaim,
            DivineAct.GrantHarvest,
            DivineAct.WithholdHarvest,
            DivineAct.OpenRoad,
            DivineAct.KindleLesson,
            DivineAct.TurnMill,
            DivineAct.RestMill,
            DivineAct.SetEngine,
            DivineAct.BankEngine,
            DivineAct.KindleLamps,
            DivineAct.DarkenLamps,
            DivineAct.BlessPresent,
            DivineAct.KeepCommons,
            DivineAct.BlessPact,
            DivineAct.WithholdPact,
            DivineAct.StopRaid,
        };
    }

    [Serializable]
    public class ChronicleRecord
    {
        public int version;
        public int year;
        public int age;
        public float dayTime;
        public int childrenBorn;
        public float knowledge;
        public bool road;
        public bool charter;
        public bool pact;
        public bool pactWithheld;
        public bool raidStopped;
        public string deal;
        public string born;
        public string lost;
        public string gardenMemory;
        public string pactMemory;
        public string raidMemory;
        public string wound;
        public string[] chronicleAges;
        public string[] chronicleEvents;
        public string[] chronicleRecent;
        public int nextId;
        public int nameCursor;
        public SettlementRecord[] settlements;
        public PersonRecord[] people;
        public string[] lines;
    }

    [Serializable]
    public class SettlementRecord
    {
        public string id;
        public string placeName;
        public float hearthX;
        public float hearthZ;
        public float fruit;
        public float meat;
        public float grain;
        public float water;
        public float wood;
        public float ore;
        public float faith;
        public int tents;
        public int houses;
        public int fields;
        public int metalTools;
        public bool smithy;
        public bool hall;
        public bool temple;
        public bool palisade;
        public bool letters;
        public bool mill;
        public bool millOn;
        public bool engine;
        public bool engineOn;
        public float drive;
        public float power;
        public bool lights;
        public bool press;
        public bool abandoned;
        public bool dread;
        public bool pactStay;
        public bool raided;
        public bool lawKept;
        public bool willRaid;
        public int herd;
        public float fish;
        public string herdName;
        public string fishName;
        public int sky;

        public static SettlementRecord From(Settlement settlement)
        {
            return new SettlementRecord
            {
                id = settlement.id,
                placeName = settlement.placeName,
                hearthX = settlement.hearthX,
                hearthZ = settlement.hearthZ,
                fruit = settlement.fruit,
                meat = settlement.meat,
                grain = settlement.grain,
                water = settlement.water,
                wood = settlement.wood,
                ore = settlement.ore,
                faith = settlement.faith,
                tents = settlement.tents,
                houses = settlement.houses,
                fields = settlement.fields,
                metalTools = settlement.metalTools,
                smithy = settlement.smithy,
                hall = settlement.hall,
                temple = settlement.temple,
                palisade = settlement.palisade,
                letters = settlement.letters,
                mill = settlement.mill,
                millOn = settlement.millOn,
                engine = settlement.engine,
                engineOn = settlement.engineOn,
                drive = settlement.drive,
                power = settlement.power,
                lights = settlement.lights,
                press = settlement.press,
                abandoned = settlement.abandoned,
                dread = settlement.dread,
                pactStay = settlement.pactStay,
                raided = settlement.raided,
                lawKept = settlement.lawKept,
                willRaid = settlement.willRaid,
                herd = settlement.herd,
                fish = settlement.fish,
                herdName = settlement.herdName,
                fishName = settlement.fishName,
                sky = (int)settlement.sky,
            };
        }

        public Settlement ToSettlement()
        {
            return new Settlement
            {
                id = id,
                placeName = placeName,
                hearthX = hearthX,
                hearthZ = hearthZ,
                fruit = fruit,
                meat = meat,
                grain = grain,
                water = water,
                wood = wood,
                ore = ore,
                faith = faith,
                tents = tents,
                houses = houses,
                fields = fields,
                metalTools = metalTools,
                smithy = smithy,
                hall = hall,
                temple = temple,
                palisade = palisade,
                letters = letters,
                mill = mill,
                millOn = millOn,
                engine = engine,
                engineOn = engineOn,
                drive = drive,
                power = power,
                lights = lights,
                press = press,
                abandoned = abandoned,
                dread = dread,
                pactStay = pactStay,
                raided = raided,
                lawKept = lawKept,
                willRaid = willRaid,
                herd = herd,
                fish = fish,
                herdName = herdName ?? "",
                fishName = fishName ?? "",
                sky = (Sky)sky,
            };
        }
    }

    [Serializable]
    public class PersonRecord
    {
        public string id;
        public string personName;
        public string partner;
        public string mother;
        public string father;
        public string bornInto;
        public string settlement;
        public bool eveShape;
        public bool alive;
        public float age;
        public float hunger;
        public float thirst;
        public float fatigue;
        public float fever;
        public float bleeding;
        public float grief;
        public float fear;
        public int trust;
        public int tool;
        public float toolWear;
        public int favor;
        public bool blessedHouse;
        public bool spokenWork;
        public int spokenLabor;
        public bool givenName;
        public string[] memories;
        public float x;
        public float y;
        public float z;

        public static PersonRecord From(Person person)
        {
            return new PersonRecord
            {
                id = person.personId,
                personName = person.personName,
                partner = person.partnerId,
                mother = person.motherId,
                father = person.fatherId,
                bornInto = person.bornInto,
                settlement = person.settlementId,
                eveShape = person.eveShape,
                alive = person.alive,
                age = person.body.age,
                hunger = person.body.hunger,
                thirst = person.body.thirst,
                fatigue = person.body.fatigue,
                fever = person.body.fever,
                bleeding = person.body.bleeding,
                grief = person.body.grief,
                fear = person.body.fear,
                trust = person.trust,
                tool = (int)person.tool,
                toolWear = person.toolWear,
                favor = person.favor,
                blessedHouse = person.blessedHouse,
                spokenWork = person.spokenWork,
                spokenLabor = (int)person.spokenLabor,
                givenName = person.givenName,
                memories = person.MemoryLines(),
                x = person.transform.position.x,
                y = person.transform.position.y,
                z = person.transform.position.z,
            };
        }

        public void Apply(Person person)
        {
            person.personId = id;
            if (!string.IsNullOrEmpty(personName)) person.personName = personName;
            person.partnerId = partner;
            person.motherId = mother;
            person.fatherId = father;
            person.bornInto = bornInto ?? "";
            if (string.IsNullOrEmpty(person.bornInto) && (person.personId == "adam" || person.personId == "eve"))
                person.bornInto = "First family";
            person.settlementId = settlement;
            person.eveShape = eveShape;
            person.alive = alive;
            person.body.age = age;
            person.body.hunger = hunger;
            person.body.thirst = thirst;
            person.body.fatigue = fatigue;
            person.body.fever = fever;
            person.body.bleeding = bleeding;
            person.body.grief = grief;
            person.body.fear = fear;
            person.trust = trust;
            person.tool = (ToolKind)tool;
            person.toolWear = toolWear;
            person.favor = favor;
            person.blessedHouse = blessedHouse;
            person.spokenWork = spokenWork;
            person.spokenLabor = (Labor)spokenLabor;
            person.givenName = givenName || person.personId == "adam" || person.personId == "eve";
            person.RestoreMemories(memories);
            var spot = person.transform.position;
            spot.x = x;
            spot.z = z;
            person.transform.position = spot;
        }
    }
}
