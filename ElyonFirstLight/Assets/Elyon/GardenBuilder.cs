using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.HighDefinition;

namespace Elyon
{
    public sealed class GardenWorld
    {
        public Vector3 Fire;
        public Vector3 Pot;
        public Vector3 Cup;
        public Transform WorkAdam;
        public Transform WorkEve;
        public Person Adam;
        public Person Eve;
        public readonly List<Transform> Trees = new List<Transform>();
    }

    public static class GardenBuilder
    {
        static Texture2D grassTex;
        static Texture2D sandTex;
        static Texture2D barkTex;
        static Texture2D rockTex;
        static Texture2D leafTex;

        public static GardenWorld Build(Transform root)
        {
            LoadArt();
            var world = new GardenWorld();
            BuildTerrain(root);
            BuildLake(root);
            BuildRocks(root);
            BuildGroundCover(root);
            world.Trees.AddRange(BuildTrees(root));
            BuildCamp(root, world);
            DressMorning();
            world.Adam = BuildPerson(root, "adam", "Adam", new Vector3(146f, 0f, 96f), world);
            world.Eve = BuildPerson(root, "eve", "Eve", new Vector3(154f, 0f, 104f), world);
            return world;
        }

        static void LoadArt()
        {
            grassTex = Resources.Load<Texture2D>("grass");
            sandTex = Resources.Load<Texture2D>("sand");
            barkTex = Resources.Load<Texture2D>("bark");
            rockTex = Resources.Load<Texture2D>("rock");
            leafTex = LeafTexture();
            Repeat(grassTex);
            Repeat(sandTex);
            Repeat(barkTex);
            Repeat(rockTex);
        }

        static void Repeat(Texture2D tex)
        {
            if (tex == null) return;
            tex.wrapMode = TextureWrapMode.Repeat;
        }

        static Texture2D LeafTexture()
        {
            var tex = new Texture2D(64, 64, TextureFormat.RGBA32, false);
            var clear = new Color(0f, 0f, 0f, 0f);
            for (int y = 0; y < 64; y++)
            {
                for (int x = 0; x < 64; x++)
                {
                    float nx = (x - 32f) / 14f;
                    float ny = (y - 30f) / 26f;
                    float oval = nx * nx + ny * ny;
                    if (oval > 1f)
                    {
                        tex.SetPixel(x, y, clear);
                        continue;
                    }
                    float vein = Mathf.Abs(x - 32f) < 1.2f || Mathf.Abs((y - 30f) - (x - 32f) * 0.4f) < 0.7f ? 0.15f : 0f;
                    float shade = 0.75f + 0.25f * (1f - oval);
                    tex.SetPixel(x, y, new Color(0.12f * shade, (0.38f + vein) * shade, 0.1f * shade, 1f));
                }
            }
            tex.Apply();
            tex.wrapMode = TextureWrapMode.Clamp;
            return tex;
        }

        public static Material Lit(Color color, float smooth, Texture2D albedo, Vector2 scale)
        {
            var shader = Shader.Find("HDRP/Lit");
            if (shader == null) shader = Shader.Find("Standard");
            var mat = new Material(shader);
            if (mat.HasProperty("_BaseColor")) mat.SetColor("_BaseColor", color);
            mat.color = color;
            if (mat.HasProperty("_Smoothness")) mat.SetFloat("_Smoothness", smooth);
            if (albedo != null)
            {
                if (mat.HasProperty("_BaseColorMap")) mat.SetTexture("_BaseColorMap", albedo);
                mat.mainTexture = albedo;
                mat.mainTextureScale = scale;
            }
            HDMaterial.ValidateMaterial(mat);
            return mat;
        }

