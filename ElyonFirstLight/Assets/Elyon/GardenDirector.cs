using UnityEngine;

namespace Elyon
{
    public class GardenDirector : MonoBehaviour
    {
        public float timeOfDay = 0.1f;
        public int dayNumber = 1;
        public float daySeconds = 180f;
        public Person selected;

        GardenWorld world;
        LivingWorld living;
        ElyonPlayer player;
        GrokSpeech speech;
        string line = "";
        string keyDraft = "";
        bool typing;

        public bool Typing => typing;

        void Awake()
        {
            var existing = transform.Find("World");
            if (existing != null) Destroy(existing.gameObject);
            var root = new GameObject("World").transform;
            root.SetParent(transform, false);
            world = GardenBuilder.Build(root);
            living = gameObject.GetComponent<LivingWorld>();
            if (living == null) living = gameObject.AddComponent<LivingWorld>();
            living.Begin(world, root, this);
            selected = world.Adam;
            speech = gameObject.GetComponent<GrokSpeech>();
            if (speech == null) speech = gameObject.AddComponent<GrokSpeech>();
            BindCamera();
            AimSun();
            keyDraft = GrokSpeech.LoadKey();
        }

        void BindCamera()
        {
            var cam = Camera.main;
            if (cam == null) return;
            player = cam.GetComponent<ElyonPlayer>();
            if (player == null) player = cam.gameObject.AddComponent<ElyonPlayer>();
            player.director = this;
            player.focus = world.Fire;
            foreach (var behaviour in cam.GetComponents<MonoBehaviour>())
            {
                if (behaviour == null || behaviour == player) continue;
                string name = behaviour.GetType().Name;
                if (name.Contains("Controller") || name.Contains("Look")) behaviour.enabled = false;
            }
        }

        void AimSun()
        {
            var lights = FindObjectsByType<Light>(FindObjectsSortMode.None);
            foreach (var light in lights)
            {
                if (light.type != LightType.Directional) continue;
                light.transform.rotation = Quaternion.Euler(32f, 145f, 0f);
                light.color = new Color(1f, 0.93f, 0.8f);
                if (light.intensity < 20f) light.intensity = 100000f;
                light.shadows = LightShadows.Soft;
            }
        }

        void Update()
        {
            float delta = Time.deltaTime;
            bool newDay = false;
            timeOfDay += delta / daySeconds;
            if (timeOfDay >= 1f)
            {
                timeOfDay -= 1f;
                newDay = true;
            }
            if (living != null) living.Tick(delta, timeOfDay, newDay);
            BillboardNames();
            if (selected != null && !selected.alive) selected = FirstLiving();
            if (Input.GetKeyDown(KeyCode.Return) || Input.GetKeyDown(KeyCode.KeypadEnter))
            {
                if (!string.IsNullOrWhiteSpace(line) && selected != null && selected.alive)
                {
                    speech.Ask(selected, line.Trim());
                    line = "";
                }
            }
            if (Input.GetKeyDown(KeyCode.C) && selected != null && selected.alive && player != null)
            {
                Vector3 feet = player.walking ? player.transform.position : player.focus;
                selected.ComeTo(feet);
            }
        }

        void BillboardNames()
        {
            var cam = Camera.main;
            if (cam == null) return;
            if (living != null)
            {
                foreach (var person in living.People)
                {
                    if (person == null || !person.alive) continue;
                    var label = person.GetComponentInChildren<TextMesh>();
                    if (label == null) continue;
                    label.transform.rotation = Quaternion.LookRotation(label.transform.position - cam.transform.position);
                }
                return;
            }
            foreach (var person in new[] { world.Adam, world.Eve })
            {
                if (person == null) continue;
                var label = person.GetComponentInChildren<TextMesh>();
                if (label == null) continue;
                label.transform.rotation = Quaternion.LookRotation(label.transform.position - cam.transform.position);
            }
        }

        public void Select(Person person)
        {
            if (person != null && person.alive) selected = person;
        }

