import unittest
from pathlib import Path
from unittest.mock import patch
import bootstrap
from gec.data import load_file


class DevelopmentSafetyTests(unittest.TestCase):
    def test_data_loader_rejects_test_before_opening_file(self):
        with patch.object(Path, 'read_text', side_effect=AssertionError('Must not open')):
            with self.assertRaises(ValueError):
                load_file('data/json/test.json', 'test')


if __name__ == '__main__':
    unittest.main()
