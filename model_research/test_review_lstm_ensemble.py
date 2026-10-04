import unittest

import numpy as np
import pandas as pd

from review_lstm_ensemble import SEEDS, align, compare


def fixtures():
    base = pd.DataFrame({'user_id': ['a']*3+['b']*3,
                         'target_week': ['2022-01-03', '2022-01-10', '2022-01-17']*2,
                         'fold': [0]*3+[1]*3, 'actual': [100., 200., 300.]*2,
                         'recurring_median': [100., 200., 300.]*2, 'candidate': 'v6_reference'})
    frames = {}
    for seed, offset in zip(SEEDS, (-30., 0., 30.)):
        frames[seed] = base.assign(seed=seed, prediction=base.actual+offset,
                                   residual=offset, absolute_error=abs(offset))
    return frames


class EnsembleReviewTests(unittest.TestCase):
    def test_known_average_metrics_and_user_interval(self):
        report = compare(fixtures())
        self.assertEqual(report['metrics']['ensemble']['WAPE'], 0.)
        self.assertEqual(report['metrics']['seed_42']['MAE_KES'], 30.)
        self.assertEqual(report['gain_vs_seed42_WAPE_pp'], 15.)
        np.testing.assert_allclose(report['ensemble_minus_seed42_WAPE_pp_95'], [-15., -15.])

    def test_alignment_handles_shuffled_rows(self):
        frames = fixtures()
        expected = align(frames)
        frames[123] = frames[123].sample(frac=1, random_state=42)
        pd.testing.assert_frame_equal(align(frames), expected)

    def test_missing_duplicate_and_mismatched_target_rejected(self):
        frames = fixtures()
        frames[123] = frames[123].iloc[:-1]
        with self.assertRaises(ValueError):
            align(frames)
        frames = fixtures()
        frames[123] = pd.concat([frames[123], frames[123].iloc[[0]]])
        with self.assertRaises(ValueError):
            align(frames)
        frames = fixtures()
        frames[123].loc[0, ['actual', 'prediction']] += 1
        with self.assertRaises(AssertionError):
            align(frames)

    def test_wrong_seed_nonfinite_and_fold_leakage_rejected(self):
        for column, value in [('seed', 999), ('prediction', np.inf), ('actual', -1.)]:
            frames = fixtures()
            frames[42].loc[0, column] = value
            with self.subTest(column=column), self.assertRaises((ValueError, AssertionError)):
                align(frames)
        frames = fixtures()
        frames[42].loc[0, 'fold'] = 2
        with self.assertRaises(ValueError):
            align(frames)


if __name__ == '__main__':
    unittest.main()
