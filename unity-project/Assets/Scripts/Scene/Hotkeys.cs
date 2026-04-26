using UnityEngine;

namespace SlopePoke.Scene
{
    /// <summary>F5 = play, F6 = pause, F7 = export coverage map (M5).</summary>
    public class Hotkeys : MonoBehaviour
    {
        void Update()
        {
            if (Input.GetKeyDown(KeyCode.F6))
            {
                Time.timeScale = Mathf.Approximately(Time.timeScale, 0f) ? 1f : 0f;
                Debug.Log($"[Hotkeys] timeScale={Time.timeScale}");
            }
            if (Input.GetKeyDown(KeyCode.F7))
            {
                Debug.Log("[Hotkeys] F7: coverage export hook (TODO: wire CoverageRaycaster).");
            }
        }
    }
}
