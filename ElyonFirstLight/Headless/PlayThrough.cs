using System;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using Elyon;
using UnityEngine;

namespace Elyon.Headless
{
    /// <summary>
    /// Headless play from Adam and Eve through the present. It does not launch the editor.
    /// </summary>
    public static class PlayThrough
    {
        const string SentinelKey = "xai-test-sentinel-DO-NOT-SAVE-9f3c2a";

        static readonly string[] AgesInOrder =
        {
            "First family",
            "Camps",
            "Farming",
            "Metal and towns",
            "Cities and empires",
            "Roads and letters",
            "Mills",
            "Industry and engines",
            "Electricity and cities of light",
            "The present",
        };

        public static int Main()
        {
            string dir = Path.Combine(Path.GetTempPath(), "elyon-headless-" + Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(dir);
            Application.persistentDataPath = dir;
            Application.dataPath = Path.Combine(dir, "ElyonFirstLight");
            Directory.CreateDirectory(Application.dataPath);
            File.WriteAllText(Path.Combine(dir, GrokSpeech.KeyFileName), SentinelKey + "\n");

            var failures = new List<string>();
            try
            {
                Run(dir, failures);
            }
            catch (Exception error)
            {
                failures.Add(error.ToString());
            }

            if (failures.Count == 0)
            {
                Console.WriteLine("PASS  Adam and Eve through the present.");
                return 0;
            }

            Console.WriteLine("FAIL");
            foreach (var failure in failures) Console.WriteLine(failure);
            return 1;
        }

        static void Run(string dir, List<string> failures)
        {
            var root = new GameObject("World").transform;
            var world = new GardenWorld
            {
                Fire = new Vector3(150f, 0f, 100f),
                Adam = PersonOn("Adam", "adam", false),
                Eve = PersonOn("Eve", "eve", true),
            };
            var director = new GardenDirector();
            var living = new GameObject("Living").AddComponent<LivingWorld>();
            living.Begin(world, root, director);

            bool named = false;
            bool refusedKey = false;
            bool herd = false;
            bool herdNamed = false;
            bool fishNamed = false;
            bool rain = false;
            bool drought = false;
            bool raidStopped = false;
            bool pact = false;
            bool attended = false;
            bool blessed = false;
            bool withheld = false;
            bool kept = false;
            int stagnant = 0;
            AgeId previous = living.Age;

            for (int step = 0; step < 140 && living.Age != AgeId.Present; step++)
            {
                Story(living, director, ref named, ref refusedKey, ref herd, ref herdNamed, ref fishNamed, ref rain, ref drought, ref raidStopped, ref pact, ref attended, ref blessed, ref withheld, ref kept);
                living.Act(DivineAct.TurnYears);
                if (living.Age == previous) stagnant++;
                else
                {
                    string opened = living.StockLine();
                    Console.WriteLine("opened  " + living.AgeName + "  year " + living.Year + "  " + opened);
                    if (living.Age == AgeId.MetalTowns && opened.IndexOf("ore 0", StringComparison.Ordinal) >= 0)
                    {
                        failures.Add("Metal opened with no ore in the ridge. " + opened);
                    }
                    if (living.Age == AgeId.RoadsAndLetters && opened.IndexOf("learning 0", StringComparison.Ordinal) >= 0)
                    {
                        failures.Add("Roads opened before anyone had taught. " + opened);
                    }
                    if (living.Age == AgeId.Industry && opened.IndexOf("drive 0", StringComparison.Ordinal) >= 0)
                    {
                        failures.Add("Industry opened with no drive. " + opened);
                    }
                    if (living.Age == AgeId.ElectricLight && opened.IndexOf("power 0", StringComparison.Ordinal) >= 0)
                    {
                        failures.Add("The lamps' age opened with no power. " + opened);
                    }
                    previous = living.Age;
                    stagnant = 0;
                }
                if (stagnant == 30)
                {
                    failures.Add("Stuck in " + living.AgeName + " at year " + living.Year + ". " + living.StockLine() + " Last: " + living.LastEvent);
                    break;
                }
            }

            if (living.Age == AgeId.Present)
            {
                living.Act(DivineAct.BlessPresent);
                Console.WriteLine("opened  " + living.AgeName + "  year " + living.Year + "  " + living.StockLine());
            }

            string book = living.ChronicleText();
            string savePath = Path.Combine(dir, LivingWorld.RecordName);
            string saved = File.Exists(savePath) ? File.ReadAllText(savePath) : "";

            if (living.Age != AgeId.Present)
            {
                failures.Add("The present never opened. Ended in " + living.AgeName + " year " + living.Year + ". " + living.StockLine());
            }

            foreach (var ageName in AgesInOrder)
            {
                string line = "The age of " + ageName + " begins.";
                if (book.IndexOf(line, StringComparison.Ordinal) < 0)
                {
                    failures.Add("An age never opens in the chronicle: " + ageName);
                }
            }

            if (!named) failures.Add("No unnamed person was given a name.");
            if (!refusedKey) failures.Add("A name that is the key was not refused.");
            if (!herd) failures.Add("No herd was kept.");
            if (!herdNamed) failures.Add("The herd was never named.");
            if (!fishNamed) failures.Add("The fish were never named.");
            if (!rain) failures.Add("Rain never fell.");
            if (!drought) failures.Add("A drought never lay on a hold.");
            if (!raidStopped) failures.Add("Elyon never stopped a raid.");
            if (!pact) failures.Add("No pact was blessed.");
            if (!attended) failures.Add("Elyon never rested attention on a living person.");
            if (!blessed) failures.Add("The attended person was never blessed.");
            if (!withheld) failures.Add("A withheld person never left for another hearth.");
            if (!kept) failures.Add("The people were not kept in the valley.");

            bool birth = false;
            bool death = false;
            bool namedSerah = false;
            foreach (var person in living.People)
            {
                if (person == null) continue;
                if (!string.IsNullOrEmpty(person.motherId) || !string.IsNullOrEmpty(person.fatherId)) birth = true;
                if (!person.alive) death = true;
                if (person.givenName && person.personName == "Serah") namedSerah = true;
                if (person.personId == "adam" || person.personId == "eve") continue;
                if (person.kinLine.IndexOf("Adam", StringComparison.Ordinal) < 0
                    || person.kinLine.IndexOf("Eve", StringComparison.Ordinal) < 0)
                {
                    failures.Add("The line back to Adam or Eve breaks for " + person.personName + ": " + person.kinLine);
                }
                if (person.alive && person.chronicle.IndexOf("Adam and Eve woke at the garden fire.", StringComparison.Ordinal) < 0)
                {
                    failures.Add("The chronicle drops the garden for " + person.personName + ".");
                }
            }

            if (!birth) failures.Add("No child was born.");
            if (!death) failures.Add("No death was recorded in the people.");
            if (!namedSerah) failures.Add("The given name Serah is not kept.");
            if (book.IndexOf("Adam and Eve woke at the garden fire.", StringComparison.Ordinal) < 0)
            {
                failures.Add("The chronicle drops the garden.");
            }
            if (book.IndexOf("is born", StringComparison.Ordinal) < 0) failures.Add("The chronicle has no birth.");
            if (book.IndexOf("dies", StringComparison.Ordinal) < 0) failures.Add("The chronicle has no death.");
            if (book.IndexOf("Elyon names", StringComparison.Ordinal) < 0) failures.Add("The chronicle has no name.");
            if (book.IndexOf("A pact holds", StringComparison.Ordinal) < 0) failures.Add("The chronicle has no pact.");
            if (book.IndexOf("Elyon stops the raid", StringComparison.Ordinal) < 0) failures.Add("The chronicle has no stopped raid.");
            if (book.IndexOf("Rain", StringComparison.Ordinal) < 0) failures.Add("The chronicle has no rain.");
            if (book.IndexOf("Drought", StringComparison.Ordinal) < 0) failures.Add("The chronicle has no drought.");
            if (book.IndexOf("herd", StringComparison.OrdinalIgnoreCase) < 0) failures.Add("The chronicle has no herd.");
            if (book.IndexOf("Carmel", StringComparison.Ordinal) < 0) failures.Add("The chronicle drops the herd's name.");
            if (book.IndexOf("Kinneret", StringComparison.Ordinal) < 0) failures.Add("The chronicle drops the fish's name.");
            if (book.IndexOf("knows Elyon is here", StringComparison.Ordinal) < 0) failures.Add("The chronicle drops the presence.");
            if (book.IndexOf("is blessed", StringComparison.Ordinal) < 0) failures.Add("The chronicle drops the blessing.");
            if (book.IndexOf("withholds a hand", StringComparison.Ordinal) < 0) failures.Add("The chronicle drops the withholding.");
            if (book.IndexOf("leaves", StringComparison.Ordinal) < 0) failures.Add("The chronicle drops the leaving.");
            if (book.IndexOf("keeps the people in the valley", StringComparison.Ordinal) < 0)
            {
                failures.Add("The chronicle drops the choice to keep the people in the valley.");
            }
            if (living.ValleyCount() <= 0) failures.Add("A later year shows no one still in the valley after they were kept.");
            if (living.ValleyLine().IndexOf("In the valley: ", StringComparison.Ordinal) != 0
                || living.ValleyLine().IndexOf("no one", StringComparison.Ordinal) >= 0)
            {
                failures.Add("A later year does not name who was kept in the valley. " + living.ValleyLine());
            }
            foreach (var person in living.People)
            {
                if (person == null || !person.alive) continue;
                if (!person.inValley)
                {
                    failures.Add(person.personName + " was kept, but a later year does not show them in the valley.");
                }
            }
            bool seasonMoved = false;
            bool laterAgeSpeaks = false;
            foreach (var person in living.People)
            {
                if (person == null) continue;
                if (person.seasonsUnder > 0) seasonMoved = true;
                if (person.alive && person.ageVoice.IndexOf("keeps the people in the valley", StringComparison.Ordinal) >= 0)
                {
                    laterAgeSpeaks = true;
                }
            }
            if (!seasonMoved) failures.Add("Faith or fear never moved for a season of attention.");
            if (!laterAgeSpeaks) failures.Add("A later age does not speak of keeping the people in the valley.");
            if (living.FamilyMemory().IndexOf("keeps the people in the valley", StringComparison.Ordinal) < 0)
            {
                failures.Add("The line does not remember that the people were kept in the valley.");
            }
            string scenePath = Path.Combine(dir, LivingWorld.SceneName);
            string scene = File.Exists(scenePath) ? File.ReadAllText(scenePath) : "";
            if (scene.Length == 0) failures.Add("The scene was not written from the simulation.");
            if (scene.IndexOf("Carmel", StringComparison.Ordinal) < 0) failures.Add("The scene drops the herd.");
            if (scene.IndexOf("weather", StringComparison.Ordinal) < 0) failures.Add("The scene drops the weather.");
            if (scene.IndexOf("lights", StringComparison.Ordinal) < 0) failures.Add("The scene drops the lamps.");
            if (scene.IndexOf("personName", StringComparison.Ordinal) < 0) failures.Add("The scene drops the people.");
            if (scene.IndexOf("inValley", StringComparison.Ordinal) < 0) failures.Add("The scene does not say who is in the valley.");
            if (scene.IndexOf("In the valley:", StringComparison.Ordinal) < 0) failures.Add("The scene drops who is still in the valley.");
            if (scene.IndexOf("no one", StringComparison.Ordinal) >= 0) failures.Add("The scene says the valley is empty after the people were kept.");
            if (scene.IndexOf(SentinelKey, StringComparison.Ordinal) >= 0) failures.Add("The key is written into the scene.");
            if (book.IndexOf("returns to the nets", StringComparison.Ordinal) < 0)
            {
                failures.Add("The chronicle never brings the fish back after the drought.");
            }
            string stock = living.StockLine();
            if (stock.IndexOf("Kinneret", StringComparison.Ordinal) < 0)
            {
                failures.Add("The present stock line drops the fish. " + stock);
            }
            if (stock.IndexOf("Carmel", StringComparison.Ordinal) < 0)
            {
                failures.Add("The present stock line drops the herd. " + stock);
            }

            if (!File.Exists(savePath)) failures.Add("The world was not saved.");
            if (saved.IndexOf(SentinelKey, StringComparison.Ordinal) >= 0)
            {
                failures.Add("The key is written into the save.");
            }
            if (!File.Exists(Path.Combine(dir, GrokSpeech.KeyFileName)))
            {
                failures.Add("The key file was not present beside the save.");
            }

            ProveSentOut(failures);

            if (failures.Count > 0)
            {
                failures.Add("Year " + living.Year + "  " + living.AgeName + "  " + living.StockLine());
                failures.Add("Chronicle: " + book);
            }
            else
            {
                Console.WriteLine("year " + living.Year + "  " + living.StockLine());
                Console.WriteLine("chronicle keeps the garden, the ages, and the names.");
            }
        }

        static void Story(
            LivingWorld living,
            GardenDirector director,
            ref bool named,
            ref bool refusedKey,
            ref bool herd,
            ref bool herdNamed,
            ref bool fishNamed,
            ref bool rain,
            ref bool drought,
            ref bool raidStopped,
            ref bool pact,
            ref bool attended,
            ref bool blessed,
            ref bool withheld,
            ref bool kept)
        {
            if (!attended)
            {
                Press(living, "Rest on Adam");
                Person adam = FindId(living, "adam");
                Person eve = FindId(living, "eve");
                bool choseAdam = adam != null && adam.godHere && (eve == null || !eve.godHere);
                Press(living, "Rest on Eve");
                attended = choseAdam
                    && eve != null
                    && eve.godHere
                    && adam != null
                    && !adam.godHere
                    && living.LastEvent.IndexOf("Elyon is here", StringComparison.Ordinal) >= 0;
            }

            if (attended && !blessed)
            {
                Person eve = FindId(living, "eve");
                if (eve != null)
                {
                    director.selected = eve;
                    living.Act(DivineAct.Bless);
                    blessed = eve.blessedHouse
                        && living.LastEvent.IndexOf("is blessed", StringComparison.Ordinal) >= 0;
                }
            }

            if (!named)
            {
                Person child = Unnamed(living);
                if (child != null)
                {
                    director.selected = child;
                    if (!refusedKey)
                    {
                        Press(living, "Name " + child.personName, SentinelKey);
                        refusedKey = living.LastEvent.IndexOf("not a name", StringComparison.Ordinal) >= 0
                            && child.personName != SentinelKey
                            && !child.givenName;
                    }
                    Press(living, "Name " + child.personName, "Serah");
                    named = child.givenName && child.personName == "Serah";
                }
            }

            if (!herd && living.Age >= AgeId.Camps)
            {
                living.Act(DivineAct.KeepHerd);
                herd = living.LastEvent.IndexOf("herd", StringComparison.OrdinalIgnoreCase) >= 0
                    || living.LastEvent.IndexOf("head", StringComparison.OrdinalIgnoreCase) >= 0;
            }

            if (herd && !herdNamed && living.Age >= AgeId.Camps)
            {
                Person namer = Adult(living) ?? Unnamed(living);
                if (namer != null) director.selected = namer;
                Press(living, "Name the herd", "Carmel");
                herdNamed = living.LastEvent.IndexOf("Carmel", StringComparison.Ordinal) >= 0;
            }

            if (living.Age >= AgeId.Farming && herd && !rain)
            {
                living.Act(DivineAct.SendRain);
                rain = living.LastEvent.IndexOf("Rain", StringComparison.Ordinal) >= 0;
                if (rain && !fishNamed)
                {
                    Person namer = director.selected != null && director.selected.alive ? director.selected : Adult(living);
                    if (namer != null) director.selected = namer;
                    Press(living, "Name the fish", "Kinneret");
                    fishNamed = living.LastEvent.IndexOf("Kinneret", StringComparison.Ordinal) >= 0;
                }
            }
            else if (living.Age >= AgeId.Farming && rain && !drought && living.Year >= 12)
            {
                living.Act(DivineAct.SendDrought);
                drought = living.LastEvent.IndexOf("Drought", StringComparison.Ordinal) >= 0;
            }

            int holds = HoldCount(living.StockLine());
            if (!withheld && holds >= 2)
            {
                Person leaver = null;
                foreach (var person in living.People)
                {
                    if (person == null || !person.alive || person.body.age < 18f) continue;
                    if (person.personId == "adam" || person.personId == "eve" || person.godHere) continue;
                    if (MembersOf(living, person.settlementId) < 2) continue;
                    leaver = person;
                    break;
                }
                if (leaver != null)
                {
                    director.selected = leaver;
                    string from = leaver.settlementId;
                    living.Act(DivineAct.WithholdPerson);
                    withheld = leaver.settlementId != from
                        && living.LastEvent.IndexOf("leaves", StringComparison.Ordinal) >= 0;
                }
            }

            if (withheld && !kept)
            {
                living.Act(DivineAct.KeepValley);
                kept = living.LastEvent.IndexOf("keeps the people in the valley", StringComparison.Ordinal) >= 0;
            }

            int holdsAfter = HoldCount(living.StockLine());
            holds = holdsAfter;
            if (!raidStopped && living.Age >= AgeId.Cities && holds >= 2)
            {
                Person speaker = Adult(living);
                if (speaker != null)
                {
                    living.ApplySpoken(speaker, "raid");
                    living.Act(DivineAct.StopRaid);
                    raidStopped = true;
                }
            }
            else if (raidStopped && !pact && living.Age >= AgeId.Cities && holds >= 2)
            {
                living.Act(DivineAct.BlessPact);
                pact = living.LastEvent.IndexOf("A pact holds", StringComparison.Ordinal) >= 0;
            }
        }

        static void ProveSentOut(List<string> failures)
        {
            string dir = Path.Combine(Path.GetTempPath(), "elyon-sent-out-" + Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(dir);
            Application.persistentDataPath = dir;
            Application.dataPath = Path.Combine(dir, "ElyonFirstLight");
            Directory.CreateDirectory(Application.dataPath);

            var root = new GameObject("SentWorld").transform;
            var world = new GardenWorld
            {
                Fire = new Vector3(150f, 0f, 100f),
                Adam = PersonOn("Adam", "adam", false),
                Eve = PersonOn("Eve", "eve", true),
            };
            var director = new GardenDirector();
            var living = new GameObject("SentLiving").AddComponent<LivingWorld>();
            living.Begin(world, root, director);

            Person eve = FindId(living, "eve");
            if (eve == null)
            {
                failures.Add("The sending had no Eve to speak.");
                return;
            }

            director.selected = eve;
            new GameObject("Speech").AddComponent<GrokSpeech>().Ask(eve, "Are you there?");
            if (eve.LatestLine.IndexOf("cannot yet answer", StringComparison.Ordinal) < 0)
            {
                failures.Add("With no key, the person did not still speak. " + eve.LatestLine);
            }

            living.Act(DivineAct.SendOut);
            if (living.ValleyCount() != 0)
            {
                failures.Add("Sending them out left people in the valley. " + living.ValleyLine());
            }
            living.Act(DivineAct.TurnYears);
            if (living.ValleyCount() != 0 || living.ValleyLine().IndexOf("no one", StringComparison.Ordinal) < 0)
            {
                failures.Add("A later year still shows people in the valley after they were sent out. " + living.ValleyLine());
            }
            Person sentEve = FindId(living, "eve");
            if (sentEve == null || !sentEve.alive || sentEve.inValley)
            {
                failures.Add("Eve is still in the valley a year after she was sent out.");
            }
            string book = living.ChronicleText();
            if (book.IndexOf("sends the people out of the valley", StringComparison.Ordinal) < 0)
            {
                failures.Add("The chronicle does not remember sending the people out.");
            }
            if (living.FamilyMemory().IndexOf("sends the people out of the valley", StringComparison.Ordinal) < 0)
            {
                failures.Add("The line does not remember sending the people out.");
            }
            bool spoke = false;
            foreach (var person in living.People)
            {
                if (person != null && person.alive
                    && person.ageVoice.IndexOf("sends the people out of the valley", StringComparison.Ordinal) >= 0)
                {
                    spoke = true;
                }
            }
            if (!spoke) failures.Add("A later age does not speak of sending the people out.");

            string scenePath = Path.Combine(dir, LivingWorld.SceneName);
            string savePath = Path.Combine(dir, LivingWorld.RecordName);
            string scene = File.Exists(scenePath) ? File.ReadAllText(scenePath) : "";
            string saved = File.Exists(savePath) ? File.ReadAllText(savePath) : "";
            if (scene.IndexOf(SentinelKey, StringComparison.Ordinal) >= 0
                || saved.IndexOf(SentinelKey, StringComparison.Ordinal) >= 0)
            {
                failures.Add("The key is written into the sending.");
            }
            if (scene.IndexOf("no one", StringComparison.Ordinal) < 0)
            {
                failures.Add("The scene for a later year does not show the valley empty.");
            }
        }

        static Person FindId(LivingWorld living, string id)
        {
            foreach (var person in living.People)
            {
                if (person != null && person.alive && person.personId == id) return person;
            }
            return null;
        }

        static int MembersOf(LivingWorld living, string settlementId)
        {
            int count = 0;
            foreach (var person in living.People)
            {
                if (person != null && person.alive && person.settlementId == settlementId) count++;
            }
            return count;
        }

        static Person Unnamed(LivingWorld living)
        {
            foreach (var person in living.People)
            {
                if (person != null && person.alive && !person.givenName) return person;
            }
            return null;
        }

        static Person Adult(LivingWorld living)
        {
            foreach (var person in living.People)
            {
                if (person != null && person.alive && person.body.age >= 18f) return person;
            }
            return null;
        }

        static int HoldCount(string stock)
        {
            const string mark = "holds ";
            int at = stock.IndexOf(mark, StringComparison.Ordinal);
            if (at < 0) return 0;
            int start = at + mark.Length;
            int end = start;
            while (end < stock.Length && stock[end] >= '0' && stock[end] <= '9') end++;
            if (end == start) return 0;
            return int.Parse(stock.Substring(start, end - start));
        }

        static void Press(LivingWorld living, string button)
        {
            HeadlessInput.Button = button;
            HeadlessInput.UseDraft = false;
            HeadlessInput.Used = false;
            MethodInfo onGui = typeof(LivingWorld).GetMethod("OnGUI", BindingFlags.Instance | BindingFlags.NonPublic);
            if (onGui == null) throw new MissingMethodException("LivingWorld.OnGUI");
            onGui.Invoke(living, null);
        }

        static void Press(LivingWorld living, string button, string draft)
        {
            HeadlessInput.Button = button;
            HeadlessInput.Draft = draft;
            HeadlessInput.UseDraft = true;
            HeadlessInput.Used = false;
            MethodInfo onGui = typeof(LivingWorld).GetMethod("OnGUI", BindingFlags.Instance | BindingFlags.NonPublic);
            if (onGui == null) throw new MissingMethodException("LivingWorld.OnGUI");
            onGui.Invoke(living, null);
        }

        static Person PersonOn(string name, string who, bool eve)
        {
            var person = new GameObject(name).AddComponent<Person>();
            person.personName = name;
            person.who = who;
            person.eveShape = eve;
            person.body.age = 30f;
            return person;
        }
    }
}
