import random
import re
from collections import defaultdict, OrderedDict

from nukery._base import Node, CloneNode
from nukery.constants import NODE_SCRIPT_FORMAT, NODE_DEFAULT_INPUTS


class StackStore(object):
    __default__ = "__default__"
    __stores = {__default__: defaultdict(list)}
    __variables = {__default__: {}}
    current = __default__
    __modified = {__default__: defaultdict(bool)}

    def __init__(self, store=None):
        if store is None:
            store = self.__default__

        self._store = store
        if self._store not in self.__stores.keys():
            self.__class__.__stores[self._store] = defaultdict(list)

        if self._store not in self.__variables.keys():
            self.__class__.__variables[self._store] = defaultdict(list)

        if self._store not in self.__modified.keys():
            self.__class__.__modified[self._store] = defaultdict(bool)

    def append(self, stack):
        self.__stores[self._store][stack.parent].append(stack)
        self.set_modified(True, stack.parent)

    def insert(self, index, stack):
        pass

    def has_value(self):
        return bool(self.__stores[self._store])

    def clear(self):
        self.__stores[self._store] = defaultdict(list)
        self.__variables[self._store] = defaultdict(list)

    @classmethod
    def get_stack_items(cls, parent=None):

        if parent is None:
            parent = StackItem.get_current_parent()
        if cls.is_modified(parent):
            cls.build_stack(parent)

        return cls.__stores[cls.current][parent]

    @classmethod
    def get_all_nodes(cls, filter_=None, group=None, recursive=False):
        nodes = []
        for stack_item in cls.__stores[cls.current][StackItem.get_current_parent()]:
            if stack_item.type not in ("node", "clone"):
                continue
            if filter_ and stack_item.node_class != filter_:
                continue
            node = stack_item.node()
            if node:
                nodes.append(node)
        return nodes

    @classmethod
    def get_node_by_name(cls, name):
        for stack_item in cls.__stores[cls.current][StackItem.get_current_parent()]:
            if stack_item.type not in ("node", "clone"):
                continue
            if stack_item.name == name:
                return stack_item.node()

    @classmethod
    def variables(cls):
        return cls.__variables[cls.current]

    @classmethod
    def set_variable(cls, var, value):
        cls.__variables[cls.current][var] = value

    @classmethod
    def build_stack(cls, parent=None):
        if parent is None:
            parent = StackItem.get_current_parent()

        new_stack = cls.__build_stack(cls.__stores[cls.current][parent])
        cls.__stores[cls.current][parent] = new_stack
        cls.set_modified(False, parent)

    @classmethod
    def build_stack_from_list(cls, stack_list):
        return cls.__build_stack(stack_list)

    @classmethod
    def __build_stack(cls, stack_list):
        """Stacks are not ordered if there are any changes made, so if changes needs to be rebuilt
        call this, this will rebuild the stack and return the new stack items.
        """

        _instance_copy = []
        _all = []
        _duplicates = {}
        _variables = defaultdict(str)
        _add_layers = {}
        _end_group = None
        _root_item = None
        for var, item in cls.variables().items():
            _variables[item.get_linked_stack()] = var
        _stacks = []
        for stack in reversed(stack_list):
            if stack.type == "add_layer":
                linked_stack = _all[-1]
                _add_layers[linked_stack] = stack
            elif stack.type == "end_group":
                _end_group = stack
            elif stack.node_class == "Root":
                _root_item = stack

            if stack.type not in ("node", "clone") or stack.node_class == "Root":
                continue
            _all.append(stack)
            _instance_copy.extend(stack.get_input_stack())

        _duplicates = {v: _instance_copy.count(v) for v in _all}
        _bottom_stack = [item for item in _all if _duplicates[item] == 0]
        last_item = _bottom_stack.pop(0)
        _new_stacks_list = []
        while last_item is not False:
            push_item = None
            if last_item is None:
                push_item = StackItem(type="push", var="0", append=False)
                _new_stacks_list.insert(0, push_item)
            elif _duplicates[last_item] > 1:
                var = _variables[last_item]
                if not var:
                    var = _variables[last_item] = cls.get_random_variable_name()
                push_item = StackItem(type="push", var=var, append=False)
                _new_stacks_list.insert(0, push_item)
                if _duplicates[last_item] == 2:
                    _duplicates[last_item] = -1

                else:
                    _duplicates[last_item] -= 1
            else:
                if _duplicates[last_item] == -1:
                    var = _variables[last_item]
                    set_item = StackItem(type="set", var=var, append=False)
                    _new_stacks_list.insert(0, set_item)
                elif last_item in _variables:
                    var = _variables[last_item]
                    if var.startswith("C"):
                        set_item = StackItem(type="set", var=var, append=False)
                        _new_stacks_list.insert(0, set_item)
                _new_stacks_list.insert(0, last_item)
                if last_item in _add_layers:
                    _new_stacks_list.insert(0, _add_layers[last_item])

            if push_item is None and last_item:
                _inputs = last_item.get_input_stack()
                for _input in _inputs:
                    if _input not in stack_list:
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

        if _end_group:
            _new_stacks_list.append(_end_group)
        if _root_item:
            _new_stacks_list.insert(0, _root_item)

        return _new_stacks_list

    @classmethod
    def get_random_variable_name(cls, prefix="N"):
        var = prefix + ''.join(random.choice("0123456789abcdef") for _ in range(8))

        if var in cls.variables().keys():
            return cls.get_random_variable_name(prefix)
        else:
            return var

    @classmethod
    def get_current(cls):
        return cls(cls.current)

    @classmethod
    def set_modified(cls, value, parent=None):
        if not isinstance(value, bool):
            raise ValueError("value must be bool")
        if parent is None:
            parent = StackItem.get_current_parent()

        cls.__modified[cls.current][parent] = value

    @classmethod
    def is_modified(cls, parent=None):
        if parent is None:
            parent = StackItem.get_current_parent()
        return cls.__modified[cls.current][parent]

    def __getitem__(self, parent):
        return self.__stores[self._store][parent]

    def __setitem__(self, parent, store):
        if isinstance(store, list):
            self.__stores[self._store][parent] = store

    def __enter__(self):
        self.__class__.current = self._store
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.__class__.current = self.__default__


