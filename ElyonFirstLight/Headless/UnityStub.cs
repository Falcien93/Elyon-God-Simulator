using System;
using System.Collections;
using System.Collections.Generic;

namespace UnityEngine
{
    public static class HeadlessInput
    {
        public static string Button = "";
        public static string Draft = "";
        public static bool UseDraft;
        public static bool Used;
    }

    public class Object
    {
        public virtual string name { get; set; }

        public static void Destroy(Object target)
        {
            if (target is GameObject go) go.SetActive(false);
            else if (target is Component component && component.gameObject != null)
            {
                component.gameObject.Detach(component);
            }
        }

        public static T FindFirstObjectByType<T>() where T : Object
        {
            return null;
        }

        public static T[] FindObjectsByType<T>(FindObjectsSortMode sort) where T : Object
        {
            return new T[0];
        }
    }

    public enum FindObjectsSortMode
    {
        None,
        InstanceID,
    }

    public class Component : Object
    {
        public GameObject gameObject;
        public Transform transform;
        public bool enabled = true;

        public T GetComponent<T>() where T : Component
        {
            return gameObject == null ? null : gameObject.GetComponent<T>();
        }

        public T[] GetComponents<T>() where T : Component
        {
            return gameObject == null ? new T[0] : gameObject.GetComponents<T>();
        }

        public T GetComponentInChildren<T>() where T : Component
        {
            return gameObject == null ? null : gameObject.GetComponentInChildren<T>();
        }

        public T GetComponentInParent<T>() where T : Component
        {
            GameObject current = gameObject;
            while (current != null)
            {
                T found = current.GetComponent<T>();
                if (found != null) return found;
                current = current.transform != null && current.transform.parent != null
                    ? current.transform.parent.gameObject
                    : null;
            }
            return null;
        }

        public T[] GetComponentsInChildren<T>() where T : Component
        {
            var list = new List<T>();
            if (gameObject != null) gameObject.Collect(list);
            return list.ToArray();
        }
    }

    public class Behaviour : Component
    {
    }

    public class MonoBehaviour : Behaviour
    {
        public Coroutine StartCoroutine(IEnumerator routine)
        {
            return null;
        }
    }

    public class GameObject : Object
    {
        public Transform transform;
        readonly List<Component> components = new List<Component>();
        bool active = true;

        public GameObject(string name)
        {
            this.name = name;
            transform = new Transform();
            transform.gameObject = this;
            transform.transform = transform;
        }

        public void SetActive(bool value)
        {
            active = value;
        }

        public T AddComponent<T>() where T : Component, new()
        {
            var component = new T();
            component.gameObject = this;
            component.transform = transform;
            components.Add(component);
            return component;
        }

        public T GetComponent<T>() where T : Component
        {
            foreach (var component in components)
            {
                if (component is T typed) return typed;
            }
            return null;
        }

        public T[] GetComponents<T>() where T : Component
        {
            var list = new List<T>();
            foreach (var component in components)
            {
                if (component is T typed) list.Add(typed);
            }
            return list.ToArray();
        }

        public T GetComponentInChildren<T>() where T : Component
        {
            T own = GetComponent<T>();
            if (own != null) return own;
            foreach (var child in transform.children)
            {
                T found = child.gameObject.GetComponentInChildren<T>();
                if (found != null) return found;
            }
            return null;
        }

        public void Collect<T>(List<T> list) where T : Component
        {
            foreach (var component in components)
            {
                if (component is T typed) list.Add(typed);
            }
            foreach (var child in transform.children) child.gameObject.Collect(list);
        }

        public void Detach(Component component)
        {
            components.Remove(component);
        }

        public static GameObject CreatePrimitive(PrimitiveType type)
        {
            var go = new GameObject(type.ToString());
            go.AddComponent<MeshCollider>();
            return go;
        }
    }

    public enum PrimitiveType
    {
        Sphere,
        Capsule,
        Cylinder,
        Cube,
        Plane,
        Quad,
    }

    public class Transform : Component
    {
        public Vector3 localPosition;
        public Quaternion localRotation = Quaternion.identity;
        public Vector3 localScale = Vector3.one;
        public Transform parent;
        public readonly List<Transform> children = new List<Transform>();

