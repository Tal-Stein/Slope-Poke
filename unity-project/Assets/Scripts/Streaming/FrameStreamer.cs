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
        RenderTexture _rt;

        void Awake()
        {
            _vcam = GetComponent<VirtualCamera>();
        }

        void OnEnable()
        {
            // HDRP renders to the targetTexture via the same pipeline it uses for
            // the screen, but only if the camera has HDAdditionalCameraData with a
            // sane clear-color mode. Without this, the RT stays black even when
            // the scene is visibly lit on a screen-rendering camera.
            var cam = _vcam.UnityCamera;
            var hdData = cam.GetComponent<HDAdditionalCameraData>()
                         ?? cam.gameObject.AddComponent<HDAdditionalCameraData>();
            hdData.clearColorMode = HDAdditionalCameraData.ClearColorMode.Sky;
            hdData.volumeLayerMask = ~0;  // honor every Volume in the scene

            _rt = new RenderTexture(_vcam.renderWidth, _vcam.renderHeight, 24,
                                    RenderTextureFormat.ARGB32);
            _rt.Create();
            cam.targetTexture = _rt;

            _sender = gameObject.AddComponent<SpoutSender>();
            _sender.spoutName = $"{_vcam.cameraId}_rgb";
            _sender.captureMethod = CaptureMethod.Texture;
            _sender.sourceTexture = _rt;
        }

        void OnDisable()
        {
            if (_sender != null) Destroy(_sender);
            if (_rt != null)
            {
                _vcam.UnityCamera.targetTexture = null;
                _rt.Release();
                Destroy(_rt);
                _rt = null;
            }
        }
    }
}