class StackItem(object):
    __current_parent = "root"

    def __init__(self, **data_dict):

        self.type = data_dict.get("type")
        self.node_class = data_dict.get("class")
        self.knobs = data_dict.get("knobs")
        self.user_knobs = data_dict.get("user_knobs", [])
        self.variable = data_dict.get("var", "")
        self.stack_index = data_dict.get("stack_index", "0")
        self.node_content = data_dict.get("node_content", "")
        self.input_script = data_dict.get("inputs")

        self.parent = self.get_current_parent()

        self.__store = StackStore.get_current()

        if self.type in ("node", "clone"):
            if self.input_script == "":
                # if there is no inputs script then it mean default input is connected.
                self.__inputs = 1
            elif re.match(r"^[\d]+(?:(?:[\+\s\d]+)$)?", self.input_script):
                self.__inputs = eval(data_dict.get("inputs"))
            else:
                raise Exception("input number {0} is unknown, "
                                "please report it to developer".format(self.input_script))
        else:
            self.__inputs = 0

        if data_dict.get("append", True):
            # if stack has end group then the stack is called in group context
            # we have to push end_group next to this.
            try:
                last_item = self.__store[self.parent][-1]
            except IndexError:
                last_item = None
            if last_item and last_item.type == "end_group":
                self.__store[self.parent].pop(-1)
                self.__store.append(self)
                self.__store.append(last_item)
            else:
                self.__store.append(self)

        if self.type == "set":
            self.__store.set_variable(self.variable, self)

        if self.type == "node":
            self._inputs_stacks = self.__get_input_stack()
            self.__node = Node(
                self.node_class,
                self.knobs,
                self.parent,
                self.user_knobs,
                self
            )
        elif self.type == "clone":
            self._inputs_stacks = self.__get_input_stack()
            original = self.get_linked_stack()
            self.__node = CloneNode(
                original.node(),
                self.knobs,
                self
            )
        else:
            self._inputs_stacks = None
            self.__node = None

        if self.type == "node":
            self.name = self.__node.knobs().get("name")
        else:
            self.name = "{}_{}".format(self.type, len(self.__store[self.parent]))

        if self.type == "node" and self.__node.is_group:
            self.__class__.join_to_parent(self.name)
        if self.type == "end_group":
            self.__class__.un_join_last_child()

    def _get_node_script(self, clone=False):
        node = self.node()
        knob_line_format = "{0} {1}"
        knob_lines = []
        if self.input_script != "":
            knob_lines.append("inputs " + self.input_script)
        user_knobs = OrderedDict()
        for n, _id, v in self.user_knobs:
            user_knobs[n] = v
        user_knob_value = {}
        for name, value in node.knobs().items():
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

    def to_script(self):
        if self.type == "node":
            if self.__node.is_group:
                node_scripts = [self._get_node_script()]
                this_index = self.index
                with self.__store:  # TODO test without context, changing _store in StackStore
                    stacks = self.__store.get_stack_items(self.key)
                for item in stacks:
                    node_scripts.append(item.to_script())
                return "\n".join(node_scripts)
            else:
                return self._get_node_script()
        elif self.type == "end_group":
            return "end_group"
        elif self.type == "set":
            return "set {} [stack {}]".format(self.variable, self.stack_index)
        elif self.type == "push":
            if self.variable != "0":
                return "push ${}".format(self.variable)
            else:
                return "push {}".format(self.variable)
        elif self.type == "clone":
            return self._get_node_script(clone=True)
        elif self.type == "add_layer":
            return "add_layer {}".format(self.variable)

    def node(self):
        if self.type not in ("node", "clone", "push"):
            return None
        elif self.type == "push":
            if self.variable in ("0", 0):
                return None
            else:
                node_stack = self.get_linked_stack()
                if node_stack:
                    return node_stack.node()
        else:
            return self.__node

    @property
    def key(self):
        return "root" if self.node_class == "Root" else "{}.{}".format(self.parent, self.name)

    @property
    def index(self):
        try:
            return self.__store[self.parent].index(self)
        except ValueError:
            return None

    @property
    def inputs(self):
        return self.__inputs

    @property
    def store_name(self):
        return StackStore.current

    def get_linked_stack(self):
        if self.type == "set":
            index = self.index
            if index is not None and index != 0:
                return self.__store[self.parent][index - 1]
        elif self.type in ("push", "clone"):
            set_stack = self.__store.variables().get(self.variable)
            if set_stack:
                return set_stack.get_linked_stack()
        else:
            return self

    def get_upward_node_stacks(self):
        """Open inputs is not handled here, not sure what is the use case of this."""
        upward_stacks = []
        inputs = []
        base_stack = self.get_linked_stack()
        while base_stack is not False:
            if base_stack is None:
                continue
            inputs = base_stack.get_input_stack() + inputs
            if inputs:
                base_stack = inputs.pop(0)
                upward_stacks.append(base_stack)
            else:
                base_stack = False
        return upward_stacks

    def get_downward_stacks(self, limit=None):
        """get all node downwards"""
        pass

    def set_input_stack(self, input_number, input_stack):
        up_stacks = input_stack.get_upward_node_stacks()  # need rework
        if self in up_stacks:
            return None

        if input_stack == self:
            return None

        if input_stack.type not in ("node", "clone"):
            return None

        current_inputs = self._inputs_stacks

        input_exists = input_number < len(current_inputs)
        if input_exists:
            current_inputs.pop(input_number)
            current_inputs.insert(input_number, input_stack)
        else:
            for i in range(len(self._inputs_stacks), input_number):
                self._inputs_stacks.insert(i, None)

            self._inputs_stacks.insert(input_number, input_stack)

        self.__inputs = len(self._inputs_stacks)

        StackStore.set_modified(True, self.parent)

        min_, max_, has_mask = NODE_DEFAULT_INPUTS.get(self.node_class, (0, 0, False))
        if has_mask and self.__inputs >= min_:
            self.input_script = "{0}+1".format(self.__inputs - 1)
        elif self.__inputs == 1:
            self.input_script = ""
        else:
            self.input_script = str(self.__inputs)

    def get_input_stack(self):
        return self._inputs_stacks

    def __get_input_stack(self, extra=0):
        this_index = self.index
        stack = []
        required_numbers = self.__inputs + extra

        required_by_last_stack = 0
        if required_numbers and this_index != 0:
            for item in reversed(self.__store[self.parent][:this_index]):
                if item.type in ("node", "push", "clone"):
                    if required_by_last_stack == 0:
                        stack.append(item.get_linked_stack())
                    else:
                        required_by_last_stack -= 1
                    if required_numbers == len(stack):
                        return stack
                    required_by_last_stack += item.inputs

        return stack

    @classmethod
    def join_to_parent(cls, child):
        cls.__current_parent += "." + child

    @classmethod
    def un_join_last_child(cls):
        cls.__current_parent = ".".join(cls.__current_parent.split(".")[:-1])

    @classmethod
    def set_current_parent(cls, parent):
        cls.__current_parent = parent

    @classmethod
    def get_current_parent(cls):
        return cls.__current_parent

    def __repr__(self):
        if self.type == "node":
            rep = "Node: " + self.name if self.name else "None"
        else:
            rep = "{}: {}".format(self.type.title(), self.name)

        return "<StackItem({}) at {}>".format(rep, id(self))

    def __hash__(self):
        return hash((self.parent, self.name))

    def __new__(cls, *args, **kwargs):
        return super(StackItem, cls).__new__(cls)

