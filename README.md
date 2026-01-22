# RBI Processing Engine

An engine to process Indonesia's Rupabumi Indonesia (RBI) data. I made this for my Flood Susceptibility Analysis project initially, but I want to make it reusable for my other projects. Might support the other landuse data as well. 

## Configuration

You can see the example in `rbi_config.yaml`.

## Usage

Get an RBI data from [here](https://tanahair.indonesia.go.id/portal-web/unduh).

Note that not all RBI data are the same! Some are using geodatabase (.gdb) format and some are using shapefile (.shp) directly.

I made this for Kabupaten Bandung, Kabupaten Bandung Barat, and Kota Cimahi, which apparently using .gdb format.

Example:

```python
from rbi_engine import RBIEngine

config_path = "rbi_config.yaml"

engine = RBIEngine.from_yaml(config_path)

settlements = engine.load_category("settlement")

print(settlements[["NAMOBJ", "geometry"]].head())
```
Example output:

```
  NAMOBJ                                           geometry
0         MULTIPOLYGON Z (((107.38528 -7.34543 0, 107.38...
1         MULTIPOLYGON Z (((107.50796 -7.375 0, 107.5079...
2         MULTIPOLYGON Z (((107.52943 -7.37479 0, 107.52...
3         MULTIPOLYGON Z (((107.49585 -7.37477 0, 107.49...
4         MULTIPOLYGON Z (((107.49885 -7.37429 0, 107.49...
```


