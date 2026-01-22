import geopandas as gpd
from abc import ABC, abstractmethod
from typing import List
import logging
from .config import RBISource

logger = logging.getLogger(__name__)


class RBILoader(ABC):
    @abstractmethod
    def load(self, source: RBISource, layer_name: str, target_crs: str) -> gpd.GeoDataFrame:
        pass

    @abstractmethod
    def list_layers(self, source: RBISource) -> List[str]:
        pass


class GDBLoader(RBILoader):
    def list_layers(self, source: RBISource) -> List[str]:
        try:
            import fiona
            layers = fiona.listlayers(str(source.path))
            return layers
        except Exception as e:
            logger.error(f"Failed listing GDB layers: {e}")
            return []

    def load(self, source: RBISource, layer_name: str, target_crs: str) -> gpd.GeoDataFrame:
        try:
            gdf = gpd.read_file(source.path, layer=layer_name)
            gdf = gdf.to_crs(target_crs)
            gdf['_source'] = source.region
            gdf['_layer'] = layer_name
            return gdf
        except Exception as e:
            logger.error(f"Failed loading {layer_name} from {source.name}: {e}")
            return gpd.GeoDataFrame()


class ShapefileLoader(RBILoader):
    def list_layers(self, source: RBISource) -> List[str]:
        if not source.path.is_dir():
            return []
        return [f.stem for f in source.path.glob("*.shp")]

    def load(self, source: RBISource, layer_name: str, target_crs: str) -> gpd.GeoDataFrame:
        shp_path = source.path / f"{layer_name}.shp"
        if not shp_path.exists():
            logger.warning(f"Shapefile not found: {shp_path}")
            return gpd.GeoDataFrame()

        try:
            gdf = gpd.read_file(shp_path)
            gdf = gdf.to_crs(target_crs)
            gdf['_source'] = source.region
            gdf['_layer'] = layer_name
            return gdf
        except Exception as e:
            logger.error(f"Failed loading {shp_path}: {e}")
            return gpd.GeoDataFrame()