        static void BuildTerrain(Transform root)
        {
            var data = new TerrainData();
            const int res = 257;
            data.heightmapResolution = res;
            data.size = new Vector3(GardenMap.WorldSize, GardenMap.TerrainHeight, GardenMap.WorldSize);
            var heights = new float[res, res];
            for (int z = 0; z < res; z++)
            {
                for (int x = 0; x < res; x++)
                {
                    float wx = x / (float)(res - 1) * GardenMap.WorldSize;
                    float wz = z / (float)(res - 1) * GardenMap.WorldSize;
                    heights[z, x] = GardenMap.Height(wx, wz) / GardenMap.TerrainHeight;
                }
            }
            data.SetHeights(0, 0, heights);

            var grass = new TerrainLayer { diffuseTexture = grassTex, tileSize = new Vector2(8f, 8f) };
            var sand = new TerrainLayer { diffuseTexture = sandTex, tileSize = new Vector2(7f, 7f) };
            if (grass.diffuseTexture == null) grass.diffuseTexture = Texture2D.whiteTexture;
            if (sand.diffuseTexture == null) sand.diffuseTexture = Texture2D.whiteTexture;
            data.terrainLayers = new[] { grass, sand };

            const int alpha = 128;
            data.alphamapResolution = alpha;
            var maps = new float[alpha, alpha, 2];
            for (int z = 0; z < alpha; z++)
            {
                for (int x = 0; x < alpha; x++)
                {
                    float wx = (x + 0.5f) / alpha * GardenMap.WorldSize;
                    float wz = (z + 0.5f) / alpha * GardenMap.WorldSize;
                    float dx = (wx - GardenMap.LakeX) / GardenMap.LakeRx;
                    float dz = (wz - GardenMap.LakeZ) / GardenMap.LakeRz;
                    float outside = Mathf.Sqrt(dx * dx + dz * dz) - 1f;
                    float sandWeight = GardenMap.InWater(wx, wz) ? 1f : Mathf.Clamp01(1f - outside / 0.16f);
                    maps[z, x, 0] = 1f - sandWeight;
                    maps[z, x, 1] = sandWeight;
                }
            }
            data.SetAlphamaps(0, 0, maps);

            var go = Terrain.CreateTerrainGameObject(data);
            go.name = "Ground";
            go.transform.SetParent(root, false);
            var terrain = go.GetComponent<Terrain>();
            terrain.drawInstanced = true;
            var terrainShader = Shader.Find("HDRP/TerrainLit");
            if (terrainShader != null)
            {
                var terrainMat = new Material(terrainShader);
                HDMaterial.ValidateMaterial(terrainMat);
                terrain.materialTemplate = terrainMat;
            }
        }

