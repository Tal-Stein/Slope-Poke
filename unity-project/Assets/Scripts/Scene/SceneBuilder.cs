using System.Collections.Generic;
using UnityEngine;

namespace SlopePoke.Scene
{
    /// <summary>
    /// Procedurally builds a rudimentary test arena on Awake — floor, occluder
    /// pillars, a DoF distance row, mixed colored targets, and a moving sphere.
    /// One SceneBuilder GameObject in the scene gives you a reproducible test
    /// environment that exercises coverage / detection / DoF / motion blur all
    /// at once.
    /// </summary>
    public class SceneBuilder : MonoBehaviour
    {
        [Header("Floor")]
        public Vector2 floorSize = new(10f, 10f);
        public Color floorColor = new(0.55f, 0.55f, 0.58f);

        [Header("Pillars (occluders at the corners)")]
        public bool buildPillars = true;
        public float pillarHeight = 4f;
        public float pillarRadius = 0.3f;
        public Color pillarColor = new(0.35f, 0.32f, 0.30f);

        [Header("DoF test row (spheres along +X)")]
        public bool buildDofRow = true;
        public float[] dofDistancesMeters = { 1f, 3f, 5f, 10f, 20f };
        public float dofRowHeight = 0.7f;
        public float dofSphereRadius = 0.35f;

        [Header("Random targets (cubes / spheres / cylinders)")]
        public int targetCount = 8;
        public bool annotateTargets = true;
        public int randomSeed = 42;
        public Vector2 targetXBounds = new(-3.5f, 3.5f);
        public Vector2 targetZBounds = new(-3.5f, 3.5f);

        [Header("Moving target (motion-blur testbed)")]
        public bool buildMovingTarget = true;
        public Vector3 movingOrigin = new(0f, 1.2f, 2f);
        public float movingAmplitude = 2.5f;
        public float movingPeriodSec = 4f;

        Material _hdrpLit;

        void Awake()
        {
            _hdrpLit = FindHdrpLitMaterial();
            BuildFloor();
            if (buildPillars) BuildPillars();
            if (buildDofRow) BuildDofRow();
            if (targetCount > 0) BuildTargets();
            if (buildMovingTarget) BuildMovingTarget();
        }

        // --- Builders ---

        void BuildFloor()
        {
            var floor = GameObject.CreatePrimitive(PrimitiveType.Plane);
            floor.name = "Floor";
            floor.transform.SetParent(transform, false);
            // Unity's default Plane is 10x10 m at scale (1,1,1).
            floor.transform.localScale = new Vector3(floorSize.x / 10f, 1f, floorSize.y / 10f);
            Tint(floor, floorColor);
        }

        void BuildPillars()
        {
            float half = floorSize.x * 0.4f;
            var corners = new[]
            {
                new Vector3(-half, pillarHeight * 0.5f, -half),
                new Vector3( half, pillarHeight * 0.5f, -half),
                new Vector3(-half, pillarHeight * 0.5f,  half),
                new Vector3( half, pillarHeight * 0.5f,  half),
            };
            for (int i = 0; i < corners.Length; i++)
            {
                var p = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
                p.name = $"Pillar_{i}";
                p.transform.SetParent(transform, false);
                p.transform.localPosition = corners[i];
                p.transform.localScale = new Vector3(pillarRadius * 2f, pillarHeight * 0.5f, pillarRadius * 2f);
                Tint(p, pillarColor);
            }
        }

        void BuildDofRow()
        {
            for (int i = 0; i < dofDistancesMeters.Length; i++)
            {
                float d = dofDistancesMeters[i];
                var s = GameObject.CreatePrimitive(PrimitiveType.Sphere);
                s.name = $"DoF_{d:0.#}m";
                s.transform.SetParent(transform, false);
                s.transform.localPosition = new Vector3(d, dofRowHeight, -2f);
                s.transform.localScale = Vector3.one * dofSphereRadius * 2f;
                // Color gradient white → orange so the row is identifiable.
                float t = (float)i / Mathf.Max(1, dofDistancesMeters.Length - 1);
                Tint(s, Color.Lerp(Color.white, new Color(1f, 0.55f, 0.1f), t));
            }
        }

        void BuildTargets()
        {
            var rng = new System.Random(randomSeed);
            var primitives = new[] { PrimitiveType.Cube, PrimitiveType.Sphere, PrimitiveType.Cylinder };
            var classNames = new Dictionary<PrimitiveType, string>
            {
                [PrimitiveType.Cube] = "cube",
                [PrimitiveType.Sphere] = "sphere",
                [PrimitiveType.Cylinder] = "cylinder",
            };
            for (int i = 0; i < targetCount; i++)
            {
                var prim = primitives[rng.Next(primitives.Length)];
                var go = GameObject.CreatePrimitive(prim);
                go.name = $"Target_{i:00}_{classNames[prim]}";
                go.transform.SetParent(transform, false);
                float x = Lerp01(rng, targetXBounds.x, targetXBounds.y);
                float z = Lerp01(rng, targetZBounds.x, targetZBounds.y);
                float y = prim == PrimitiveType.Cylinder ? 1f : 0.5f;
                go.transform.localPosition = new Vector3(x, y, z);
                go.transform.localScale = Vector3.one * (float)(0.5 + rng.NextDouble() * 0.6);
                go.transform.localRotation = Quaternion.Euler(0f, (float)(rng.NextDouble() * 360.0), 0f);
                Tint(go, Color.HSVToRGB((float)rng.NextDouble(), 0.7f, 0.9f));
                if (annotateTargets)
                {
                    var ann = go.AddComponent<AnnotatedObject>();
                    ann.objectId = i + 1;
                    ann.className = classNames[prim];
                }
            }
        }

        void BuildMovingTarget()
        {
            var go = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            go.name = "MovingTarget";
            go.transform.SetParent(transform, false);
            go.transform.localPosition = movingOrigin;
            go.transform.localScale = Vector3.one * 0.5f;
            Tint(go, new Color(0.2f, 0.8f, 1f));
            var mover = go.AddComponent<MovingTarget>();
            mover.origin = movingOrigin;
            mover.amplitude = movingAmplitude;
            mover.periodSec = movingPeriodSec;
            if (annotateTargets)
            {
                var ann = go.AddComponent<AnnotatedObject>();
                ann.objectId = 999;
                ann.className = "moving_sphere";
            }
        }

        // --- Helpers ---

        static float Lerp01(System.Random rng, float a, float b) =>
            a + (b - a) * (float)rng.NextDouble();

        void Tint(GameObject go, Color color)
        {
            var mr = go.GetComponent<MeshRenderer>();
            if (mr == null) return;
            // Instance the material so each object has a distinct color without
            // touching the shared HDRP/Lit asset.
            var src = _hdrpLit != null ? _hdrpLit : mr.sharedMaterial;
            var mat = new Material(src) { name = $"{go.name}_mat" };
            // HDRP/Lit uses _BaseColor; legacy / URP fall back to color.
            if (mat.HasProperty("_BaseColor")) mat.SetColor("_BaseColor", color);
            else mat.color = color;
            mr.sharedMaterial = mat;
        }

        static Material FindHdrpLitMaterial()
        {
            var shader = Shader.Find("HDRP/Lit");
            return shader != null ? new Material(shader) { name = "HDRPLit_template" } : null;
        }
    }
}
