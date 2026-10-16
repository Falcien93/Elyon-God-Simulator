using System.Collections.Generic;
using UnityEngine;

namespace Elyon
{
    public enum DayPhase
    {
        Wake,
        Eat,
        Drink,
        Work,
        Rest,
        Coming,
    }

    [System.Serializable]
    public class Body
    {
        public float hunger = 42f;
        public float thirst = 36f;
        public float fatigue = 12f;
        public float fever;
        public float bleeding;
        public float age = 30f;
        public float grief;
        public float fear;
        public bool child;

        public float Strength
        {
            get
            {
                float burden =
                    hunger * 0.18f +
                    thirst * 0.22f +
                    fatigue * 0.32f +
                    fever * 0.45f +
                    bleeding * 0.55f +
                    grief * 0.2f +
                    fear * 0.16f +
                    (child ? 18f : 0f) +
                    (age < 14f ? (14f - age) * 1.5f : 0f) +
                    Mathf.Max(0f, age - 30f) * 0.15f;
                return Mathf.Clamp(100f - burden, 8f, 100f);
            }
        }

        public float Speed => Mathf.Lerp(0.45f, 1.85f, Strength / 100f);

        public string CardLine()
        {
            string tired = fatigue > 55f ? " Tired. Moving slowly." : "";
            return
                "hunger " + Mathf.RoundToInt(hunger) +
                "   thirst " + Mathf.RoundToInt(thirst) +
                "   fatigue " + Mathf.RoundToInt(fatigue) +
                "\nfever " + Mathf.RoundToInt(fever) +
                "   bleeding " + Mathf.RoundToInt(bleeding) +
                "   grief " + Mathf.RoundToInt(grief) +
                "   fear " + Mathf.RoundToInt(fear) +
                "\nage " + Mathf.RoundToInt(age) +
                (age < 14f ? "   young" : "") +
                "   child " + (child ? "in their care" : "none") +
                "   strength " + Mathf.RoundToInt(Strength) +
                tired;
        }
    }

    public class Person : MonoBehaviour
    {
        public string who = "adam";
        public string personName = "Adam";
        public string personId = "";
        public string partnerId = "";
        public string motherId = "";
        public string fatherId = "";
        public string settlementId = "eden";
        public string kinLine = "";
        public string bornInto = "";
        public string lineMemory = "";
        public string homeName = "the fire";
        public string ageName = "First family";
        public string ageVoice = "";
        public string worldLine = "";
        public string dutyLabel = "";
        public Vector3 dutyTarget;
        public bool hasDuty;
        public bool alive = true;
        public bool arrived;
        public bool scarce;
        public bool eveShape;
        public Labor labor = Labor.Gather;
        public ToolKind tool = ToolKind.Hands;
        public float toolWear;
        public LivingWorld home;
        public Body body = new Body();
        public int trust = 40;
        public int favor;
        public bool blessedHouse;
        public string holdFacts = "";
        public bool spokenWork;
        public Labor spokenLabor = Labor.Gather;
        public Transform hips;
        public Transform thighL;
        public Transform thighR;
        public Transform shinL;
        public Transform shinR;
        public Transform shoulderL;
        public Transform shoulderR;
        public Transform axe;
        public float standHip = 0.92f;
        public float massKg = 74f;
        public Transform workTree;
        public Vector3 seat;
        public Vector3 pot;
        public Vector3 cup;
        public Vector3 fire;

        readonly List<string> memories = new List<string>();
        readonly List<string> said = new List<string>();
        List<Vector3> path = new List<Vector3>();
        int pathIndex;
        Vector3 goal;
        DayPhase phase = DayPhase.Eat;
        DayPhase posed = (DayPhase)(-1);
        bool sitting;
        float swing;
        bool coming;
        bool moving;
        float gait;

        public string LatestLine => said.Count == 0 ? "" : said[said.Count - 1];

