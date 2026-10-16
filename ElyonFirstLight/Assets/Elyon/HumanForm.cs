using UnityEngine;
using UnityEngine.Rendering.HighDefinition;

namespace Elyon
{
    /// <summary>
    /// A skinned body: face, ears, limbs, skin, and a mass that sits in the hips and shoulders.
    /// Adam carries more weight than Eve. Motion stays on a kinematic rigidbody.
    /// </summary>
    public static class HumanForm
    {
        const int Hips = 0;
        const int Spine = 1;
        const int Chest = 2;
        const int Neck = 3;
        const int Head = 4;
        const int ThighL = 5;
        const int ShinL = 6;
        const int FootL = 7;
        const int ThighR = 8;
        const int ShinR = 9;
        const int FootR = 10;
        const int ArmL = 11;
        const int ForeL = 12;
        const int HandL = 13;
        const int ArmR = 14;
        const int ForeR = 15;
        const int HandR = 16;
        const int BoneCount = 17;
        const int Segments = 14;

        struct BodyShape
        {
            public float Mass;
            public float HipY;
            public float Shoulder;
            public float Chest;
            public float Waist;
            public float Hip;
            public float Thigh;
            public float Calf;
            public float UpperArm;
            public float Forearm;
            public float ChestForward;
            public float Belly;
            public Color Skin;
            public Color Hair;
            public bool Eve;
        }

        public static void Attach(Person person, bool eve)
        {
            BodyShape shape = eve ? EveShape() : AdamShape();
            person.massKg = shape.Mass;
            person.standHip = shape.HipY;
            var armature = new GameObject("Armature").transform;
            armature.SetParent(person.transform, false);
            var bones = new Transform[BoneCount];
            BuildSkeleton(armature, bones, shape, person);

            var skin = SkinMaterial(shape);
            var body = new MeshDraft();
            Vector3 hip = Local(person, bones[Hips]);
            Vector3 chest = Local(person, bones[Chest]);
            Vector3 neck = Local(person, bones[Neck]);
            Vector3 head = Local(person, bones[Head]);
            Torso(body, hip, chest, neck, shape);
            Limb(body, hip + new Vector3(-shape.Hip * 0.28f, -0.02f, 0f), Local(person, bones[ThighL]), Local(person, bones[ShinL]), shape.Thigh, shape.Thigh * 0.72f, ThighL, 0.18f);
            Limb(body, Local(person, bones[ThighL]), Local(person, bones[ShinL]), Local(person, bones[FootL]), shape.Thigh * 0.72f, shape.Calf, ShinL, 0.08f);
            Foot(body, bones[FootL], person, FootL, shape);
            Limb(body, hip + new Vector3(shape.Hip * 0.28f, -0.02f, 0f), Local(person, bones[ThighR]), Local(person, bones[ShinR]), shape.Thigh, shape.Thigh * 0.72f, ThighR, 0.18f);
            Limb(body, Local(person, bones[ThighR]), Local(person, bones[ShinR]), Local(person, bones[FootR]), shape.Thigh * 0.72f, shape.Calf, ShinR, 0.08f);
            Foot(body, bones[FootR], person, FootR, shape);
            Limb(body, chest + new Vector3(-shape.Shoulder * 0.5f, 0.02f, 0f), Local(person, bones[ArmL]), Local(person, bones[ForeL]), shape.UpperArm, shape.UpperArm * 0.82f, ArmL, 0.12f);
            Limb(body, Local(person, bones[ArmL]), Local(person, bones[ForeL]), Local(person, bones[HandL]), shape.UpperArm * 0.78f, shape.Forearm, ForeL, 0.02f);
            Hand(body, bones[HandL], person, HandL, -1f, shape);
            Limb(body, chest + new Vector3(shape.Shoulder * 0.5f, 0.02f, 0f), Local(person, bones[ArmR]), Local(person, bones[ForeR]), shape.UpperArm, shape.UpperArm * 0.82f, ArmR, 0.12f);
            Limb(body, Local(person, bones[ArmR]), Local(person, bones[ForeR]), Local(person, bones[HandR]), shape.UpperArm * 0.78f, shape.Forearm, ForeR, 0.02f);
            Hand(body, bones[HandR], person, HandR, 1f, shape);
            HeadMesh(body, head, shape);

            var renderer = SkinRenderer(person.transform, body.ToMesh(person.personName + " Body", true), bones, skin);
            renderer.localBounds = new Bounds(new Vector3(0f, 1f, 0f), new Vector3(1.6f, 2.2f, 1.2f));
            Linen(person.transform, bones, shape);
            Face(bones[Head], shape, skin);
            Hair(bones[Head], shape);
            Axe(bones[HandR], person);
            Physics(person, shape);
            Label(bones[Head], person.personName);
        }

