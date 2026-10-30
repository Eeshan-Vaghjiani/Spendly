import unittest
from analyze_v9_results import validate_final_records


class FinalCoverageChecks(unittest.TestCase):
    def test_expected_set(self):
        self.assertEqual(validate_final_records([{'candidate':'a'},{'candidate':'b'}],{'a','b'}),2)

    def test_missing_duplicate_extra_rejected(self):
        for names in ([],['a'],['a','a'],['a','b','c']):
            with self.assertRaises(ValueError):
                validate_final_records([{'candidate':n} for n in names],{'a','b'})


if __name__=='__main__':unittest.main()