        public int childCount
        {
            get { return children.Count; }
        }

        public Vector3 position
        {
            get { return parent == null ? localPosition : parent.TransformPoint(localPosition); }
            set { localPosition = parent == null ? value : parent.InverseTransformPoint(value); }
        }

        public Quaternion rotation
        {
            get { return parent == null ? localRotation : parent.rotation * localRotation; }
            set { localRotation = parent == null ? value : Quaternion.Inverse(parent.rotation) * value; }
        }

        public override string name
        {
            get { return gameObject != null ? gameObject.name : base.name; }
            set { if (gameObject != null) gameObject.name = value; else base.name = value; }
        }

        public Vector3 forward
        {
            get { return rotation * Vector3.forward; }
        }

        public Vector3 up
        {
            get { return rotation * Vector3.up; }
        }

        public Vector3 right
        {
            get { return rotation * Vector3.right; }
        }

        public Matrix4x4 worldToLocalMatrix
        {
            get { return Matrix4x4.identity; }
        }

        public Matrix4x4 localToWorldMatrix
        {
            get { return Matrix4x4.identity; }
        }

        public Transform GetChild(int index)
        {
            return children[index];
        }

        public void SetParent(Transform next, bool worldPositionStays)
        {
            Vector3 world = worldPositionStays ? position : Vector3.zero;
            if (parent != null) parent.children.Remove(this);
            parent = next;
            if (next != null) next.children.Add(this);
            if (worldPositionStays) position = world;
        }

        public Transform Find(string path)
        {
            foreach (var child in children)
            {
                if (child.gameObject != null && child.gameObject.name == path) return child;
            }
            return null;
        }

        public Vector3 TransformPoint(Vector3 point)
        {
            var scaled = new Vector3(point.x * localScale.x, point.y * localScale.y, point.z * localScale.z);
            return position + (localRotation * scaled);
        }

        public Vector3 InverseTransformPoint(Vector3 world)
        {
            Vector3 delta = world - position;
            Vector3 turned = Quaternion.Inverse(localRotation) * delta;
            return new Vector3(SafeDiv(turned.x, localScale.x), SafeDiv(turned.y, localScale.y), SafeDiv(turned.z, localScale.z));
        }

        public Vector3 InverseTransformDirection(Vector3 direction)
        {
            return Quaternion.Inverse(rotation) * direction;
        }

        static float SafeDiv(float value, float scale)
        {
            return Math.Abs(scale) < 0.0001f ? 0f : value / scale;
        }
    }

    public struct Vector2
    {
        public float x;
        public float y;

        public Vector2(float x, float y)
        {
            this.x = x;
            this.y = y;
        }

        public static Vector2 one
        {
            get { return new Vector2(1f, 1f); }
        }

        public static Vector2 zero
        {
            get { return new Vector2(0f, 0f); }
        }

        public static Vector2 operator +(Vector2 a, Vector2 b)
        {
            return new Vector2(a.x + b.x, a.y + b.y);
        }

        public static Vector2 operator *(Vector2 a, float b)
        {
            return new Vector2(a.x * b, a.y * b);
        }
    }

    public struct Vector3
    {
        public float x;
        public float y;
        public float z;

        public Vector3(float x, float y, float z)
        {
            this.x = x;
            this.y = y;
            this.z = z;
        }

        public static Vector3 zero
        {
            get { return new Vector3(0f, 0f, 0f); }
        }

        public static Vector3 one
        {
            get { return new Vector3(1f, 1f, 1f); }
        }

        public static Vector3 up
        {
            get { return new Vector3(0f, 1f, 0f); }
        }

        public static Vector3 forward
        {
            get { return new Vector3(0f, 0f, 1f); }
        }

        public static Vector3 right
        {
            get { return new Vector3(1f, 0f, 0f); }
        }

        public float sqrMagnitude
        {
            get { return x * x + y * y + z * z; }
        }

        public float magnitude
        {
            get { return (float)Math.Sqrt(sqrMagnitude); }
        }

        public Vector3 normalized
        {
            get
            {
                float mag = magnitude;
                if (mag < 0.0001f) return zero;
                return this / mag;
            }
        }

        public void Normalize()
        {
            Vector3 n = normalized;
            x = n.x;
            y = n.y;
            z = n.z;
        }

