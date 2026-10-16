using System.IO;
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
        ElyonPlayer player;
        GrokSpeech speech;
        string line = "";
        string keyDraft = "";
        bool typing;
        bool shots;
        int shotFrame;

        public bool Typing => typing;

        void Awake()
        {
            var existing = transform.Find("World");
            if (existing != null) Destroy(existing.gameObject);
            var root = new GameObject("World").transform;
            root.SetParent(transform, false);
            world = GardenBuilder.Build(root);
            selected = world.Adam;
            speech = gameObject.GetComponent<GrokSpeech>();
            if (speech == null) speech = gameObject.AddComponent<GrokSpeech>();
            BindCamera();
            AimSun();
            keyDraft = GrokSpeech.LoadKey();
            shots = System.Environment.GetEnvironmentVariable("ELYON_SHOT") == "1";
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
            timeOfDay += delta / daySeconds;
            if (timeOfDay >= 1f)
            {
                timeOfDay -= 1f;
                dayNumber++;
            }
            if (world.Adam != null) world.Adam.Tick(timeOfDay, delta);
            if (world.Eve != null) world.Eve.Tick(timeOfDay, delta);
            BillboardNames();
            if (Input.GetKeyDown(KeyCode.Return) || Input.GetKeyDown(KeyCode.KeypadEnter))
            {
                if (!string.IsNullOrWhiteSpace(line) && selected != null)
                {
                    speech.Ask(selected, line.Trim());
                    line = "";
                }
            }
            if (Input.GetKeyDown(KeyCode.C) && selected != null && player != null)
            {
                Vector3 feet = player.walking ? player.transform.position : player.focus;
                selected.ComeTo(feet);
            }
            if (shots) Capture();
        }

        void BillboardNames()
        {
            var cam = Camera.main;
            if (cam == null) return;
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
            selected = person;
        }

        void Capture()
        {
            shotFrame++;
            if (shotFrame == 40)
            {
                string sky = System.Environment.GetEnvironmentVariable("ELYON_SKY");
                if (!string.IsNullOrEmpty(sky)) ScreenCapture.CaptureScreenshot(sky);
            }
            if (shotFrame == 50 && player != null && world.Adam != null)
            {
                player.FrameAdam(world.Adam.transform);
            }
            if (shotFrame == 90)
            {
                string walk = System.Environment.GetEnvironmentVariable("ELYON_WALK");
                if (!string.IsNullOrEmpty(walk)) ScreenCapture.CaptureScreenshot(walk);
            }
            if (shotFrame == 110) Application.Quit();
        }

        void OnGUI()
        {
            var area = new Rect(16f, 16f, 420f, Screen.height - 32f);
            GUILayout.BeginArea(area);
            GUI.color = new Color(0.96f, 0.9f, 0.75f);
            GUILayout.Label("Elyon  ·  First Light  ·  day " + dayNumber + "  ·  " + ClockName());
            GUILayout.Label(player != null && player.walking ? "Walking among them" : "Above the garden");
            Card(world.Adam);
            Card(world.Eve);
            GUILayout.Space(8f);
            GUILayout.Label(selected == null ? "Select Adam or Eve" : "Speaking with " + selected.personName);
            GUI.SetNextControlName("say");
            line = GUILayout.TextField(line, 240, GUILayout.Height(28f));
            typing = GUI.GetNameOfFocusedControl() == "say" || GUI.GetNameOfFocusedControl() == "key";
            GUILayout.BeginHorizontal();
            if (GUILayout.Button("Speak", GUILayout.Height(28f)) && selected != null)
            {
                speech.Ask(selected, line.Trim());
                line = "";
            }
            if (GUILayout.Button("Come here", GUILayout.Height(28f)) && selected != null && player != null)
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
            GUILayout.EndArea();
        }

        void Card(Person person)
        {
            if (person == null) return;
            string mark = person == selected ? "  ·  chosen" : "";
            GUILayout.Label(person.personName + "  ·  " + person.ActLabel + mark);
            GUILayout.Label(person.body.CardLine());
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
            var record = JsonUtility.ToJson(new GardenRecord
            {
                day = dayNumber,
                time = timeOfDay,
                adamHunger = world.Adam.body.hunger,
                eveHunger = world.Eve.body.hunger,
            });
            File.WriteAllText(Path.Combine(Application.persistentDataPath, "elyon-first-light.json"), record);
        }
    }

    [System.Serializable]
    public class GardenRecord
    {
        public int day;
        public float time;
        public float adamHunger;
        public float eveHunger;
    }
}
