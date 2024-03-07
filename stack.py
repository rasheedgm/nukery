import collections

from _base import Node

class StackItem(object):
    __instances = collections.defaultdict(collections.OrderedDict)
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
            self.__inputs = int(self.knobs.get("inputs", 1))
        else:
            self.__inputs = 0

        if self.key not in self.__instances[self.parent].keys():
            self.__instances[self.parent][self.key] = self

        if self.type == "set":
            self.__named_stack[self.variable] = self.get_previous_stack(1)[int(self.stack_index)]

        if self.type == "node" and self.node_class == "Group":
            self.__class__.join_to_parent(self.name)
        if self.type == "end_group":
            self.__class__.un_join_last_child()

    def node(self):
        if self.type in ("node", "clone"):
            return Node(
                self.node_class,
                self.parent,
                self.user_knobs,
                **self.knobs
            )

    @property
    def key(self):
        return "{}.{}".format(self.parent, self.name)

    def get_previous_stack(self, extra=0):
        this_index = list(self.__instances[self.parent].keys()).index(self.key)
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
            node = self.__named_stack[self.variable]
            rep = "{}: {}".format(self.type.title(), node.name if node.name else "None")
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
