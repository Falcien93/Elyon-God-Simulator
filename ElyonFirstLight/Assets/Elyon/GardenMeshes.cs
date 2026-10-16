using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;

namespace Elyon
{
    public sealed class MeshDraft
    {
        public readonly List<Vector3> Verts = new List<Vector3>();
        public readonly List<Vector2> Uv = new List<Vector2>();
        public readonly List<Color> Colors = new List<Color>();
        public readonly List<int> Tris = new List<int>();
        public readonly List<BoneWeight> Weights = new List<BoneWeight>();

        public int Add(Vector3 position, Vector2 uv, Color color, BoneWeight weight)
        {
            Verts.Add(position);
            Uv.Add(uv);
            Colors.Add(color);
            Weights.Add(weight);
            return Verts.Count - 1;
        }

        public static BoneWeight Bone(int index)
        {
            return new BoneWeight { boneIndex0 = index, weight0 = 1f };
        }

        public static BoneWeight Blend(int a, int b, float towardB)
        {
            towardB = Mathf.Clamp01(towardB);
            return new BoneWeight
            {
                boneIndex0 = a,
                weight0 = 1f - towardB,
                boneIndex1 = b,
                weight1 = towardB,
            };
        }

        public int Ring(Vector3 center, Vector3 axis, float rx, float ry, int segments, float v, Color color, BoneWeight weight)
        {
            axis.Normalize();
            Vector3 side = Vector3.Cross(axis, Mathf.Abs(axis.y) > 0.9f ? Vector3.forward : Vector3.up).normalized;
            Vector3 up = Vector3.Cross(axis, side).normalized;
            int start = Verts.Count;
            for (int i = 0; i < segments; i++)
            {
                float a = i / (float)segments * Mathf.PI * 2f;
                Vector3 offset = side * (Mathf.Cos(a) * rx) + up * (Mathf.Sin(a) * ry);
                Add(center + offset, new Vector2(i / (float)segments, v), color, weight);
            }
            return start;
        }

        public void Bridge(int a, int b, int segments)
        {
            for (int i = 0; i < segments; i++)
            {
                int i2 = (i + 1) % segments;
                Tris.Add(a + i);
                Tris.Add(b + i);
                Tris.Add(a + i2);
                Tris.Add(a + i2);
                Tris.Add(b + i);
                Tris.Add(b + i2);
            }
        }

        public void Cap(int ring, int segments, bool outwardAlongUp, BoneWeight weight, Color color)
        {
            Vector3 center = Vector3.zero;
            for (int i = 0; i < segments; i++) center += Verts[ring + i];
            center /= segments;
            int c = Add(center, new Vector2(0.5f, outwardAlongUp ? 1f : 0f), color, weight);
            for (int i = 0; i < segments; i++)
            {
                int i2 = (i + 1) % segments;
                if (outwardAlongUp)
                {
                    Tris.Add(c);
                    Tris.Add(ring + i);
                    Tris.Add(ring + i2);
                }
                else
                {
                    Tris.Add(c);
                    Tris.Add(ring + i2);
                    Tris.Add(ring + i);
                }
            }
        }

        public Mesh ToMesh(string name, bool skin)
        {
            var mesh = new Mesh { name = name };
            if (Verts.Count > 65000) mesh.indexFormat = IndexFormat.UInt32;
            mesh.SetVertices(Verts);
            mesh.SetUVs(0, Uv);
            mesh.SetColors(Colors);
            mesh.SetTriangles(Tris, 0);
            mesh.RecalculateNormals();
            if (skin && Weights.Count == Verts.Count) mesh.boneWeights = Weights.ToArray();
            FaceOutward(mesh);
            mesh.RecalculateBounds();
            return mesh;
        }

        static void FaceOutward(Mesh mesh)
        {
            var vertices = mesh.vertices;
            var normals = mesh.normals;
            if (vertices.Length == 0) return;
            int side = 0;
            for (int i = 1; i < vertices.Length; i++)
            {
                if (vertices[i].x > vertices[side].x) side = i;
            }
            if (normals[side].x >= 0f) return;
            var triangles = mesh.triangles;
            for (int i = 0; i < triangles.Length; i += 3)
            {
                int swap = triangles[i];
                triangles[i] = triangles[i + 1];
                triangles[i + 1] = swap;
            }
            mesh.triangles = triangles;
            mesh.RecalculateNormals();
        }
    }

    public static class GardenMeshes
    {
        public static Mesh Trunk(float height, float radius, int salt)
        {
            var draft = new MeshDraft();
            const int segments = 12;
            const int rings = 8;
            int previous = -1;
            var tint = new Color(0.72f, 0.58f, 0.42f);
            for (int r = 0; r <= rings; r++)
            {
                float t = r / (float)rings;
                float flare = t < 0.18f ? Mathf.Lerp(1.7f, 1f, t / 0.18f) : 1f;
                float taper = Mathf.Lerp(1f, 0.55f, t);
                float wobble = 1f + (Mathf.PerlinNoise(salt * 0.17f, t * 3f) - 0.5f) * 0.12f;
                float y = t * height;
                float rx = radius * flare * taper * wobble;
                int ring = draft.Ring(new Vector3(0f, y, 0f), Vector3.up, rx, rx * 0.92f, segments, t, tint, MeshDraft.Bone(0));
                if (previous >= 0) draft.Bridge(previous, ring, segments);
                previous = ring;
            }
            draft.Cap(previous, segments, true, MeshDraft.Bone(0), tint);
            return draft.ToMesh("Trunk", false);
        }

