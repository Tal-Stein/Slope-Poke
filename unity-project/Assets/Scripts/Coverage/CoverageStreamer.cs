using System.Collections.Generic;
using NetMQ;
using NetMQ.Sockets;
using SlopePoke.Cameras;
using SlopePoke.Streaming;
using UnityEngine;

namespace SlopePoke.Coverage
{
    /// <summary>
    /// Publishes coverage grids from every CoverageRaycaster in the scene over a
    /// dedicated ZMQ PUB socket. Sends only when a grid's Generation changes, so
    /// static rigs ship one message and stay quiet.
    /// </summary>
    public class CoverageStreamer : MonoBehaviour
    {
        public string bindEndpoint = "tcp://127.0.0.1:5557";

        PublisherSocket _pub;
        CoverageRaycaster[] _rays;
        Dictionary<CoverageRaycaster, int> _lastGen;

        void OnEnable()
        {
            ForceDotNet.Force();
            AsyncIO.ForceDotNet.Force();
            _pub = new PublisherSocket();
            _pub.Options.SendHighWatermark = 8;
            _pub.Bind(bindEndpoint);
            _rays = FindObjectsByType<CoverageRaycaster>(FindObjectsSortMode.None);
            _lastGen = new Dictionary<CoverageRaycaster, int>();
            foreach (var r in _rays) _lastGen[r] = -1;
            Debug.Log($"[CoverageStreamer] bound {bindEndpoint}, {_rays.Length} raycasters");
        }

        void OnDisable()
        {
            _pub?.Dispose();
            _pub = null;
        }

        void LateUpdate()
        {
            if (_pub == null) return;
            foreach (var r in _rays)
            {
                if (r == null || !r.isActiveAndEnabled) continue;
                if (!_lastGen.TryGetValue(r, out var gen)) gen = -1;
                if (r.Generation == gen) continue;
                _lastGen[r] = r.Generation;

                var cam = r.GetComponent<VirtualCamera>();
                var cameraId = cam != null ? cam.cameraId : r.gameObject.name;
                _pub.SendMoreFrame(cameraId).SendFrame(BuildPayload(cameraId, r));
            }
        }

        static byte[] BuildPayload(string cameraId, CoverageRaycaster r)
        {
            int h = r.Grid.GetLength(0);
            int w = r.Grid.GetLength(1);
            var flat = new double[h * w];
            for (int j = 0; j < h; j++)
                for (int i = 0; i < w; i++)
                    flat[j * w + i] = r.Grid[j, i];

            var doc = new Dictionary<string, object>
            {
                ["camera_id"] = cameraId,
                ["generation"] = r.Generation,
                ["width"] = w,
                ["height"] = h,
                ["world_min"] = new[] { (double)r.worldMin.x, (double)r.worldMin.y },
                ["world_max"] = new[] { (double)r.worldMax.x, (double)r.worldMax.y },
                ["grid"] = flat,
            };
            return MsgPackEncoder.Encode(doc);
        }
    }
}
