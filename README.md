# Single-city EVCS accessibility demo

This folder is a runnable single-city calculation demo for the Chinese 199 cities EVCS accessibility dataset. The bundled sample city is Shenzhen; the workflow can be reused for another city by replacing the same three input layers.

- `data/sample_city_population_ev_demand.gpkg`: 100 m research units with population and allocated EV demand.
- `data/sample_city_evcs_fixed_power_7_60.*`: EVCS point layer for the sample city. The effective-capacity field is `FixPwr_kW = 60 * fast_piles + 7 * slow_piles`.
- `data/sample_city_osm_drive.graphml`: the OSM drive-network graph used for road-distance routing.

The `outputs/` folder contains the already computed demo results. Running the script regenerates these files.

## Folder Structure

```text
single_city_accessibility_demo/
|-- README.md
|-- compute_travel_distance_accessibility.py
|-- compute_2sfca_accessibility.py
|-- data/
|   |-- sample_city_population_ev_demand.gpkg
|   |-- sample_city_evcs_fixed_power_7_60.cpg
|   |-- sample_city_evcs_fixed_power_7_60.dbf
|   |-- sample_city_evcs_fixed_power_7_60.prj
|   |-- sample_city_evcs_fixed_power_7_60.shp
|   |-- sample_city_evcs_fixed_power_7_60.shx
|   `-- sample_city_osm_drive.graphml
`-- outputs/
    |-- single_city_travel_distance_nearest_1to8_evcs.csv
    |-- single_city_2sfca_1to8km_distance_threshold.csv
    |-- travel_distance_run_report.json
    `-- two_sfca_run_report.json
```

## Environment

The script was checked with Python 3.8 and these main packages:

```bash
pip install pandas numpy geopandas osmnx networkx pyproj tqdm
```

## Run

From this folder, run the two calculations separately.

```bash
python compute_travel_distance_accessibility.py
python compute_2sfca_accessibility.py
```

For a quick smoke test:

```bash
python compute_travel_distance_accessibility.py --max-units 5000
python compute_2sfca_accessibility.py --max-units 5000
```

The output tables keep the city fields (`city`, `city_name`, and `city_en`) so users can see that the bundled sample city is Shenzhen. The two report JSON files record input counts, graph metadata, runtime, output paths, row counts, and output hashes.

## Method In Short

Travel-distance accessibility snaps each 100 m research unit and each EVCS point to the projected OSM drive network. For each research unit, the script searches shortest road paths and records the road-network distance to the nearest 1st to 8th EVCS. If fewer than eight EVCS can be reached through the directed graph, the missing ranks are left blank.

The 2SFCA product uses the same snapped road network. For each threshold `r` in 1, 1.5, and 2-8 km, the Gaussian distance-decay weight is:

```text
W(d, r) = [exp(-0.5 * (d / r)^2) - exp(-0.5)] / [1 - exp(-0.5)], if d <= r
W(d, r) = 0, otherwise
```

The station supply is:

```text
S_j = 60 * fast_piles_j + 7 * slow_piles_j
```

The population-denominator 2SFCA value is:

```text
R_j(r) = S_j / sum_i [pop_i * W(d_ij, r)]
A_i(r) = sum_j [R_j(r) * W(d_ij, r)]
```

The EV-demand-normalized fields convert the population-denominator value to kW per 1,000 EVs:

```text
ev1000_ai_i(r) = A_i(r) * city_pop_total / city_ev_total * 1000
```

This demo is intentionally city-level. The national workflow repeats the same logic for the full set of cities and then aggregates the city outputs into the released national products.
