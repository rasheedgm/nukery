import re
import random
from collections import defaultdict, OrderedDict
from copy import deepcopy

from nukery.constants import NODE_DEFAULT_INPUTS, NODE_SCRIPT_FORMAT, CLONE_KNOBS


class SessionStore(object):
    """"""
    __default__ = "__default__"
    __sessions = {__default__: defaultdict(list)}
    __variable = {__default__: {}}
    _current_session = __default__
    stack = {__default__: defaultdict(list)}

    def __init__(self, session):
        self.session = session
        if self.session not in self.__sessions.keys():
            self.__class__.__sessions[self.session] = defaultdict(list)
            self.__class__.__variable[self.session] = {}
            self.__class__.stack[self.session] = defaultdict(list)

    @classmethod
    def append(cls, item):
        cls.get_current()[item.parent].append(item)

    @classmethod
    def remove(cls, item):
        cls.get_current()[item.parent].remove(item)
        # cls.get_current_stack()[item.parent].remove(item)

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
    def get_current_stack(cls):
        return cls.stack[cls._current_session]

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
        """Build script text from node_store list.
        """
        print(node_store_list)
        node_store_list = deepcopy(node_store_list)
        _instance_copy = []
        _all = []
        _duplicates = {}
        _clones = {}
        _variables = defaultdict(str)
        _add_layers = {}
        _end_group = None
        _root_item = None
        _tail_item = []
        for var, item in cls.__variable[cls._current_session].items():
            _variables[item] = var
        _stacks = []
        for item in node_store_list:
            if item.node_class == "Root":
                _root_item = item
                continue
            out_len = len([o for o in item.outputs if o in node_store_list])
            _duplicates[item] = out_len
            if out_len == 0:
                _tail_item.append(item)

            if item.type == "clone":
                if item.variable not in _clones:
                    _clones[item.variable] = [SessionStore.get_variable(item.variable)]
                _clones[item.variable].append(item)
        last_item = _tail_item.pop(0)
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

                if last_item.variable and last_item in _clones[last_item.variable]:
                    _clones[last_item.variable].remove(last_item)
                    if not _clones[last_item.variable]:
                        # there are not more clone then this will be base for other clones
                        set_item = "set {0} [stack 0]".format(last_item.variable)
                        _new_stacks_list.insert(0, set_item)
                        _new_stacks_list.insert(0, last_item.to_script())
                    else:
                        # there are more clones so this has to be clone script
                        _new_stacks_list.insert(0, last_item.to_script(as_clone=True))
                else:
                    _new_stacks_list.insert(0, last_item.to_script())

            if push_item is None and last_item:
                _inputs = last_item.inputs
                for _input in _inputs:
                    if _input not in node_store_list:
                        _index = _inputs.index(_input)
                        _inputs.remove(_input)
                        _inputs.insert(_index, None)
                _stacks = _inputs + _stacks

            if _stacks:
                last_item = _stacks.pop(0)
            elif _tail_item:
                last_item = _tail_item.pop(0)
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
    # stack = defaultdict(list) # needs session.
    _current_parent = "root"
    __add_layer = None
    _name_pattern = re.compile("^(.*?)(\d+)?$")

    def __init__(self, **kwargs):

        self.type = kwargs.get("type")
        self._node_class = kwargs.get("class")
        self.knobs = kwargs.get("knobs", {})
        self.user_knobs = kwargs.get("user_knobs", [])
        self.variable = kwargs.get("var", "")
        self.stack_index = kwargs.get("stack_index", "0")
        self.node_content = kwargs.get("node_content", "")
        input_script = kwargs.get("inputs")
        self.parent = self.get_current_parent()

        self.inputs = []
        self.outputs = []
        self._add_layer = None

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
                item = self.pop_from_stack()
                self.set_input(i, item)

            SessionStore.append(self)
            self.add_to_stack(self)
            if self.is_group:
                self.join_to_parent(self.name)

        if self.type == "set":
            if self.parent in SessionStore.get_current_stack():
                stack_item = SessionStore.get_current_stack()[self.parent][int(self.stack_index)]
            else:
                stack_item = None

            if self.variable.startswith("C"):
                stack_item.variable = self.variable
            SessionStore.set_variable(self.variable, stack_item)

        if self.type == "push":
            self.add_to_stack(SessionStore.get_variable(self.variable))
        if self.type == "end_group":
            self.un_join_last_child()

        if self.__class__.__add_layer:
            if self.type == "clone":
                original = SessionStore.get_variable(self.variable)
                original.add_layer = self.__class__.__add_layer
            else:
                self._add_layer = self.__class__.__add_layer
            self.__class__.__add_layer = None

        if self.type == "add_layer":
            self.__class__.__add_layer = self.variable

    def to_script(self, as_clone=False):
        """ Get script text of the node, if as clone is True then it will only return clone like text

        Args:
            as_clone(bool): if True it will only return clone like text

        Returns:
            str: script text of the node.
        """
        if self.is_group:
            if as_clone:
                raise Exception("Clone is not supported with group nodes.")
            node_scripts = [self._get_node_script()]
            nodes_stores = SessionStore.get_current()["{}.{}".format(self.parent, self.name)]
            node_scripts.append(SessionStore.build_script_from_list(nodes_stores))
            node_scripts.append("end_group")
            return "\n".join(node_scripts)
        else:
            if as_clone:
                node_script = self._get_clone_script()
            else:
                node_script = self._get_node_script()
                if self.add_layer:
                    node_script = "add_layer {0}\n{1}".format(self.add_layer, node_script)

            return node_script

    def _get_clone_script(self):
        knob_line_format = "{0} {1}"
        knob_lines = []
        if self.input_script != "":
            knob_lines.append("inputs " + self.input_script)
        for name, value in self.knobs.items():
            if name not in CLONE_KNOBS:
                continue
            knob_line = knob_line_format.format(name, value)

            knob_lines.append(knob_line)

        knob_line_script = "\n ".join(knob_lines)
        if not self.variable:
            raise Exception("Clone variable is not defined for {0}".format(self.name))
        class_text = "clone ${}".format(self.variable)
        return NODE_SCRIPT_FORMAT.format(class_text, knob_line_script)

    def _get_node_script(self):
        knob_line_format = "{0} {1}"
        knob_lines = []
        if self.input_script != "":
            knob_lines.append("inputs " + self.input_script)
        user_knobs = OrderedDict()
        for n, _id, v in self.user_knobs:
            user_knobs[n] = v
        user_knob_value = {}
        if self.type == "clone":
            original = SessionStore.get_variable(self.variable)
            knobs = deepcopy(original.knobs)
            knobs.update(deepcopy(self.knobs))
        else:
            knobs = self.knobs
        for name, value in knobs.items():
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
        return NODE_SCRIPT_FORMAT.format(self.node_class, knob_line_script)

    def delete(self):
        for out in self.outputs:
            input0 = self.inputs[0] if self.inputs else None
            index = out.inputs.index(self)
            out.set_input(index, input0)

        for input_ in self.inputs:
            if input_:
                input_.remove_output(self)

        self.inputs = []
        self.outputs = []

        SessionStore.remove(self)

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
    def node_class(self):
        if self.type == "clone":
            original = SessionStore.get_variable(self.variable)
            return original.node_class

        return self._node_class

    @property
    def add_layer(self):
        if self.type == "clone":
            original = SessionStore.get_variable(self.variable)
            return original.add_layer
        return self._add_layer

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

        return next((item for item in SessionStore.get_current()[parent] if item.name == name and item.type == "node"), None)

    @classmethod
    def get_by_class(cls, class_):
        parent = NodeStore.get_current_parent()
        return next((item for item in SessionStore.get_current()[parent] if item.node_class == class_), None)

    def add_to_stack(self, item):
        SessionStore.get_current_stack()[self.parent].insert(0, item)

    def pop_from_stack(self):
        stack = SessionStore.get_current_stack()[self.parent]
        return stack.pop(0) if stack else None

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
        if self.type == "node":
            return hash((self.parent, self.name))
        else:
            return hash(id(self))

    def __repr__(self):
        name = self.name if self.name else self.type
        return "<NodeStore({}) at {}>".format(name, hex(id(self)))
