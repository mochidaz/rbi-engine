import geopandas as gpd
import pandas as pd
import logging
from typing import Dict, List, Optional, Union, Literal
from pathlib import Path

from .config import RBIConfig
from .loaders import GDBLoader, ShapefileLoader

logger = logging.getLogger(__name__)


class RBIEngine:
    def __init__(self, config: RBIConfig):
        self.config = config
        self.loaders = {
            'gdb': GDBLoader(),
            'shapefile': ShapefileLoader()
        }
        self._layer_catalog: Optional[pd.DataFrame] = None

    @classmethod
    def from_yaml(cls, yaml_path: Union[str, Path]) -> 'RBIEngine':
        config = RBIConfig.from_yaml(yaml_path)
        return cls(config)

    def catalog_layers(self, force_refresh: bool = False) -> pd.DataFrame:
        if self._layer_catalog is not None and not force_refresh:
            return self._layer_catalog

        logger.info("Cataloging RBI layers...")
        catalog = []

        for source in self.config.sources:
            loader = self.loaders.get(source.type)
            if not loader:
                continue

            layers = loader.list_layers(source)
            for layer_name in layers:
                geom_type = self._detect_geometry_type(layer_name)
                category = self._detect_category(layer_name)

                catalog.append({
                    'source': source.name,
                    'region': source.region,
                    'layer': layer_name,
                    'category': category,
                    'geometry_type': geom_type
                })

        self._layer_catalog = pd.DataFrame(catalog)
        logger.info(f"Found {len(self._layer_catalog)} layers")
        return self._layer_catalog

    def _detect_geometry_type(self, layer_name: str) -> Optional[str]:
        if "_AR_" in layer_name or layer_name.endswith("_AR"): return "polygon"
        if "_LN_" in layer_name or layer_name.endswith("_LN"): return "line"
        if "_PT_" in layer_name or layer_name.endswith("_PT"): return "point"
        return None

    def _detect_category(self, layer_name: str) -> Optional[str]:
        for cat_name, pattern in self.config.layer_patterns.items():
            if pattern.matches(layer_name):
                return cat_name
        return None

    def load_category(self, category: str, regions: Optional[List[str]] = None,
                      geometry_type: Optional[str] = None, harmonize_fields: bool = True) -> gpd.GeoDataFrame:
        logger.info(f"Loading category: {category.upper()}")
        catalog = self.catalog_layers()
        mask = catalog['category'] == category

        if regions:
            mask &= catalog['region'].isin(regions)
        if geometry_type:
            mask &= catalog['geometry_type'] == geometry_type

        layers_to_load = catalog[mask]

        frames = []
        for _, row in layers_to_load.iterrows():
            source = next(s for s in self.config.sources if s.name == row['source'])
            loader = self.loaders[source.type]
            gdf = loader.load(source, row['layer'], self.config.target_crs)
            if not gdf.empty:
                frames.append(gdf)

        if not frames:
            return gpd.GeoDataFrame()

        if harmonize_fields:
            template = frames[0]
            frames = [self._harmonize_fields(gdf, template) for gdf in frames]

        result = pd.concat(frames, ignore_index=True)
        return gpd.GeoDataFrame(result, crs=self.config.target_crs)

    def load_roads_buffered(self, regions: Optional[List[str]] = None, default_buffer: float = 3.0) -> gpd.GeoDataFrame:
        logger.info("Loading road...")
        roads = self.load_category("road", regions=regions, geometry_type="line")
        if roads.empty: return gpd.GeoDataFrame()

        roads_metric = roads.to_crs(self.config.metric_crs)
        roads_metric['road_class'] = 'other'
        roads_metric['buffer_width'] = default_buffer

        for road_buffer in self.config.road_buffers:
            mask = roads_metric.apply(lambda row: road_buffer.matches_remark(row.get('REMARK', '')), axis=1)
            roads_metric.loc[mask, 'road_class'] = road_buffer.class_name
            roads_metric.loc[mask, 'buffer_width'] = road_buffer.width_meters

        roads_metric['geometry'] = roads_metric.apply(lambda row: row.geometry.buffer(row['buffer_width']), axis=1)
        return roads_metric.to_crs(self.config.target_crs)

    def _harmonize_fields(self, gdf: gpd.GeoDataFrame, template: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        # I think this should have some kind of config too?
        # to rename certain fields to standard names.
        # for now, I'm doing this specifically for BIG's RBI.
        rename_map = {
            'SHAPE_Area': 'SHAPE_AREA', 'NAMOBJ (Nama Objek)': 'NAMOBJ',
            'FCODE (Feature Code)': 'FCODE', 'REMARK (Catatan)': 'REMARK'
        }
        gdf = gdf.rename(columns=rename_map)
        target_cols = [c for c in template.columns if c in gdf.columns or c == 'geometry']
        return gdf[target_cols]