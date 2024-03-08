from collections import defaultdict
import re

from _base import Node, CloneNode

NODE_SCRIPT_FORMAT = """{0} {{
 {1}
}}"""


class StackStore:

    def __init__(self):
        self._values = list()
        self._keys = list()

    def index(self, key):
        return self._keys.index(key)

    def pop_by_index(self, index):
        self._keys.pop(index)
        self._values.pop(index)

    def pop(self, key):
        index = self.index(key)
        self.pop_by_index(index)

    def insert(self, index, key, value):
        self._keys.insert(index, key)
        self._values.insert(index, value)

    def clear(self):
        self._values = list()
        self._keys = list()

    def get(self, item):
        try:
            index = self.index(item)
        except ValueError:
            return None

        return self._values[index]

    def __iter__(self):
        return iter(self._keys)

    def __getitem__(self, item):
        index = self.index(item)
        return self._values[index]

    def __setitem__(self, key, value):
        try:
            index = self.index(key)
        except ValueError:
            index = None

        if index is None:
            self._keys.append(key)
            self._values.append(value)
        else:
            self.pop_by_index(index)
            self.insert(index, key, value)

    def __len__(self):
        return len(self._keys)

    def __repr__(self):
        return str(self.items())

    def keys(self):
        return self._keys

    def values(self):
        return self._values

    def items(self):
        return zip(self._keys, self._values)



class StackItem(object):
    __instances = defaultdict(StackStore)
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

        if self.key not in self.__instances[self.parent].keys():
            self.__instances[self.parent][self.key] = self

        if self.type == "node":
            self.__node = Node(
                self.node_class,
                self.knobs,
                self.parent,
                self.user_knobs,
                self
            )
        elif self.type == "clone":
            original = self.__named_stack.get(self.variable)
            self.__node = CloneNode(
                original.node(),
                self.knobs,
                self
            )
        else:
            self.__node = None

        if self.type == "set":
            self.__named_stack[self.variable] = self.get_previous_stack(1)[int(self.stack_index)]

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
        user_knobs = StackItem()
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
                for item in stacks.values():
                    node_scripts.append(item.to_script())
                return "\n".join(node_scripts)
            else:
                return self._get_node_script()
        elif self.type == "end_group":
            return "end_group"
        elif self.type == "set":
            return "set {} [stack {}]".format(self.variable, self.stack_index)
        elif self.type == "push":
            return "push ${}".format(self.variable)
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
                node_stack = self.__named_stack.get(self.variable)
                if node_stack:
                    return node_stack.node()
        else:
            return self.__node

    @property
    def key(self):
        return "{}.{}".format(self.parent, self.name)

    @property
    def index(self):
        return self.__instances[self.parent].index(self.key)

    def get_previous_stack(self, extra=0):
        this_index = self.index
        stack = []
        last_stack_item = None
        required_numbers = self.__inputs + extra
        count = 0
        if required_numbers and this_index != 0:
            keys_to_inspect = reversed(self.__instances[self.parent].keys()[:this_index])
            for key in keys_to_inspect:
                item = self.__instances[self.parent][key]
                if item.type in ("node", "push", "clone"):
                    stack = item.get_stack(required_numbers)
                    break

        #     try:
        #         last_stack_item = self.__instances[self.parent][self.__instances[self.parent].keys()[this_index - 1]]
        #     except IndexError:
        #         pass
        # if last_stack_item:
        #     stack = last_stack_item.stack(self.__inputs + extra)

        return stack

    def get_stack(self, numbers=0):
        needed_from_previous = numbers - 1
        stack = self.get_previous_stack(needed_from_previous) if needed_from_previous else []
        for i in range(self.__inputs):
            if stack:
                stack.pop(-1)
        stack.append(self)
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
    def get_stack_items(cls, parent=None):
        if parent is None:
            return cls.__instances
        else:
            return cls.__instances[parent]

    @classmethod
    def get_last_stack_item(cls):
        stacks = cls.__instances[cls.__current_parent].values()
        return stacks[-1] if stacks else None

    @classmethod
    def get_stack_item(cls, key, parent=None):
        if parent is None:
            parent = cls.__current_parent
        return cls.__instances[parent].get(key)

    @classmethod
    def get_all_nodes(cls, filter_=None, group=None, recursive=False):
        nodes = []
        for key, stack_item in cls.__instances[cls.__current_parent].items():
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
            try:
                node = self.__named_stack[self.variable]
            except KeyError:
                node = None
            name = node.name if node and node.name else "None"
            rep = "{}: {}".format(self.type.title(), name)
        else:
            rep = "{}: {}".format(self.type.title(), self.name)

        return "<StackItem({}) at {}>".format(rep, id(self))

    def __new__(cls, *args, **kwargs):
        parent = cls.__current_parent
        name = kwargs.get("name")
        key = "{}.{}".format(parent, name)
        if key in cls.__instances[parent].keys():
            return cls.__instances[parent][key]
        else:
            return super(StackItem, cls).__new__(cls)