        void OnGUI()
        {
            var area = new Rect(16f, 16f, 420f, Screen.height - 32f);
            GUILayout.BeginArea(area);
            GUI.color = new Color(0.96f, 0.9f, 0.75f);
            string ageName = living != null ? living.AgeName : "First Light";
            GUILayout.Label("Elyon  ·  " + ageName + "  ·  year " + dayNumber + "  ·  " + ClockName());
            GUILayout.Label(player != null && player.walking ? "Walking among them" : "Above the garden");
            PeopleCards();
            GUILayout.Space(8f);
            GUILayout.Label(selected == null || !selected.alive ? "Select a person" : "Speaking with " + selected.personName);
            GUI.SetNextControlName("say");
            line = GUILayout.TextField(line, 240, GUILayout.Height(28f));
            typing = GUI.GetNameOfFocusedControl() == "say" || GUI.GetNameOfFocusedControl() == "key" || GUI.GetNameOfFocusedControl() == "elyon-name";
            GUILayout.BeginHorizontal();
            if (GUILayout.Button("Speak", GUILayout.Height(28f)) && selected != null && selected.alive)
            {
                speech.Ask(selected, line.Trim());
                line = "";
            }
            if (GUILayout.Button("Come here", GUILayout.Height(28f)) && selected != null && selected.alive && player != null)
            {
                Vector3 feet = player.walking ? player.transform.position : player.focus;
                selected.ComeTo(feet);
            }
            if (GUILayout.Button(player != null && player.walking ? "Sky" : "Walk", GUILayout.Height(28f)) && player != null)
            {
                player.SetWalking(!(player.walking));
            }
            GUILayout.EndHorizontal();
            GUILayout.Space(10f);
            GUILayout.Label("xAI key (this computer only)");
            GUI.SetNextControlName("key");
            keyDraft = GUILayout.PasswordField(keyDraft, '*', 200, GUILayout.Height(24f));
            if (GUILayout.Button("Keep the key here")) GrokSpeech.SaveKey(keyDraft);
            if (string.IsNullOrEmpty(GrokSpeech.LoadKey())) GUILayout.Label(GrokSpeech.MissingKeyLine);
            GUILayout.Label("M sky/walk   drag look   WASD move   click a person   Enter speak   C call them along the shore");
            GUILayout.Label("The hand of Elyon is on the right. The years turn there.");
            GUILayout.EndArea();
        }

        void PeopleCards()
        {
            int shown = 0;
            if (selected != null && selected.alive)
            {
                Card(selected);
                shown++;
            }
            if (living == null)
            {
                if (world.Adam != selected) Card(world.Adam);
                if (world.Eve != selected) Card(world.Eve);
                return;
            }
            foreach (var person in living.People)
            {
                if (shown >= 8) break;
                if (person == null || !person.alive || person == selected) continue;
                Card(person);
                shown++;
            }
        }

        Person FirstLiving()
        {
            if (living == null) return world.Adam;
            foreach (var person in living.People)
            {
                if (person != null && person.alive) return person;
            }
            return null;
        }

        void Card(Person person)
        {
            if (person == null) return;
            string mark = person == selected ? "  ·  chosen" : "";
            GUILayout.Label(person.personName + "  ·  " + person.ActLabel + mark);
            if (!string.IsNullOrEmpty(person.kinLine)) GUILayout.Label(person.kinLine);
            if (!string.IsNullOrEmpty(person.lineMemory)) GUILayout.Label(person.lineMemory);
            if (person.home != null)
            {
                string called = person.home.LivingNames(person);
                if (!string.IsNullOrEmpty(called)) GUILayout.Label(called);
            }
            if (person == selected && !string.IsNullOrEmpty(person.chronicle)) GUILayout.Label(person.chronicle);
            GUILayout.Label(person.body.CardLine());
            if (!string.IsNullOrEmpty(person.ToolLine())) GUILayout.Label(person.ToolLine());
            if (person.godHere) GUILayout.Label("Elyon is here.");
            if (!person.inValley) GUILayout.Label("Outside the valley.");
            if (person.favor > 0) GUILayout.Label("blessed");
            if (person.turnedAway) GUILayout.Label("A hand is withheld.");
            if (person == selected && string.IsNullOrEmpty(GrokSpeech.LoadKey()))
            {
                GUILayout.Label("A key is needed before they can answer.");
            }
            if (!string.IsNullOrEmpty(person.LatestLine)) GUILayout.Label("“" + person.LatestLine + "”");
            GUILayout.Space(6f);
        }

        string ClockName()
        {
            if (timeOfDay < 0.08f) return "Waking";
            if (timeOfDay < 0.18f) return "Morning meal";
            if (timeOfDay < 0.26f) return "Drinking";
            if (timeOfDay < 0.72f) return "Work";
            if (timeOfDay < 0.92f) return "Rest";
            return "Evening";
        }

        public void SaveRecord()
        {
            if (living != null) living.Save();
        }
    }
}
