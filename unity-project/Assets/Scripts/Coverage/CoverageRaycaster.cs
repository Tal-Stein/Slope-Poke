using System.Collections.Generic;
using SlopePoke.Cameras;
using UnityEngine;

namespace SlopePoke.Coverage
{
    /// <summary>
    /// Per-camera coverage via dense frustum raycasting. Recomputes only when the
    /// owning VirtualCamera's transform or focal length changes — no polling.
    /// Result is a 2D top-down grid over the configured world AABB.
    /// </summary>
    [RequireComponent(typeof(VirtualCamera))]
    public class CoverageRaycaster : MonoBehaviour
    {
        [Header("Top-down grid (world units)")]
        public Vector2 worldMin = new(-10f, -10f);
        public Vector2 worldMax = new(10f, 10f);
        public Vector2Int resolution = new(128, 128);

        [Header("Frustum sampling")]
        public Vector2Int rayGrid = new(64, 36);
        public float maxRayDistance = 100f;

        public float[,] Grid { get; private set; }
        /// <summary>Increments every time Recompute() runs — pollers can detect updates.</summary>
        public int Generation { get; private set; }

        VirtualCamera _vcam;
        Camera _cam;
        Vector3 _lastPos;
        Quaternion _lastRot;
        float _lastFocal;

        void Awake()
        {
            _vcam = GetComponent<VirtualCamera>();
            _cam = _vcam.UnityCamera;
            Grid = new float[resolution.y, resolution.x];
        }

        void Update()
        {
            if (transform.position == _lastPos &&
                transform.rotation == _lastRot &&
                Mathf.Approximately(_cam.focalLength, _lastFocal)) return;

            Recompute();
            _lastPos = transform.position;
            _lastRot = transform.rotation;
            _lastFocal = _cam.focalLength;
        }

        public void Recompute()
        {
            System.Array.Clear(Grid, 0, Grid.Length);
            float du = 1f / rayGrid.x;
            float dv = 1f / rayGrid.y;
            for (int j = 0; j < rayGrid.y; j++)
            {
                for (int i = 0; i < rayGrid.x; i++)
                {
                    var vp = new Vector3((i + 0.5f) * du, (j + 0.5f) * dv, 0f);
                    var ray = _cam.ViewportPointToRay(vp);
                    if (!Physics.Raycast(ray, out var hit, maxRayDistance)) continue;
                    int gx = Mathf.FloorToInt(
                        Mathf.InverseLerp(worldMin.x, worldMax.x, hit.point.x) * resolution.x);
                    int gy = Mathf.FloorToInt(
                        Mathf.InverseLerp(worldMin.y, worldMax.y, hit.point.z) * resolution.y);
                    if (gx < 0 || gx >= resolution.x || gy < 0 || gy >= resolution.y) continue;
                    Grid[gy, gx] = 1f;
                }
            }
            Generation++;
        }
    }
}