        static void BuildLake(Transform root)
        {
            const int seg = 72;
            var go = new GameObject("Lake");
            go.transform.SetParent(root, false);
            go.transform.position = new Vector3(GardenMap.LakeX, GardenMap.WaterY, GardenMap.LakeZ);
            var lakeMesh = GardenMeshes.Ellipse(GardenMap.LakeRx, GardenMap.LakeRz, seg);
            go.AddComponent<MeshFilter>().sharedMesh = lakeMesh;
            var renderer = go.AddComponent<MeshRenderer>();
            var color = new Color(0.05f, 0.22f, 0.26f, 0.55f);
            var mat = Lit(color, 0.94f, null, Vector2.one);
            if (mat.HasProperty("_SurfaceType")) mat.SetFloat("_SurfaceType", 1f);
            if (mat.HasProperty("_BlendMode")) mat.SetFloat("_BlendMode", 0f);
            if (mat.HasProperty("_ZWrite")) mat.SetFloat("_ZWrite", 0f);
            mat.EnableKeyword("_SURFACE_TYPE_TRANSPARENT");
            mat.SetOverrideTag("RenderType", "Transparent");
            mat.renderQueue = 3000;
            if (mat.HasProperty("_BaseColor")) mat.SetColor("_BaseColor", color);
            mat.color = color;
            renderer.sharedMaterial = mat;
            renderer.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            var water = go.AddComponent<WaterSurface>();
            water.surfaceType = WaterSurfaceType.OceanSeaLake;
            water.geometryType = WaterGeometryType.Custom;
            if (water.meshRenderers == null) water.meshRenderers = new List<MeshRenderer>();
            water.meshRenderers.Add(renderer);
            water.repetitionSize = 70f;
            water.largeWindSpeed = 3.5f;
            water.ripplesWindSpeed = 5.5f;
            water.largeChaos = 0.28f;
            water.ripplesChaos = 0.45f;
            water.timeMultiplier = 0.4f;
            water.startSmoothness = 0.97f;
            water.endSmoothness = 0.86f;
            water.absorptionDistance = 3.4f;
            water.maxRefractionDistance = 5f;
            water.volumeDepth = 6f;
            water.foam = true;
            water.caustics = true;
            water.tessellation = false;
            water.underWater = false;

            var shore = new GameObject("Shore");
            shore.transform.SetParent(root, false);
            shore.transform.position = new Vector3(GardenMap.LakeX, GardenMap.WaterY + 0.05f, GardenMap.LakeZ);
            shore.AddComponent<MeshFilter>().sharedMesh = GardenMeshes.ShoreRibbon(GardenMap.LakeRx, GardenMap.LakeRz, 2.4f, seg);
            var shoreRenderer = shore.AddComponent<MeshRenderer>();
            var foam = Lit(new Color(0.82f, 0.8f, 0.72f, 0.45f), 0.2f, sandTex, new Vector2(8f, 1f));
            if (foam.HasProperty("_SurfaceType")) foam.SetFloat("_SurfaceType", 1f);
            foam.EnableKeyword("_SURFACE_TYPE_TRANSPARENT");
            foam.renderQueue = 3000;
            shoreRenderer.sharedMaterial = foam;
            shoreRenderer.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;

            var probeGo = new GameObject("LakeReflection");
            probeGo.transform.SetParent(root, false);
            probeGo.transform.position = new Vector3(GardenMap.LakeX, GardenMap.WaterY + 2f, GardenMap.LakeZ);
            var probe = probeGo.AddComponent<ReflectionProbe>();
            probe.mode = UnityEngine.Rendering.ReflectionProbeMode.Realtime;
            probe.refreshMode = UnityEngine.Rendering.ReflectionProbeRefreshMode.OnAwake;
            probe.size = new Vector3(90f, 20f, 70f);
            probe.intensity = 1f;
        }

        static List<Transform> BuildTrees(Transform root)
        {
            var trees = new List<Transform>();
            var spots = new List<Vector3>
            {
                new Vector3(168f, 0f, 108f),
                new Vector3(162f, 0f, 86f),
                new Vector3(40f, 0f, 108f),
                new Vector3(36f, 0f, 84f),
                new Vector3(100f, 0f, 156f),
                new Vector3(100f, 0f, 42f),
                new Vector3(78f, 0f, 150f),
                new Vector3(124f, 0f, 148f),
                new Vector3(70f, 0f, 48f),
                new Vector3(132f, 0f, 52f),
                new Vector3(24f, 0f, 130f),
                new Vector3(176f, 0f, 140f),
                new Vector3(22f, 0f, 60f),
                new Vector3(178f, 0f, 58f),
            };
            for (int i = 0; i < spots.Count; i++)
            {
                if (GardenMap.InWater(spots[i].x, spots[i].z)) continue;
                string kind = i == 4 ? "life" : i == 5 ? "knowledge" : "tree";
                trees.Add(MakeTree(root, spots[i], kind, i));
            }
            return trees;
        }