        public static float Distance(Vector3 a, Vector3 b)
        {
            return (a - b).magnitude;
        }

        public static Vector3 Lerp(Vector3 a, Vector3 b, float t)
        {
            return a + (b - a) * t;
        }

        public static Vector3 Cross(Vector3 a, Vector3 b)
        {
            return new Vector3(a.y * b.z - a.z * b.y, a.z * b.x - a.x * b.z, a.x * b.y - a.y * b.x);
        }

        public static float Dot(Vector3 a, Vector3 b)
        {
            return a.x * b.x + a.y * b.y + a.z * b.z;
        }

        public static Vector3 operator +(Vector3 a, Vector3 b)
        {
            return new Vector3(a.x + b.x, a.y + b.y, a.z + b.z);
        }

        public static Vector3 operator -(Vector3 a, Vector3 b)
        {
            return new Vector3(a.x - b.x, a.y - b.y, a.z - b.z);
        }

        public static Vector3 operator -(Vector3 a)
        {
            return new Vector3(-a.x, -a.y, -a.z);
        }

        public static Vector3 operator *(Vector3 a, float b)
        {
            return new Vector3(a.x * b, a.y * b, a.z * b);
        }

        public static Vector3 operator *(float b, Vector3 a)
        {
            return a * b;
        }

        public static Vector3 operator /(Vector3 a, float b)
        {
            return new Vector3(a.x / b, a.y / b, a.z / b);
        }
    }

    public struct Quaternion
    {
        public float x;
        public float y;
        public float z;
        public float w;

        public Quaternion(float x, float y, float z, float w)
        {
            this.x = x;
            this.y = y;
            this.z = z;
            this.w = w;
        }

        public static Quaternion identity
        {
            get { return new Quaternion(0f, 0f, 0f, 1f); }
        }

        public static Quaternion Euler(float x, float y, float z)
        {
            return identity;
        }

        public static Quaternion Euler(Vector3 euler)
        {
            return identity;
        }

        public static Quaternion Inverse(Quaternion q)
        {
            return new Quaternion(-q.x, -q.y, -q.z, q.w);
        }

        public static Quaternion LookRotation(Vector3 forward)
        {
            return identity;
        }

        public static Quaternion LookRotation(Vector3 forward, Vector3 upwards)
        {
            return identity;
        }

        public static Quaternion Slerp(Quaternion a, Quaternion b, float t)
        {
            return t < 0.5f ? a : b;
        }

        public static Vector3 operator *(Quaternion q, Vector3 v)
        {
            if (q.x == 0f && q.y == 0f && q.z == 0f) return v;
            var u = new Vector3(q.x, q.y, q.z);
            return (u * (2f * Vector3.Dot(u, v)))
                + (v * (q.w * q.w - Vector3.Dot(u, u)))
                + (Vector3.Cross(u, v) * (2f * q.w));
        }

        public static Quaternion operator *(Quaternion a, Quaternion b)
        {
            return new Quaternion(
                a.w * b.x + a.x * b.w + a.y * b.z - a.z * b.y,
                a.w * b.y - a.x * b.z + a.y * b.w + a.z * b.x,
                a.w * b.z + a.x * b.y - a.y * b.x + a.z * b.w,
                a.w * b.w - a.x * b.x - a.y * b.y - a.z * b.z);
        }
    }

    public struct Color
    {
        public float r;
        public float g;
        public float b;
        public float a;

        public static Color white
        {
            get { return new Color(1f, 1f, 1f, 1f); }
        }

        public Color(float r, float g, float b)
        {
            this.r = r;
            this.g = g;
            this.b = b;
            this.a = 1f;
        }

        public Color(float r, float g, float b, float a)
        {
            this.r = r;
            this.g = g;
            this.b = b;
            this.a = a;
        }
    }

    public struct Rect
    {
        public float x;
        public float y;
        public float width;
        public float height;

        public Rect(float x, float y, float width, float height)
        {
            this.x = x;
            this.y = y;
            this.width = width;
            this.height = height;
        }
    }

    public struct Bounds
    {
        public Vector3 center;
        public Vector3 size;

        public Bounds(Vector3 center, Vector3 size)
        {
            this.center = center;
            this.size = size;
        }
    }