        static BodyShape AdamShape()
        {
            return new BodyShape
            {
                Mass = 78f,
                HipY = 0.92f,
                Shoulder = 0.46f,
                Chest = 0.20f,
                Waist = 0.16f,
                Hip = 0.18f,
                Thigh = 0.11f,
                Calf = 0.075f,
                UpperArm = 0.065f,
                Forearm = 0.048f,
                ChestForward = 0.035f,
                Belly = 0.045f,
                Skin = new Color(0.55f, 0.36f, 0.24f),
                Hair = new Color(0.08f, 0.05f, 0.03f),
                Eve = false,
            };
        }

        static BodyShape EveShape()
        {
            return new BodyShape
            {
                Mass = 58f,
                HipY = 0.88f,
                Shoulder = 0.36f,
                Chest = 0.16f,
                Waist = 0.125f,
                Hip = 0.19f,
                Thigh = 0.105f,
                Calf = 0.068f,
                UpperArm = 0.05f,
                Forearm = 0.038f,
                ChestForward = 0.055f,
                Belly = 0.02f,
                Skin = new Color(0.73f, 0.52f, 0.40f),
                Hair = new Color(0.16f, 0.09f, 0.05f),
                Eve = true,
            };
        }

        static void BuildSkeleton(Transform armature, Transform[] bones, BodyShape shape, Person person)
        {
            bones[Hips] = Bone(armature, "Hips", new Vector3(0f, shape.HipY, 0f));
            bones[Spine] = Bone(bones[Hips], "Spine", new Vector3(0f, 0.16f, 0.005f));
            bones[Chest] = Bone(bones[Spine], "Chest", new Vector3(0f, 0.2f, 0.01f));
            bones[Neck] = Bone(bones[Chest], "Neck", new Vector3(0f, 0.16f, 0.01f));
            bones[Head] = Bone(bones[Neck], "Head", new Vector3(0f, 0.12f, 0.015f));
            bones[ThighL] = Bone(bones[Hips], "ThighL", new Vector3(-0.1f, -0.04f, 0f));
            bones[ShinL] = Bone(bones[ThighL], "ShinL", new Vector3(0f, -0.42f, 0f));
            bones[FootL] = Bone(bones[ShinL], "FootL", new Vector3(0f, -0.4f, 0.02f));
            bones[ThighR] = Bone(bones[Hips], "ThighR", new Vector3(0.1f, -0.04f, 0f));
            bones[ShinR] = Bone(bones[ThighR], "ShinR", new Vector3(0f, -0.42f, 0f));
            bones[FootR] = Bone(bones[ShinR], "FootR", new Vector3(0f, -0.4f, 0.02f));
            bones[ArmL] = Bone(bones[Chest], "UpperArmL", new Vector3(-shape.Shoulder * 0.48f, 0.04f, 0f));
            bones[ForeL] = Bone(bones[ArmL], "ForearmL", new Vector3(0f, -0.3f, 0f));
            bones[HandL] = Bone(bones[ForeL], "HandL", new Vector3(0f, -0.26f, 0f));
            bones[ArmR] = Bone(bones[Chest], "UpperArmR", new Vector3(shape.Shoulder * 0.48f, 0.04f, 0f));
            bones[ForeR] = Bone(bones[ArmR], "ForearmR", new Vector3(0f, -0.3f, 0f));
            bones[HandR] = Bone(bones[ForeR], "HandR", new Vector3(0f, -0.26f, 0f));

            person.hips = bones[Hips];
            person.thighL = bones[ThighL];
            person.shinL = bones[ShinL];
            person.thighR = bones[ThighR];
            person.shinR = bones[ShinR];
            person.shoulderL = bones[ArmL];
            person.shoulderR = bones[ArmR];
        }

        static Transform Bone(Transform parent, string name, Vector3 local)
        {
            var go = new GameObject(name);
            go.transform.SetParent(parent, false);
            go.transform.localPosition = local;
            go.transform.localRotation = Quaternion.identity;
            return go.transform;
        }

