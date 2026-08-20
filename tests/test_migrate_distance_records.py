import unittest

from scripts.migrate_distance_records import migrate_entries


class MigrateDistanceRecordsTests(unittest.TestCase):
    def test_migrates_name_based_edge_id_without_changing_distance(self):
        legacy = {
            "stations": [
                {"id": "station:国家会展中心", "name": "国家会展中心"},
                {"id": "station:虹桥火车站", "name": "虹桥火车站"},
            ],
            "edges": [{"id": "2:station:国家会展中心:station:虹桥火车站", "line_id": "2", "from_station_id": "station:国家会展中心", "to_station_id": "station:虹桥火车站"}],
        }
        official = {
            "stations": [{"id": "station0234", "name": "国家会展中心"}, {"id": "station0223", "name": "虹桥火车站"}],
            "edges": [{"id": "2:station0234:station0223", "line_id": "2", "from_station_id": "station0234", "to_station_id": "station0223"}],
        }

        result = migrate_entries([{"edge_id": "2:station:国家会展中心:station:虹桥火车站", "distance_m": 1842, "verification": "reviewed"}], legacy, official)

        self.assertEqual(result, [{"edge_id": "2:station0234:station0223", "distance_m": 1842, "verification": "reviewed"}])


if __name__ == "__main__":
    unittest.main()