    public struct BoneWeight
    {
        public int boneIndex0;
        public int boneIndex1;
        public int boneIndex2;
        public int boneIndex3;
        public float weight0;
        public float weight1;
        public float weight2;
        public float weight3;
    }

    public struct Matrix4x4
    {
        public static Matrix4x4 identity
        {
            get { return new Matrix4x4(); }
        }

        public static Matrix4x4 operator *(Matrix4x4 a, Matrix4x4 b)
        {
            return identity;
        }
    }

    public struct Ray
    {
        public Vector3 origin;
        public Vector3 direction;
    }

    public struct RaycastHit
    {
        public Collider collider;
    }

    public static class Mathf
    {
        public const float PI = (float)Math.PI;
        public const float Deg2Rad = PI / 180f;
        public const float Rad2Deg = 180f / PI;

        public static float Abs(float v)
        {
            return Math.Abs(v);
        }

        public static int Abs(int v)
        {
            return Math.Abs(v);
        }

        public static float Sin(float v)
        {
            return (float)Math.Sin(v);
        }

        public static float Cos(float v)
        {
            return (float)Math.Cos(v);
        }

        public static float Sqrt(float v)
        {
            return (float)Math.Sqrt(v);
        }

        public static float Atan2(float y, float x)
        {
            return (float)Math.Atan2(y, x);
        }

        public static float Clamp(float v, float min, float max)
        {
            if (v < min) return min;
            if (v > max) return max;
            return v;
        }

        public static int Clamp(int v, int min, int max)
        {
            if (v < min) return min;
            if (v > max) return max;
            return v;
        }

        public static float Clamp01(float v)
        {
            return Clamp(v, 0f, 1f);
        }

        public static float Min(float a, float b)
        {
            return a < b ? a : b;
        }

        public static int Min(int a, int b)
        {
            return a < b ? a : b;
        }

        public static float Max(float a, float b)
        {
            return a > b ? a : b;
        }

        public static int Max(int a, int b)
        {
            return a > b ? a : b;
        }

        public static float Lerp(float a, float b, float t)
        {
            return a + (b - a) * Clamp01(t);
        }

        public static int RoundToInt(float v)
        {
            return (int)Math.Round(v);
        }

        public static int FloorToInt(float v)
        {
            return (int)Math.Floor(v);
        }

        public static int CeilToInt(float v)
        {
            return (int)Math.Ceiling(v);
        }

        public static float Floor(float v)
        {
            return (float)Math.Floor(v);
        }

        public static float PingPong(float t, float length)
        {
            if (length <= 0f) return 0f;
            float mod = t % (length * 2f);
            if (mod < 0f) mod += length * 2f;
            return mod <= length ? mod : length * 2f - mod;
        }

        public static float PerlinNoise(float x, float y)
        {
            float n = (float)Math.Sin(x * 12.9898f + y * 78.233f) * 43758.5453f;
            return n - (float)Math.Floor(n);
        }
    }

    public static class Debug
    {
        public static void Log(object message)
        {
        }

        public static void LogWarning(object message)
        {
        }
    }

    public static class Application
    {
        public static string persistentDataPath = "";
        public static string dataPath = "";
    }

    public static class Screen
    {
        public static int width = 1280;
        public static int height = 720;
    }

    public static class Time
    {
        public static float deltaTime = 0.02f;
    }

    public static class Input
    {
        public static Vector3 mousePosition
        {
            get { return Vector3.zero; }
        }

        public static bool GetKey(KeyCode key)
        {
            return false;
        }

        public static bool GetKeyDown(KeyCode key)
        {
            return false;
        }

        public static bool GetMouseButton(int button)
        {
            return false;
        }

        public static bool GetMouseButtonDown(int button)
        {
            return false;
        }

        public static float GetAxis(string name)
        {
            return 0f;
        }
    }

    public enum KeyCode
    {
        None,
        Return,
        KeypadEnter,
        W,
        A,
        S,
        D,
        C,
        M,
        UpArrow,
        DownArrow,
        LeftArrow,
        RightArrow,
    }

    public class GUILayoutOption
    {
    }

    public static class GUILayout
    {
        public static GUILayoutOption Height(float height)
        {
            return new GUILayoutOption();
        }