        static Vector3 Local(Person person, Transform bone)
        {
            return person.transform.InverseTransformPoint(bone.position);
        }

        static void Torso(MeshDraft draft, Vector3 hip, Vector3 chest, Vector3 neck, BodyShape shape)
        {
            Vector3 crotch = hip + new Vector3(0f, -0.12f, 0.01f);
            Vector3 waist = Vector3.Lerp(hip, chest, 0.28f);
            Vector3 ribs = Vector3.Lerp(hip, chest, 0.62f);
            Vector3 shoulder = chest + new Vector3(0f, 0.08f, 0f);
            Vector3[] centers = { crotch, hip, waist, ribs, chest, shoulder, neck };
            float[] rx = { shape.Hip * 0.72f, shape.Hip, shape.Waist, shape.Chest * 0.92f, shape.Chest, shape.Shoulder * 0.55f, 0.055f };
            float[] ry = { shape.Hip * 0.62f, shape.Hip * 0.78f, shape.Waist * 0.85f, shape.Chest * 0.8f, shape.Chest * 0.86f, shape.Shoulder * 0.36f, 0.05f };
            float[] forward = { 0.01f, shape.Belly * 0.4f, shape.Belly, shape.ChestForward * 0.7f, shape.ChestForward, 0.02f, 0.01f };
            int[] bones = { Hips, Hips, Spine, Spine, Chest, Chest, Neck };
            int previous = -1;
            for (int i = 0; i < centers.Length; i++)
            {
                var weight = i == 0
                    ? MeshDraft.Bone(Hips)
                    : MeshDraft.Blend(bones[i - 1], bones[i], 0.35f);
                Vector3 center = centers[i] + new Vector3(0f, 0f, forward[i]);
                int ring = draft.Ring(center, Vector3.up, rx[i], ry[i], Segments, i / 6f, SkinTint(shape, 0.15f - i * 0.01f), weight);
                if (previous >= 0) draft.Bridge(previous, ring, Segments);
                previous = ring;
            }
        }

        static void Limb(MeshDraft draft, Vector3 from, Vector3 mid, Vector3 to, float r0, float r1, int bone, float muscle)
        {
            Vector3 a = Vector3.Lerp(from, mid, 0.15f);
            Vector3 b = Vector3.Lerp(mid, to, 0.85f);
            const int rings = 5;
            int previous = -1;
            Vector3 axis = b - a;
            for (int r = 0; r <= rings; r++)
            {
                float t = r / (float)rings;
                float radius = Mathf.Lerp(r0, r1, t) * (1f + muscle * Mathf.Sin(t * Mathf.PI));
                Vector3 center = Vector3.Lerp(a, b, t);
                int ring = draft.Ring(center, axis, radius, radius * 0.9f, 10, t, Color.white, MeshDraft.Bone(bone));
                if (previous >= 0) draft.Bridge(previous, ring, 10);
                previous = ring;
            }
        }

        static void Foot(MeshDraft draft, Transform foot, Person person, int bone, BodyShape shape)
        {
            Vector3 origin = Local(person, foot);
            Vector3 forward = person.transform.InverseTransformDirection(foot.forward);
            Vector3 up = person.transform.InverseTransformDirection(foot.up);
            var weight = MeshDraft.Bone(bone);
            int previous = -1;
            for (int i = 0; i < 3; i++)
            {
                Vector3 center = origin + forward * (0.02f + i * 0.05f) + up * 0.025f;
                int ring = draft.Ring(center, forward, 0.045f, 0.028f, 8, i / 2f, SkinTint(shape, 0f), weight);
                if (previous >= 0) draft.Bridge(previous, ring, 8);
                previous = ring;
            }
            if (previous >= 0) draft.Cap(previous, 8, true, weight, SkinTint(shape, 0f));
        }

        static void Hand(MeshDraft draft, Transform hand, Person person, int bone, float side, BodyShape shape)
        {
            Vector3 origin = Local(person, hand);
            Vector3 down = person.transform.InverseTransformDirection(-hand.up);
            Vector3 right = person.transform.InverseTransformDirection(hand.right) * side;
            var weight = MeshDraft.Bone(bone);
            int previous = -1;
            for (int i = 0; i < 3; i++)
            {
                Vector3 center = origin + down * (i * 0.035f) + right * 0.005f;
                float radius = i == 2 ? 0.02f : 0.032f;
                int ring = draft.Ring(center, down, radius, 0.016f, 8, i / 2f, SkinTint(shape, 0.02f), weight);
                if (previous >= 0) draft.Bridge(previous, ring, 8);
                previous = ring;
            }
            Vector3 thumb = origin + right * 0.03f + down * 0.02f;
            int thumbRing = draft.Ring(thumb, right, 0.012f, 0.012f, 6, 0f, SkinTint(shape, 0.02f), weight);
            draft.Cap(thumbRing, 6, true, weight, SkinTint(shape, 0.02f));
        }