        public string ToolLine()
        {
            if (tool == ToolKind.Hands) return "";
            string name = tool == ToolKind.Axe ? "axe" : tool == ToolKind.Hoe ? "hoe" : "hammer";
            int edge = Mathf.RoundToInt(100f - Mathf.Clamp(toolWear, 0f, 40f) * 2.5f);
            return name + "   edge " + edge;
        }

        public string Persona => personName + ", " + (string.IsNullOrEmpty(kinLine) ? "awake and speaking with Elyon" : kinLine);

        public bool Working => alive && !coming && phase == DayPhase.Work;

        public string ActLabel
        {
            get
            {
                if (coming) return "following the shore toward Elyon";
                if (phase == DayPhase.Work && !string.IsNullOrEmpty(dutyLabel)) return dutyLabel;
                switch (phase)
                {
                    case DayPhase.Wake: return "waking, seated at the fire";
                    case DayPhase.Eat: return "eating from the pot";
                    case DayPhase.Drink: return "drinking from the cup";
                    case DayPhase.Work: return "walking the shore to a tree, then swinging an axe";
                    case DayPhase.Rest: return "resting by the fire";
                    default: return "following the shore toward Elyon";
                }
            }
        }

        public void BindDay(Vector3 firePoint, Vector3 potPoint, Vector3 cupPoint, Transform tree, Vector3 seatPoint)
        {
            fire = firePoint;
            pot = potPoint;
            cup = cupPoint;
            workTree = tree;
            seat = seatPoint;
            transform.position = GardenMap.OnLand(seat);
            phase = DayPhase.Eat;
            SetGoal(pot);
        }

        public string WorldBrief()
        {
            string memory = memories.Count == 0 ? "" : " You remember: " + string.Join(" | ", memories);
            string news = string.IsNullOrEmpty(worldLine) ? "" : " Just now: " + worldLine;
            string voice = string.IsNullOrEmpty(ageVoice) ? "" : " " + ageVoice;
            string work = string.IsNullOrEmpty(dutyLabel) ? "" : " Your work is " + dutyLabel + ".";
            string facts = string.IsNullOrEmpty(holdFacts) ? "" : " " + holdFacts;
            string people = string.IsNullOrEmpty(kinLine) ? "" : " Your parents and your people: " + kinLine + ".";
            string line = string.IsNullOrEmpty(lineMemory) ? "" : " The line remembers: " + lineMemory;
            return "The age is " + ageName + "." + voice + " You are in " + homeName + ". It is " + ActLabel + "." + work + people + line + " " + body.CardLine().Replace("\n", " ") + "." + facts + news + memory;
        }

        public void Remember(string line)
        {
            if (string.IsNullOrWhiteSpace(line)) return;
            string trimmed = line.Trim();
            for (int i = 0; i < memories.Count; i++)
            {
                if (memories[i] == trimmed) return;
            }
            memories.Add(trimmed);
            if (memories.Count > 8) memories.RemoveAt(0);
        }

        public string[] MemoryLines()
        {
            var copy = new string[memories.Count];
            for (int i = 0; i < memories.Count; i++) copy[i] = memories[i];
            return copy;
        }

        public void RestoreMemories(string[] lines)
        {
            memories.Clear();
            if (lines == null) return;
            for (int i = 0; i < lines.Length; i++) Remember(lines[i]);
        }

        public void ApplyTrust(int delta)
        {
            trust = Mathf.Clamp(trust + delta, 0, 100);
        }

        public void HearLocal(string line, bool fromMind)
        {
            if (string.IsNullOrWhiteSpace(line)) return;
            said.Add(line.Trim());
            if (said.Count > 4) said.RemoveAt(0);
            if (fromMind && line.IndexOf("eat", System.StringComparison.OrdinalIgnoreCase) >= 0)
            {
                body.hunger = Mathf.Max(0f, body.hunger - 8f);
            }
        }

        public void ComeTo(Vector3 elyon)
        {
            coming = true;
            SetGoal(elyon);
        }

        public void Retarget()
        {
            if (!alive) return;
            SetGoal(GoalForPhase());
        }

