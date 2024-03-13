import random

from collections import defaultdict, OrderedDict
import re

from nukery._base import Node, CloneNode
from nukery.constants import NODE_SCRIPT_FORMAT, NODE_DEFAULT_INPUTS

class StackItem(object):
    __instances = defaultdict(list)
    __named_stack = {}
    __current_parent = "root"

    def __init__(self, **data_dict):

        self.type = data_dict.get("type")
        self.node_class = data_dict.get("class")
        self.knobs = data_dict.get("knobs")
        self.user_knobs = data_dict.get("user_knobs")
        self.variable = data_dict.get("var")
        self.stack_index = data_dict.get("stack_index", "0")
        self.node_content = data_dict.get("node_content")
        self.input_script = data_dict.get("inputs")

        self.parent = self.__current_parent

        if self.type == "node":
            self.name = self.knobs.get("name")
        else:
            self.name = "{}_{}".format(self.type, len(self.__instances[self.parent]))

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

        # if self.key not in self.__instances[self.parent].keys():
        if data_dict.get("append", True):
            self.__instances[self.parent].append(self)

        if self.type == "set":
            self.__named_stack[self.variable] = self

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
            self.__node = None

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
                stacks = self.get_stack_items(self.key)
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
            return self.__instances[self.parent].index(self)
        except ValueError:
            return None
    @property
    def inputs(self):
        return self.__inputs

    def get_linked_stack(self):
        if self.type == "set":
            index = self.index
            if index is not None and index != 0:
                return self.__instances[self.parent][index - 1]
        elif self.type in ("push", "clone"):
            set_stack = self.__named_stack.get(self.variable)
            if set_stack:
                return set_stack.get_linked_stack()
        else:
            return self

    def get_upward_stacks(self):
        """Open inputs is not handled here, not sure what is the use case of this."""
        stacks = []
        items = [self.__instances[self.parent][self.index-1]]
        previous_inputs = self.inputs
        while items:
            item = items.pop(0)
            if item in stacks:
                continue
            # TODO as of now not handling groups.
            # group_key = "{}.{}".format(item.parent, item.name)
            # if group_key in self.__instances.keys():
            #     stacks.extend(reversed(self.__instances[group_key]))
            if item.node_class == "Root":
                continue
            if previous_inputs:
                stacks.append(item)
                items.append(self.__instances[item.parent][item.index - 1])
                previous_inputs -= 1

            previous_inputs += item.inputs

            if item.type == "push":
                # add set item to check
                items.append(self.__named_stack[item.variable])
            elif item.type not in ("node", "clone"):
                items.append(self.__instances[item.parent][item.index - 1])

        stacks.reverse()
        return stacks

    def get_downward_stacks(self, limit=None):
        """Open inputs are set as None in this result"""
        downward_items = [self]
        stacks = [self]
        sets = []

        for item in self.__instances[self.parent][self.index+1:]:
            if item.type == "set":
                sets.append(item.variable)
                downward_items.append(item)
            elif item.type == "push":
                if item.variable in sets:
                    downward_items.append(item)
                else:
                    downward_items.append(None)
                stacks.insert(0, item)
            elif item.type in ("node", "clone"):
                for i in range(item.inputs):
                    if stacks:
                        item_input = stacks.pop(0)
                        if item_input in downward_items:
                            if item not in downward_items:
                                downward_items.append(item)

                stacks.insert(0, item)
            else:
                downward_items.append(item)

            if limit and len(downward_items) >= limit + 1:
                break

        return downward_items[1:]

    @classmethod
    def rebuild(cls, parent=None):
        if parent is None:
            parent = cls.__current_parent
        _instance_copy = []
        _all = []
        _duplicates = {}
        _variables = defaultdict(str)
        _add_layers = {}
        _end_group = None
        for var, item in cls.__named_stack.items():
            _variables[item.get_linked_stack()] = var
        _stacks = []
        for stack in reversed(cls.__instances[parent]):
            if stack.type == "add_layer":
                linked_stack = _all[-1]
                _add_layers[linked_stack] = stack
            elif stack.type == "end_group":
                _end_group = stack

            if stack.type not in ("node", "clone") or stack.node_class == "Root":
                continue
            _all.append(stack)
            _instance_copy.extend(stack.get_input_stack())

        _duplicates = {v: _instance_copy.count(v) for v in _all}
        _bottom_stack = [item for item in _all if _duplicates[item] == 0]
        last_item = _bottom_stack.pop(0)
        _new_instance_list = []
        while last_item is not False:
            push_item = None
            if last_item is None:
                push_item = StackItem(type="push", var="0", append=False)
                _new_instance_list.insert(0, push_item)
            elif _duplicates[last_item] > 1:
                var = _variables[last_item]
                if not var:
                    var = _variables[last_item] = cls.get_random_variable_name()
                push_item = StackItem(type="push", var=var, append=False)
                _new_instance_list.insert(0, push_item)
                if _duplicates[last_item] == 2:
                    _duplicates[last_item] = -1

                else:
                    _duplicates[last_item] -= 1
            else:
                if _duplicates[last_item] == -1:
                    var = _variables[last_item]
                    set_item = StackItem(type="set", var=var, append=False)
                    _new_instance_list.insert(0, set_item)
                elif last_item in _variables:
                    var = _variables[last_item]
                    if var.startswith("C"):
                        set_item = StackItem(type="set", var=var, append=False)
                        _new_instance_list.insert(0, set_item)
                _new_instance_list.insert(0, last_item)
                if last_item in _add_layers:
                    _new_instance_list.insert(0, _add_layers[last_item])

            if push_item is None and last_item:
                _stacks = last_item.get_input_stack() + _stacks

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
            _new_instance_list.append(_end_group)

        return _new_instance_list

    def set_input_stack(self, input_number, input_stack):
        down_stacks = self.get_downward_stacks()  # need rework
        if input_stack in down_stacks:
            return None

        current_inputs = self._inputs_stacks

        input_exists = input_number < len(current_inputs)
        if input_exists:
            current_inputs.pop(input_number)
            current_inputs.insert(input_number, input_stack)
        else:
            # self._inputs_stacks = []
            for i in range(len(self._inputs_stacks), input_number):
                print(i, len(self._inputs_stacks), input_number)
                self._inputs_stacks.insert(i, None)

            self._inputs_stacks.insert(input_number, input_stack)

        self.__inputs = len(self._inputs_stacks)

        min_, max_, has_mask = NODE_DEFAULT_INPUTS.get(self.node_class, (0, 0, False))
        if has_mask and self.__inputs >= min_:
            self.input_script = "{0}+1".format(self.__inputs - 1)
        elif self.__inputs == 1:
            self.input_script = ""
        else:
            self.input_script = str(self.__inputs)

        self.__instances[self.parent] = self.rebuild(self.parent)

    def get_input_stack(self):
        return self._inputs_stacks

    def __get_input_stack(self, extra=0):
        this_index = self.index
        stack = []
        required_numbers = self.__inputs + extra

        required_by_last_stack = 0
        if required_numbers and this_index != 0:
            for item in reversed(self.__instances[self.parent][:this_index]):
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
    def get_random_variable_name(cls, prefix="N"):
        var = prefix + ''.join(random.choice("0123456789abcdef") for _ in range(8))

        if var in cls.__named_stack.keys():
            return cls.get_random_variable_name(prefix)
        else:
            return var

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
    def get_stack_items(cls, parent=None):
        if parent is None:
            return cls.__instances
        else:
            return cls.__instances[parent]

    @classmethod
    def get_last_stack_item(cls):
        stacks = cls.__instances[cls.__current_parent]
        return stacks[-1] if stacks else None

    @classmethod
    def get_all_nodes(cls, filter_=None, group=None, recursive=False):
        nodes = []
        for  stack_item in cls.__instances[cls.__current_parent]:
            if stack_item.type not in ("node", "clone"):
                continue
            if filter_ and stack_item.node_class != filter_:
                continue
            node = stack_item.node()
            if node:
                nodes.append(node)
        return nodes

    @classmethod
    def _get_name_from_args(cls, **kwargs):
        name = kwargs.get("name")
        if name is None:
            if kwargs.get("type") in ("push", "clone", "set"):
                name = "{}_{}".format(kwargs.get("type"), kwargs.get("var"))
            else:
                name = "{}_{}".format(kwargs.get("type"), len(cls.__instances[cls.__current_parent]))
        return name

    def __repr__(self):
        if self.type == "node":
            rep = "Node: " + self.name if self.name else "None"
        elif self.type in ("push", "set"):
            rep = "{}: {}".format(self.type.title(), self.name)
        else:
            rep = "{}: {}".format(self.type.title(), self.name)

        return "<StackItem({}) at {}>".format(rep, id(self))

    def __hash__(self):
        return hash((self.parent, self.name))

    def __new__(cls, *args, **kwargs):
        return super(StackItem, cls).__new__(cls)

