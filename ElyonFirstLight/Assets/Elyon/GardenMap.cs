using System.Collections.Generic;
using UnityEngine;

namespace Elyon
{
    /// <summary>
    /// The lake is a closed bowl. People may walk the shore around it.
    /// Only Elyon may step on the water.
    /// </summary>
    public static class GardenMap
    {
        public const float WorldSize = 200f;
        public const float LakeX = 100f;
        public const float LakeZ = 100f;
        public const float LakeRx = 36f;
        public const float LakeRz = 24f;
        public const float WaterY = 10f;
        public const float TerrainHeight = 48f;
        public const int Cells = 100;

        public static float CellSize => WorldSize / Cells;

        public static bool InWater(float x, float z)
        {
            float dx = (x - LakeX) / LakeRx;
            float dz = (z - LakeZ) / LakeRz;
            return dx * dx + dz * dz <= 1f;
        }

        public static float Height(float x, float z)
        {
            x = Mathf.Clamp(x, 0f, WorldSize);
            z = Mathf.Clamp(z, 0f, WorldSize);
            float dx = (x - LakeX) / LakeRx;
            float dz = (z - LakeZ) / LakeRz;
            float ellipse = dx * dx + dz * dz;
            if (ellipse < 1f)
            {
                return WaterY - 4.4f - (1f - ellipse) * 2.2f;
            }

            float nx = x / WorldSize;
            float nz = z / WorldSize;
            float hills = Mathf.PerlinNoise(nx * 3.4f + 0.2f, nz * 3.4f + 1.7f);
            float broad = Mathf.PerlinNoise(nx * 1.15f + 4.2f, nz * 1.15f + 0.4f);
            float edge = Mathf.Min(Mathf.Min(x, WorldSize - x), Mathf.Min(z, WorldSize - z));
            float rim = Mathf.Clamp01(1f - edge / 26f);
            float shore = Mathf.Clamp01((Mathf.Sqrt(ellipse) - 1f) / 0.22f);
            float y = WaterY + 0.45f + shore * (1.8f + hills * 6.5f + broad * 8f) + rim * 12f;
            return Mathf.Min(y, TerrainHeight - 0.5f);
        }

        public static Vector3 OnLand(Vector3 world)
        {
            world.y = Height(world.x, world.z);
            return world;
        }

        public static List<Vector3> Route(Vector3 from, Vector3 to)
        {
            int sx = ToCell(from.x);
            int sz = ToCell(from.z);
            int gx = ToCell(to.x);
            int gz = ToCell(to.z);
            if (!NearestLand(ref sx, ref sz) || !NearestLand(ref gx, ref gz))
            {
                return new List<Vector3> { Lift(from) };
            }

            var raw = Search(sx, sz, gx, gz);
            if (raw.Count == 0)
            {
                return new List<Vector3> { Lift(from) };
            }

            return Pull(raw);
        }

        static int ToCell(float v)
        {
            int i = Mathf.FloorToInt(v / CellSize);
            return Mathf.Clamp(i, 0, Cells - 1);
        }

        static Vector3 CellCenter(int ix, int iz)
        {
            return Lift(new Vector3((ix + 0.5f) * CellSize, 0f, (iz + 0.5f) * CellSize));
        }

        static Vector3 Lift(Vector3 p)
        {
            p.y = Height(p.x, p.z);
            return p;
        }

        static bool LandCell(int ix, int iz)
        {
            if (ix < 0 || iz < 0 || ix >= Cells || iz >= Cells) return false;
            float x = (ix + 0.5f) * CellSize;
            float z = (iz + 0.5f) * CellSize;
            return !InWater(x, z);
        }

        static bool NearestLand(ref int ix, ref int iz)
        {
            if (LandCell(ix, iz)) return true;
            for (int r = 1; r < Cells; r++)
            {
                for (int dz = -r; dz <= r; dz++)
                {
                    int ax = ix - r;
                    int bx = ix + r;
                    int z = iz + dz;
                    if (LandCell(ax, z)) { ix = ax; iz = z; return true; }
                    if (LandCell(bx, z)) { ix = bx; iz = z; return true; }
                }
                for (int dx = -r + 1; dx <= r - 1; dx++)
                {
                    int az = iz - r;
                    int bz = iz + r;
                    int x = ix + dx;
                    if (LandCell(x, az)) { ix = x; iz = az; return true; }
                    if (LandCell(x, bz)) { ix = x; iz = bz; return true; }
                }
            }
            return false;
        }

        static List<Vector3> Search(int sx, int sz, int gx, int gz)
        {
            int n = Cells * Cells;
            var came = new int[n];
            var cost = new float[n];
            for (int i = 0; i < n; i++)
            {
                came[i] = -1;
                cost[i] = float.PositiveInfinity;
            }

            int start = sz * Cells + sx;
            int goal = gz * Cells + gx;
            cost[start] = 0f;
            var open = new List<int> { start };
            int[] dx = { 1, -1, 0, 0 };
            int[] dz = { 0, 0, 1, -1 };

            while (open.Count > 0)
            {
                int best = 0;
                float bestScore = float.PositiveInfinity;
                for (int i = 0; i < open.Count; i++)
                {
                    int id = open[i];
                    int x = id % Cells;
                    int z = id / Cells;
                    float score = cost[id] + Mathf.Abs(x - gx) + Mathf.Abs(z - gz);
                    if (score < bestScore)
                    {
                        bestScore = score;
                        best = i;
                    }
                }

                int current = open[best];
                open.RemoveAt(best);
                if (current == goal) break;

                int cx = current % Cells;
                int cz = current / Cells;
                for (int k = 0; k < 4; k++)
                {
                    int nx = cx + dx[k];
                    int nz = cz + dz[k];
                    if (!LandCell(nx, nz)) continue;
                    int next = nz * Cells + nx;
                    float step = cost[current] + 1f;
                    if (step >= cost[next]) continue;
                    cost[next] = step;
                    came[next] = current;
                    if (!open.Contains(next)) open.Add(next);
                }
            }

            var cells = new List<Vector3>();
            if (came[goal] < 0 && start != goal) return cells;
            int walk = goal;
            while (walk >= 0)
            {
                cells.Add(CellCenter(walk % Cells, walk / Cells));
                if (walk == start) break;
                walk = came[walk];
            }
            cells.Reverse();
            return cells;
        }

        static List<Vector3> Pull(List<Vector3> raw)
        {
            if (raw.Count < 3) return raw;
            var pulled = new List<Vector3> { raw[0] };
            int anchor = 0;
            for (int i = 2; i < raw.Count; i++)
            {
                if (!Clear(raw[anchor], raw[i]))
                {
                    pulled.Add(raw[i - 1]);
                    anchor = i - 1;
                }
            }
            pulled.Add(raw[raw.Count - 1]);
            return pulled;
        }

        static bool Clear(Vector3 a, Vector3 b)
        {
            float distance = Vector3.Distance(a, b);
            int steps = Mathf.Max(1, Mathf.CeilToInt(distance / 1.1f));
            for (int i = 0; i <= steps; i++)
            {
                Vector3 p = Vector3.Lerp(a, b, i / (float)steps);
                if (InWater(p.x, p.z)) return false;
            }
            return true;
        }
    }
}