        public void ApplyAge(float years)
        {
            body.age = years;
            float scale = years >= 16f ? 1f : Mathf.Lerp(0.42f, 1f, Mathf.Max(0f, years) / 16f);
            var armature = transform.Find("Armature");
            if (armature != null) armature.localScale = Vector3.one * scale;
            var capsule = GetComponent<CapsuleCollider>();
            float height = (eveShape ? 1.62f : 1.78f) * scale;
            if (capsule != null)
            {
                capsule.height = height;
                capsule.radius = (eveShape ? 0.16f : 0.18f) * scale;
                capsule.center = new Vector3(0f, height * 0.5f, 0f);
            }
            var bodyPhysics = GetComponent<Rigidbody>();
            if (bodyPhysics != null) bodyPhysics.mass = (eveShape ? 58f : 78f) * scale;
            massKg = (eveShape ? 58f : 78f) * scale;
        }

        public void Die()
        {
            alive = false;
            coming = false;
            moving = false;
            foreach (var renderer in GetComponentsInChildren<Renderer>()) renderer.enabled = false;
            var capsule = GetComponent<CapsuleCollider>();
            if (capsule != null) capsule.enabled = false;
            var bodyPhysics = GetComponent<Rigidbody>();
            if (bodyPhysics != null) bodyPhysics.detectCollisions = false;
        }

        public void Tick(float timeOfDay, float delta)
        {
            if (!alive) return;
            TickBody(delta);
            if (!coming)
            {
                DayPhase next = PhaseAt(timeOfDay);
                if (next != phase)
                {
                    phase = next;
                    OnEnterPhase();
                }
            }
            else if (Vector3.Distance(transform.position, goal) < 1.7f)
            {
                coming = false;
                phase = PhaseAt(timeOfDay);
                OnEnterPhase();
            }

            Follow(delta);
            Pose(delta);
        }

        public static DayPhase PhaseAt(float timeOfDay)
        {
            if (timeOfDay < 0.08f) return DayPhase.Wake;
            if (timeOfDay < 0.18f) return DayPhase.Eat;
            if (timeOfDay < 0.26f) return DayPhase.Drink;
            if (timeOfDay < 0.72f) return DayPhase.Work;
            return DayPhase.Rest;
        }

        void OnEnterPhase()
        {
            if (phase == DayPhase.Eat)
            {
                bool ate = home == null || home.TryServeMeal(this);
                body.hunger = Mathf.Max(0f, body.hunger - (ate ? 22f : 6f));
                if (!ate) body.fear = Mathf.Min(100f, body.fear + 4f);
            }
            if (phase == DayPhase.Drink)
            {
                bool drank = home == null || home.TryServeWater(this);
                body.thirst = Mathf.Max(0f, body.thirst - (drank ? 28f : 8f));
            }
            if (phase == DayPhase.Rest)
            {
                bool bed = home == null || home.HasBed(this);
                body.fatigue = Mathf.Max(0f, body.fatigue - (bed ? 24f : 8f));
            }
            SetGoal(GoalForPhase());
        }

        Vector3 GoalForPhase()
        {
            if (phase == DayPhase.Work && hasDuty) return dutyTarget;
            switch (phase)
            {
                case DayPhase.Eat: return pot;
                case DayPhase.Drink: return cup;
                case DayPhase.Work: return workTree != null ? workTree.position : seat;
                default: return seat;
            }
        }

        void SetGoal(Vector3 world)
        {
            goal = world;
            path = GardenMap.Route(transform.position, world);
            pathIndex = 0;
            if (path.Count > 1 && Vector3.Distance(path[0], transform.position) < 0.4f) pathIndex = 1;
        }

