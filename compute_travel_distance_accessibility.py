from __future__ import annotations

import argparse
import hashlib
import heapq
import json
import math
import time
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List

import geopandas as gpd
import networkx as nx
import numpy as np
import osmnx as ox
import pandas as pd
from pyproj import CRS

try:
    from tqdm.auto import tqdm
except Exception:  # pragma: no cover
    tqdm = None


HERE = Path(__file__).resolve().parent
DATA_DIR = HERE / "data"
OUTPUT_DIR = HERE / "outputs"

SAMPLE_CITY_NAME_ZH = "深圳市"
SAMPLE_CITY_NAME_EN = "Shenzhen"

POPULATION_GPKG = DATA_DIR / "sample_city_population_ev_demand.gpkg"
EVCS_SHP = DATA_DIR / "sample_city_evcs_fixed_power_7_60.shp"
ROAD_GRAPHML = DATA_DIR / "sample_city_osm_drive.graphml"

TOP_K = 8
ACCESS_SPEED_KPH = 30.0
RADIUS_KM_LIST = [1, 1.5, 2, 3, 4, 5, 6, 7, 8]
RADIUS_M_LIST = [r * 1000.0 for r in RADIUS_KM_LIST]
MAX_RADIUS_M = max(RADIUS_M_LIST)

DEFAULT_HWY_SPEEDS = {
    "motorway": 100,
    "motorway_link": 60,
    "trunk": 80,
    "trunk_link": 50,
    "primary": 60,
    "primary_link": 45,
    "secondary": 50,
    "secondary_link": 40,
    "tertiary": 40,
    "tertiary_link": 35,
    "unclassified": 30,
    "residential": 30,
    "living_street": 20,
    "service": 20,
    "road": 30,
}
FALLBACK_SPEED = 30


