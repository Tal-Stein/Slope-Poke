using System;
using System.Threading;
using NetMQ;
using NetMQ.Sockets;
using UnityEngine;

namespace SlopePoke.Cameras
{
    /// <summary>
    /// Custom PTZ rig. Pan/tilt/zoom are exposed as direct setters (no Cinemachine
    /// blending) so that closed-loop Python controllers see predictable step
    /// responses. Commands arrive over a ZMQ REP socket on its own thread; the
    /// MonoBehaviour applies them on the next Update tick.
    /// </summary>
    public class PTZController : MonoBehaviour
    {
        [Header("Identity")]
        public string cameraId = "ptzA";

        [Header("Limits (degrees)")]
        public Vector2 panRange = new(-180f, 180f);
        public Vector2 tiltRange = new(-90f, 30f);
        public Vector2 zoomRangeMm = new(15f, 200f);  // focal length

        [Header("Max angular velocity (deg/s)")]
        public float maxPanRate = 120f;
        public float maxTiltRate = 90f;

        [Header("Control endpoint")]
        public string bindEndpoint = "tcp://127.0.0.1:5556";

        public float Pan { get; private set; }
        public float Tilt { get; private set; }
        public float ZoomMm { get; private set; }

        Camera _cam;
        Thread _thread;
        volatile bool _stop;

        struct Target { public float pan, tilt, zoom; public bool hasPan, hasTilt, hasZoom; }
        Target _target;
        readonly object _targetLock = new();

        void Awake()
        {
            _cam = GetComponentInChildren<Camera>();
            ZoomMm = _cam != null ? _cam.focalLength : 35f;
        }

        void OnEnable()
        {
            _stop = false;
            _thread = new Thread(RunZmq) { IsBackground = true, Name = "ptz-zmq" };
            _thread.Start();
        }

        void OnDisable()
        {
            _stop = true;
            _thread?.Join(500);
        }

        void Update()
        {
            Target t;
            lock (_targetLock) t = _target;
            float dt = Time.deltaTime;

            if (t.hasPan)
            {
                float clamped = Mathf.Clamp(t.pan, panRange.x, panRange.y);
                Pan = StepToward(Pan, clamped, maxPanRate * dt);
            }
            if (t.hasTilt)
            {
                float clamped = Mathf.Clamp(t.tilt, tiltRange.x, tiltRange.y);
                Tilt = StepToward(Tilt, clamped, maxTiltRate * dt);
            }
            if (t.hasZoom)
            {
                ZoomMm = Mathf.Clamp(t.zoom, zoomRangeMm.x, zoomRangeMm.y);
                if (_cam != null) _cam.focalLength = ZoomMm;
            }

            transform.localRotation = Quaternion.Euler(-Tilt, Pan, 0f);
        }

        static float StepToward(float current, float target, float maxStep)
        {
            float delta = Mathf.Clamp(target - current, -maxStep, maxStep);
            return current + delta;
        }

        void RunZmq()
        {
            AsyncIO.ForceDotNet.Force();
            using var rep = new ResponseSocket();
            rep.Bind(bindEndpoint);
            while (!_stop)
            {
                if (!rep.TryReceiveFrameString(TimeSpan.FromMilliseconds(100), out var msg)) continue;
                try
                {
                    HandleCommand(msg);
                    rep.SendFrame("{\"ok\":true}");
                }
                catch (Exception ex)
                {
                    rep.SendFrame($"{{\"ok\":false,\"err\":\"{ex.Message}\"}}");
                }
            }
        }

        void HandleCommand(string json)
        {
            // Tiny ad-hoc parser: expects {"pan":..,"tilt":..,"zoom":..} (any subset).
            // Avoids Newtonsoft / System.Text.Json dependency footprint.
            var t = new Target();
            json = json.Trim().TrimStart('{').TrimEnd('}');
            foreach (var pair in json.Split(','))
            {
                var kv = pair.Split(':');
                if (kv.Length != 2) continue;
                var key = kv[0].Trim().Trim('"');
                if (!float.TryParse(kv[1].Trim(), System.Globalization.NumberStyles.Float,
                                    System.Globalization.CultureInfo.InvariantCulture, out var val))
                    continue;
                switch (key)
                {
                    case "pan":  t.pan = val;  t.hasPan = true; break;
                    case "tilt": t.tilt = val; t.hasTilt = true; break;
                    case "zoom": t.zoom = val; t.hasZoom = true; break;
                }
            }
            lock (_targetLock) _target = t;
        }
    }
}