        static void HeadMesh(MeshDraft draft, Vector3 center, BodyShape shape)
        {
            const int lat = 14;
            const int lon = 18;
            int previous = -1;
            for (int y = 0; y <= lat; y++)
            {
                float v = y / (float)lat;
                float phi = v * Mathf.PI;
                int start = draft.Verts.Count;
                for (int x = 0; x < lon; x++)
                {
                    float u = x / (float)lon;
                    float theta = u * Mathf.PI * 2f;
                    var sphere = new Vector3(
                        Mathf.Sin(phi) * Mathf.Cos(theta),
                        Mathf.Cos(phi),
                        Mathf.Sin(phi) * Mathf.Sin(theta));
                    Vector3 sculpted = Sculpt(sphere, shape.Eve);
                    sculpted = new Vector3(sculpted.x * 0.108f, sculpted.y * 0.132f, sculpted.z * 0.116f);
                    float warmth = sculpted.z > 0.02f && sculpted.y < 0.02f && sculpted.y > -0.04f ? 0.08f : 0f;
                    draft.Add(center + sculpted, new Vector2(u, v), SkinTint(shape, warmth), MeshDraft.Bone(Head));
                }
                if (previous >= 0) draft.Bridge(previous, start, lon);
                previous = start;
            }
        }

        static Vector3 Sculpt(Vector3 p, bool eve)
        {
            float x = p.x;
            float y = p.y;
            float z = p.z;
            float jaw = Mathf.Clamp01((-y + 0.05f) * 1.4f);
            x *= 1f - jaw * (eve ? 0.04f : 0.0f) + jaw * (eve ? 0f : 0.08f);
            if (y < -0.35f && z > 0f)
            {
                float chin = Mathf.Clamp01((-y - 0.35f) * 3f) * Mathf.Clamp01(z);
                z += chin * (eve ? 0.08f : 0.12f);
                y -= chin * 0.04f;
            }
            float noseX = Mathf.Abs(x);
            float noseY = Mathf.Abs(y - 0.02f);
            if (noseX < 0.2f && noseY < 0.24f && z > 0.15f)
            {
                float nose = Mathf.Clamp01(1f - noseX / 0.2f) * Mathf.Clamp01(1f - noseY / 0.24f);
                z += nose * (eve ? 0.18f : 0.22f);
            }
            for (int side = -1; side <= 1; side += 2)
            {
                float dx = x - 0.2f * side;
                float dy = y - 0.08f;
                float socket = dx * dx / 0.02f + dy * dy / 0.012f;
                if (socket < 1f && z > 0.15f) z -= (1f - socket) * 0.14f;
            }
            if (noseX < 0.28f && Mathf.Abs(y + 0.28f) < 0.07f && z > 0.2f)
            {
                z += (0.07f - Mathf.Abs(y + 0.28f)) * 1.1f;
            }
            if (y > 0.12f && y < 0.32f && z > 0.15f && noseX < 0.45f)
            {
                z += (eve ? 0.03f : 0.05f);
            }
            return new Vector3(x, y, z);
        }

        static Color SkinTint(BodyShape shape, float warmth)
        {
            return new Color(
                Mathf.Clamp01(shape.Skin.r + warmth),
                Mathf.Clamp01(shape.Skin.g + warmth * 0.35f),
                Mathf.Clamp01(shape.Skin.b + warmth * 0.2f),
                1f);
        }

