using UnityEngine;

namespace Elyon
{
    /// <summary>
    /// Sky is a free camera above the garden. Walk stands on the ground, and on the lake.
    /// </summary>
    public class ElyonPlayer : MonoBehaviour
    {
        public GardenDirector director;
        public bool walking;
        public float yaw = 35f;
        public float pitch = 28f;
        public float distance = 26f;
        public Vector3 focus = new Vector3(150f, 12f, 100f);
        public float lookYaw = 180f;
        public float lookPitch;
        Vector3 feet = new Vector3(146f, 0f, 90f);

        Camera cam;

        void Awake()
        {
            cam = GetComponent<Camera>();
            if (cam == null) cam = Camera.main;
            feet.y = GardenMap.Height(feet.x, feet.z);
        }

        void Update()
        {
            if (director != null && director.Typing) return;
            if (Input.GetKeyDown(KeyCode.M)) walking = !walking;
            if (Input.GetMouseButtonDown(0) && !PointerOnPanel()) TrySelect();
            if (walking) Walk();
            else Orbit();
        }

        void LateUpdate()
        {
            if (walking) PlaceWalkCamera();
            else PlaceSkyCamera();
        }

        public void SetWalking(bool value)
        {
            walking = value;
        }

        public void FrameAdam(Transform adam)
        {
            if (adam == null) return;
            walking = true;
            Vector3 face = adam.position + adam.forward * 3.2f;
            face.y = GardenMap.InWater(face.x, face.z) ? GardenMap.WaterY : GardenMap.Height(face.x, face.z);
            feet = face;
            Vector3 flat = adam.position - feet;
            flat.y = 0f;
            lookYaw = Mathf.Atan2(flat.x, flat.z) * Mathf.Rad2Deg;
            lookPitch = -6f;
        }

        void Orbit()
        {
            if (!PointerOnPanel() && (Input.GetMouseButton(1) || Input.GetMouseButton(0)))
            {
                yaw += Input.GetAxis("Mouse X") * 4f;
                pitch = Mathf.Clamp(pitch - Input.GetAxis("Mouse Y") * 2.5f, 8f, 70f);
            }
            float wheel = Input.GetAxis("Mouse ScrollWheel");
            if (Mathf.Abs(wheel) > 0.001f) distance = Mathf.Clamp(distance - wheel * 18f, 8f, 80f);
            Vector3 pan = Vector3.zero;
            if (Input.GetKey(KeyCode.W) || Input.GetKey(KeyCode.UpArrow)) pan += FlatForward();
            if (Input.GetKey(KeyCode.S) || Input.GetKey(KeyCode.DownArrow)) pan -= FlatForward();
            if (Input.GetKey(KeyCode.D) || Input.GetKey(KeyCode.RightArrow)) pan += FlatRight();
            if (Input.GetKey(KeyCode.A) || Input.GetKey(KeyCode.LeftArrow)) pan -= FlatRight();
            focus += pan * 18f * Time.deltaTime;
            focus.x = Mathf.Clamp(focus.x, 4f, GardenMap.WorldSize - 4f);
            focus.z = Mathf.Clamp(focus.z, 4f, GardenMap.WorldSize - 4f);
            focus.y = GardenMap.InWater(focus.x, focus.z) ? GardenMap.WaterY : GardenMap.Height(focus.x, focus.z);
        }

        void Walk()
        {
            if (!PointerOnPanel() && (Input.GetMouseButton(1) || Input.GetMouseButton(0)))
            {
                lookYaw += Input.GetAxis("Mouse X") * 3.2f;
                lookPitch = Mathf.Clamp(lookPitch - Input.GetAxis("Mouse Y") * 2.2f, -35f, 25f);
            }
            float wheel = Input.GetAxis("Mouse ScrollWheel");
            Vector3 move = Vector3.zero;
            Vector3 forward = WalkForward();
            Vector3 right = new Vector3(forward.z, 0f, -forward.x);
            if (Input.GetKey(KeyCode.W) || Input.GetKey(KeyCode.UpArrow)) move += forward;
            if (Input.GetKey(KeyCode.S) || Input.GetKey(KeyCode.DownArrow)) move -= forward;
            if (Input.GetKey(KeyCode.D) || Input.GetKey(KeyCode.RightArrow)) move += right;
            if (Input.GetKey(KeyCode.A) || Input.GetKey(KeyCode.LeftArrow)) move -= right;
            if (move.sqrMagnitude > 0.001f)
            {
                feet += move.normalized * 3.2f * Time.deltaTime;
                feet.x = Mathf.Clamp(feet.x, 1f, GardenMap.WorldSize - 1f);
                feet.z = Mathf.Clamp(feet.z, 1f, GardenMap.WorldSize - 1f);
            }
            feet.y = GardenMap.InWater(feet.x, feet.z) ? GardenMap.WaterY : GardenMap.Height(feet.x, feet.z);
            if (Mathf.Abs(wheel) > 0.001f) lookPitch = Mathf.Clamp(lookPitch - wheel * 20f, -35f, 25f);
        }

        void PlaceSkyCamera()
        {
            float yawRad = yaw * Mathf.Deg2Rad;
            float pitchRad = pitch * Mathf.Deg2Rad;
            Vector3 offset = new Vector3(
                Mathf.Sin(yawRad) * Mathf.Cos(pitchRad),
                Mathf.Sin(pitchRad),
                Mathf.Cos(yawRad) * Mathf.Cos(pitchRad));
            transform.position = focus + Vector3.up * 1.5f + offset * distance;
            transform.rotation = Quaternion.LookRotation((focus + Vector3.up * 1.2f) - transform.position, Vector3.up);
        }

        void PlaceWalkCamera()
        {
            Vector3 forward = WalkForward();
            Vector3 eye = feet + Vector3.up * 1.65f;
            transform.position = eye - forward * 2.4f + Vector3.up * 0.15f;
            Vector3 look = eye + forward * 8f + Vector3.up * (lookPitch * 0.05f);
            transform.rotation = Quaternion.LookRotation(look - transform.position, Vector3.up);
        }

        Vector3 FlatForward()
        {
            float yawRad = yaw * Mathf.Deg2Rad;
            return new Vector3(Mathf.Sin(yawRad), 0f, Mathf.Cos(yawRad));
        }

        Vector3 FlatRight()
        {
            Vector3 f = FlatForward();
            return new Vector3(f.z, 0f, -f.x);
        }

        Vector3 WalkForward()
        {
            float yawRad = lookYaw * Mathf.Deg2Rad;
            return new Vector3(Mathf.Sin(yawRad), 0f, Mathf.Cos(yawRad));
        }

        static bool PointerOnPanel()
        {
            if (Screen.width < 800) return false;
            float x = Input.mousePosition.x;
            return x < 450f || x > Screen.width - 360f;
        }

        void TrySelect()
        {
            if (director == null || cam == null) return;
            Ray ray = cam.ScreenPointToRay(Input.mousePosition);
            if (!Physics.Raycast(ray, out RaycastHit hit, 400f)) return;
            var person = hit.collider.GetComponentInParent<Person>();
            if (person != null) director.Select(person);
        }
    }
}
