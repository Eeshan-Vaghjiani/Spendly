import unittest
import pandas as pd
from analyze_alert_results import event_counts


class EventChecks(unittest.TestCase):
    def test_valid_and_missing_event_ids(self):
        f=pd.DataFrame(dict(events_with_ids=[52,0],event_recall=[6/52,float('nan')]))
        self.assertEqual(event_counts(f).tolist(),[6.,0.])

    def test_impossible_event_counts_rejected(self):
        for support,recall in [(52,2.),(52,-.1),(-1,0.),(1.5,1.)]:
            with self.assertRaises(ValueError):
                event_counts(pd.DataFrame(dict(events_with_ids=[support],event_recall=[recall])))


if __name__=='__main__':unittest.main()