def iter_progress(items: Iterable, **kwargs):
    if tqdm is None:
        return items
    return tqdm(items, **kwargs)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_file(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Missing required file: {path}")


def format_report_path(path: Path) -> str:
    return path.resolve().relative_to(HERE).as_posix()


def add_speeds_and_times(G: nx.MultiDiGraph) -> nx.MultiDiGraph:
    try:
        G = ox.routing.add_edge_speeds(
            G, hwy_speeds=DEFAULT_HWY_SPEEDS, fallback=FALLBACK_SPEED
        )
        G = ox.routing.add_edge_travel_times(G)
    except AttributeError:
        G = ox.add_edge_speeds(
            G, hwy_speeds=DEFAULT_HWY_SPEEDS, fallback=FALLBACK_SPEED
        )
        G = ox.add_edge_travel_times(G)
    return G


def load_projected_graph() -> nx.MultiDiGraph:
    require_file(ROAD_GRAPHML)
    G = ox.load_graphml(ROAD_GRAPHML)
    try:
        G = ox.projection.project_graph(G)
    except AttributeError:
        G = ox.project_graph(G)
    return add_speeds_and_times(G)


def load_population(max_units: int | None = None) -> gpd.GeoDataFrame:
    require_file(POPULATION_GPKG)
    pop = gpd.read_file(POPULATION_GPKG)
    required = {
        "oid",
        "pop",
        "ev_demand",
        "city_pop_total",
        "city_ev_total",
    }
    missing = required - set(pop.columns)
    if missing:
        raise ValueError(f"Population GeoPackage is missing columns: {sorted(missing)}")
    if pop.crs is None:
        raise ValueError("The population GeoPackage has no CRS.")
    pop = pop.sort_values("oid").reset_index(drop=True)
    if max_units is not None:
        pop = pop.head(max_units).copy()
    for col in ["pop", "ev_demand", "city_pop_total", "city_ev_total"]:
        pop[col] = pd.to_numeric(pop[col], errors="coerce")
    pop["pop"] = pop["pop"].fillna(0).clip(lower=0)
    pop["ev_demand"] = pop["ev_demand"].fillna(0).clip(lower=0)
    pop_wgs84 = pop.to_crs("EPSG:4326")
    pop["lon"] = pop_wgs84.geometry.x.to_numpy(dtype=float)
    pop["lat"] = pop_wgs84.geometry.y.to_numpy(dtype=float)
    return pop


def load_evcs() -> gpd.GeoDataFrame:
    require_file(EVCS_SHP)
    evcs = gpd.read_file(EVCS_SHP)
    if evcs.crs is None:
        raise ValueError("The EVCS shapefile has no CRS.")
    if len(evcs) == 0:
        raise ValueError("The EVCS shapefile is empty.")

    if "FixPwr_kW" not in evcs.columns:
        if {"FNum_qy", "SNum_qy"}.issubset(evcs.columns):
            evcs["FixPwr_kW"] = (
                pd.to_numeric(evcs["FNum_qy"], errors="coerce").fillna(0) * 60.0
                + pd.to_numeric(evcs["SNum_qy"], errors="coerce").fillna(0) * 7.0
            )
        else:
            raise ValueError("The EVCS shapefile needs FixPwr_kW or FNum_qy/SNum_qy.")

    evcs["FixPwr_kW"] = pd.to_numeric(evcs["FixPwr_kW"], errors="coerce").fillna(0)
    evcs = evcs.reset_index(drop=True)
    evcs["d_id_internal"] = np.arange(1, len(evcs) + 1, dtype=np.int32)
    return evcs


def prepare_snap_data(
    G: nx.MultiDiGraph, pop: gpd.GeoDataFrame, evcs: gpd.GeoDataFrame
) -> dict:
    graph_crs = CRS.from_user_input(G.graph["crs"])
    pop_proj = pop.to_crs(graph_crs)
    pop_x = pop_proj.geometry.x.to_numpy(dtype=float)
    pop_y = pop_proj.geometry.y.to_numpy(dtype=float)

    evcs_proj = evcs.to_crs(graph_crs)
    evcs_x = evcs_proj.geometry.x.to_numpy(dtype=float)
    evcs_y = evcs_proj.geometry.y.to_numpy(dtype=float)

    pop_nodes = np.asarray(ox.distance.nearest_nodes(G, X=pop_x, Y=pop_y))
    evcs_nodes = np.asarray(ox.distance.nearest_nodes(G, X=evcs_x, Y=evcs_y))

    node_x = {node: float(data["x"]) for node, data in G.nodes(data=True)}
    node_y = {node: float(data["y"]) for node, data in G.nodes(data=True)}

    pop_node_x = np.asarray([node_x[node] for node in pop_nodes], dtype=float)
    pop_node_y = np.asarray([node_y[node] for node in pop_nodes], dtype=float)
    evcs_node_x = np.asarray([node_x[node] for node in evcs_nodes], dtype=float)
    evcs_node_y = np.asarray([node_y[node] for node in evcs_nodes], dtype=float)

    pop_access_m = np.hypot(pop_x - pop_node_x, pop_y - pop_node_y)
    evcs_access_m = np.hypot(evcs_x - evcs_node_x, evcs_y - evcs_node_y)

    return {
        "pop_x": pop_x,
        "pop_y": pop_y,
        "pop_nodes": pop_nodes,
        "pop_access_m": pop_access_m,
        "evcs_nodes": evcs_nodes,
        "evcs_access_m": evcs_access_m,
    }


def access_time_seconds(dist_m: float) -> float:
    speed_mps = ACCESS_SPEED_KPH * 1000.0 / 3600.0
    return float(dist_m) / speed_mps if speed_mps > 0 else math.nan


def build_compact_adjacency(
    G: nx.MultiDiGraph, reverse: bool = False, include_time: bool = False
) -> Dict[object, list]:
    compact = {}
    for u in iter_progress(
        list(G.nodes()), desc="Build reverse adjacency" if reverse else "Build adjacency"
    ):
        compact_list = []
        if u not in G.adj:
            compact[u] = compact_list
            continue

        for v, edge_data in G.adj[u].items():
            best_len = None
            best_time = None
            attrs_iter = edge_data.values() if G.is_multigraph() else [edge_data]

            for attrs in attrs_iter:
                edge_len = attrs.get("length", None)
                if edge_len is None or pd.isna(edge_len):
                    geom = attrs.get("geometry", None)
                    edge_len = geom.length if geom is not None else None
                if edge_len is None or pd.isna(edge_len):
                    continue

                edge_len = float(edge_len)
                edge_time = attrs.get("travel_time", edge_len / (FALLBACK_SPEED * 1000 / 3600))
                edge_time = float(edge_time) if not pd.isna(edge_time) else 0.0

                if (
                    best_len is None
                    or edge_len < best_len
                    or (
                        include_time
                        and abs(edge_len - best_len) < 1e-9
                        and edge_time < best_time
                    )
                ):
                    best_len = edge_len
                    best_time = edge_time

            if best_len is not None:
                if reverse:
                    if include_time:
                        compact_list.append((v, best_len, best_time))
                    else:
                        compact.setdefault(v, []).append((u, best_len))
                else:
                    if include_time:
                        compact_list.append((v, best_len, best_time))
                    else:
                        compact_list.append((v, best_len))

        if not reverse:
            compact[u] = compact_list
        else:
            compact.setdefault(u, compact.get(u, []))

    return compact


def k_nearest_evcs_by_shortest_distance(
    source_node: object,
    compact_adj: Dict[object, list],
    facility_ids_by_node: dict,
    facility_info: dict,
    k: int = TOP_K,
) -> List[dict]:
    heap = [(0.0, 0.0, source_node)]
    best = {source_node: (0.0, 0.0)}
    visited = set()
    results = []

    while heap and len(results) < k:
        dist_u, time_u, u = heapq.heappop(heap)
        if u in visited:
            continue
        visited.add(u)

        if u in facility_ids_by_node:
            fac_ids = sorted(
                facility_ids_by_node[u],
                key=lambda fid: facility_info[fid]["d_access_dist_m"],
            )
            for fac_id in fac_ids:
                info = facility_info[fac_id]
                results.append(
                    {
                        "d_id_internal": fac_id,
                        "net_dist_m": dist_u,
                        "net_time_s": time_u,
                        "d_access_dist_m": info["d_access_dist_m"],
                        "d_access_time_s": info["d_access_time_s"],
                    }
                )
                if len(results) >= k:
                    break

        if len(results) >= k:
            break

        for v, edge_len, edge_time in compact_adj.get(u, []):
            new_dist = dist_u + edge_len
            new_time = time_u + edge_time
            old = best.get(v)
            if (
                old is None
                or new_dist < old[0]
                or (abs(new_dist - old[0]) < 1e-9 and new_time < old[1])
            ):
                best[v] = (new_dist, new_time)
                heapq.heappush(heap, (new_dist, new_time, v))

    return results


def compute_travel_distance(
    G: nx.MultiDiGraph, pop: gpd.GeoDataFrame, evcs: gpd.GeoDataFrame, snap: dict
) -> pd.DataFrame:
    evcs_nodes = snap["evcs_nodes"]
    evcs_access_m = snap["evcs_access_m"]
    pop_nodes = snap["pop_nodes"]
    pop_access_m = snap["pop_access_m"]

    facility_ids_by_node = defaultdict(list)
    facility_info = {}
    for idx, d_node in enumerate(evcs_nodes):
        fac_id = int(idx + 1)
        facility_ids_by_node[d_node].append(fac_id)
        d_access = float(evcs_access_m[idx])
        facility_info[fac_id] = {
            "d_access_dist_m": d_access,
            "d_access_time_s": access_time_seconds(d_access),
        }

    compact_adj = build_compact_adjacency(G, reverse=False, include_time=True)

    unique_o_nodes = pd.unique(pop_nodes)
    records = []
    for o_node in iter_progress(
        unique_o_nodes, total=len(unique_o_nodes), desc="Nearest EVCS"
    ):
        nearest = k_nearest_evcs_by_shortest_distance(
            source_node=o_node,
            compact_adj=compact_adj,
            facility_ids_by_node=facility_ids_by_node,
            facility_info=facility_info,
            k=TOP_K,
        )
        row = {"o_node": o_node, "found_count": len(nearest)}
        for rank in range(1, TOP_K + 1):
            if rank <= len(nearest):
                item = nearest[rank - 1]
                row[f"trip{rank}_dist_km_node_to_evcs"] = (
                    item["net_dist_m"] + item["d_access_dist_m"]
                ) / 1000.0
            else:
                row[f"trip{rank}_dist_km_node_to_evcs"] = np.nan
        records.append(row)

    node_result = pd.DataFrame.from_records(records)
    node_result = node_result.set_index("o_node")

    out = pd.DataFrame(
        {
            "city": SAMPLE_CITY_NAME_EN,
            "o_lon": pop["lon"].to_numpy(dtype=float),
            "o_lat": pop["lat"].to_numpy(dtype=float),
            "value": pop["pop"].to_numpy(dtype=float),
            "o_node": pop_nodes,
            "o_access_dist_m": pop_access_m,
        }
    )
    out = out.join(node_result, on="o_node")
    out["found_count"] = out["found_count"].fillna(0).astype(np.int16)

    for rank in range(1, TOP_K + 1):
        src = f"trip{rank}_dist_km_node_to_evcs"
        dst = f"nearest_{rank}_evcs_dist_km"
        valid = out[src].notna()
        out[dst] = np.where(
            valid,
            out["o_access_dist_m"] / 1000.0 + out[src],
            np.nan,
        )

    keep = ["city", "o_lon", "o_lat", "value", "found_count"]
    keep.extend([f"nearest_{rank}_evcs_dist_km" for rank in range(1, TOP_K + 1)])
    return out[keep]


def bounded_dijkstra_lengths(
    source_node: object, compact_adj: Dict[object, list], max_dist: float
) -> Dict[object, float]:
    heap = [(0.0, source_node)]
    best = {source_node: 0.0}
    visited = set()

    while heap:
        dist_u, u = heapq.heappop(heap)
        if u in visited:
            continue
        visited.add(u)
        if dist_u > max_dist:
            continue
        for v, edge_len in compact_adj.get(u, []):
            new_dist = dist_u + edge_len
            if new_dist > max_dist:
                continue
            old = best.get(v)
            if old is None or new_dist < old:
                best[v] = new_dist
                heapq.heappush(heap, (new_dist, v))
    return best


def decay_weights(dist_m: np.ndarray, radius_m: float) -> np.ndarray:
    d = np.asarray(dist_m, dtype=float)
    w = np.zeros_like(d, dtype=float)
    valid = np.isfinite(d) & (d >= 0) & (d <= radius_m)
    if not np.any(valid):
        return w
    x = d[valid] / radius_m
    vals = (np.exp(-0.5 * x**2) - np.exp(-0.5)) / (1.0 - np.exp(-0.5))
    vals[vals < 0] = 0
    w[valid] = vals
    return w


def radius_label(r_km: float) -> str:
    if abs(r_km - 1.5) < 1e-9:
        return "1_5k"
    return f"{int(r_km)}k"


def compute_2sfca(
    G: nx.MultiDiGraph, pop: gpd.GeoDataFrame, evcs: gpd.GeoDataFrame, snap: dict
) -> pd.DataFrame:
    pop_nodes = snap["pop_nodes"]
    pop_access_m = snap["pop_access_m"]
    evcs_nodes = snap["evcs_nodes"]
    evcs_access_m = snap["evcs_access_m"]

    pop_weights = pop["pop"].to_numpy(dtype=float)
    fac_supply = evcs["FixPwr_kW"].to_numpy(dtype=float)

    pop_indices_by_node = defaultdict(list)
    for idx, node in enumerate(pop_nodes):
        pop_indices_by_node[node].append(idx)
    pop_indices_by_node = {
        node: np.asarray(indices, dtype=np.int64)
        for node, indices in pop_indices_by_node.items()
    }

    facility_groups = defaultdict(list)
    for idx, node in enumerate(evcs_nodes):
        facility_groups[node].append(idx)

    compact_adj = build_compact_adjacency(G, reverse=True, include_time=False)
    access_by_r = {
        r_km: np.zeros(len(pop), dtype=float) for r_km in RADIUS_KM_LIST
    }

    for d_node, fac_indices in iter_progress(
        list(facility_groups.items()), desc="2SFCA by EVCS node"
    ):
        fac_indices = np.asarray(fac_indices, dtype=np.int64)
        min_d_access = np.nanmin(evcs_access_m[fac_indices])
        max_net_limit = MAX_RADIUS_M - min_d_access
        if not np.isfinite(max_net_limit) or max_net_limit < 0:
            continue

        dist_by_node = bounded_dijkstra_lengths(d_node, compact_adj, max_net_limit)
        if not dist_by_node:
            continue

        candidate_idx_parts = []
        candidate_net_parts = []
        for node, net_dist in dist_by_node.items():
            pop_idxs = pop_indices_by_node.get(node)
            if pop_idxs is None:
                continue
            candidate_idx_parts.append(pop_idxs)
            candidate_net_parts.append(
                np.full(len(pop_idxs), float(net_dist), dtype=float)
            )

        if not candidate_idx_parts:
            continue

        cand_pop_idx = np.concatenate(candidate_idx_parts)
        cand_net_dist = np.concatenate(candidate_net_parts)

        for fac_idx in fac_indices:
            supply_j = fac_supply[fac_idx]
            d_access_j = evcs_access_m[fac_idx]
            if not np.isfinite(supply_j) or supply_j <= 0:
                continue
            if not np.isfinite(d_access_j):
                continue

            total_dist = cand_net_dist + pop_access_m[cand_pop_idx] + d_access_j

            for r_km, radius_m in zip(RADIUS_KM_LIST, RADIUS_M_LIST):
                valid = np.isfinite(total_dist) & (total_dist <= radius_m)
                if not np.any(valid):
                    continue

                valid_pop_idx = cand_pop_idx[valid]
                valid_dist = total_dist[valid]
                weights = decay_weights(valid_dist, radius_m)
                positive = weights > 0
                if not np.any(positive):
                    continue

                valid_pop_idx = valid_pop_idx[positive]
                weights = weights[positive]
                denom = np.sum(pop_weights[valid_pop_idx] * weights)
                if not np.isfinite(denom) or denom <= 0:
                    continue

                ratio_j = supply_j / denom
                np.add.at(access_by_r[r_km], valid_pop_idx, ratio_j * weights)

    city_pop_total = float(pop["city_pop_total"].dropna().iloc[0])
    city_ev_total = float(pop["city_ev_total"].dropna().iloc[0])
    scale_to_ev1000 = city_pop_total / city_ev_total * 1000.0

    out = pd.DataFrame(
        {
            "city_name": SAMPLE_CITY_NAME_ZH,
            "city_en": SAMPLE_CITY_NAME_EN,
            "lon": pop["lon"].to_numpy(dtype=float),
            "lat": pop["lat"].to_numpy(dtype=float),
            "unit_pop": pop["pop"].to_numpy(dtype=float),
            "units_EVs": pop["ev_demand"].to_numpy(dtype=float),
        }
    )

    for r_km in RADIUS_KM_LIST:
        out[f"pop_ai{radius_label(r_km)}"] = access_by_r[r_km]
    for r_km in RADIUS_KM_LIST:
        ai_at_public_precision = np.asarray(
            [float(f"{value:.10f}") for value in access_by_r[r_km]],
            dtype=float,
        )
        out[f"ev1000_ai{radius_label(r_km)}"] = (
            ai_at_public_precision * scale_to_ev1000
        )

    return out


def write_travel_public(df: pd.DataFrame, path: Path) -> None:
    def fmt_6_to_2(x: float) -> str:
        if pd.isna(x):
            return ""
        return f"{float(f'{float(x):.6f}'):.2f}"

    out = df.copy()
    out["o_lon"] = out["o_lon"].map(lambda x: f"{x:.6f}")
    out["o_lat"] = out["o_lat"].map(lambda x: f"{x:.6f}")
    out["value"] = out["value"].map(fmt_6_to_2)
    for rank in range(1, TOP_K + 1):
        col = f"nearest_{rank}_evcs_dist_km"
        out[col] = out[col].map(fmt_6_to_2)
    out.to_csv(path, index=False, encoding="utf-8", lineterminator="\n")


def write_2sfca_public(df: pd.DataFrame, path: Path) -> None:
    df.to_csv(
        path,
        index=False,
        encoding="utf-8-sig",
        float_format="%.10f",
        lineterminator="\n",
    )


def build_base_report(pop: gpd.GeoDataFrame, evcs: gpd.GeoDataFrame, G: nx.MultiDiGraph) -> dict:
    return {
        "demo": "single-city EVCS accessibility demo",
        "sample_city": {
            "city_name": SAMPLE_CITY_NAME_ZH,
            "city_en": SAMPLE_CITY_NAME_EN,
        },
        "research_units": int(len(pop)),
        "evcs_points": int(len(evcs)),
        "road_nodes": int(len(G.nodes)),
        "road_edges": int(len(G.edges)),
        "graph_crs": str(G.graph.get("crs")),
        "osmnx_created_date": G.graph.get("created_date"),
        "osmnx_created_with": G.graph.get("created_with"),
        "inputs": {
            "population_ev_demand_gpkg": format_report_path(POPULATION_GPKG),
            "evcs_fixed_power_shp": format_report_path(EVCS_SHP),
            "road_graphml": format_report_path(ROAD_GRAPHML),
        },
        "outputs": {},
    }



def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compute nearest 1-8 EVCS travel-distance accessibility for the "
            "bundled single-city sample."
        )
    )
    parser.add_argument(
        "--max-units",
        type=int,
        default=None,
        help="Optional smoke-test limit. Omit it to run the full bundled sample city.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    start = time.time()
    OUTPUT_DIR.mkdir(exist_ok=True)

    for path in [POPULATION_GPKG, EVCS_SHP, ROAD_GRAPHML]:
        require_file(path)

    print("Loading input data...")
    pop = load_population(max_units=args.max_units)
    evcs = load_evcs()
    G = load_projected_graph()

    print(f"Research units: {len(pop):,}")
    print(f"EVCS points: {len(evcs):,}")
    print(f"Road graph: {len(G.nodes):,} nodes, {len(G.edges):,} edges")

    print("Snapping population and EVCS points to the road network...")
    snap = prepare_snap_data(G, pop, evcs)

    print("Computing nearest 1-8 EVCS travel-distance accessibility...")
    travel = compute_travel_distance(G, pop, evcs, snap)
    travel_path = OUTPUT_DIR / "single_city_travel_distance_nearest_1to8_evcs.csv"
    write_travel_public(travel, travel_path)

    report = build_base_report(pop, evcs, G)
    report["task"] = "travel-distance accessibility"
    report["outputs"]["travel_distance"] = {
        "path": format_report_path(travel_path),
        "sha256": sha256(travel_path),
        "rows": int(len(travel)),
    }
    report["runtime_seconds"] = round(time.time() - start, 3)

    report_path = OUTPUT_DIR / "travel_distance_run_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print("Run finished.")
    print(f"Output: {travel_path}")
    print(f"Report: {report_path}")


if __name__ == "__main__":
    main()
