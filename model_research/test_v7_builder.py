"""Check that repository-only rebuilds retain the audited source contract."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import nbformat
import build_v7_evidence as builder


class BuilderChecks(unittest.TestCase):
    def test_rebuild_without_private_downloads(self):
        source=builder.HERE/'Spending_Model_Upload_V6_R3_Kaggle.ipynb'
        before=hashlib.sha256(source.read_bytes()).hexdigest()
        audit=builder.HERE/'evidence/v7_source_audit/v6_verified_audit.json'
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary); (root/'evidence/v7_source_audit').mkdir(parents=True)
            for name in ('v7_features.py','v7_collective.py','v7_runtime.py','v7_recovery.py',
                         'v7_experiments.py','V7_NOTEBOOK_TEXT.md'):
                (root/name).write_bytes((builder.HERE/name).read_bytes())
            output=root/'rebuilt.ipynb'
            with patch.object(builder,'HERE',root),patch.object(builder,'OUTPUT',output):
                builder.build(source,audit_path=audit)
            generated=nbformat.read(output,as_version=4)
            checked=nbformat.read(builder.OUTPUT,as_version=4)
            self.assertEqual(generated.metadata.spendly,checked.metadata.spendly)
            self.assertEqual([c.source for c in generated.cells],[c.source for c in checked.cells])
            changed=nbformat.read(source,as_version=4); changed.cells[0].source+='\nmodified'
            modified=root/'modified.ipynb'; nbformat.write(changed,modified)
            with patch.object(builder,'HERE',root),patch.object(builder,'OUTPUT',output):
                with self.assertRaisesRegex(ValueError,'differs'):
                    builder.build(modified,audit_path=audit)
        self.assertEqual(before,hashlib.sha256(source.read_bytes()).hexdigest())


if __name__=='__main__': unittest.main()
