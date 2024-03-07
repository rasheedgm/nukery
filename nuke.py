from parser import Parser
from stack import StackItem
from _base import Node, CloneNode


def open_script(file_path):

    for node_data in Parser.from_file(file_path):
        # print(node_data)
        StackItem(**node_data)


def all_nodes(filter_=None, group=None, recursive=False):
    """

    Args:
        filter_: filter by class
        group:  Not implemented yet
        recursive:

    Returns:

    """
    return StackItem.get_all_nodes(filter_, group, recursive)


def selected_nodes():
    return [n for n in all_nodes() if n["selected"]]


def selected_node():
    selected = selected_nodes()
    return selected[0] if selected else None



file_ = "C:/Users/gmabd/Documents/Feuze/Projects/XYZ/01_Shots/Reel03/sh200/Renders/Render/final_comp/test.nk"


# for nd in Parser.from_file(file_):
#     StackItem(**nd)
#
# si = StackItem.get_stack_items("root")["root.Grade6"]
# print(StackItem.get_stack_items("root"))

open_script(file_)
print(all_nodes("Merge2"))