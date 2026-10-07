"""Hardware Acceleration, Device Detection & Performance Optimization (Phase 9).
Detects available compute hardware (CUDA, DirectML, CPU) and provides adaptive
profiles optimized for low-end hardware, Windows, Android, and offline operation.
"""
import os
import sys
import time
import platform
import logging
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional

logger = logging.getLogger("sports_analyzer.core.hardware")


@dataclass
class HardwareSpecs:
    platform: str
    os_name: str
    os_version: str
    architecture: str
    cpu_count: int
    primary_device: str  # "cuda", "directml", or "cpu"
    device_name: str
    cuda_available: bool
    directml_available: bool
    fp16_supported: bool
    memory_gb: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PerformanceProfile:
    name: str  # "low_power", "balanced", "max_performance", "custom"
    frame_skip: int  # 0 = every frame, 1 = every 2nd frame, 2 = every 3rd frame
    pose_cadence: int  # 1 = every frame, 2 = every 2nd frame, 3 = every 3rd frame
    input_size: int  # 320, 480, 640
    target_fps: float  # 15.0, 30.0, 60.0
    fp16: bool
    auto_throttle: bool  # adaptively increase frame_skip if latency exceeds frame budget

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# Predefined tuning profiles
PREDEFINED_PROFILES = {
    "low_power": PerformanceProfile(
        name="low_power",
        frame_skip=2,      # Process detection every 3rd frame
        pose_cadence=3,    # Estimate pose every 3rd frame
        input_size=320,    # Lightweight resolution for low-end / battery
        target_fps=20.0,
        fp16=False,
        auto_throttle=True
    ),
    "balanced": PerformanceProfile(
        name="balanced",
        frame_skip=1,      # Process detection every 2nd frame
        pose_cadence=2,    # Estimate pose every 2nd frame
        input_size=480,    # Balanced speed/accuracy
        target_fps=30.0,
        fp16=False,
        auto_throttle=True
    ),
    "max_performance": PerformanceProfile(
        name="max_performance",
        frame_skip=0,      # Process every single frame
        pose_cadence=1,    # Full pose on every frame
        input_size=640,    # Native YOLOv8 resolution
        target_fps=60.0,
        fp16=True,
        auto_throttle=False
    )
}


class HardwareManager:
    """Manages hardware detection, compute devices, and performance regulation."""

    def __init__(self):
        self.specs = self._detect_hardware()
        self.active_profile = self._choose_default_profile()

    def _detect_hardware(self) -> HardwareSpecs:
        os_sys = platform.system()
        cpu_cnt = os.cpu_count() or 4
        arch = platform.machine()
        cuda_avail = False
        directml_avail = False
        device = "cpu"
        device_name = f"Generic CPU ({cpu_cnt} cores)"
        fp16 = False

        # 1. Probe PyTorch CUDA
        try:
            import torch
            if torch.cuda.is_available():
                cuda_avail = True
                device = "cuda"
                device_name = torch.cuda.get_device_name(0)
                fp16 = True
        except Exception:
            pass

        # 2. Probe DirectML on Windows (if not CUDA)
        if not cuda_avail and os_sys == "Windows":
            try:
                import torch_directml
                if torch_directml.is_available():
                    directml_avail = True
                    device = "directml"
                    device_name = "DirectML DirectX 12 Accelerator"
            except Exception:
                # DirectML fallback: check if Windows DirectX 12 capability is present
                if os.path.exists(r"C:\Windows\System32\d3d12.dll"):
                    directml_avail = True

        return HardwareSpecs(
            platform=os_sys,
            os_name=platform.platform(),
            os_version=platform.version(),
            architecture=arch,
            cpu_count=cpu_cnt,
            primary_device=device,
            device_name=device_name,
            cuda_available=cuda_avail,
            directml_available=directml_avail,
            fp16_supported=fp16
        )

    def _choose_default_profile(self) -> PerformanceProfile:
        """Picks the optimal profile based on detected hardware."""
        if self.specs.cuda_available:
            return PREDEFINED_PROFILES["max_performance"]
        elif self.specs.cpu_count >= 8:
            return PREDEFINED_PROFILES["balanced"]
        else:
            return PREDEFINED_PROFILES["low_power"]

    def set_profile(self, profile_name: str, overrides: Optional[Dict[str, Any]] = None) -> PerformanceProfile:
        """Sets the active profile with optional fine-tuned parameters."""
        if profile_name in PREDEFINED_PROFILES:
            base = PREDEFINED_PROFILES[profile_name]
            params = base.to_dict()
        else:
            params = PREDEFINED_PROFILES["balanced"].to_dict()
            params["name"] = profile_name

        if overrides:
            for k, v in overrides.items():
                if k in params and v is not None:
                    params[k] = v

        self.active_profile = PerformanceProfile(**params)
        logger.info(f"Active performance profile switched to: {self.active_profile.name}")
        return self.active_profile

    def run_benchmark(self, frames_count: int = 10) -> Dict[str, Any]:
        """Runs a quick synthetic benchmark to measure processing latency and FPS."""
        import numpy as np

        latencies = []
        for _ in range(frames_count):
            t0 = time.perf_counter()
            # Simulate image processing load (matrix ops + normalization)
            dummy = np.random.randint(0, 255, (self.active_profile.input_size, self.active_profile.input_size, 3), dtype=np.uint8)
            _ = dummy.astype(np.float32) / 255.0
            dt = (time.perf_counter() - t0) * 1000.0  # ms
            latencies.append(dt)

        avg_latency_ms = sum(latencies) / len(latencies)
        estimated_fps = 1000.0 / max(0.1, avg_latency_ms)

        return {
            "device": self.specs.primary_device,
            "device_name": self.specs.device_name,
            "profile": self.active_profile.name,
            "input_size": self.active_profile.input_size,
            "avg_latency_ms": round(avg_latency_ms, 2),
            "estimated_fps": round(estimated_fps, 1),
            "frames_tested": frames_count
        }


# Global singleton hardware manager
hardware_manager = HardwareManager()
