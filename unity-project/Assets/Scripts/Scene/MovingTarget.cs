using UnityEngine;

namespace SlopePoke.Scene
{
    /// <summary>
    /// Sinusoidal back-and-forth motion along world +X. Wired up by SceneBuilder
    /// for motion-blur and tracking tests; usable standalone too.
    /// </summary>
    public class MovingTarget : MonoBehaviour
    {
        public Vector3 origin;
        public float amplitude = 2.5f;
        public float periodSec = 4f;

        void Start()
        {
            // If origin wasn't set explicitly, anchor at the current position.
            if (origin == Vector3.zero) origin = transform.position;
        }

        void Update()
        {
            float t = Mathf.Sin(Time.time * 2f * Mathf.PI / Mathf.Max(0.01f, periodSec));
            transform.position = origin + new Vector3(t * amplitude, 0f, 0f);
        }
    }
}
