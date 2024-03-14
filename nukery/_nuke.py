from nukery.parser import NukeScriptParser
from nukery.stack import StackItem, StackStore


def open_script(file_path):
    for node_data in NukeScriptParser.from_file(file_path):
        StackItem(**node_data)


def all_nodes(filter_=None, group=None, recursive=False):
    """

    Args:
        filter_: filter by class
        group:  Not implemented yet
        recursive:

    Returns:

    """
    return StackStore.get_all_nodes(filter_, group, recursive)


def selected_nodes():
    return [n for n in all_nodes() if n["selected"]]


def selected_node():
    selected = selected_nodes()
    return selected[0] if selected else None


def save_script_as(file_path):
    script = []
    for stack in StackStore.get_stack_items("root"):
        script.append(stack)
    with open(file_path, "w") as f:
        f.write("\n".join(script))

    return True