        static Transform MakeTree(Transform root, Vector3 spot, string kind, int salt)
        {
            var go = new GameObject(kind == "tree" ? "Tree" : kind == "life" ? "Tree of Life" : "Tree of Knowledge");
            go.transform.SetParent(root, false);
            spot.y = GardenMap.Height(spot.x, spot.z);
            go.transform.position = spot;
            float tall = kind == "life" ? 9.5f : kind == "knowledge" ? 8.2f : 6.2f + (salt % 4) * 0.7f;
            var bark = Lit(new Color(0.35f, 0.22f, 0.12f), 0.28f, barkTex, new Vector2(1f, 3f));
            var trunk = new GameObject("Trunk");
            trunk.transform.SetParent(go.transform, false);
            trunk.AddComponent<MeshFilter>().sharedMesh = GardenMeshes.Trunk(tall, 0.22f + (salt % 3) * 0.04f, salt);
            trunk.AddComponent<MeshRenderer>().sharedMaterial = bark;

            for (int b = 0; b < 4; b++)
            {
                float ang = b / 4f * Mathf.PI * 2f + salt;
                var branch = new GameObject("Branch");
                branch.transform.SetParent(go.transform, false);
                branch.transform.localPosition = new Vector3(Mathf.Cos(ang) * 0.35f, tall * 0.46f, Mathf.Sin(ang) * 0.35f);
                branch.transform.localRotation = Quaternion.Euler(Mathf.Sin(ang) * 70f, 0f, Mathf.Cos(ang) * 70f);
                branch.AddComponent<MeshFilter>().sharedMesh = GardenMeshes.Trunk(tall * 0.28f, 0.05f, salt + b);
                branch.AddComponent<MeshRenderer>().sharedMaterial = bark;
            }

            Color leafColor = kind == "knowledge"
                ? new Color(0.45f, 0.22f, 0.12f)
                : kind == "life"
                    ? new Color(0.2f, 0.48f, 0.18f)
                    : new Color(0.16f, 0.38f, 0.14f);
            var leaves = Lit(leafColor, 0.22f, leafTex, Vector2.one);
            if (leaves.HasProperty("_AlphaCutoffEnable")) leaves.SetFloat("_AlphaCutoffEnable", 1f);
            if (leaves.HasProperty("_AlphaCutoff")) leaves.SetFloat("_AlphaCutoff", 0.35f);
            if (leaves.HasProperty("_DoubleSidedEnable")) leaves.SetFloat("_DoubleSidedEnable", 1f);
            leaves.EnableKeyword("_ALPHATEST_ON");
            int cards = kind == "tree" ? 18 : 28;
            for (int i = 0; i < cards; i++)
            {
                float ang = (i * 2.399f) + salt;
                float rad = 0.4f + (i % 5) * 0.35f;
                float y = tall * (0.48f + (i % 7) * 0.06f);
                var card = GameObject.CreatePrimitive(PrimitiveType.Quad);
                Object.Destroy(card.GetComponent<Collider>());
                card.transform.SetParent(go.transform, false);
                card.transform.localPosition = new Vector3(Mathf.Cos(ang) * rad, y, Mathf.Sin(ang) * rad);
                card.transform.localRotation = Quaternion.Euler(0f, -ang * Mathf.Rad2Deg, (i % 2 == 0 ? 18f : -18f));
                card.transform.localScale = new Vector3(1.4f, 1.8f, 1f);
                card.GetComponent<MeshRenderer>().sharedMaterial = leaves;
                card.GetComponent<MeshRenderer>().shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.TwoSided;
            }

            if (kind == "knowledge")
            {
                var fruitMat = Lit(new Color(0.72f, 0.55f, 0.16f), 0.45f, null, Vector2.one);
                for (int i = 0; i < 5; i++)
                {
                    var fruit = GameObject.CreatePrimitive(PrimitiveType.Sphere);
                    Object.Destroy(fruit.GetComponent<Collider>());
                    fruit.transform.SetParent(go.transform, false);
                    fruit.transform.localScale = Vector3.one * 0.18f;
                    fruit.transform.localPosition = new Vector3(Mathf.Cos(i) * 0.8f, tall * 0.62f, Mathf.Sin(i) * 0.8f);
                    fruit.GetComponent<MeshRenderer>().sharedMaterial = fruitMat;
                }
            }
            return go.transform;
        }

