from nukery.parser import NukeScriptParser
from nukery.session import StackItem, SessionStore


def script_open(file_path):
    if SessionStore.get_current().has_value():
        raise Exception("Script already open")

    for node_data in NukeScriptParser.from_file(file_path):
        StackItem(**node_data)

    SessionStore.set_modified(False, set_all=True)


def script_clear():
    """clear script"""
    SessionStore.get_current().clear()
    SessionStore.set_modified(False, set_all=True)


def all_nodes(filter_=None, group=None, recursive=False):
    """

    Args:
        filter_: filter by class
        group:  Not implemented yet
        recursive:

    Returns:

    """
    return SessionStore.get_all_nodes(filter_, group, recursive)


def to_node(name):
    return SessionStore.get_node_by_name(name)


def selected_nodes():
    selected = []
    for stack in SessionStore.get_stack_items(StackItem.get_current_parent()):
        node = stack.node()
        if node and node["selected"] in (True, "true"):
            selected.append(node)
    return selected


def selected_node():
    for stack in reversed(SessionStore.get_stack_items(StackItem.get_current_parent())):
        node = stack.node()
        if node and node["selected"] in (True, "true"):
            return node


def clear_selection():
    for node in selected_nodes():
        node.set_selected(False)


def save_script_as(file_path):
    script = []
    for stack in SessionStore.get_stack_items("root"):
        script.append(stack)
    with open(file_path, "w") as f:
        f.write("\n".join(script))

    return True


def get_script_text(selected=False):
    """Returns script text"""
    node_stack = []
    current_stack = SessionStore.get_stack_items(StackItem.get_current_parent())
    for stack in current_stack:
        if stack.type in ("node", "clone"):
            if selected:
                if stack.node()["selected"] not in (True, "true"):
                    continue
            if stack.index != 0 and current_stack[stack.index - 1].type == "add_layer":
                node_stack.append(current_stack[stack.index - 1])
            node_stack.append(stack)
    full_stacks = SessionStore.build_stack_from_list(node_stack)
    node_scripts = []
    for stack in full_stacks:
        node_scripts.append(stack.to_script())

    return "\n".join(node_scripts) + "\n"


def node_copy(s):
    """Save selected node to file or clipboard"""

    if not selected_node():
        raise Exception("No node selected")

    copy_script = get_script_text(selected=True)
    if s in ("clipboard", "%clipboard%"):
        return NotImplemented
        # import platform
        # import subprocess
        # if platform.system() == "Darwin":
        #     cmd = 'echo "' + copy_script + '"|pbcopy'
        # else:
        #     cmd = 'echo "' + copy_script + '"|clip'
        # subprocess.check_call(cmd, shell=True)
        # print("Nodes copied to clipboard")
    else:
        with open(s, "w") as f:  # TODO test
            f.write(copy_script)

    return True


def delete(node):
    """Delete node """
    # when delete handle inputs as nuke does
    return NotImplemented


def node_paste(s):
    """Paste node from file or clipboard"""
    # parse it and add to stack
    return NotImplemented


def create_node(node_class, **kwargs):
    """Create node"""
    _selected = selected_node()
    clear_selection()  # TODO check if this is time taking
    last_node = _selected
    inputs = ""
    if not _selected:
        current_stacks = SessionStore.get_stack_items(StackItem.get_current_parent())
        if current_stacks:
            last_stack = current_stacks[-1]
            last_node = last_stack.get_linked_stack().node()
        inputs = "0"
    if last_node:
        if not kwargs.get("ypos"):
            kwargs["ypos"] = str(int(last_node["ypos"]) + 50)

        if not kwargs.get("xpos"):
            kwargs["xpos"] = last_node["xpos"]
    else:
        if not kwargs.get("ypos"):
            kwargs["ypos"] = "0"

        if not kwargs.get("xpos"):
            kwargs["xpos"] = "0"

    if not kwargs.get("name"):
        kwargs["name"] = "{0}1".format(node_class)

    kwargs["selected"] = kwargs.get("selected", "true")

    stack_data = {
        "type": "node",
        "class": node_class,
        "knobs": kwargs,
        "inputs": inputs,

    }
    item = StackItem(**stack_data)
    node = item.node()
    if node.is_group:
        inputs_node = {
            "type": "node",
            "class": "Input",
            "knobs": {
                "xpos": "0",
            },
            "inputs": "0",
        }
        StackItem(**inputs_node)
        outputs_node = {
            "type": "node",
            "class": "Output",
            "knobs": {
                "xpos": "0",
                "ypos": "300"
            },
            "inputs": "",
        }
        StackItem(**outputs_node)
        end_group = {
            "type": "end_group",
            "class": "",
        }
        StackItem(**end_group)

    return node


