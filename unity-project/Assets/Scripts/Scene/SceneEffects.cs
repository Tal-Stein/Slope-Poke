using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.HighDefinition;

namespace SlopePoke.Scene
{
    /// <summary>
    /// Bootstraps the HDRP global Volume + profile so the per-camera physical
    /// properties on VirtualCamera (aperture / focus / shutter) actually render.
    ///
    /// Drop one SceneEffects GameObject into the scene; on Awake it ensures a
    /// global Volume exists with DepthOfField (PhysicalCamera mode), MotionBlur
    /// (intensity from configured shutter angle), and Exposure (compensation).
    ///
    /// DoF is per-camera "for free" via Physical Camera mode. Motion blur and
    /// exposure are scene-wide here (per-camera versions need layer-based
    /// volume stacks; defer until needed).
    /// </summary>
    public class SceneEffects : MonoBehaviour
    {
        [Header("Depth of field")]
        public bool enableDepthOfField = true;

        [Header("Motion blur (scene default)")]
        public bool enableMotionBlur = true;
        [Range(0f, 360f)] public float shutterAngleDeg = 180f;

        [Header("Exposure")]
        public bool enableExposure = true;
        [Range(-5f, 5f)] public float exposureCompensationEv;
        public ExposureMode exposureMode = ExposureMode.Fixed;
        public float fixedExposureEv = 13f;

        Volume _volume;
        VolumeProfile _profile;

        void Awake()
        {
            EnsureVolume();
            ApplyOverrides();
        }

        void OnValidate()
        {
            if (_profile != null) ApplyOverrides();
        }

        void EnsureVolume()
        {
            _volume = GetComponent<Volume>() ?? gameObject.AddComponent<Volume>();
            _volume.isGlobal = true;
            _volume.priority = 100f;
            if (_profile == null)
            {
                _profile = ScriptableObject.CreateInstance<VolumeProfile>();
                _profile.name = "SlopePokeRuntimeProfile";
            }
            _volume.sharedProfile = _profile;
        }

        void ApplyOverrides()
        {
            ConfigureDoF();
            ConfigureMotionBlur();
            ConfigureExposure();
        }

        void ConfigureDoF()
        {
            if (!_profile.TryGet<DepthOfField>(out var dof))
                dof = _profile.Add<DepthOfField>(true);
            dof.active = enableDepthOfField;
            // PhysicalCamera mode reads aperture / focusDistance from each rendering Camera,
            // giving us per-camera DoF without per-camera volumes.
            dof.focusMode.overrideState = true;
            dof.focusMode.value = DepthOfFieldMode.UsePhysicalCamera;
        }

        void ConfigureMotionBlur()
        {
            if (!_profile.TryGet<MotionBlur>(out var mb))
                mb = _profile.Add<MotionBlur>(true);
            mb.active = enableMotionBlur;
            mb.intensity.overrideState = true;
            mb.intensity.value = Mathf.Clamp01(shutterAngleDeg / 360f);
        }

        void ConfigureExposure()
        {
            if (!_profile.TryGet<Exposure>(out var exp))
                exp = _profile.Add<Exposure>(true);
            exp.active = enableExposure;
            exp.mode.overrideState = true;
            exp.mode.value = exposureMode;
            exp.compensation.overrideState = true;
            exp.compensation.value = exposureCompensationEv;
            if (exposureMode == ExposureMode.Fixed)
            {
                exp.fixedExposure.overrideState = true;
                exp.fixedExposure.value = fixedExposureEv;
            }
        }
    }
}
