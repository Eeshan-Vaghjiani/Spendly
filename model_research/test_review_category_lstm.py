"""Review harness tests; candidate probes require the supplied hash-pinned file."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import review_category_lstm as review


class ReviewTests(unittest.TestCase):
    def test_unreviewed_notebook_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'notebook.ipynb'
            path.write_text('{"cells": []}')
            with self.assertRaisesRegex(ValueError, 'differs'):
                review.inspect(path)

    def test_synthetic_history_is_ordered_and_disjoint(self):
        frame = review.fixture()
        self.assertEqual(frame.user_id.nunique(), 2)
        self.assertFalse(frame.duplicated(['user_id', 'week']).any())
        self.assertTrue(frame.groupby('user_id').week.apply(lambda s: s.is_monotonic_increasing).all())

    def test_no_dynamic_notebook_top_level_execution(self):
        import json
        code = 'raise AssertionError("top-level must never run")\n'
        code += '\n'.join(f'def {name}(): pass' for name in sorted(review.FUNCTIONS))
        raw = json.dumps({'cells': [{'cell_type': 'code', 'source': [code]}]}).encode()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'fixture.ipynb'
            path.write_bytes(raw)
            with patch.object(review, 'NOTEBOOK_SHA', review.hashlib.sha256(raw).hexdigest()):
                _, ns, parsed = review.inspect(path)
        self.assertEqual(parsed, 1)
        self.assertTrue(review.FUNCTIONS <= ns.keys())


if __name__ == '__main__':
    unittest.main()