        static void Face(Transform head, BodyShape shape, Material skin)
        {
            var white = Lit(new Color(0.92f, 0.9f, 0.86f), 0.62f, null);
            var iris = Lit(shape.Eve ? new Color(0.18f, 0.36f, 0.26f) : new Color(0.22f, 0.15f, 0.09f), 0.35f, null);
            var lip = Lit(new Color(0.55f, 0.28f, 0.26f), 0.48f, null);
            for (int side = -1; side <= 1; side += 2)
            {
                var eye = Sphere(head, "Eye", new Vector3(0.032f * side, 0.012f, 0.055f), 0.016f, white);
                Sphere(eye, "Iris", new Vector3(0f, 0f, 0.012f), 0.008f, iris);
                var ear = new GameObject("Ear");
                ear.transform.SetParent(head, false);
                ear.transform.localPosition = new Vector3(0.09f * side, -0.01f, 0f);
                ear.transform.localRotation = Quaternion.Euler(0f, side * 90f, 0f);
                var filter = ear.AddComponent<MeshFilter>();
                filter.sharedMesh = GardenMeshes.Trunk(0.07f, 0.012f, side + 3);
                ear.AddComponent<MeshRenderer>().sharedMaterial = skin;
            }
            var mouth = Quad(head, "Mouth", new Vector3(0f, -0.035f, 0.09f), new Vector3(0.045f, 0.012f, 1f), lip);
            mouth.localRotation = Quaternion.identity;
        }

        static void Hair(Transform head, BodyShape shape)
        {
            var hair = Shader.Find("HDRP/Hair");
            Material mat = hair != null ? new Material(hair) : Lit(shape.Hair, 0.22f, null);
            if (mat.HasProperty("_BaseColor")) mat.SetColor("_BaseColor", shape.Hair);
            mat.color = shape.Hair;
            if (mat.HasProperty("_Smoothness")) mat.SetFloat("_Smoothness", 0.22f);
            HDMaterial.ValidateMaterial(mat);
            var scalp = Sphere(head, "Scalp", new Vector3(0f, 0.04f, -0.005f), 0.125f, mat);
            scalp.localScale = new Vector3(1.05f, 0.72f, 1.05f);
            if (!shape.Eve)
            {
                Sphere(head, "Beard", new Vector3(0f, -0.055f, 0.03f), 0.07f, mat);
                return;
            }
            Lock(head, mat, new Vector3(0f, -0.02f, -0.06f), 0.16f);
            Lock(head, mat, new Vector3(-0.07f, -0.01f, 0f), 0.18f);
            Lock(head, mat, new Vector3(0.07f, -0.01f, 0f), 0.18f);
        }

        static void Lock(Transform head, Material mat, Vector3 local, float length)
        {
            var go = new GameObject("Lock");
            go.transform.SetParent(head, false);
            go.transform.localPosition = local;
            go.AddComponent<MeshFilter>().sharedMesh = GardenMeshes.Trunk(length, 0.02f, 2);
            go.AddComponent<MeshRenderer>().sharedMaterial = mat;
        }

        static void Linen(Transform root, Transform[] bones, BodyShape shape)
        {
            var draft = new MeshDraft();
            var cloth = shape.Eve ? new Color(0.82f, 0.74f, 0.62f) : new Color(0.62f, 0.48f, 0.30f);
            int previous = -1;
            for (int i = 0; i < 6; i++)
            {
                float t = i / 5f;
                Vector3 center = bones[Hips].localPosition + new Vector3(0f, 0.02f - t * 0.55f, 0.02f);
                float radius = Mathf.Lerp(shape.Waist * 1.15f, shape.Hip * 1.35f, t);
                radius *= 1f + 0.04f * Mathf.Sin(i * 1.7f);
                var weight = MeshDraft.Bone(Hips);
                int ring = draft.Ring(center, Vector3.up, radius, radius * 0.8f, Segments, t, cloth, weight);
                if (previous >= 0) draft.Bridge(previous, ring, Segments);
                previous = ring;
            }
            var mat = Lit(cloth, 0.45f, null);
            if (mat.HasProperty("_DoubleSidedEnable")) mat.SetFloat("_DoubleSidedEnable", 1f);
            SkinRenderer(root, draft.ToMesh("Linen", true), bones, mat);
        }

