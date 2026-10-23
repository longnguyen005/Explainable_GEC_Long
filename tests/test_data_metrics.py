import unittest
import bootstrap
from legacy_source.audit_counts import decode_record
from gec.metrics import score, checked


class AlignmentTests(unittest.TestCase):
    def test_multi_token_to_fly_excluded(self):
        raw = {'source': ['To', 'fly', 'is', 'easy', '.'],
               'target': ['Flying', 'is', 'easy', '.'],
               'correction_index': [0, 5, 6], 'error_type': 'Gerund'}
        row = decode_record(raw, 'train', 1)
        self.assertFalse(row['retained'])
        self.assertTrue(row['legacy_retained'])
        self.assertEqual(row['source_positions_clean_0based'], [0, 1])

    def test_placeholder_projection(self):
        raw = {'source': ['She', '[NONE]', 'go'], 'target': ['She', 'can', 'go'],
               'correction_index': [1, 5], 'error_type': 'Auxiliary Verb'}
        row = decode_record(raw, 'dev', 1)
        self.assertEqual(row['clean_source_tokens'], ['She', 'go'])
        self.assertEqual(row['labels_after_filter'], ['O', 'O'])
        self.assertEqual(row['source_gap_positions_clean_0based'], [1])

    def test_one_to_one_source_position(self):
        raw = {'source': ['She', 'go'], 'target': ['She', 'goes'],
               'correction_index': [1, 4], 'error_type': 'Subject-Verb Agreement'}
        row = decode_record(raw, 'dev', 1)
        self.assertEqual(row['labels_after_filter'], ['O', 'SVA'])


class MetricsTests(unittest.TestCase):
    def test_wrong_type_is_one_untyped_tp(self):
        rows = score('sample', ['SVA', 'NNUM', 'O'], ['NNUM', 'O', 'VFORM'])
        typed, untyped = rows[-2:]
        self.assertEqual((typed['TP'], typed['FP'], typed['FN']), (0, 2, 2))
        self.assertEqual((untyped['TP'], untyped['FP'], untyped['FN']), (1, 1, 1))

    def test_all_O_and_empty(self):
        for yt, yp in [(['O'], ['O']), ([], [])]:
            self.assertEqual(score('sample', yt, yp)[-2]['F0.5'], 0)

    def test_perfect_and_false_negative(self):
        self.assertEqual(score('perfect', ['SVA'], ['SVA'])[-2]['F0.5'], 1)
        self.assertEqual(score('miss', ['SVA'], ['O'])[-2]['FN'], 1)

    def test_reject_length_and_unknown_labels(self):
        with self.assertRaises(ValueError):
            checked(['O', 'SVA'], ['O'])
        with self.assertRaises(ValueError):
            checked(['O'], ['BAD'])


if __name__ == '__main__':
    unittest.main()
