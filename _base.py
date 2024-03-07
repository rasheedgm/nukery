from collections import OrderedDict, defaultdict
import re



NODE_SCRIPT_FORMAT = """{0} {{
 {1}
}}"""


class StackItem(object):
    __instances = defaultdict(OrderedDict)
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

        self.parent = self.__current_parent

        if self.type == "node":
            self.name = self.knobs.get("name")
        else:
            self.name = "{}_{}".format(self.type, len(self.__instances[self.parent]))

        if self.type in ("node", "clone"):
            inputs_script = data_dict.get("inputs")
            if re.match(r"^[\d]+(?:(?:[\+\s\d]+)$)?", inputs_script):
                self.__inputs = eval(data_dict.get("inputs"))
            else:
                raise Exception("input number {0} is unknown, "
                                "please report it to developer".format(inputs_script))
        else:
            self.__inputs = 0

        if self.key not in self.__instances[self.parent].keys():
            self.__instances[self.parent][self.key] = self

        if self.type == "set":
            print("SET", self.variable, type(self.variable))
            self.__named_stack[self.variable] = self.get_previous_stack(1)[int(self.stack_index)]

        if self.type == "node" and self.node_class == "Group":
            self.__class__.join_to_parent(self.name)
        if self.type == "end_group":
            self.__class__.un_join_last_child()

    def _get_node_script(self, clone=False):
        node = self.node()
        knob_line_format = "{0} {1}"
        knob_lines = []
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
            if self.node_class == "Group":
                node_scripts = [self._get_node_script()]
                this_index = self.index
                print(self.key)
                stacks = self.get_stack_items(self.key)
                print(stacks.values())
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
        elif self.type == "node":
            return Node(
                self.node_class,
                self.knobs,
                self.parent,
                self.user_knobs,
            )
        elif self.type == "clone":
            original = self.__named_stack.get(self.variable)
            return CloneNode(
                original.node(),
                self.knobs
            )
        else:
            if self.variable in ("0", 0):
                return None
            else:
                node_stack = self.__named_stack.get(self.variable)
                if node_stack:
                    return node_stack.node()

    @property
    def key(self):
        return "{}.{}".format(self.parent, self.name)

    @property
    def index(self):
        return list(self.__instances[self.parent].keys()).index(self.key)

    def get_previous_stack(self, extra=0):
        this_index = self.index
        stack = []
        last_stack_item = None
        required_numbers = self.__inputs + extra
        count = 0
        if required_numbers and this_index != 0:
            keys_to_inspect = [list(self.__instances[self.parent].keys())[i] for i in range(this_index-1, -0, -1)]
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
    def get_stack_item(cls, key, parent=None):
        if parent is None:
            parent = cls.__current_parent
        print(" -- ",cls.__instances[parent].get(key))
        return cls.__instances[parent].get(key)

    @classmethod
    def get_all_nodes(cls, filter_=None, group=None, recursive=False):
        nodes = []
        for key, stack_item in cls.__instances[cls.__current_parent].items():
            if filter_ and stack_item.node_class != filter_:
                continue
            node = stack_item.node()
            if node:
                nodes.append(node)
        return nodes

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



class Node(object):
    __instances = {}

    def __init__(self, class_, knobs=None, parent_node=None, user_knobs=None, inputs=None):
        self.__class = class_
        self.__knobs = OrderedDict()
        self.__user_knobs = user_knobs if user_knobs else []
        if knobs:
            for key, value in knobs.items(): # set this sepretely in to knobs
                self.__knobs[key] = value

        self.parent_node = parent_node

        key = "{}.{}".format(self.parent_node, self.name)
        if key not in self.__class__.__instances.keys():
            self.__class__.__instances[key] = self

    @property
    def name(self):
        return self.__knobs.get("name")

    def knobs(self):
        return self.__knobs

    def get_class(self):
        return self.__class

    def get_inputs(self):
        nodes = []
        key = "{}.{}".format(self.parent_node, self.name)
        stack_item = StackItem.get_stack_item(key, self.parent_node)
        print(stack_item.get_previous_stack())
        for item in stack_item.get_previous_stack():
            nodes.append(item.node())
        return nodes

    def set_input(self, index, node):
        return NotImplemented

    def to_script(self):
        knob_line_format = "{0} {1}"
        knob_lines = []
        user_knobs = {n: v for n, _id, v in self.__user_knobs}
        for name, value in self.__knobs.items():
            knob_line = knob_line_format.format(name, value)
            if name in user_knobs.keys():
                knob_lines.append("addUserKnob " + user_knobs.get(name))
            knob_lines.append(knob_line)
        knob_line_script = "\n ".join(knob_lines)
        return NODE_SCRIPT_FORMAT.format(self.__class, knob_line_script)

    def __getitem__(self, item):
        return self.__knobs.get(item)

    def __setitem__(self, key, value):
        self.__knobs[key] = value

    def __repr__(self):
        name = self["name"]
        return name if name else "None"

    def __new__(cls, class_=None, knobs=None, parent_node=None, user_knobs=None, inputs=None):
        name = knobs.get("name") if knobs else "{}_{}".format(class_, len(cls.__instances))
        key = "{}.{}".format(parent_node, name)
        instance = cls.__instances.get(key)
        if not instance:
            instance = super(Node, cls).__new__(cls)

        return instance


class CloneNode(Node):

    def __init__(self, original_node, knobs, inputs=None):
        super(CloneNode, self).__init__(original_node.get_class(), knobs, original_node.parent_node, inputs)
        self.original_node = original_node
        # modification needed

    def __getitem__(self, item):
        if item in self.knobs().keys():
            return self.knobs().get(item)
        else:
            return self.original_node[item]

    def __setitem__(self, key, value):
        if key in self.knobs().keys():
            self[key] = value
        else:
            self.original_node[key] = value

