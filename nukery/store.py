import re
from collections import defaultdict, OrderedDict
from copy import deepcopy
import random

from nukery.constants import NODE_DEFAULT_INPUTS, NODE_SCRIPT_FORMAT


class SessionStore(object):
    __default__ = "__default__"
    __sessions = {__default__: defaultdict(list)}
    __variable = {__default__: {}}
    _current_session = __default__

    def __init__(self, session):
        self.session = session
        if self.session not in self.__sessions.keys():
            self.__class__.__sessions[self.session] = defaultdict(list)
            self.__class__.__variable[self.session] = {}

    @classmethod
    def append(cls, item):
        cls.get_current()[item.parent].append(item)

    @classmethod
    def remove(cls, item):
        cls.get_current()[item.parent].remove(item)

    @classmethod
    def has_value(cls):
        return any(s for s in cls.get_current().values())

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

    @classmethod
    def build_script(cls, parent=None):
        if parent is None:
            parent = NodeStore.get_current_parent()
        return cls.__build_script(cls.get_current()[parent])

    @classmethod
    def build_script_from_list(cls, stack_list):
        return cls.__build_script(stack_list)

    @classmethod
    def __build_script(cls, node_store_list):
        """Stacks are not ordered if there are any changes made, so if changes needs to be rebuilt
        call this, this will rebuild the stack and return the new stack items.
        """
        node_store_list = deepcopy(node_store_list)
        _instance_copy = []
        _all = []
        _duplicates = {}
        _variables = defaultdict(str)
        _add_layers = {}
        _end_group = None
        _root_item = None
        for var, item in cls.__variable[cls._current_session].items():
            _variables[item] = var
        _stacks = []
        for node_store in reversed(node_store_list):
            if node_store.node_class == "Root":
                _root_item = node_store
                continue

            _all.append(node_store)
            _instance_copy.extend(node_store.inputs)

        _duplicates = {v: _instance_copy.count(v) for v in _all}

        _bottom_stack = [item for item in _all if _duplicates[item] == 0]
        last_item = _bottom_stack.pop(0)
        _new_stacks_list = []
        while last_item is not False:
            push_item = None
            if last_item is None:
                push_item = "push 0"
                _new_stacks_list.insert(0, push_item)
            elif _duplicates[last_item] > 1:
                var = _variables[last_item]
                if not var:
                    var = _variables[last_item] = cls.get_random_variable_name()
                push_item = "push ${0}".format(var)
                _new_stacks_list.insert(0, push_item)
                if _duplicates[last_item] == 2:
                    _duplicates[last_item] = -1

                else:
                    _duplicates[last_item] -= 1
            else:
                if _duplicates[last_item] == -1:
                    var = _variables[last_item]
                    set_item = "set {0} [stack 0]".format(var)
                    _new_stacks_list.insert(0, set_item)
                elif last_item in _variables:
                    var = _variables[last_item]
                    if var.startswith("C"):
                        set_item = "set {0} [stack 0]".format(var)
                        _new_stacks_list.insert(0, set_item)
                _new_stacks_list.insert(0, last_item.to_script())

            if push_item is None and last_item:
                _inputs = last_item.inputs
                for _input in _inputs:
                    if _input not in node_store_list:
                        _inputs.remove(_input)
                _stacks = _inputs + _stacks

            if _stacks:
                last_item = _stacks.pop(0)
            elif _instance_copy:
                if _bottom_stack:
                    last_item = _bottom_stack.pop(0)
                else:
                    last_item = False
            else:
                last_item = False

        if _root_item:
            _new_stacks_list.insert(0, _root_item.to_script())

        return "\n".join(_new_stacks_list)

    @classmethod
    def get_random_variable_name(cls, prefix="N"):
        var = prefix + ''.join(random.choice("0123456789abcdef") for _ in range(8))

        if var in cls.__variable[cls._current_session].keys():
            return cls.get_random_variable_name(prefix)
        else:
            return var

    def __enter__(self):
        self.__class__._current_session = self.session
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.__class__._current_session = self.__default__

    def __del__(self):
        self.__class__.__sessions[self.session] = defaultdict(list)
        self.__class__.__variable[self.session] = {}


class NodeStore(object):
    stack = defaultdict(list)
    _current_parent = "root"
    _add_layer = None
    _name_pattern = re.compile("^(.*?)(\d+)?$")

    def __init__(self, **kwargs):

        self.type = kwargs.get("type")
        self.node_class = kwargs.get("class")
        self.knobs = kwargs.get("knobs", {})
        self.user_knobs = kwargs.get("user_knobs", [])
        self.variable = kwargs.get("var", "")
        self.stack_index = kwargs.get("stack_index", "0")
        self.node_content = kwargs.get("node_content", "")
        input_script = kwargs.get("inputs")
        self.parent = self.get_current_parent()

        self.inputs = []
        self.outputs = []
        self.add_layer = None

        if self.type == "node" and self.knobs.get("name") is None:
            self.knobs["name"] = "{0}1".format(self.node_class)

        # if node name exists in this context increment the name suffix
        if self.type == "node" and self.get_by_name(self.name):
            name, _ = self._name_pattern.match(self.name).groups()
            node_numbers = set()

            for item in SessionStore.get_current()[self.parent]:
                item_name = item.name
                match = self._name_pattern.match(item_name)
                _name, _number = match.groups() if match else (None, None)
                if _number is not None and _name == name:
                    node_numbers.add(int(_number))

            number_range = set(range(1, max(node_numbers) + 2))
            missing = number_range - node_numbers
            number = min(missing)
            self.knobs["name"] = "{0}{1}".format(name, number)

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
                item = self.stack[self.parent].pop(0) if self.stack[self.parent] else None
                self.set_input(i, item)

            SessionStore.append(self)
            self.add_to_stack(self)
            if self.is_group:
                self.join_to_parent(self.name)

        if self.type == "set":
            if self.parent in self.stack:
                stack_item = self.stack[self.parent][int(self.stack_index)]
            else:
                stack_item = None
            SessionStore.set_variable(self.variable, stack_item)
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
        for out in self.outputs:
            input0 = self.inputs[0] if self.inputs else None
            index = out.inputs.index(self)
            out.set_input(index, input0)

        for input_ in self.inputs:
            if input_:
                input_.remove_output(self)

        SessionStore.remove(self)
        del self

    def set_input(self, index, item):
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
        if self.type == "clone":
            original = SessionStore.get_variable(self.variable)
            return original.name
        elif self.type != "node":
            return self.type.title()

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

        if "." in name:
            parent = ".".join(name.split(".")[:-1])
            name = name.split(".")[-1]
        else:
            if name == "root":  # TODO not working
                parent = "root"
            else:
                parent = cls._current_parent

        return next((item for item in SessionStore.get_current()[parent] if item.name == name), None)

    @classmethod
    def get_by_class(cls, class_):
        parent = NodeStore.get_current_parent()
        return next((item for item in SessionStore.get_current()[parent] if item.node_class == class_), None)

    @classmethod
    def add_to_stack(cls, item):
        cls.stack[cls._current_parent].insert(0, item)

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

    def __eq__(self, other):
        return (other.name, other.parent) == (self.name, self.parent)

    def __hash__(self):
        return hash((self.parent, self.name))

    def __repr__(self):
        name = self.name if self.name else self.type
        return "<NodeStore({}) at {}>".format(name, hex(id(self)))

