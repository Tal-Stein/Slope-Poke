using Klak.Spout;
using SlopePoke.Cameras;
using UnityEngine;
using UnityEngine.Rendering.HighDefinition;

namespace SlopePoke.Streaming
{
    /// <summary>
    /// Per-camera Spout sender. Sits on the same GameObject as a VirtualCamera and
    /// pushes that camera's color RT into a Spout sender named "<cameraId>_rgb".
    /// </summary>
    [RequireComponent(typeof(VirtualCamera))]
    public class FrameStreamer : MonoBehaviour
    {
        VirtualCamera _vcam;
        SpoutSender _sender;

        void Awake()
        {
            _vcam = GetComponent<VirtualCamera>();
        }

        void OnEnable()
        {
            // KlakSpout's Camera capture method hooks into the SRP render-pipeline
            // callbacks and grabs the camera's final output (post-tonemapping,
            // post-exposure) for every render. Texture mode (writing through a
            // managed RT) frequently produces black frames in HDRP because HDRP
            // skips post-processing for non-screen cameras. Camera mode avoids
            // that path entirely.
            var cam = _vcam.UnityCamera;
            var hdData = cam.GetComponent<HDAdditionalCameraData>()
                         ?? cam.gameObject.AddComponent<HDAdditionalCameraData>();
            hdData.clearColorMode = HDAdditionalCameraData.ClearColorMode.Sky;
            hdData.volumeLayerMask = ~0;

            _sender = gameObject.AddComponent<SpoutSender>();
            _sender.spoutName = $"{_vcam.cameraId}_rgb";
            _sender.captureMethod = CaptureMethod.Camera;
            _sender.sourceCamera = cam;
        }

        void OnDisable()
        {
            if (_sender != null) Destroy(_sender);
        }
    }
}
