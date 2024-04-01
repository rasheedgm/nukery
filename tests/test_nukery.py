import unittest
import nukery


class TestNukery(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(TestNukery, self).__init__(*args, **kwargs)
        self.file_path = ""



    def test_script_open(self):
        nukery.script_open(self.file_path)
        self.all_nodes = nukery.all_nodes()
        nukery.script_clear()
        self.assertTrue(self.all_nodes)


    def test_all_nodes(self):
        expected_root_names = set(("Grade1", "Transform1", "Group1"))
        expected_group1 = set(["Input1", "Grade2", "Output1"])
        expected_recursive = expected_root_names.union(expected_group1)

        nukery.script_open(self.file_path)
        result_root = set([n.name for n in nukery.all_nodes()])
        result_recursive = set([n.name for n in nukery.all_nodes(recursive=True)])
        result_group1 = set([n.name for n in nukery.all_nodes(group="root.Group1")])
        nukery.script_clear()
        self.assertEqual(expected_root_names, result_root)
        self.assertEqual(expected_group1, result_group1)
        self.assertEqual(expected_recursive, result_recursive)


    def test_selected_node(self):
        pass