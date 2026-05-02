using System.IO;
using Newtonsoft.Json;
using Newtonsoft.Json.Serialization;
using SlopePoke.Cameras;
using SlopePoke.Coverage;
using SlopePoke.Streaming;
using UnityEngine;
using UnityEngine.Rendering.HighDefinition;

namespace SlopePoke.Scene
{
    /// <summary>
    /// Reads a cameras.json (matching slope_poke.config.models.CamerasConfig) at Awake
    /// and instantiates each camera entry with the right components.
    ///
    /// Global overrides on this component let you cap render resolution and coverage
    /// ray density without editing per-camera JSON — useful when scene complexity
    /// pushes the GPU harder than expected.
    /// </summary>
    public class CamerasLoader : MonoBehaviour
    {
        [Header("Source")]
        [Tooltip("Path to cameras.json. If relative, resolved against StreamingAssets first, " +
                 "then the repo root (../../configs/cameras).")]
        public string configPath = "cameras.json";

        [Header("Global overrides (set both axes >0 to apply)")]
        [Tooltip("Override every camera's render width/height. Useful for GPU perf testing.")]
        public Vector2Int resolutionOverride = Vector2Int.zero;

        [Header("Coverage")]
        [Tooltip("Add a CoverageRaycaster to every spawned VirtualCamera.")]
        public bool addCoverageRaycaster;
        [Tooltip("Override CoverageRaycaster.rayGrid (frustum sample density). 0 = use default.")]
        public Vector2Int coverageRayGridOverride = Vector2Int.zero;
        [Tooltip("Override CoverageRaycaster.resolution (top-down grid resolution). 0 = use default.")]
        public Vector2Int coverageGridResolutionOverride = Vector2Int.zero;

        void Awake()
        {
            var path = ResolveConfigPath(configPath);
            if (path == null || !File.Exists(path))
            {
                Debug.LogError($"[CamerasLoader] Config not found at '{configPath}'. " +
                               $"Tried StreamingAssets and repo configs/cameras.");
                return;
            }
            var json = File.ReadAllText(path);
            var settings = new JsonSerializerSettings
            {
                ContractResolver = new DefaultContractResolver
                {
                    NamingStrategy = new SnakeCaseNamingStrategy(),
                },
                MissingMemberHandling = MissingMemberHandling.Ignore,
            };
            // Strip the optional $schema field by parsing into a Newtonsoft JObject first
            // and removing it — JSON Schema annotations aren't part of CamerasConfig.
            var jobj = Newtonsoft.Json.Linq.JObject.Parse(json);
            jobj.Remove("$schema");
            var cfg = jobj.ToObject<CamerasConfigDto>(JsonSerializer.Create(settings));
            if (cfg?.Cameras == null)
            {
                Debug.LogError($"[CamerasLoader] '{path}' has no 'cameras' array.");
                return;
            }
            int spawned = 0;
            foreach (var entry in cfg.Cameras)
            {
                if (entry == null || string.IsNullOrEmpty(entry.Id)) continue;
                Spawn(entry);
                spawned++;
            }
            Debug.Log($"[CamerasLoader] spawned {spawned} cameras from '{path}'.");
        }

        string ResolveConfigPath(string p)
        {
            if (Path.IsPathRooted(p) && File.Exists(p)) return p;
            var inStreaming = Path.Combine(Application.streamingAssetsPath, p);
            if (File.Exists(inStreaming)) return inStreaming;
            // Fallback: repo-relative configs/cameras/<file>. Useful pre-StreamingAssets-setup.
            var repoConfig = Path.GetFullPath(Path.Combine(
                Application.dataPath, "..", "..", "configs", "cameras", p));
            if (File.Exists(repoConfig)) return repoConfig;
            return null;
        }

        void Spawn(CameraConfigDto e)
        {
            switch (e.Rig)
            {
                case "ptz":
                    SpawnPtz(e);
                    break;
                default:
                    SpawnFixed(e);
                    break;
            }
        }

        void SpawnFixed(CameraConfigDto e)
        {
            var go = new GameObject(e.Id);
            ApplyTransform(go.transform, e);
            go.AddComponent<Camera>();
            ConfigureHdrpCamera(go);
            var vcam = go.AddComponent<VirtualCamera>();
            ApplyVirtualCameraFields(vcam, e);
            go.AddComponent<FrameStreamer>();
            MaybeAddCoverage(go, vcam);
        }

        // Attach HDAdditionalCameraData immediately after the Camera so HDRP
        // registers this camera in its render loop on the very next frame.
        // Adding it later (e.g., from FrameStreamer.OnEnable) sometimes leaves
        // the camera invisible to HDRP's per-frame render scheduler.
        // Bright-pink test color: if you see pink tiles in slope-poke view,
        // the camera IS rendering and we just need to fix sky/geometry. If
        // they're still black, HDRP is still not running this camera.
        static void ConfigureHdrpCamera(GameObject go)
        {
            var cam = go.GetComponent<Camera>();
            var hdData = cam.GetComponent<HDAdditionalCameraData>()
                         ?? cam.gameObject.AddComponent<HDAdditionalCameraData>();
            hdData.clearColorMode = HDAdditionalCameraData.ClearColorMode.Color;
            hdData.backgroundColorHDR = new Color(1f, 0f, 1f, 1f);  // diagnostic pink
            hdData.volumeLayerMask = ~0;
        }

