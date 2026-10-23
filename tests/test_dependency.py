import unittest
import bootstrap
import spacy
from spacy.tokens import Doc
from gec.dependency import describe


class DependencyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nlp = spacy.load('en_core_web_sm', disable=['ner', 'lemmatizer'])

    def test_auxiliary_subject_and_exact_token_sequence(self):
        words = ['She', 'does', 'not', 'go', '.']
        doc = self.nlp(Doc(self.nlp.vocab, words=words, spaces=[True]*4 + [False]))
        self.assertEqual([t.text for t in doc], words)
        rows = describe(doc)
        self.assertEqual(rows[3]['subject_text'], 'She')
        self.assertEqual(rows[1]['subject_text'], 'She')
        self.assertEqual(rows[3]['subject_distance'], '-3')
        self.assertEqual(rows[1]['subject_relation'], 'auxiliary_head')

    def test_subject_to_the_right(self):
        words = ['What', 'are', 'our', 'reasons', '?']
        doc = self.nlp(Doc(self.nlp.vocab, words=words, spaces=[True]*4 + [False]))
        row = describe(doc)[1]
        self.assertEqual(row['subject_text'], 'reasons')
        self.assertEqual(row['subject_distance'], '2')


if __name__ == '__main__':
    unittest.main()
