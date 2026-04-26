using System.Collections.Generic;
using NetMQ;
using NetMQ.Sockets;
using SlopePoke.Cameras;
using UnityEngine;

namespace SlopePoke.Streaming
{
    /// <summary>
    /// Single ZMQ PUB socket that ships per-frame metadata for all VirtualCameras
    /// in the scene. Topic = camera_id (UTF-8 bytes), body = msgpack-encoded JSON.
    /// </summary>
    public class MetadataPublisher : MonoBehaviour
    {
        public string bindEndpoint = "tcp://127.0.0.1:5555";
        public int frameIndex;

        PublisherSocket _pub;
        VirtualCamera[] _cams;

        void OnEnable()
        {
            ForceDotNet.Force();
            AsyncIO.ForceDotNet.Force();
            _pub = new PublisherSocket();
            _pub.Options.SendHighWatermark = 32;
            _pub.Bind(bindEndpoint);
            _cams = FindObjectsByType<VirtualCamera>(FindObjectsSortMode.None);
            Debug.Log($"[MetadataPublisher] bound {bindEndpoint}, {_cams.Length} cameras");
        }

        void OnDisable()
        {
            _pub?.Dispose();
            _pub = null;
            NetMQConfig.Cleanup(false);
        }

        void LateUpdate()
        {
            if (_pub == null) return;
            float t = Time.time;
            foreach (var cam in _cams)
            {
                var intr = cam.GetIntrinsicsPx();
                var pose = cam.GetWorldPoseRowMajor();
                var payload = BuildPayload(cam.cameraId, frameIndex, t, intr, pose);
                _pub.SendMoreFrame(cam.cameraId).SendFrame(payload);
            }
            frameIndex++;
        }

        static byte[] BuildPayload(string id, int frame, float t, CameraIntrinsics intr, float[] pose)
        {
            // Hand-rolled msgpack map for "camera_id, frame_index, timestamp,
            // sender, intrinsics{...}, extrinsics{matrix:4x4}, objects:[]".
            // Kept dependency-free for now; swap to MessagePack-CSharp later if desired.
            var doc = new Dictionary<string, object>
            {
                ["camera_id"] = id,
                ["frame_index"] = frame,
                ["timestamp"] = (double)t,
                ["sender"] = "rgb",
                ["intrinsics"] = new Dictionary<string, object>
                {
                    ["fx"] = (double)intr.fx,
                    ["fy"] = (double)intr.fy,
                    ["cx"] = (double)intr.cx,
                    ["cy"] = (double)intr.cy,
                    ["width"] = intr.width,
                    ["height"] = intr.height,
                    ["distortion"] = intr.distortion,
                },
                ["extrinsics"] = new Dictionary<string, object>
                {
                    ["matrix"] = new[]
                    {
                        new[] { pose[0], pose[1], pose[2], pose[3] },
                        new[] { pose[4], pose[5], pose[6], pose[7] },
                        new[] { pose[8], pose[9], pose[10], pose[11] },
                        new[] { pose[12], pose[13], pose[14], pose[15] },
                    },
                },
                ["objects"] = System.Array.Empty<object>(),
            };
            return MsgPackEncoder.Encode(doc);
        }
    }
}
