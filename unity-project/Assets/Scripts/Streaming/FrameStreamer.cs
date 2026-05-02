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
            var cam = _vcam.UnityCamera;
            var hdData = cam.GetComponent<HDAdditionalCameraData>()
                         ?? cam.gameObject.AddComponent<HDAdditionalCameraData>();
            hdData.clearColorMode = HDAdditionalCameraData.ClearColorMode.Sky;
            hdData.volumeLayerMask = ~0;

            // DefaultHDR picks the project's HDR-precision format (typically
            // R11G11B10_UFloat or R16G16B16A16_SFloat). HDRP writes its
            // post-processed final color to this and KlakSpout downsamples to
            // 8-bit RGBA at the Spout boundary — required for proper
            // tonemapping/exposure to land in the captured pixels.
            _rt = new RenderTexture(_vcam.renderWidth, _vcam.renderHeight, 24,
                                    RenderTextureFormat.DefaultHDR);
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
