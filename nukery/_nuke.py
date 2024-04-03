import platform
import subprocess

from nukery.parser import NukeScriptParser
from nukery.store import SessionStore, NodeStore
from nukery._base import Node


def script_open(file_path):
    """ Open file in to the session.

    Args:
        file_path(str): nuke file path.

    """
    if SessionStore.has_value():
        raise Exception("Script already open")

    for node_data in NukeScriptParser.from_file(file_path):
        NodeStore(**node_data)


def script_clear():
    """ Clear script"""
    SessionStore.clear()  # TOOD test


def all_nodes(filter_=None, group=None, recursive=False):
    """ Get all nodes from the session.

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
            if node_store.node_class == "Root":
                continue
            if filter_ and node_store.node_class != filter_:
                continue
            node = Node(node_store=node_store)
            nodes.append(node)
    return nodes


def to_node(name):
    """ Get node object by name, node will search in the context and the session
    """
    node_store = NodeStore.get_by_name(name)
    if node_store:
        return Node(node_store=node_store)


def select_all():
    """ Set all nodes to selected.
    """
    for node_store in SessionStore.get_current()[NodeStore.get_current_parent()]:
        if node_store.node_class == "Root":
            continue
        node = Node(node_store=node_store)
        if node and node["selected"] not in (True, "true"):
            node.set_selected(True)


def selected_nodes():
    """ Get selected nodes from the session and the context.

    Returns:
        list: list of Nodes
    """
    selected = []
    for node_store in SessionStore.get_current()[NodeStore.get_current_parent()]:
        node = Node(node_store=node_store)
        if node and node["selected"] in (True, "true"):
            selected.append(node)
    return selected


def selected_node():
    """Select last selected node(this last by store session,
    does not promise returning node that last selected
    """
    for node_store in reversed(SessionStore.get_current()[NodeStore.get_current_parent()]):
        node = Node(node_store=node_store)
        if node and node["selected"] in (True, "true"):
            return node


def clear_selection():
    """ Clear current selection """
    for node in selected_nodes():
        node.set_selected(False)


def save_script_as(file_path):
    """ Save current session to a file."""
    script = SessionStore.build_script("root")
    with open(file_path, "w") as f:
        f.write(script)

    return True


def delete(node):
    """Delete a node """
    node.node_store.delete()


def get_script_text(selected=False):
    """ Returns script text.

    Args:
        selected(bool): if true then script text for selected node will be returned
    """
    node_stores = []
    current_nodes = SessionStore.get_current()[NodeStore.get_current_parent()]
    if selected:
        for node_store in current_nodes:
            if node_store.type in ("node", "clone"):
                if node_store.knobs.get("selected", "false") == "false":
                    continue
                node_stores.append(node_store)
    else:
        node_stores = current_nodes.copy()

    return SessionStore.build_script_from_list(node_stores)


def node_copy(file_name=None):
    """Save selected node to file or clipboard

    Args:
        file_name(str): file name to save, if None the script text will be copied to clipboard
    """

    if not selected_node():
        raise Exception("No node selected")

    copy_script = get_script_text(selected=True)
    if file_name is None:
        system_os = platform.system()
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
    """Paste node from file or clipboard

    Args:
        file_name(str): file path to import node from,
                        if this is None then will try to import form clipboard
    """
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
    """Create a node

    Args:
        node_class(str): class for the node to create
    Keyword Args:
        knobs can be initialized by passing as key word args
    """
    _selected = selected_node()
    _selected = selected_node().node_store if _selected else None
    clear_selection()  # TODO check if this is time taking
    last_node = _selected
    inputs = ""
    current_stack = SessionStore.get_current_stack()[NodeStore.get_current_parent()]
    # if no selected nodes then we need node from stack to set x,y pos.
    if not _selected:
        last_node = current_stack[0] if current_stack else None
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

    #  if selected node is not in the current stack add it to the stack.
    if _selected and current_stack and _selected != current_stack[0]:
        current_stack.insert(0, _selected)

    if not node_class == "Root":
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
    """Get Root nodes."""

    node_store = NodeStore.get_by_class("Root")
    if node_store:
        return Node(node_store=node_store)
    else:
        current_parent = NodeStore.get_current_parent()
        NodeStore.set_current_parent("root")
        node = create_node("Root")
        NodeStore.set_current_parent(current_parent)
        return node
