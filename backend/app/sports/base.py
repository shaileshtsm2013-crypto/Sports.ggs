from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import numpy as np


class SportsAnalyzer(ABC):
    """
    Abstract base class for all sport-specific computer vision analyzers.
    Enables pluggable sport modules (Volleyball, Kabaddi, Kho Kho, etc.)
    without modifying the core vision engine.
    """

    def __init__(self, sport_name: str):
        self.sport_name = sport_name
        self.court_calibrated: bool = False
        self.court_dimensions_meters: Dict[str, float] = {}

    @abstractmethod
    def calibrate_court(self, frame: np.ndarray, manual_points: Optional[List[Dict[str, float]]] = None) -> bool:
        """Calibrates court boundaries, perspective transformation, and lines."""
        pass

    @abstractmethod
    def analyze_frame(self, frame_idx: int, timestamp: float, players: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Executes sport-specific kinematic and tactical analysis on the frame.
        Returns detected events, player zones, and metric updates.
        """
        pass

    @abstractmethod
    def get_court_layout(self) -> Dict[str, Any]:
        """Returns standard dimensions and line coordinate definitions for the sport."""
        pass
