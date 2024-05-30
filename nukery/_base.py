from nukery.constants import CLONE_KNOBS
from nukery.store import NodeStore, SessionStore


class Node(object):

    def __init__(self, class_=None, knobs=None, user_knobs=None, node_store=None):
        if node_store:
            self.node_store = node_store
        else:
            node_data = {
                "type": "node",
                "class": class_,
                "knobs": knobs,
                "user_knobs": user_knobs,
                "inputs": "",
            }
            self.node_store = NodeStore(**node_data)

    @property
    def name(self):
        return self["name"]

    @property
    def full_name(self):
        return "{0}.{1}".format(self.parent, self.name)

    @property
    def selected(self):
        return self.node_store.knobs.get("selected", "false") == "true"

    @property
    def parent(self):
        return self.node_store.parent

    def knobs(self):
        return self.node_store.knobs

    def knob(self, name):
        return self[name]

    def get_class(self):
        return self.node_store.node_class

    def get_inputs(self):
        return self.node_store.inputs

    def input(self, index):
        if len(self.node_store.inputs) <= index:
            return None
        return self.node_store.inputs[index]

    def get_outputs(self):
        return self.node_store.outputs

    def set_input(self, index, node):
        self.node_store.set_input(index, node.node_store)

    def set_name(self, name):
        self["name"] = name

    def set_xpos(self, value):
        self["xpos"] = str(value)

    def set_ypos(self, value):
        self["ypos"] = str(value)

    def set_xypos(self, x, y):
        self.set_xpos(x)
        self.set_ypos(y)

    def set_selected(self, value=True):
        if not isinstance(value, bool):
            raise ValueError("value has to be bool")
        if value:
            self.node_store.knobs["selected"] = "true"
        else:
            self.node_store.knobs.pop("selected", None)

    def __setitem__(self, key, value):
        if key == "name":
            ns = self.node_store.get_by_name(value)
            if ns == self.node_store:
                return
            if ns:
                raise Exception("Node name already exists")

        if self.node_store.type == "clone":
            if key not in CLONE_KNOBS:
                original = SessionStore.get_variable(self.node_store.variable)
                original.knobs[key] = value
                return True

        self.node_store.knobs[key] = value

    def __getitem__(self, item):
        if self.node_store.type == "clone":
            if item not in self.node_store.knobs:
                original = SessionStore.get_variable(self.node_store.variable)
                return original.knobs.get(item)
        return self.node_store.knobs.get(item)

    def __enter__(self):  # TODO test this
        if self.node_store.is_group:
            NodeStore.set_current_parent("{0}.{1}".format(self.parent, self.name))
            return self
        else:
            raise TypeError("Context is only available with group nodes.")

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.node_store.is_group:
            NodeStore.un_join_last_child()

    def __repr__(self):
        mem = hex(id(self))
        if self.node_store.type == "clone":
            return "<Clone({0}) at {1}>".format(self.name, mem)
        elif self.node_store.node_class == "Root":
            return "<Root at {0}>".format(mem)
        return "<Node({0}) at {1}>".format(self.name, mem)
