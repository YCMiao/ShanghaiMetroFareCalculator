import json
import tempfile
import unittest
from pathlib import Path
from scripts.audit_server import resolve

class AuditServerTests(unittest.TestCase):
    def test_resolve_moves_edge_from_audit_to_manual_and_network(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); (root/'data').mkdir()
            (root/'data/distance-audit.json').write_text(json.dumps({'entries':[{'edge_id':'1:A:B'}]}))
            (root/'data/metro-network.json').write_text(json.dumps({'edges':[{'id':'1:A:B','distance_m':None}]}))
            self.assertEqual(resolve(root,'1:A:B',1234),{'remaining':0})
            self.assertEqual(json.loads((root/'data/metro-network.json').read_text())['edges'][0]['distance_m'],1234)
            self.assertEqual(json.loads((root/'data/manual-distances.json').read_text())['entries'][0]['verification'],'reviewed')
