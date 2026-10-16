#if UNITY_EDITOR
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace Elyon.EditorTools
{
    public static class GardenMenu
    {
        [MenuItem("Elyon/Open First Light")]
        public static void Open()
        {
            EnsureDirector();
        }

        public static void BuildBatch()
        {
            EnsureDirector();
            EditorApplication.Exit(0);
        }

        public static void PlayBatch()
        {
            EnsureDirector();
            EditorApplication.playModeStateChanged += OnPlayMode;
            EditorApplication.isPlaying = true;
        }

        static void OnPlayMode(PlayModeStateChange state)
        {
            if (state == PlayModeStateChange.EnteredEditMode)
            {
                EditorApplication.Exit(0);
            }
        }

        static void EnsureDirector()
        {
            var scene = EditorSceneManager.GetActiveScene();
            if (!scene.IsValid() || string.IsNullOrEmpty(scene.path))
            {
                string[] scenes = AssetDatabase.FindAssets("t:Scene");
                if (scenes.Length > 0)
                {
                    string path = "Assets/OutdoorsScene.unity";
                    if (!System.IO.File.Exists(path)) path = AssetDatabase.GUIDToAssetPath(scenes[0]);
                    scene = EditorSceneManager.OpenScene(path);
                }
            }

            var director = Object.FindFirstObjectByType<GardenDirector>();
            if (director == null)
            {
                var go = new GameObject("Elyon");
                go.AddComponent<GardenDirector>();
                go.AddComponent<GrokSpeech>();
            }

            PlayerSettings.productName = "Elyon First Light";
            PlayerSettings.companyName = "Elyon";
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            AssetDatabase.SaveAssets();
        }
    }
}
#endif
