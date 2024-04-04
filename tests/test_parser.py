import os
import unittest
from collections import OrderedDict
from nukery.parser import NukeScriptParser

import pickle


class TestPaser(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(TestPaser, self).__init__(*args, **kwargs)
        self.file_path = os.path.join(os.path.dirname(__file__), "files/test_file.nk")
        self.result_file = os.path.join(os.path.dirname(__file__), "files/parser_result.pkl")

    def test_from_file(self):
        file_ = "" # TODO set this
        with open(self.result_file,  'rb') as f:
            expected_result = pickle.load(f)

        result = list(NukeScriptParser.from_file(self.file_path))

        self.assertEqual(expected_result, result)