        public static Mesh Boulder(int salt)
        {
            var draft = new MeshDraft();
            const int lat = 10;
            const int lon = 14;
            var tint = new Color(0.75f, 0.72f, 0.66f);
            int previous = -1;
            for (int y = 0; y <= lat; y++)
            {
                float v = y / (float)lat;
                float phi = v * Mathf.PI;
                float ringR = Mathf.Sin(phi);
                int start = draft.Verts.Count;
                for (int x = 0; x < lon; x++)
                {
                    float u = x / (float)lon;
                    float theta = u * Mathf.PI * 2f;
                    var p = new Vector3(Mathf.Cos(theta) * ringR, Mathf.Cos(phi), Mathf.Sin(theta) * ringR);
                    float n = Mathf.PerlinNoise(p.x * 1.8f + salt, p.z * 1.8f + 2f);
                    p *= 0.55f + n * 0.5f;
                    p.y *= 0.72f;
                    draft.Add(p, new Vector2(u, v), tint, MeshDraft.Bone(0));
                }
                if (previous >= 0) draft.Bridge(previous, start, lon);
                previous = start;
            }
            return draft.ToMesh("Boulder", false);
        }

        public static Mesh Tuft()
        {
            var draft = new MeshDraft();
            var tint = new Color(0.45f, 0.62f, 0.28f);
            for (int blade = 0; blade < 3; blade++)
            {
                float yaw = blade * 120f * Mathf.Deg2Rad;
                var right = new Vector3(Mathf.Cos(yaw), 0f, Mathf.Sin(yaw));
                int a = draft.Add(right * -0.04f, new Vector2(0f, 0f), tint, MeshDraft.Bone(0));
                int b = draft.Add(right * 0.04f, new Vector2(1f, 0f), tint, MeshDraft.Bone(0));
                int c = draft.Add(new Vector3(0f, 0.34f, 0f) + right * 0.01f, new Vector2(0.5f, 1f), tint, MeshDraft.Bone(0));
                draft.Tris.Add(a);
                draft.Tris.Add(c);
                draft.Tris.Add(b);
                draft.Tris.Add(a);
                draft.Tris.Add(b);
                draft.Tris.Add(c);
            }
            return draft.ToMesh("Tuft", false);
        }

        public static Mesh Ellipse(float rx, float rz, int segments)
        {
            var draft = new MeshDraft();
            var tint = new Color(0.55f, 0.72f, 0.74f);
            int center = draft.Add(Vector3.zero, new Vector2(0.5f, 0.5f), tint, MeshDraft.Bone(0));
            for (int i = 0; i < segments; i++)
            {
                float a = i / (float)segments * Mathf.PI * 2f;
                draft.Add(new Vector3(Mathf.Cos(a) * rx, 0f, Mathf.Sin(a) * rz), new Vector2(Mathf.Cos(a) * 0.5f + 0.5f, Mathf.Sin(a) * 0.5f + 0.5f), tint, MeshDraft.Bone(0));
            }
            for (int i = 0; i < segments; i++)
            {
                int next = i == segments - 1 ? 1 : i + 2;
                draft.Tris.Add(center);
                draft.Tris.Add(i + 1);
                draft.Tris.Add(next);
            }
            return draft.ToMesh("Lake", false);
        }

        public static Mesh ShoreRibbon(float rx, float rz, float width, int segments)
        {
            var draft = new MeshDraft();
            var tint = new Color(0.86f, 0.84f, 0.78f, 0.7f);
            int inner = draft.Verts.Count;
            for (int i = 0; i < segments; i++)
            {
                float a = i / (float)segments * Mathf.PI * 2f;
                float c = Mathf.Cos(a);
                float s = Mathf.Sin(a);
                draft.Add(new Vector3(c * rx, 0f, s * rz), new Vector2(i / (float)segments, 0f), tint, MeshDraft.Bone(0));
            }
            int outer = draft.Verts.Count;
            for (int i = 0; i < segments; i++)
            {
                float a = i / (float)segments * Mathf.PI * 2f;
                float c = Mathf.Cos(a);
                float s = Mathf.Sin(a);
                float len = Mathf.Sqrt(c * c * rx * rx + s * s * rz * rz);
                float nx = len < 0.001f ? c : c * rx / len;
                float nz = len < 0.001f ? s : s * rz / len;
                draft.Add(new Vector3(c * rx + nx * width, 0.02f, s * rz + nz * width), new Vector2(i / (float)segments, 1f), tint, MeshDraft.Bone(0));
            }
            draft.Bridge(inner, outer, segments);
            return draft.ToMesh("Shore", false);
        }
    }
}