        static void Axe(Transform hand, Person person)
        {
            var handle = new GameObject("Axe");
            handle.transform.SetParent(hand, false);
            handle.transform.localPosition = new Vector3(0f, -0.08f, 0.02f);
            handle.transform.localRotation = Quaternion.Euler(0f, 0f, 0f);
            var wood = Lit(new Color(0.35f, 0.22f, 0.1f), 0.32f, null);
            handle.AddComponent<MeshFilter>().sharedMesh = GardenMeshes.Trunk(0.55f, 0.012f, 1);
            handle.AddComponent<MeshRenderer>().sharedMaterial = wood;
            var head = new GameObject("AxeHead");
            head.transform.SetParent(handle.transform, false);
            head.transform.localPosition = new Vector3(0.04f, 0.5f, 0f);
            var iron = Lit(new Color(0.55f, 0.56f, 0.52f), 0.72f, null);
            var draft = new MeshDraft();
            int ring = draft.Ring(Vector3.zero, Vector3.right, 0.02f, 0.055f, 8, 0.5f, Color.white, MeshDraft.Bone(0));
            draft.Cap(ring, 8, false, MeshDraft.Bone(0), Color.white);
            int far = draft.Ring(new Vector3(0.08f, 0f, 0f), Vector3.right, 0.012f, 0.04f, 8, 1f, Color.white, MeshDraft.Bone(0));
            draft.Bridge(ring, far, 8);
            draft.Cap(far, 8, true, MeshDraft.Bone(0), Color.white);
            head.AddComponent<MeshFilter>().sharedMesh = draft.ToMesh("AxeHead", false);
            head.AddComponent<MeshRenderer>().sharedMaterial = iron;
            person.axe = handle.transform;
            handle.SetActive(false);
        }

        static void Physics(Person person, BodyShape shape)
        {
            var body = person.gameObject.AddComponent<Rigidbody>();
            body.mass = shape.Mass;
            body.isKinematic = true;
            body.useGravity = true;
            body.interpolation = RigidbodyInterpolation.Interpolate;
            body.collisionDetectionMode = CollisionDetectionMode.ContinuousSpeculative;
            var capsule = person.gameObject.AddComponent<CapsuleCollider>();
            capsule.height = shape.Eve ? 1.62f : 1.78f;
            capsule.radius = shape.Hip * 0.85f;
            capsule.center = new Vector3(0f, capsule.height * 0.5f, 0f);
        }

        static void Label(Transform head, string personName)
        {
            var go = new GameObject("Name");
            go.transform.SetParent(head, false);
            go.transform.localPosition = new Vector3(0f, 0.22f, 0f);
            var label = go.AddComponent<TextMesh>();
            label.text = personName;
            label.characterSize = 0.08f;
            label.anchor = TextAnchor.MiddleCenter;
            label.alignment = TextAlignment.Center;
            label.color = new Color(0.96f, 0.92f, 0.84f);
            label.fontSize = 48;
        }

        static SkinnedMeshRenderer SkinRenderer(Transform root, Mesh mesh, Transform[] bones, Material material)
        {
            var go = new GameObject(mesh.name);
            go.transform.SetParent(root, false);
            var renderer = go.AddComponent<SkinnedMeshRenderer>();
            var bind = new Matrix4x4[bones.Length];
            for (int i = 0; i < bones.Length; i++)
            {
                bind[i] = bones[i].worldToLocalMatrix * go.transform.localToWorldMatrix;
            }
            mesh.bindposes = bind;
            renderer.sharedMesh = mesh;
            renderer.bones = bones;
            renderer.rootBone = bones[Hips];
            renderer.sharedMaterial = material;
            renderer.updateWhenOffscreen = true;
            renderer.quality = SkinQuality.Bone4;
            return renderer;
        }

        static Material SkinMaterial(BodyShape shape)
        {
            var mat = Lit(shape.Skin, 0.36f, SkinTexture(shape));
            if (mat.HasProperty("_MaterialID")) mat.SetFloat("_MaterialID", 1f);
            mat.EnableKeyword("_MATERIAL_FEATURE_SUBSURFACE_SCATTERING");
            if (mat.HasProperty("_SubsurfaceMask")) mat.SetFloat("_SubsurfaceMask", 1f);
            if (mat.HasProperty("_Thickness")) mat.SetFloat("_Thickness", shape.Eve ? 0.55f : 0.7f);
            if (mat.HasProperty("_VertexColorMode")) mat.SetFloat("_VertexColorMode", 1f);
            var normal = PoreNormal();
            if (mat.HasProperty("_NormalMap")) mat.SetTexture("_NormalMap", normal);
            if (mat.HasProperty("_NormalScale")) mat.SetFloat("_NormalScale", 0.45f);
            HDMaterial.ValidateMaterial(mat);
            return mat;
        }