        public static void BeginArea(Rect area)
        {
        }

        public static void EndArea()
        {
        }

        public static void BeginHorizontal()
        {
        }

        public static void EndHorizontal()
        {
        }

        public static void Space(float pixels)
        {
        }

        public static void Label(string text)
        {
        }

        public static bool Button(string text)
        {
            return Button(text, null);
        }

        public static bool Button(string text, GUILayoutOption option)
        {
            if (!HeadlessInput.Used && text == HeadlessInput.Button)
            {
                HeadlessInput.Used = true;
                return true;
            }
            return false;
        }

        public static string TextField(string text, int maxLength, GUILayoutOption option)
        {
            if (!HeadlessInput.UseDraft) return text;
            string draft = HeadlessInput.Draft ?? "";
            if (draft.Length > maxLength) draft = draft.Substring(0, maxLength);
            return draft;
        }

        public static string PasswordField(string text, char mask, int maxLength, GUILayoutOption option)
        {
            return text ?? "";
        }
    }

    public static class GUI
    {
        public static Color color;

        public static void SetNextControlName(string name)
        {
        }

        public static string GetNameOfFocusedControl()
        {
            return "";
        }
    }

    public static class JsonUtility
    {
        public static string ToJson(object value)
        {
            return Write(value);
        }

        public static T FromJson<T>(string json) where T : new()
        {
            return new T();
        }

        static string Write(object value)
        {
            if (value == null) return "null";
            Type type = value.GetType();
            if (type == typeof(string)) return Quote((string)value);
            if (type == typeof(bool)) return (bool)value ? "true" : "false";
            if (type == typeof(int)) return ((int)value).ToString(System.Globalization.CultureInfo.InvariantCulture);
            if (type == typeof(float)) return ((float)value).ToString("R", System.Globalization.CultureInfo.InvariantCulture);
            if (type.IsEnum) return ((int)value).ToString(System.Globalization.CultureInfo.InvariantCulture);
            if (type.IsArray)
            {
                var array = (Array)value;
                var parts = new List<string>();
                foreach (var item in array) parts.Add(Write(item));
                return "[" + string.Join(",", parts) + "]";
            }
            var fields = type.GetFields(System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.Public);
            var body = new List<string>();
            foreach (var field in fields)
            {
                object fieldValue = field.GetValue(value);
                if (fieldValue != null && typeof(Object).IsAssignableFrom(field.FieldType)) continue;
                body.Add(Quote(field.Name) + ":" + Write(fieldValue));
            }
            return "{" + string.Join(",", body) + "}";
        }

        static string Quote(string text)
        {
            if (text == null) return "\"\"";
            return "\"" + text.Replace("\\", "\\\\").Replace("\"", "\\\"").Replace("\n", "\\n") + "\"";
        }
    }

    public class Shader : Object
    {
        public static Shader Find(string name)
        {
            return new Shader();
        }
    }

    public class Texture : Object
    {
    }

    public enum TextureFormat
    {
        RGBA32,
    }

    public enum TextureWrapMode
    {
        Repeat,
        Clamp,
    }

    public class Texture2D : Texture
    {
        public TextureWrapMode wrapMode;

        public Texture2D(int width, int height, TextureFormat format, bool mipChain)
        {
        }

        public void SetPixel(int x, int y, Color color)
        {
        }

        public void Apply()
        {
        }

        public static Texture2D whiteTexture
        {
            get { return new Texture2D(1, 1, TextureFormat.RGBA32, false); }
        }
    }

    public class Material : Object
    {
        public Color color;
        public Texture mainTexture;
        public Vector2 mainTextureScale;
        public int renderQueue;

        public Material(Shader shader)
        {
        }

        public bool HasProperty(string name)
        {
            return false;
        }

        public void SetOverrideTag(string tag, string value)
        {
        }

        public void SetColor(string name, Color color)
        {
        }

        public void SetFloat(string name, float value)
        {
        }

        public void SetTexture(string name, Texture texture)
        {
        }

        public void EnableKeyword(string keyword)
        {
        }
    }

    public class Mesh : Object
    {
        public Vector3[] vertices = new Vector3[0];
        public Vector3[] normals = new Vector3[0];
        public int[] triangles = new int[0];
        public BoneWeight[] boneWeights = new BoneWeight[0];
        public Matrix4x4[] bindposes = new Matrix4x4[0];
        public Rendering.IndexFormat indexFormat;