        void SpawnPtz(CameraConfigDto e)
        {
            // Parent: PTZController. Child: actual Camera.
            var rig = new GameObject(e.Id);
            ApplyTransform(rig.transform, e);
            var ptz = rig.AddComponent<PTZController>();
            ptz.cameraId = e.Id;
            if (e.Ptz != null)
            {
                ptz.panRange = new Vector2(e.Ptz.PanRangeDeg[0], e.Ptz.PanRangeDeg[1]);
                ptz.tiltRange = new Vector2(e.Ptz.TiltRangeDeg[0], e.Ptz.TiltRangeDeg[1]);
                ptz.zoomRangeMm = new Vector2(e.Ptz.ZoomRangeMm[0], e.Ptz.ZoomRangeMm[1]);
                ptz.maxPanRate = e.Ptz.MaxPanRateDegS;
                ptz.maxTiltRate = e.Ptz.MaxTiltRateDegS;
            }
            var cam = new GameObject($"{e.Id}_camera");
            cam.transform.SetParent(rig.transform, false);
            cam.AddComponent<Camera>();
            ConfigureHdrpCamera(cam);
            var vcam = cam.AddComponent<VirtualCamera>();
            ApplyVirtualCameraFields(vcam, e);
            cam.AddComponent<FrameStreamer>();
            MaybeAddCoverage(cam, vcam);
        }

        static void ApplyTransform(Transform t, CameraConfigDto e)
        {
            if (e.Position != null && e.Position.Length == 3)
                t.position = new Vector3(e.Position[0], e.Position[1], e.Position[2]);
            if (e.RotationEulerDeg != null && e.RotationEulerDeg.Length == 3)
                t.rotation = Quaternion.Euler(
                    e.RotationEulerDeg[0], e.RotationEulerDeg[1], e.RotationEulerDeg[2]);
        }

        void ApplyVirtualCameraFields(VirtualCamera v, CameraConfigDto e)
        {
            v.cameraId = e.Id;
            if (e.Intrinsics != null)
            {
                v.focalLengthMm = e.Intrinsics.FocalLengthMm;
                if (e.Intrinsics.SensorSizeMm != null && e.Intrinsics.SensorSizeMm.Length == 2)
                    v.sensorSizeMm = new Vector2(
                        e.Intrinsics.SensorSizeMm[0], e.Intrinsics.SensorSizeMm[1]);
                if (e.Intrinsics.PrincipalPointPx != null && e.Intrinsics.PrincipalPointPx.Length == 2)
                    v.principalPointPx = new Vector2(
                        e.Intrinsics.PrincipalPointPx[0], e.Intrinsics.PrincipalPointPx[1]);
                v.renderWidth = e.Intrinsics.RenderWidth;
                v.renderHeight = e.Intrinsics.RenderHeight;
            }
            if (resolutionOverride.x > 0 && resolutionOverride.y > 0)
            {
                v.renderWidth = resolutionOverride.x;
                v.renderHeight = resolutionOverride.y;
            }
            if (e.Distortion != null)
            {
                v.k1 = e.Distortion.K1;
                v.k2 = e.Distortion.K2;
                v.p1 = e.Distortion.P1;
                v.p2 = e.Distortion.P2;
                v.k3 = e.Distortion.K3;
            }
            if (e.Noise != null)
            {
                v.gaussianSigma = e.Noise.GaussianSigma;
                v.saltPepperRate = e.Noise.SaltPepperRate;
            }
            if (e.Optics != null)
            {
                v.shutterAngleDeg = e.Optics.ShutterAngleDeg;
                v.aperture = e.Optics.ApertureFstop;
                v.focusDistance = e.Optics.FocusDistanceM;
                v.exposureCompensationEv = e.Optics.ExposureCompensationEv;
            }
        }

        void MaybeAddCoverage(GameObject host, VirtualCamera vcam)
        {
            if (!addCoverageRaycaster) return;
            var ray = host.AddComponent<CoverageRaycaster>();
            if (coverageRayGridOverride.x > 0 && coverageRayGridOverride.y > 0)
                ray.rayGrid = coverageRayGridOverride;
            if (coverageGridResolutionOverride.x > 0 && coverageGridResolutionOverride.y > 0)
                ray.resolution = coverageGridResolutionOverride;
        }

        // --- Plain DTOs matching slope_poke.config.models (snake_case via NamingStrategy). ---

        class CamerasConfigDto
        {
            public CameraConfigDto[] Cameras;
        }

        class CameraConfigDto
        {
            public string Id;
            public string Rig;
            public float[] Position;
            public float[] RotationEulerDeg;
            public IntrinsicsDto Intrinsics;
            public DistortionDto Distortion;
            public NoiseDto Noise;
            public OpticsDto Optics;
            public PtzDto Ptz;
        }

        class IntrinsicsDto
        {
            public float FocalLengthMm = 35f;
            public float[] SensorSizeMm = { 36f, 24f };
            public float[] PrincipalPointPx = { 0f, 0f };
            public int RenderWidth = 1920;
            public int RenderHeight = 1080;
        }

        class DistortionDto
        {
            public float K1, K2, P1, P2, K3;
        }

        class NoiseDto
        {
            public float GaussianSigma;
            public float SaltPepperRate;
        }

        class OpticsDto
        {
            public float ShutterAngleDeg = 180f;
            public float ApertureFstop = 5.6f;
            public float FocusDistanceM = 5f;
            public float ExposureCompensationEv;
        }

        class PtzDto
        {
            public float[] PanRangeDeg = { -180f, 180f };
            public float[] TiltRangeDeg = { -90f, 30f };
            public float[] ZoomRangeMm = { 15f, 200f };
            public float MaxPanRateDegS = 120f;
            public float MaxTiltRateDegS = 90f;
        }
    }
}
