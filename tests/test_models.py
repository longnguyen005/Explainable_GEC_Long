import unittest
import bootstrap
import numpy as np
from gec.models import decode_lr, decode_knn, select_lr


class SelectionTests(unittest.TestCase):
    def test_total_error_probability_and_best_error_class(self):
        p = np.array([[0.4, 0.3, 0.2, 0.1]])
        self.assertEqual(decode_lr(p, ['O', 'SVA', 'NNUM', 'VFORM'], .55).tolist(), ['SVA'])
        self.assertEqual(decode_lr(p, ['O', 'SVA', 'NNUM', 'VFORM'], .65).tolist(), ['O'])

    def test_near_tie_prefers_smaller_C(self):
        grid = [{'C': 3., 'tau': .65, 'F0.5': .22047, 'P': .301},
                {'C': 1., 'tau': .45, 'F0.5': .22016, 'P': .253},
                {'C': .1, 'tau': .3, 'F0.5': .21505, 'P': .289}]
        chosen, _ = select_lr(grid, .005)
        self.assertEqual(chosen['C'], 1.)

    def test_knn_total_error_fraction_and_fixed_type_tie(self):
        labels = np.array([['SVA', 'NNUM', 'O', 'O']])
        self.assertEqual(decode_knn(labels, 4, .5).tolist(), ['SVA'])
        self.assertEqual(decode_knn(labels, 4, .75).tolist(), ['O'])


if __name__ == '__main__':
    unittest.main()