        public void SetVertices(List<Vector3> list)
        {
            vertices = list.ToArray();
        }

        public void SetUVs(int channel, List<Vector2> list)
        {
        }

        public void SetColors(List<Color> list)
        {
        }

        public void SetTriangles(List<int> list, int submesh)
        {
            triangles = list.ToArray();
        }

        public void RecalculateNormals()
        {
            normals = new Vector3[vertices.Length];
            for (int i = 0; i < normals.Length; i++) normals[i] = Vector3.up;
        }

        public void RecalculateBounds()
        {
        }
    }

    public class Renderer : Component
    {
        public bool enabled = true;
        public Material sharedMaterial;
        public Material material;
        public Bounds localBounds;
    }

    public class MeshFilter : Component
    {
        public Mesh sharedMesh;
    }

    public class MeshRenderer : Renderer
    {
        public Rendering.ShadowCastingMode shadowCastingMode;
    }

    public class SkinnedMeshRenderer : Renderer
    {
        public Mesh sharedMesh;
        public Transform[] bones;
        public Transform rootBone;
        public bool updateWhenOffscreen;
        public SkinQuality quality;
    }

    public enum SkinQuality
    {
        Auto,
        Bone1,
        Bone2,
        Bone4,
    }

    public class Collider : Component
    {
        public bool enabled = true;
    }

    public class MeshCollider : Collider
    {
    }

    public class CapsuleCollider : Collider
    {
        public float height;
        public float radius;
        public Vector3 center;
    }

    public class Rigidbody : Component
    {
        public float mass;
        public bool isKinematic;
        public bool useGravity;
        public bool detectCollisions = true;
        public RigidbodyInterpolation interpolation;
        public CollisionDetectionMode collisionDetectionMode;

        public void MovePosition(Vector3 position)
        {
            if (transform != null) transform.position = position;
        }

        public void MoveRotation(Quaternion rotation)
        {
            if (transform != null) transform.rotation = rotation;
        }
    }

    public enum RigidbodyInterpolation
    {
        None,
        Interpolate,
        Extrapolate,
    }

    public enum CollisionDetectionMode
    {
        Discrete,
        Continuous,
        ContinuousSpeculative,
    }

    public enum LightType
    {
        Spot,
        Directional,
        Point,
    }

    public enum LightShadows
    {
        None,
        Hard,
        Soft,
    }

    public class Light : Behaviour
    {
        public LightType type;
        public Color color;
        public float range;
        public float intensity;
        public LightShadows shadows;
    }

    public class Camera : Behaviour
    {
        public static Camera main;

        public Ray ScreenPointToRay(Vector3 position)
        {
            return new Ray();
        }
    }

    public static class Physics
    {
        public static bool Raycast(Ray ray, out RaycastHit hit, float maxDistance)
        {
            hit = new RaycastHit();
            return false;
        }
    }

    public class TerrainData : Object
    {
        public int heightmapResolution;
        public int alphamapResolution;
        public Vector3 size;
        public float[,,] alphamap;
        TerrainLayer[] layers = new TerrainLayer[0];

        public TerrainLayer[] terrainLayers
        {
            get { return layers; }
            set { layers = value; }
        }

        public void SetHeights(int xBase, int yBase, float[,] heights)
        {
        }

        public void SetAlphamaps(int x, int y, float[,,] maps)
        {
        }
    }

    public class TerrainLayer : Object
    {
        public Texture2D diffuseTexture;
        public Vector2 tileSize;
    }

    public class Terrain : Component
    {
        public TerrainData terrainData;
        public Material materialTemplate;
        public bool drawInstanced;

        public static GameObject CreateTerrainGameObject(TerrainData data)
        {
            var go = new GameObject("Terrain");
            var terrain = go.AddComponent<Terrain>();
            terrain.terrainData = data;
            return go;
        }
    }

    public class TextMesh : Component
    {
        public string text = "";
        public float characterSize;
        public TextAnchor anchor;
        public TextAlignment alignment;
        public Color color;
        public int fontSize;
    }

    public enum TextAnchor
    {
        MiddleCenter,
    }

