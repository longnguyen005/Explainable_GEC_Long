import unittest
import bootstrap
from summarize_reviews import parse_raw_sheet, read_rows
from gec.io_utils import read_json


class ReviewStandardizationTests(unittest.TestCase):
    def test_raw_sheets_match_reference_and_status_metrics(self):
        ref_dir = bootstrap.ROOT / 'outputs/dev_run_001/baseline_ref'
        reference = read_rows(ref_dir / 'fp_reference.csv')
        self.assertEqual(len(reference), 63)

        loan = parse_raw_sheet(ref_dir / 'raw_TV1_Loan.csv', reference)
        yen = parse_raw_sheet(ref_dir / 'raw_TV2_Yen.csv', reference)
        self.assertEqual(len(loan), 63)
        self.assertEqual(len(yen), 63)
        self.assertEqual(loan[0]['reviewer'], 'VŨ THỊ LOAN')
        self.assertEqual(yen[0]['reviewer'], 'MAI HẢI YẾN')

        status = read_json(ref_dir / 'review_status.json')
        self.assertTrue(status['independent_reviews_complete'])
        self.assertTrue(status['consensus_complete'])
        self.assertEqual((status['A'], status['B'], status['C']), (34, 14, 15))
        self.assertEqual(status['B_in_scope_3_types'], 10)
        self.assertEqual(status['B_out_of_scope'], 4)
        self.assertAlmostEqual(status['estimated_precision_in_scope_3_types'], 40 / 93, places=12)
        self.assertAlmostEqual(status['estimated_precision'], 44 / 93, places=12)
        self.assertAlmostEqual(status['assumption_upper_bound_in_scope_3_types'], 55 / 93, places=12)
        self.assertAlmostEqual(status['assumption_upper_bound'], 59 / 93, places=12)


if __name__ == '__main__':
    unittest.main()
