#!/usr/bin/env python3
"""Command-line program for shortest-distance Shanghai Metro routes."""

from __future__ import annotations

import argparse
import heapq
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Route:
    station_ids: list[str]
    edge_ids: list[str]
    distance_m: int


def station_ids_for_name(network: dict, name: str) -> list[str]:
    normalized_name = name.strip()
    return [station["id"] for station in network["stations"] if station["name"].strip() == normalized_name]


def shortest_path(network: dict, origin_name: str, destination_name: str) -> Route:
    origins = station_ids_for_name(network, origin_name)
    destinations = set(station_ids_for_name(network, destination_name))
    if not origins:
        raise ValueError(f"unknown origin station: {origin_name}")
    if not destinations:
        raise ValueError(f"unknown destination station: {destination_name}")

    adjacency: dict[str, list[tuple[str, int, str]]] = {}
    for edge in [*network["edges"], *network["transfers"]]:
        distance = edge["distance_m"]
        if not isinstance(distance, int) or distance < 0:
            raise ValueError(f"distance is missing: {edge['id']}")
        left, right = edge["from_station_id"], edge["to_station_id"]
        adjacency.setdefault(left, []).append((right, distance, edge["id"]))
        adjacency.setdefault(right, []).append((left, distance, edge["id"]))

    distances = {station_id: 0 for station_id in origins}
    previous: dict[str, tuple[str, str]] = {}
    queue = [(0, index, station_id) for index, station_id in enumerate(origins)]
    heapq.heapify(queue)
    sequence = len(queue)
    destination_id = None

    while queue:
        distance, _, station_id = heapq.heappop(queue)
        if distance != distances[station_id]:
            continue
        if station_id in destinations:
            destination_id = station_id
            break
        for next_id, edge_distance, edge_id in adjacency.get(station_id, []):
            next_distance = distance + edge_distance
            if next_distance < distances.get(next_id, float("inf")):
                distances[next_id] = next_distance
                previous[next_id] = (station_id, edge_id)
                heapq.heappush(queue, (next_distance, sequence, next_id))
                sequence += 1

    if destination_id is None:
        raise ValueError(f"no route from {origin_name} to {destination_name}")

    station_ids, edge_ids = [destination_id], []
    while station_ids[-1] not in origins:
        prior_id, edge_id = previous[station_ids[-1]]
        station_ids.append(prior_id)
        edge_ids.append(edge_id)
    station_ids.reverse()
    edge_ids.reverse()
    return Route(station_ids=station_ids, edge_ids=edge_ids, distance_m=distances[destination_id])


def format_route(network: dict, route: Route) -> str:
    names = {station["id"]: station["name"].strip() for station in network["stations"]}
    edges = {edge["id"]: edge for edge in [*network["edges"], *network["transfers"]]}
    route_names = []
    for station_id in route.station_ids:
        name = names[station_id]
        if not route_names or route_names[-1] != name:
            route_names.append(name)
    transfer_lines = []
    for index, edge_id in enumerate(route.edge_ids):
        if not edge_id.startswith("transfer:"):
            continue
        before = next((edges[item]["line_id"] for item in reversed(route.edge_ids[:index]) if "line_id" in edges[item]), None)
        after = next((edges[item]["line_id"] for item in route.edge_ids[index + 1:] if "line_id" in edges[item]), None)
        station_name = names[route.station_ids[index]]
        transfer_lines.append(f"{station_name}（{before}号线 → {after}号线）")
    lines = [f"总距离：{route.distance_m} m", f"途经：{' → '.join(route_names)}"]
    if transfer_lines:
        lines.append(f"换乘：{'；'.join(transfer_lines)}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="按区间距离计算上海地铁最短路径")
    parser.add_argument("origin", help="起点站名")
    parser.add_argument("destination", help="终点站名")
    parser.add_argument("--network", type=Path, default=Path("data/metro-network.json"))
    args = parser.parse_args()
    try:
        network = json.loads(args.network.read_text())
        print(format_route(network, shortest_path(network, args.origin, args.destination)))
    except ValueError as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
