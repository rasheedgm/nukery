import platform
import subprocess

from nukery.parser import NukeScriptParser
from nukery.store import SessionStore, NodeStore
from nukery._base import Node


def script_open(file_path):
    if SessionStore.has_value():
        raise Exception("Script already open")

    for node_data in NukeScriptParser.from_file(file_path):
        NodeStore(**node_data)


def script_clear():
    """clear script"""
    SessionStore.get_current().clear() # TOOD test


def all_nodes(filter_=None, group=None, recursive=False):
    """

    Args:
        filter_: filter by class
        group:  name of the group, root.Group1
        recursive: if true return node recursively form child groups

    Returns:
        list(Nodes) : Return list of nodes.
    """
    nodes = []
    if group and not group.startswith("root"):
        group = "root." + group
    parent = group if group else NodeStore.get_current_parent()
    parent_keys = [parent]
    if recursive:
        parent_keys = [k for k in SessionStore.get_current().keys() if k.startswith(parent)]
    for parent_key in parent_keys:
        for node_store in SessionStore.get_current()[parent_key]:
            if filter_ and node_store.node_class != filter_:
                continue
            node = Node(node_store=node_store)
            nodes.append(node)
    return nodes


def to_node(name):
    node_store = NodeStore.get_by_name(name)
    if node_store:
        return Node(node_store=node_store)


def select_all():
    for node_store in SessionStore.get_current()[NodeStore.get_current_parent()]:
        node = Node(node_store=node_store)
        if node and node["selected"] not in (True, "true"):
            node.set_selected(True)


def selected_nodes():
    selected = []
    for node_store in SessionStore.get_current()[NodeStore.get_current_parent()]:
        node = Node(node_store=node_store)
        if node and node["selected"] in (True, "true"):
            selected.append(node)
    return selected


def selected_node():
    for node_store in reversed(SessionStore.get_current()[NodeStore.get_current_parent()]):
        node = Node(node_store=node_store)
        if node and node["selected"] in (True, "true"):
            return node


def clear_selection():
    for node in selected_nodes():
        node.set_selected(False)


def save_script_as(file_path):
    script = SessionStore.build_script("root")
    with open(file_path, "w") as f:
        f.write(script)

    return True


def delete(node):
    """Delete node """
    SessionStore.remove(node.node_store)
    del node


def get_script_text(selected=False):
    """Returns script text"""
    node_stores = []
    current_nodes = SessionStore.get_current()[NodeStore.get_current_parent()]
    for node_store in current_nodes:
        if node_store.type in ("node", "clone"):
            if selected:
                if node_store.knobs.get("selected", "false") == "false":
                    continue
            node_stores.append(node_store)

    return SessionStore.build_script_from_list(node_stores)


def node_copy(file_name=None):
    """Save selected node to file or clipboard"""

    if not selected_node():
        raise Exception("No node selected")

    copy_script = get_script_text(selected=True)
    if file_name is None:
        system_os = platform.system()
        # windows
        if system_os == 'Windows':
            cmd = 'clip'
        elif system_os == 'Darwin':
            cmd = 'pbcopy'
        else:
            cmd = ['xclip', '-selection', 'c']
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            close_fds=True
        )
        res, error = process.communicate(input=copy_script.encode('utf-8'))
        if error:
            raise Exception("Error copying to clipboard")
    else:
        with open(file_name, "w") as f:  # TODO test
            f.write(copy_script)

    return True


def node_paste(file_name=None):
    """Paste node from file or clipboard"""
    if file_name is None:
        system_os = platform.system()
        # windows
        if system_os == 'Windows':
            cmd = ['powershell', 'Get-Clipboard']
        elif system_os == 'Darwin':
            cmd = ['pbpaste']
        else:
            cmd = ['xclip', '-selection', 'clipboard', '-out', '-nonewline']

        process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        result,  error = process.communicate()
        if error:
            raise Exception("Error copying to clipboard")

        script = result.decode('utf-8')

    else:
        with open(file_name, "r") as f:
            script = f.read()

    nodes = []
    for node_data in NukeScriptParser.from_text(script):
        node_store = NodeStore(**node_data)
        nodes.append(Node(node_store=node_store))

    return nodes


def create_node(node_class, **kwargs):
    """Create node"""
    _selected = selected_node()
    _selected = selected_node().node_store if _selected else None
    clear_selection()  # TODO check if this is time taking
    last_node = _selected
    inputs = ""
    if not _selected:
        last_node = NodeStore.stack[0] if NodeStore.stack else None
        inputs = "0"
    if last_node:
        if not kwargs.get("ypos"):
            kwargs["ypos"] = str(int(last_node.knobs.get("ypos", "0")) + 50)

        if not kwargs.get("xpos"):
            kwargs["xpos"] = last_node.knobs.get("xpos", "0")
    else:
        if not kwargs.get("ypos"):
            kwargs["ypos"] = "0"

        if not kwargs.get("xpos"):
            kwargs["xpos"] = "0"

    NodeStore.add_to_stack(_selected)

    kwargs["selected"] = kwargs.get("selected", "true")

    stack_data = {
        "type": "node",
        "class": node_class,
        "knobs": kwargs,
        "inputs": inputs,

    }
    node_store = NodeStore(**stack_data)
    node = Node(node_store=node_store)
    if node_store.is_group:
        inputs_node = {
            "type": "node",
            "class": "Input",
            "knobs": {
                "xpos": "0",
            },
            "inputs": "0",
        }
        NodeStore(**inputs_node)
        outputs_node = {
            "type": "node",
            "class": "Output",
            "knobs": {
                "xpos": "0",
                "ypos": "300"
            },
            "inputs": "",
        }
        NodeStore(**outputs_node)
        end_group = {
            "type": "end_group",
            "class": "",
        }
        NodeStore(**end_group)

    return node


def root():
    node_store = NodeStore.get_by_class("Root")
    if node_store:
        return Node(node_store=node_store)
    else:
        current_parent = NodeStore.get_current_parent()
        NodeStore.set_current_parent("root")
        node = create_node("Root")
        NodeStore.set_current_parent(current_parent)
        return node
