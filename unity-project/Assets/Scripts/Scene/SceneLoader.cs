using System.IO;
using UnityEngine;

namespace SlopePoke.Scene
{
    /// <summary>
    /// Loads scene_config.json at startup, applies fixed seed + fixed timestep, and
    /// instantiates configurable scene content. Camera config is loaded by the
    /// camera prefabs themselves via VirtualCamera fields (deferred to M2).
    /// </summary>
    public class SceneLoader : MonoBehaviour
    {
        public string scenePath = "configs/scenes/example.json";

        [System.Serializable]
        public class SceneConfig
        {
            public int seed = 42;
            public float fixedDeltaTime = 1f / 60f;
            public string roomMaterial = "default";
            public Vector3 roomDimensions = new(10f, 3f, 10f);
            public string lighting = "directional";
        }

        public SceneConfig Config { get; private set; }

        void Awake()
        {
            var path = Path.Combine(Application.streamingAssetsPath, scenePath);
            if (File.Exists(path))
            {
                Config = JsonUtility.FromJson<SceneConfig>(File.ReadAllText(path));
            }
            else
            {
                Debug.LogWarning($"[SceneLoader] {path} not found, using defaults.");
                Config = new SceneConfig();
            }

            UnityEngine.Random.InitState(Config.seed);
            Time.fixedDeltaTime = Config.fixedDeltaTime;
            Debug.Log($"[SceneLoader] seed={Config.seed} fixedDeltaTime={Config.fixedDeltaTime}");
        }
    }
}