        static Texture2D SkinTexture(BodyShape shape)
        {
            var tex = new Texture2D(128, 128, TextureFormat.RGBA32, true);
            for (int y = 0; y < 128; y++)
            {
                for (int x = 0; x < 128; x++)
                {
                    float pore = Mathf.PerlinNoise(x * 0.35f, y * 0.35f);
                    float blot = Mathf.PerlinNoise(x * 0.05f + 4f, y * 0.05f);
                    float shade = 0.86f + pore * 0.1f + blot * 0.08f;
                    tex.SetPixel(x, y, new Color(shape.Skin.r * shade, shape.Skin.g * shade, shape.Skin.b * shade, 1f));
                }
            }
            tex.Apply();
            tex.wrapMode = TextureWrapMode.Repeat;
            return tex;
        }

        static Texture2D PoreNormal()
        {
            var tex = new Texture2D(64, 64, TextureFormat.RGBA32, true);
            for (int y = 0; y < 64; y++)
            {
                for (int x = 0; x < 64; x++)
                {
                    float h = Mathf.PerlinNoise(x * 0.45f, y * 0.45f);
                    tex.SetPixel(x, y, new Color(0.5f, 0.5f + (h - 0.5f) * 0.25f, 1f, 1f));
                }
            }
            tex.Apply();
            tex.wrapMode = TextureWrapMode.Repeat;
            return tex;
        }

        static Material Lit(Color color, float smooth, Texture2D albedo)
        {
            var shader = Shader.Find("HDRP/Lit");
            if (shader == null) shader = Shader.Find("Standard");
            var mat = new Material(shader);
            if (mat.HasProperty("_BaseColor")) mat.SetColor("_BaseColor", color);
            mat.color = color;
            if (mat.HasProperty("_Smoothness")) mat.SetFloat("_Smoothness", smooth);
            if (mat.HasProperty("_Metallic")) mat.SetFloat("_Metallic", 0f);
            if (albedo != null)
            {
                if (mat.HasProperty("_BaseColorMap")) mat.SetTexture("_BaseColorMap", albedo);
                mat.mainTexture = albedo;
            }
            HDMaterial.ValidateMaterial(mat);
            return mat;
        }

        static Transform Sphere(Transform parent, string name, Vector3 local, float radius, Material material)
        {
            var draft = new MeshDraft();
            const int lat = 8;
            const int lon = 10;
            int previous = -1;
            for (int y = 0; y <= lat; y++)
            {
                float v = y / (float)lat;
                float phi = v * Mathf.PI;
                int start = draft.Verts.Count;
                for (int x = 0; x < lon; x++)
                {
                    float theta = x / (float)lon * Mathf.PI * 2f;
                    var p = new Vector3(Mathf.Sin(phi) * Mathf.Cos(theta), Mathf.Cos(phi), Mathf.Sin(phi) * Mathf.Sin(theta)) * radius;
                    draft.Add(p, new Vector2(x / (float)lon, v), Color.white, MeshDraft.Bone(0));
                }
                if (previous >= 0) draft.Bridge(previous, start, lon);
                previous = start;
            }
            var go = new GameObject(name);
            go.transform.SetParent(parent, false);
            go.transform.localPosition = local;
            go.AddComponent<MeshFilter>().sharedMesh = draft.ToMesh(name, false);
            go.AddComponent<MeshRenderer>().sharedMaterial = material;
            return go.transform;
        }

        static Transform Quad(Transform parent, string name, Vector3 local, Vector3 scale, Material material)
        {
            var draft = new MeshDraft();
            draft.Add(new Vector3(-0.5f, -0.5f, 0f), new Vector2(0f, 0f), Color.white, MeshDraft.Bone(0));
            draft.Add(new Vector3(0.5f, -0.5f, 0f), new Vector2(1f, 0f), Color.white, MeshDraft.Bone(0));
            draft.Add(new Vector3(-0.5f, 0.5f, 0f), new Vector2(0f, 1f), Color.white, MeshDraft.Bone(0));
            draft.Add(new Vector3(0.5f, 0.5f, 0f), new Vector2(1f, 1f), Color.white, MeshDraft.Bone(0));
            draft.Tris.Add(0);
            draft.Tris.Add(2);
            draft.Tris.Add(1);
            draft.Tris.Add(2);
            draft.Tris.Add(3);
            draft.Tris.Add(1);
            var go = new GameObject(name);
            go.transform.SetParent(parent, false);
            go.transform.localPosition = local;
            go.transform.localScale = scale;
            go.AddComponent<MeshFilter>().sharedMesh = draft.ToMesh(name, false);
            go.AddComponent<MeshRenderer>().sharedMaterial = material;
            return go.transform;
        }
    }
}
