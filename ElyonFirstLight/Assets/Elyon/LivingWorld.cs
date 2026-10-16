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

        readonly List<Person> people = new List<Person>();
        readonly List<Settlement> settlements = new List<Settlement>();
        readonly List<string> log = new List<string>();

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
        bool shownRoad;
        bool shownEastFire;
        bool shownFarFire;

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
                    home.faith = Mathf.Clamp(home.faith + 2f, 0f, 100f);
                    Note(person.personName + " is blessed. Trust and faith rise.");
                    break;
                case DivineAct.Heal:
                    if (person == null) { Note("No one is here to heal."); break; }
                    person.body.fever = 0f;
                    person.body.bleeding = 0f;
                    home.faith = Mathf.Clamp(home.faith + 2f, 0f, 100f);
                    Note(person.personName + " is healed.");
                    break;
                case DivineAct.SetFruit:
                    home.fruit += 6f;
                    if (person != null) person.body.hunger = Mathf.Max(0f, person.body.hunger - 10f);
                    Note("Fruit is set at " + home.placeName + ".");
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
                    home.water += 12f;
                    if (home.fields > 0) home.grain += 4f;
                    home.faith = Mathf.Clamp(home.faith + 2f, 0f, 100f);
                    Note(home.fields > 0 ? "Rain falls on the fields." : "Rain fills the stores.");
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
                    CalmMembers(home, 10f);
                    Note("A law is proclaimed in the hall. Fear eases.");
                    break;
                case DivineAct.GrantHarvest:
                    home.grain += 8f;
                    home.faith = Mathf.Clamp(home.faith + 5f, 0f, 100f);
                    Note("The harvest is granted to " + home.placeName + ".");
                    break;
                case DivineAct.WithholdHarvest:
                    home.grain *= 0.5f;
                    home.faith = Mathf.Max(0f, home.faith - 8f);
                    foreach (var member in people)
                    {
                        if (member.alive && member.settlementId == home.id)
                        {
                            member.body.fear = Mathf.Min(100f, member.body.fear + 6f);
                        }
                    }
                    Note("The harvest is withheld. Faith falls and fear rises.");
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
                    break;
            }

            RefreshKin();
            Save();
        }

        void CloseYear(bool fromGod)
        {
            ConsumeYear();
            AgeBodies();
            Mishaps();
            Deaths();
            Newcomer();
            Births();
            if (Ages.ReadyForNext(age, Facts())) Advance();
            Craft();
            BuildPlaces();
            Trade();
            foreach (var person in people) person.arrived = false;
            year++;
            if (director != null) director.dayNumber = year;
            jobStamp = -1;
            AssignJobs();
            RefreshKin();
            visualsDirty = true;
            if (fromGod && (log.Count == 0 || !log[log.Count - 1].StartsWith("Year " + (year - 1), StringComparison.Ordinal)))
            {
                Note("Year " + (year - 1) + " turns. " + Ages.Name(age) + ".");
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
                person.Die();
                Grieve(person);
                Note(person.personName + " dies. The house grieves.");
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
            Note(name + " comes to " + home.placeName + " and keeps house with " + lone.personName + ".");
            lone.Remember(name + " keeps house with me.");
            arrived.Remember("I keep house with " + lone.personName + ".");
        }

        void Births()
        {
            if (AliveCount() >= PopulationCap) return;
            for (int i = 0; i < people.Count; i++)
            {
                Person one = people[i];
                if (!one.alive || one.arrived || one.body.age < 18f || one.body.age > 48f) continue;
                if (one.body.Strength < 35f) continue;
                Person two = Find(one.partnerId);
                if (two == null || !two.alive || two.arrived) continue;
                if (two.body.age < 18f || two.body.age > 50f || two.body.Strength < 35f) continue;
                if (string.CompareOrdinal(one.personId, two.personId) > 0) continue;
                if (HasInfant(one, two)) continue;
                Settlement home = HomeOf(one);
                if (home.Meals < 8f || !home.TakeMeal(2f)) continue;
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
                childrenBorn++;
                one.body.child = true;
                two.body.child = true;
                string line = name + " is born into the house of " + one.personName + " and " + two.personName + ".";
                Note(line);
                one.Remember(line);
                two.Remember(line);
                if (AliveCount() >= PopulationCap) return;
            }
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

            if (age >= AgeId.Cities && home.hall) FoundFarHold(home);

            if (age >= AgeId.RoadsAndLetters && !home.letters && knowledge >= 4f && home.wood >= 5f)
            {
                home.wood -= 5f;
                home.letters = true;
                Note("A house of letters is kept.");
            }

            if (age >= AgeId.RoadsAndLetters && !roadOpen && home.letters && knowledge >= 8f && home.wood >= 6f && settlements.Count >= 2)
            {
                home.wood -= 6f;
                roadOpen = true;
                Note("The people open the road.");
            }

            if (age >= AgeId.Mills && !home.mill && home.wood >= 8f && home.grain >= 4f)
            {
                home.wood -= 8f;
                home.grain -= 4f;
                home.mill = true;
                home.millOn = true;
                Note("The mill is raised and set turning.");
            }

            visualsDirty = true;
        }

        void FoundFarHold(Settlement home)
        {
            if (FindSettlement("far") != null) return;
            if (Members(home) < 6) return;
            Person mover = null;
            foreach (var person in people)
            {
                if (!person.alive || person.settlementId != home.id) continue;
                if (person.personId == "adam" || person.personId == "eve") continue;
                if (person.body.age < 18f || string.IsNullOrEmpty(person.partnerId)) continue;
                Person partner = Find(person.partnerId);
                if (partner == null || !partner.alive) continue;
                mover = person;
                break;
            }

            if (mover == null) return;
            var far = new Settlement
            {
                id = "far",
                placeName = "the far hold",
                hearthX = 38f,
                hearthZ = 74f,
                fruit = 0f,
                water = 8f,
                wood = 0f,
                faith = home.faith,
            };
            far.grain = home.grain * 0.2f;
            home.grain -= far.grain;
            far.fruit = home.fruit * 0.2f;
            home.fruit -= far.fruit;
            if (home.wood >= 6f)
            {
                home.wood -= 6f;
                far.wood = 2f;
                far.tents = 1;
                far.fields = 1;
            }
            settlements.Add(far);
            MoveHousehold(mover, far);
            Note("A household plants the far hold and carries a share of the food.");
        }

        void Trade()
        {
            if (!roadOpen) return;
            Settlement main = MainHome();
            Settlement far = FindSettlement("far");
            if (main == null || far == null || main == far) return;
            Settlement rich = main.grain >= far.grain ? main : far;
            Settlement poor = rich == main ? far : main;
            float gift = rich.grain * 0.15f;
            if (gift < 0.5f) return;
            rich.grain -= gift;
            poor.grain += gift;
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
                        home.wood += 3.2f * effort;
                        home.fruit += 8.2f * effort;
                        break;
                    case Labor.Hunt:
                        home.meat += 8.5f * effort;
                        home.wood += 0.35f * effort;
                        break;
                    case Labor.Farm:
                        float mill = home.mill && home.millOn ? 1.8f : 1f;
                        float field = home.fields > 0 ? 1f : 0.35f;
                        home.grain += 9f * effort * mill * field;
                        break;
                    case Labor.Smith:
                        home.ore += 1.4f * effort;
                        break;
                    case Labor.Tend:
                        home.faith = Mathf.Clamp(home.faith + 3.5f * effort, 0f, 100f);
                        break;
                    case Labor.Teach:
                        knowledge += 1.6f * effort;
                        break;
                    case Labor.Guard:
                        person.body.fear = Mathf.Max(0f, person.body.fear - 8f * effort);
                        break;
                }
            }
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
            if (farmers + smiths + tenders + teachers + guards + hunters >= adults.Count)
            {
                farmers = Mathf.Max(0, adults.Count - (smiths + tenders + teachers + guards + hunters));
            }

            foreach (var person in adults)
            {
                Labor labor = Labor.Gather;
                if (smiths > 0) { labor = Labor.Smith; smiths--; }
                else if (tenders > 0) { labor = Labor.Tend; tenders--; }
                else if (teachers > 0) { labor = Labor.Teach; teachers--; }
                else if (guards > 0) { labor = Labor.Guard; guards--; }
                else if (farmers > 0 && age >= AgeId.Farming) { labor = Labor.Farm; farmers--; }
                else if (hunters > 0) { labor = Labor.Hunt; hunters--; }
                SetDuty(person, labor);
            }

            foreach (var person in people)
            {
                if (!person.alive || person.body.age >= 14f) continue;
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
                else
                {
                    SetDuty(person, Labor.Gather);
                }
            }
        }

        void SetDuty(Person person, Labor labor)
        {
            person.labor = labor;
            Settlement home = HomeOf(person);
            if (home == null) return;
            Vector3 site = Dry(home.Hearth);
            Transform tree = null;
            string label = "gathering";
            switch (labor)
            {
                case Labor.Gather:
                    tree = NearestTree(home.Hearth);
                    site = tree != null ? tree.position : site;
                    label = person.tool == ToolKind.Axe ? "cutting wood at a tree" : "gathering fruit and wood";
                    break;
                case Labor.Hunt:
                    site = Dry(home.Hearth + new Vector3(7f, 0f, 5f));
                    label = "hunting out from the camp";
                    break;
                case Labor.Farm:
                    site = FieldPoint(home, IndexOfLabor(person, Labor.Farm));
                    label = "tending a field";
                    break;
                case Labor.Smith:
                    site = Ridge();
                    label = "working the smithy";
                    break;
                case Labor.Tend:
                    site = Dry(home.Hearth + new Vector3(0f, 0f, 5f));
                    label = "tending the temple";
                    break;
                case Labor.Teach:
                    site = Dry(home.Hearth + new Vector3(4f, 0f, -2f));
                    label = "teaching in the house of letters";
                    break;
                case Labor.Guard:
                    site = Dry(home.Hearth + new Vector3(-3f, 0f, -2f));
                    label = "keeping watch by the hall";
                    break;
            }

            person.workTree = labor == Labor.Gather && person.tool == ToolKind.Axe ? tree : null;
            person.hasDuty = true;
            person.dutyTarget = site;
            person.dutyLabel = label;
            if (person.alive) person.Retarget();
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
                Settlement kinHome = HomeOf(person);
                if (kinHome != null) person.homeName = kinHome.placeName;
                person.kinLine = KinLine(person);
                person.worldLine = LastEvent;
            }
        }

        string KinLine(Person person)
        {
            Person mother = Find(person.motherId);
            Person father = Find(person.fatherId);
            Person partner = Find(person.partnerId);
            string line;
            if (person.personId == "adam") line = "the first man";
            else if (person.personId == "eve") line = "the first woman";
            else if (mother != null && father != null) line = "child of " + mother.personName + " and " + father.personName;
            else if (mother != null) line = "child of " + mother.personName;
            else if (father != null) line = "child of " + father.personName;
            else line = "of " + person.homeName;

            if (partner != null) line += ", keeping house with " + partner.personName;
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
            if (roadOpen && !shownRoad && far != null)
            {
                shownRoad = true;
                PlaceRoad(main.Hearth, far.Hearth);
            }
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
            if (person.tool == ToolKind.Axe && person.labor == Labor.Gather) return 1.35f;
            if (person.tool == ToolKind.Hoe && person.labor == Labor.Farm) return 1.45f;
            if (person.tool == ToolKind.Hammer && person.labor == Labor.Smith) return 1.35f;
            return 1f;
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
                if (!NameUsed(candidate))
                {
                    nameCursor = (nameCursor + i + 1) % Names.Length;
                    return candidate;
                }
            }
            return "Young one " + nextId;
        }

        bool NameUsed(string personName)
        {
            foreach (var person in people)
            {
                if (person.personName == personName) return true;
            }
            return false;
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
                    version = 2,
                    year = year,
                    age = (int)age,
                    dayTime = director != null ? director.timeOfDay : 0.1f,
                    childrenBorn = childrenBorn,
                    knowledge = knowledge,
                    road = roadOpen,
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
                age = (AgeId)Mathf.Clamp(record.age, 0, (int)AgeId.Mills);
                childrenBorn = record.childrenBorn;
                knowledge = record.knowledge;
                roadOpen = record.road;
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
            GUILayout.Label(Ages.Name(age) + "  ·  year " + year);
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
            DivineAct.RaiseShelter,
            DivineAct.SendRain,
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
            var spot = person.transform.position;
            spot.x = x;
            spot.z = z;
            person.transform.position = spot;
        }
    }
}
