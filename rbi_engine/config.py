from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Union, Literal
import yaml
import logging

logger = logging.getLogger(__name__)


@dataclass
class RBISource:
    name: str
    region: str
    type: Literal["gdb", "shapefile"]
    path: Path

    def __post_init__(self):
        self.path = Path(self.path)
        if not self.path.exists():
            logger.warning(f"Path not found: {self.path}")


@dataclass
class LayerPattern:
    category: str
    layer_names: List[str]
    name_patterns: List[str] = field(default_factory=list)
    geometry_type: Optional[str] = None

    def matches(self, layer_name: str) -> bool:
        import re
        if layer_name in self.layer_names:
            return True
        for pattern in self.name_patterns:
            if re.search(pattern, layer_name, re.IGNORECASE):
                return True
        return False


@dataclass
class LandUseCategory:
    name: str
    weight: float
    patterns: List[str]
    priority: int = 0
    description: str = ""

    def matches_remark(self, remark: str) -> bool:
        if not isinstance(remark, str):
            return False
        remark_upper = remark.upper()
        return any(p.upper() in remark_upper for p in self.patterns)


@dataclass
class RoadBuffer:
    class_name: str
    width_meters: float
    patterns: List[str]

    def matches_remark(self, remark: str) -> bool:
        if not isinstance(remark, str):
            return False
        remark_upper = remark.upper()
        return any(p.upper() in remark_upper for p in self.patterns)


@dataclass
class RBIConfig:
    sources: List[RBISource]
    layer_patterns: Dict[str, LayerPattern]
    landuse_categories: List[LandUseCategory]
    road_buffers: List[RoadBuffer]
    target_crs: str = "EPSG:4326"
    metric_crs: str = "EPSG:32748"

    @classmethod
    def from_yaml(cls, yaml_path: Union[str, Path]) -> 'RBIConfig':
        with open(yaml_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        parsed_patterns = {}
        for key, val in config.get('layer_patterns', {}).items():
            params = val.copy()
            params.pop('category', None)
            parsed_patterns[key] = LayerPattern(category=key, **params)

        return cls(
            sources=[RBISource(**src) for src in config.get('sources', [])],
            layer_patterns=parsed_patterns,
            landuse_categories=[LandUseCategory(**lu) for lu in config.get('landuse_categories', [])],
            road_buffers=[RoadBuffer(**rb) for rb in config.get('road_buffers', [])],
            target_crs=config.get('target_crs', 'EPSG:4326'),
            metric_crs=config.get('metric_crs', 'EPSG:32748')
        )