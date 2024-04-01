import unittest
from collections import OrderedDict
from nukery.parser import NukeScriptParser

class TestPaser(unittest.TestCase):

    def test_from_file(self):
        file_ = "" # TODO set this
        expected_result = [] # TODO set this
        result = list(NukeScriptParser.from_file(file_))

        self.assertEqual(expected_result, result)