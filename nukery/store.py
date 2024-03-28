import re
from collections import defaultdict, OrderedDict

from nukery.constants import NODE_DEFAULT_INPUTS, NODE_SCRIPT_FORMAT


class SessionStore(object):
    __default__ = "__default__"
    __sessions = {__default__: defaultdict(list)}
    __variable = {__default__: {}}
    _current_session = __default__

    def __init__(self, session):
        self.session = session

    @classmethod
    def append(cls, item):
        cls.get_current()[item.parent].append(item)

    @classmethod
    def remove(cls, item):
        cls.get_current()[item.parent].remove(item)

    @classmethod
    def set_variable(cls, var, item):
        cls.__variable[cls._current_session][var] = item

    @classmethod
    def get_variable(cls, var):
        if var in ("0", 0):
            return None
        return cls.__variable[cls._current_session][var]

    @classmethod
    def get_current(cls):
        return cls.__sessions[cls._current_session]

    @classmethod
    def set_current(cls, session):
        cls._current_session = session

    def __enter__(self):
        self.__class__._current_session = self.session
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.__class__._current_session = self.__default__



class NodeStore(object):
    stack = []
    _current_parent = "root"
    _add_layer = None

    def __init__(self, **kwargs):

        self.type = kwargs.get("type")
        self.node_class = kwargs.get("class")
        self.knobs = kwargs.get("knobs")
        self.user_knobs = kwargs.get("user_knobs", [])
        self.variable = kwargs.get("var", "")
        self.stack_index = kwargs.get("stack_index", "0")
        self.node_content = kwargs.get("node_content", "")
        input_script = kwargs.get("inputs")
        self.parent = self.get_current_parent()

        self.inputs = []
        self.outputs = []
        self.add_layer = None

        if self.type in ("node", "clone"):
            if input_script == "":
                # if there is no inputs script then it mean default input is connected.
                input_count = 1
            elif re.match(r"^[\d]+(?:(?:[\+\s\d]+)$)?", input_script):
                input_count = eval(input_script)
            else:
                raise Exception("input number {0} is unknown, "
                                "please report it to developer".format(input_script))
            for i in range(input_count):
                item = self.stack.pop(0) if self.stack else None
                self.set_input(i, item)

            SessionStore.append(self)
            self.add_to_stack(self)
            if self.is_group:
                self.join_to_parent(self.knobs.get("name"))

        if self.type == "set":
            SessionStore.set_variable(self.variable, self.stack[int(self.stack_index)])
        if self.type == "push":
            self.add_to_stack(SessionStore.get_variable(self.variable))
        if self.type == "end_group":
            self.un_join_last_child()

        if self.__class__._add_layer:
            self.add_layer = self.__class__._add_layer
            self.__class__._add_layer = None

        if self.type == "add_layer":
            self.__class__._add_layer = self.variable

    def to_script(self):
        if self.type == "node":
            if self.is_group:
                node_scripts = [self._get_node_script()]
                nodes_stores = SessionStore.get_current()["{}.{}".format(self.parent, self.name)]
                for item in nodes_stores:
                    node_scripts.append(item.to_script())
                node_scripts.append("end_group")
                return "\n".join(node_scripts)
            else:
                node_script = self._get_node_script()
                if self.add_layer:
                    return "add_layer {0}\n{1}".format(self.add_layer, node_script)
                else:
                    return node_script
        elif self.type == "clone":
            return self._get_node_script(clone=True)

    def _get_node_script(self, clone=False):
        knob_line_format = "{0} {1}"
        knob_lines = []
        if self.input_script != "":
            knob_lines.append("inputs " + self.input_script)
        user_knobs = OrderedDict()
        for n, _id, v in self.user_knobs:
            user_knobs[n] = v
        user_knob_value = {}
        for name, value in self.knobs.items():
            knob_line = knob_line_format.format(name, value)
            if name in user_knobs.keys():
                user_knob_value[name] = value
                continue
            knob_lines.append(knob_line)
        for name, value in user_knobs.items():
            knob_lines.append("addUserKnob " + value)
            if name in user_knob_value.keys():
                knob_lines.append(knob_line_format.format(name, user_knob_value[name]))
        knob_line_script = "\n ".join(knob_lines)
        class_text = "clone ${}".format(self.variable) if clone else self.node_class
        return NODE_SCRIPT_FORMAT.format(class_text, knob_line_script)

    def delete(self):
        print("delete", self.name)
        for out in self.outputs:
            input0 = self.inputs[0] if self.inputs else None
            index = out.inputs.index(self)
            out.set_input(index, input0)
            print("out reset", out.name, out.inputs)

        for input_ in self.inputs:
            if input_:
                input_.remove_output(self)

        SessionStore.remove(self)
        del self

    def set_input(self, index, item):
        print("set input", self.name, index, item)
        input_exists = index < len(self.inputs)
        if input_exists:
            self.inputs.pop(index)
        else:
            for i in range(len(self.inputs), index):
                self.inputs.insert(i, None)
        self.inputs.insert(index, item)

        # if it is None and if last items are none then remove those.
        if item is None and input_exists:
            for i in range(len(self.inputs)-1, -1, -1):
                print(i, index, self.inputs[i])
                if self.inputs[i] is None:
                    self.inputs.pop(i)
                else:
                    break
        if item:
            item.add_output(self)

    def unset_input(self, index):
        item = self.inputs.pop(index)
        # if there are inputs after index then this should be set to None
        if len(self.inputs) > index:
            self.inputs.insert(index, None)
            # if all of next items are none then remove those.
            if all((n is None for n in self.inputs[index:])):
                self.inputs = self.inputs[:index]
        if item:
            item.remove_output(self)

    def add_output(self, item):
        if item not in self.outputs:
            self.outputs.append(item)

    def remove_output(self, item):
        if item in self.outputs:
            self.outputs.remove(item)

    @property
    def name(self):
        return self.knobs.get("name")

    @property
    def input_script(self):
        min_, max_, has_mask = NODE_DEFAULT_INPUTS.get(self.node_class, (0, 0, False))
        input_len = len(self.inputs)
        if has_mask and input_len >= min_:
            return "{0}+1".format(input_len - 1)
        elif input_len == 1:
            return ""
        else:
            return str(input_len)

    @property
    def is_group(self):
        return self.node_class == "Group" or \
                (self.node_class == "LiveGroup" and self.knobs.get("published", "false") == "false")

    @classmethod
    def get_by_name(cls, name):
        return next((item for item in SessionStore.get_current()[cls._current_parent] if item.name == name), None)

    @classmethod
    def add_to_stack(cls, item):
        cls.stack.insert(0, item)

    @classmethod
    def join_to_parent(cls, child):
        cls._current_parent += "." + child

    @classmethod
    def un_join_last_child(cls):
        cls._current_parent = ".".join(cls._current_parent.split(".")[:-1])

    @classmethod
    def set_current_parent(cls, parent):
        cls._current_parent = parent

    @classmethod
    def get_current_parent(cls):
        return cls._current_parent

    def __repr__(self):
        return self.name

