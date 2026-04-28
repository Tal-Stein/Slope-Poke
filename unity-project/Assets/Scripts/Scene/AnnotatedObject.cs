using System.Collections.Generic;
using UnityEngine;

namespace SlopePoke.Scene
{
    /// <summary>
    /// Tag a GameObject with this component to publish ground-truth annotations for it
    /// in the per-frame metadata stream. MetadataPublisher discovers all instances via
    /// FindObjectsByType and serialises them under the "objects" key.
    ///
    /// World pose and bbox corners are emitted in Unity world coordinates (left-handed,
    /// +Y up). Camera extrinsics ship in OpenCV convention (Y-flipped); CV consumers
    /// that need to project world points must apply the same flip themselves. Keeping
    /// the world frame Unity-native means object trajectories round-trip cleanly through
    /// recording.json and the Unity editor.
    /// </summary>
    public class AnnotatedObject : MonoBehaviour
    {
        public int objectId;
        public string className = "object";

        [Tooltip("If null, falls back to the first MeshFilter/SkinnedMeshRenderer found in children.")]
        public Bounds localBoundsOverride;
        public bool useLocalBoundsOverride;

        Bounds? _cachedLocalBounds;

        /// <summary>4x4 row-major local-to-world transform of this GameObject.</summary>
        public float[] WorldPoseRowMajor()
        {
            var m = transform.localToWorldMatrix;
            return new[]
            {
                m.m00, m.m01, m.m02, m.m03,
                m.m10, m.m11, m.m12, m.m13,
                m.m20, m.m21, m.m22, m.m23,
                m.m30, m.m31, m.m32, m.m33,
            };
        }

        /// <summary>8 oriented-bbox corners in world space (Unity convention).</summary>
        public float[][] BoundingBoxWorld()
        {
            var b = LocalBounds();
            var min = b.min;
            var max = b.max;
            var corners = new[]
            {
                new Vector3(min.x, min.y, min.z),
                new Vector3(max.x, min.y, min.z),
                new Vector3(max.x, max.y, min.z),
                new Vector3(min.x, max.y, min.z),
                new Vector3(min.x, min.y, max.z),
                new Vector3(max.x, min.y, max.z),
                new Vector3(max.x, max.y, max.z),
                new Vector3(min.x, max.y, max.z),
            };
            var t = transform.localToWorldMatrix;
            var result = new float[8][];
            for (int i = 0; i < 8; i++)
            {
                var w = t.MultiplyPoint3x4(corners[i]);
                result[i] = new[] { w.x, w.y, w.z };
            }
            return result;
        }

        Bounds LocalBounds()
        {
            if (useLocalBoundsOverride) return localBoundsOverride;
            if (_cachedLocalBounds.HasValue) return _cachedLocalBounds.Value;

            var mf = GetComponentInChildren<MeshFilter>();
            if (mf != null && mf.sharedMesh != null)
            {
                _cachedLocalBounds = mf.sharedMesh.bounds;
                return _cachedLocalBounds.Value;
            }
            var smr = GetComponentInChildren<SkinnedMeshRenderer>();
            if (smr != null && smr.sharedMesh != null)
            {
                _cachedLocalBounds = smr.sharedMesh.bounds;
                return _cachedLocalBounds.Value;
            }
            // Fallback: unit cube around origin.
            _cachedLocalBounds = new Bounds(Vector3.zero, Vector3.one);
            return _cachedLocalBounds.Value;
        }

        public Dictionary<string, object> ToMsgPackDict()
        {
            var bbox = BoundingBoxWorld();
            var pose = WorldPoseRowMajor();
            return new Dictionary<string, object>
            {
                ["object_id"] = objectId,
                ["class_name"] = className,
                ["world_pose"] = new[]
                {
                    new[] { (double)pose[0],  (double)pose[1],  (double)pose[2],  (double)pose[3]  },
                    new[] { (double)pose[4],  (double)pose[5],  (double)pose[6],  (double)pose[7]  },
                    new[] { (double)pose[8],  (double)pose[9],  (double)pose[10], (double)pose[11] },
                    new[] { (double)pose[12], (double)pose[13], (double)pose[14], (double)pose[15] },
                },
                ["bbox_3d"] = new[]
                {
                    new[] { (double)bbox[0][0], (double)bbox[0][1], (double)bbox[0][2] },
                    new[] { (double)bbox[1][0], (double)bbox[1][1], (double)bbox[1][2] },
                    new[] { (double)bbox[2][0], (double)bbox[2][1], (double)bbox[2][2] },
                    new[] { (double)bbox[3][0], (double)bbox[3][1], (double)bbox[3][2] },
                    new[] { (double)bbox[4][0], (double)bbox[4][1], (double)bbox[4][2] },
                    new[] { (double)bbox[5][0], (double)bbox[5][1], (double)bbox[5][2] },
                    new[] { (double)bbox[6][0], (double)bbox[6][1], (double)bbox[6][2] },
                    new[] { (double)bbox[7][0], (double)bbox[7][1], (double)bbox[7][2] },
                },
            };
        }
    }
}