        static void BuildRocks(Transform root)
        {
            var mat = Lit(new Color(0.45f, 0.42f, 0.38f), 0.18f, rockTex, Vector2.one);
            var spots = new[]
            {
                new Vector3(130f, 0f, 70f),
                new Vector3(64f, 0f, 132f),
                new Vector3(158f, 0f, 128f),
                new Vector3(48f, 0f, 70f),
            };
            var mesh = GardenMeshes.Boulder(3);
            foreach (var spot in spots)
            {
                if (GardenMap.InWater(spot.x, spot.z)) continue;
                var go = new GameObject("Rock");
                go.transform.SetParent(root, false);
                var p = spot;
                p.y = GardenMap.Height(p.x, p.z);
                go.transform.position = p;
                go.transform.localScale = new Vector3(1.4f, 0.8f, 1.1f);
                go.AddComponent<MeshFilter>().sharedMesh = mesh;
                go.AddComponent<MeshRenderer>().sharedMaterial = mat;
            }
        }

        static void BuildCamp(Transform root, GardenWorld world)
        {
            world.Fire = new Vector3(150f, 0f, 100f);
            world.Fire.y = GardenMap.Height(world.Fire.x, world.Fire.z);
            world.Pot = world.Fire + new Vector3(1.1f, 0f, 0.2f);
            world.Pot.y = GardenMap.Height(world.Pot.x, world.Pot.z);
            world.Cup = world.Fire + new Vector3(0.2f, 0f, 1.15f);
            world.Cup.y = GardenMap.Height(world.Cup.x, world.Cup.z);

            var wood = Lit(new Color(0.32f, 0.18f, 0.08f), 0.3f, barkTex, Vector2.one);
            var logMesh = GardenMeshes.Trunk(1.1f, 0.08f, 4);
            for (int i = 0; i < 4; i++)
            {
                var log = new GameObject("Log");
                log.transform.SetParent(root, false);
                log.transform.position = world.Fire + new Vector3(0f, 0.12f, 0f);
                log.transform.rotation = Quaternion.Euler(80f, i * 40f, 20f);
                log.AddComponent<MeshFilter>().sharedMesh = logMesh;
                log.AddComponent<MeshRenderer>().sharedMaterial = wood;
            }

            var flame = new GameObject("Flame");
            flame.transform.SetParent(root, false);
            flame.transform.position = world.Fire + new Vector3(0f, 0.15f, 0f);
            flame.AddComponent<MeshFilter>().sharedMesh = GardenMeshes.Trunk(0.7f, 0.16f, 9);
            var flameMat = Lit(new Color(1f, 0.45f, 0.12f), 0.2f, null, Vector2.one);
            if (flameMat.HasProperty("_EmissiveColor")) flameMat.SetColor("_EmissiveColor", new Color(4f, 1.2f, 0.2f));
            flameMat.EnableKeyword("_EMISSIVE_COLOR");
            flame.AddComponent<MeshRenderer>().sharedMaterial = flameMat;

            var lightGo = new GameObject("Campfire");
            lightGo.transform.SetParent(root, false);
            lightGo.transform.position = world.Fire + new Vector3(0f, 1.1f, 0f);
            var light = lightGo.AddComponent<Light>();
            light.type = LightType.Point;
            light.color = new Color(1f, 0.62f, 0.28f);
            light.range = 9f;
            light.intensity = 2500f;
            var camp = lightGo.AddComponent<HDAdditionalLightData>();
            camp.SetIntensity(2500f, LightUnit.Lumen);

            Prop(root, "Pot", world.Pot + Vector3.up * 0.15f, new Vector3(0.34f, 0.16f, 0.34f), new Color(0.25f, 0.22f, 0.18f));
            Prop(root, "Cup", world.Cup + Vector3.up * 0.08f, new Vector3(0.1f, 0.08f, 0.1f), new Color(0.55f, 0.42f, 0.28f));

            world.WorkAdam = NearestTree(world.Trees, new Vector3(168f, 0f, 108f));
            world.WorkEve = NearestTree(world.Trees, new Vector3(162f, 0f, 86f));
        }