        void Follow(float delta)
        {
            if (pathIndex >= path.Count)
            {
                moving = false;
                sitting = phase != DayPhase.Work && phase != DayPhase.Coming && !coming;
                return;
            }

            Vector3 target = path[pathIndex];
            Vector3 flat = target - transform.position;
            flat.y = 0f;
            if (flat.magnitude < 0.35f)
            {
                pathIndex++;
                sitting = false;
                return;
            }

            sitting = false;
            moving = true;
            Vector3 step = flat.normalized * body.Speed * delta;
            if (step.magnitude > flat.magnitude) step = flat;
            Vector3 next = transform.position + step;
            if (GardenMap.InWater(next.x, next.z))
            {
                pathIndex++;
                return;
            }
            next.y = GardenMap.Height(next.x, next.z);
            var bodyPhysics = GetComponent<Rigidbody>();
            if (bodyPhysics != null) bodyPhysics.MovePosition(next);
            else transform.position = next;
            if (flat.sqrMagnitude > 0.001f)
            {
                Quaternion turn = Quaternion.Slerp(transform.rotation, Quaternion.LookRotation(flat.normalized, Vector3.up), 8f * delta);
                if (bodyPhysics != null) bodyPhysics.MoveRotation(turn);
                else transform.rotation = turn;
            }
        }

        void TickBody(float delta)
        {
            float hungerRate = scarce ? 0.2f : 0.09f;
            body.hunger = Mathf.Clamp(body.hunger + hungerRate * delta, 0f, 100f);
            body.thirst = Mathf.Clamp(body.thirst + 0.11f * delta, 0f, 100f);
            float work = phase == DayPhase.Work ? 0.22f : -0.04f;
            body.fatigue = Mathf.Clamp(body.fatigue + work * delta, 0f, 100f);
            if (body.bleeding > 0f) body.bleeding = Mathf.Max(0f, body.bleeding - 0.02f * delta);
            if (body.fatigue > 70f) body.fear = Mathf.Min(100f, body.fear + 0.02f * delta);
        }

        void Pose(float delta)
        {
            bool chop = phase == DayPhase.Work && workTree != null && Vector3.Distance(transform.position, workTree.position) < 1.8f;
            if (chop)
            {
                swing += delta * 2.4f;
                sitting = false;
            }
            else swing = 0f;

            if (hips == null) return;
            bool sitNow = sitting && !chop;
            hips.localPosition = new Vector3(0f, sitNow ? standHip * 0.55f : standHip, sitNow ? 0.05f : 0f);
            float strideL = 0f;
            float strideR = 0f;
            if (!sitNow && moving && !chop)
            {
                gait += delta * Mathf.Max(0.6f, body.Speed) * 3.4f;
                strideL = Mathf.Sin(gait) * 28f;
                strideR = Mathf.Sin(gait + Mathf.PI) * 28f;
            }
            if (thighL != null) thighL.localRotation = Quaternion.Euler(sitNow ? 78f : 6f + strideL, 6f, 3f);
            if (thighR != null) thighR.localRotation = Quaternion.Euler(sitNow ? 78f : 6f + strideR, -6f, -3f);
            if (shinL != null) shinL.localRotation = Quaternion.Euler(sitNow ? -84f : -Mathf.Max(0f, -strideL) * 1.15f, 0f, 0f);
            if (shinR != null) shinR.localRotation = Quaternion.Euler(sitNow ? -84f : -Mathf.Max(0f, -strideR) * 1.15f, 0f, 0f);
            if (shoulderL != null && !chop)
            {
                shoulderL.localRotation = Quaternion.Euler(8f - strideL * 0.45f, 0f, -12f);
            }
            if (shoulderR != null)
            {
                float axeAngle = chop ? Mathf.Lerp(-20f, 70f, Mathf.PingPong(swing, 1f)) : 8f - strideR * 0.45f;
                shoulderR.localRotation = Quaternion.Euler(axeAngle, 0f, 12f);
            }
            if (axe != null) axe.gameObject.SetActive(body.age >= 14f && tool == ToolKind.Axe && (chop || phase == DayPhase.Work));
            if (sitNow && posed != phase)
            {
                Vector3 look = GoalForPhase() - transform.position;
                look.y = 0f;
                if (look.sqrMagnitude > 0.01f) transform.rotation = Quaternion.LookRotation(look.normalized, Vector3.up);
            }
            posed = phase;
        }
    }
}
