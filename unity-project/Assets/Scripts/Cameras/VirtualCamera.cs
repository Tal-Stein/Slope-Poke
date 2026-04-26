using UnityEngine;

namespace SlopePoke.Cameras
{
    /// <summary>
    /// Wraps a Unity Camera with serializable intrinsics + lens parameters.
    /// FrameStreamer reads these to fill outgoing metadata; SceneLoader populates
    /// them from camera_config.json.
    /// </summary>
    [RequireComponent(typeof(Camera))]
    public class VirtualCamera : MonoBehaviour
    {
        [Header("Identity")]
        public string cameraId = "cameraA";

        [Header("Intrinsics (overrides Unity Camera if non-zero)")]
        public float focalLengthMm = 35f;
        public Vector2 sensorSizeMm = new(36f, 24f);
        public Vector2 principalPointPx;   // 0 = image center
        public int renderWidth = 1920;
        public int renderHeight = 1080;

        [Header("Distortion (Brown-Conrady, OpenCV order)")]
        public float k1, k2, p1, p2, k3;

        [Header("Noise")]
        public float gaussianSigma;
        public float saltPepperRate;

        [Header("Optics")]
        public float shutterAngleDeg = 180f;  // motion blur (HDRP)
        public float aperture = 5.6f;         // f-stop
        public float focusDistance = 5f;
        public float exposureCompensationEv;

        Camera _cam;
        public Camera UnityCamera => _cam ??= GetComponent<Camera>();

        void OnValidate()
        {
            var c = UnityCamera;
            c.usePhysicalProperties = true;
            c.focalLength = focalLengthMm;
            c.sensorSize = sensorSizeMm;
        }

        public CameraIntrinsics GetIntrinsicsPx()
        {
            // Pinhole intrinsics derived from physical lens + render resolution.
            float fx = focalLengthMm * renderWidth / sensorSizeMm.x;
            float fy = focalLengthMm * renderHeight / sensorSizeMm.y;
            float cx = renderWidth * 0.5f + principalPointPx.x;
            float cy = renderHeight * 0.5f + principalPointPx.y;
            return new CameraIntrinsics
            {
                fx = fx, fy = fy, cx = cx, cy = cy,
                width = renderWidth, height = renderHeight,
                distortion = new[] { k1, k2, p1, p2, k3 },
            };
        }

        public float[] GetWorldPoseRowMajor()
        {
            // Unity is +Y up, +Z forward (left-handed). Convert to OpenCV +Z forward,
            // +Y down by flipping Y on the camera-to-world rows. World->camera is the
            // inverse of the camera transform.
            var w2c = transform.worldToLocalMatrix;
            // Flip Y (row 1) to match OpenCV convention.
            for (int c = 0; c < 4; c++) w2c[1, c] = -w2c[1, c];
            return new[]
            {
                w2c.m00, w2c.m01, w2c.m02, w2c.m03,
                w2c.m10, w2c.m11, w2c.m12, w2c.m13,
                w2c.m20, w2c.m21, w2c.m22, w2c.m23,
                w2c.m30, w2c.m31, w2c.m32, w2c.m33,
            };
        }
    }

    [System.Serializable]
    public struct CameraIntrinsics
    {
        public float fx, fy, cx, cy;
        public int width, height;
        public float[] distortion;
    }
}