        static Transform NearestTree(List<Transform> trees, Vector3 hint)
        {
            Transform best = null;
            float bestD = float.PositiveInfinity;
            foreach (var tree in trees)
            {
                if (tree.name.Contains("Life") || tree.name.Contains("Knowledge")) continue;
                float d = Vector3.Distance(tree.position, hint);
                if (d < bestD)
                {
                    bestD = d;
                    best = tree;
                }
            }
            return best != null ? best : (trees.Count > 0 ? trees[0] : null);
        }

        static void Prop(Transform root, string name, Vector3 pos, Vector3 scale, Color color)
        {
            var go = new GameObject(name);
            go.transform.SetParent(root, false);
            go.transform.position = pos;
            go.transform.localScale = scale;
            go.AddComponent<MeshFilter>().sharedMesh = GardenMeshes.Trunk(1f, 0.5f, name.Length);
            go.AddComponent<MeshRenderer>().sharedMaterial = Lit(color, 0.35f, null, Vector2.one);
        }

        static Person BuildPerson(Transform root, string who, string personName, Vector3 spot, GardenWorld world)
        {
            var go = new GameObject(personName);
            go.transform.SetParent(root, false);
            var person = go.AddComponent<Person>();
            person.who = who;
            person.personName = personName;
            if (who == "adam") person.body.fatigue = 18f;
            else person.body.fatigue = 10f;
            HumanForm.Attach(person, who == "eve");
            Vector3 seat = spot;
            seat.y = 0f;
            Transform tree = who == "eve" ? world.WorkEve : world.WorkAdam;
            person.BindDay(world.Fire, world.Pot, world.Cup, tree, seat);
            return person;
        }

        static void BuildGroundCover(Transform root)
        {
            var mesh = GardenMeshes.Tuft();
            var mat = Lit(new Color(0.34f, 0.48f, 0.18f), 0.15f, grassTex, Vector2.one);
            if (mat.HasProperty("_DoubleSidedEnable")) mat.SetFloat("_DoubleSidedEnable", 1f);
            if (mat.HasProperty("_AlphaCutoffEnable")) mat.SetFloat("_AlphaCutoffEnable", 1f);
            mat.EnableKeyword("_DOUBLESIDED_ON");
            var cover = new GameObject("Meadow");
            cover.transform.SetParent(root, false);
            for (int i = 0; i < 180; i++)
            {
                float x = 18f + (i * 47 % 164);
                float z = 16f + (i * 29 % 168);
                if (GardenMap.InWater(x, z)) continue;
                if (Vector3.Distance(new Vector3(x, 0f, z), new Vector3(150f, 0f, 100f)) < 6f) continue;
                var tuft = new GameObject("Grass");
                tuft.transform.SetParent(cover.transform, false);
                float y = GardenMap.Height(x, z);
                tuft.transform.position = new Vector3(x, y, z);
                tuft.transform.rotation = Quaternion.Euler(0f, i * 37f, 0f);
                float scale = 0.7f + (i % 5) * 0.12f;
                tuft.transform.localScale = new Vector3(scale, scale, scale);
                tuft.AddComponent<MeshFilter>().sharedMesh = mesh;
                tuft.AddComponent<MeshRenderer>().sharedMaterial = mat;
            }
        }

        static void DressMorning()
        {
            var volume = Object.FindFirstObjectByType<Volume>();
            if (volume == null || volume.profile == null) return;
            if (!volume.profile.TryGet(out Fog fog)) fog = volume.profile.Add<Fog>();
            fog.active = true;
            fog.enabled.Override(true);
            fog.albedo.Override(new Color(0.74f, 0.78f, 0.82f));
            fog.meanFreePath.Override(140f);
            fog.baseHeight.Override(6f);
            fog.maximumHeight.Override(90f);
        }
    }
}