    public enum TextAlignment
    {
        Center,
        Left,
    }

    public class ReflectionProbe : Behaviour
    {
        public Rendering.ReflectionProbeMode mode;
        public Rendering.ReflectionProbeRefreshMode refreshMode;
        public Vector3 size;
        public float intensity;
    }

    public static class Resources
    {
        public static T Load<T>(string path) where T : Object
        {
            return null;
        }
    }

    public class Coroutine
    {
    }

    public class UnityWebRequest : IDisposable
    {
        public enum Result
        {
            InProgress,
            Success,
            ConnectionError,
            ProtocolError,
            DataProcessingError,
        }

        public const string kHttpVerbPOST = "POST";
        public UploadHandler uploadHandler;
        public DownloadHandler downloadHandler;
        public Result result;
        public string error;
        public long responseCode;
        public int timeout;

        public UnityWebRequest(string url, string method)
        {
        }

        public void SetRequestHeader(string name, string value)
        {
        }

        public UnityWebRequestAsyncOperation SendWebRequest()
        {
            return new UnityWebRequestAsyncOperation();
        }

        public void Dispose()
        {
        }
    }

    public class UnityWebRequestAsyncOperation
    {
    }

    public class DownloadHandler
    {
        public string text = "";
    }

    public class DownloadHandlerBuffer : DownloadHandler
    {
    }

    public class UploadHandler
    {
    }

    public class UploadHandlerRaw : UploadHandler
    {
        public UploadHandlerRaw(byte[] body)
        {
        }
    }
}

namespace UnityEngine.Rendering
{
    public enum IndexFormat
    {
        UInt16,
        UInt32,
    }

    public enum ShadowCastingMode
    {
        Off,
        On,
        TwoSided,
    }

    public enum ReflectionProbeMode
    {
        Baked,
        Realtime,
    }

    public enum ReflectionProbeRefreshMode
    {
        OnAwake,
        ViaScripting,
    }
}

namespace UnityEngine.Rendering.HighDefinition
{
    public enum LightUnit
    {
        Lumen,
        Candela,
    }

    public static class HDMaterial
    {
        public static void ValidateMaterial(UnityEngine.Material material)
        {
        }
    }

    public class HDAdditionalLightData : UnityEngine.MonoBehaviour
    {
        public void SetIntensity(float intensity, LightUnit unit)
        {
        }
    }

    public class Volume : UnityEngine.MonoBehaviour
    {
        public VolumeProfile profile;
    }

    public class VolumeProfile
    {
        public bool TryGet<T>(out T component) where T : new()
        {
            component = default(T);
            return false;
        }

        public T Add<T>() where T : new()
        {
            return new T();
        }
    }

    public class Fog
    {
        public bool active;
        public BoolParameter enabled = new BoolParameter();
        public ColorParameter albedo = new ColorParameter();
        public FloatParameter meanFreePath = new FloatParameter();
        public FloatParameter baseHeight = new FloatParameter();
        public FloatParameter maximumHeight = new FloatParameter();
    }

    public class BoolParameter
    {
        public void Override(bool value)
        {
        }
    }

    public class ColorParameter
    {
        public void Override(UnityEngine.Color value)
        {
        }
    }

    public class FloatParameter
    {
        public void Override(float value)
        {
        }
    }
}

namespace UnityEngine.Rendering.HighDefinition
{
    public enum WaterSurfaceType
    {
        OceanSeaLake,
    }

    public enum WaterGeometryType
    {
        Custom,
    }

    public class WaterSurface : UnityEngine.MonoBehaviour
    {
        public WaterSurfaceType surfaceType;
        public WaterGeometryType geometryType;
        public List<UnityEngine.MeshRenderer> meshRenderers = new List<UnityEngine.MeshRenderer>();
        public float repetitionSize;
        public float largeWindSpeed;
        public float ripplesWindSpeed;
        public float largeChaos;
        public float ripplesChaos;
        public float timeMultiplier;
        public float startSmoothness;
        public float endSmoothness;
        public float absorptionDistance;
        public float maxRefractionDistance;
        public float volumeDepth;
        public bool foam;
        public bool caustics;
        public bool tessellation;
        public bool underWater;
    }
}

namespace UnityEngine.Networking
{
}
