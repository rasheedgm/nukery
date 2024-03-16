from collections import OrderedDict, defaultdict
import re


class Node(object):
    __instances = {}
    __name_pattern = re.compile("^(.*?)(\d+)?$")

    def __init__(self, class_, knobs=None, parent_node=None, user_knobs=None, stack_item=None):
        self.__class = class_
        self.__knobs = OrderedDict()
        self.__user_knobs = user_knobs if user_knobs else []
        if knobs:
            for key, value in knobs.items(): # set this sepretely in to knobs
                self.__knobs[key] = value

        self.parent_node = parent_node
        # TODO i need to rethink how to link stack item and node object
        self.__stack_item = stack_item

        if self.name is None:
            self["name"] = "{}1".format(self.__class)

        if self.__stack_item.store_name not in self.__instances.keys():
            self.__instances[self.__stack_item.store_name] = defaultdict(dict)

        # key = "{}.{}".format(self.parent_node, self.name)
        # if node name exists in this context increment the name suffix
        if self.name in self.__instances[self.__stack_item.store_name][self.parent_node].keys():
            name, _ = self.__name_pattern.match(self.name).groups()
            node_numbers = set()

            for k in self.__instances[self.__stack_item.store_name][self.parent_node].keys():
                match = self.__name_pattern.match(k)
                _name, _number = match.groups() if match else (None, None)
                #_number = 1 if _number is None else _number # TODO test name without number
                if _name == name:
                    node_numbers.add(int(_number))

            number_range = set(range(1, max(node_numbers)+2))
            missing = number_range - node_numbers
            number = min(missing)
            self.__knobs["name"] = "{}{}".format(name, number)

        self.__class__.__instances[self.__stack_item.store_name][self.parent_node][self.name] = self

    @property
    def name(self):
        return self.__knobs.get("name")

    @property
    def is_group(self):
        return (self.__class == "Group" or (self.__class == "LiveGroup"
                                            and self.knobs().get("published", "false").lower() == "false"))

    def knobs(self):
        return self.__knobs

    def get_class(self):
        return self.__class

    def set_selected(self, value=True):
        if not isinstance(value, bool):
            raise ValueError("value has to be bool")
        if value:
            self.__knobs["selected"] = "true"
        else:
            self.__knobs.pop("selected", None)

    def get_inputs(self):
        nodes = []
        for item in self.__stack_item.get_input_stack():
            if item:
                nodes.append(item.node())
            else:
                nodes.append(None)
        return nodes

    def set_input(self, index, node):
        self.__stack_item.set_input_stack(index, node.__stack_item)

    def to_script(self):
        return self.__stack_item.to_script()

    def __enter__(self): # TODO test this
        if self.is_group:
            self.__stack_item.set_current_parent(self.__stack_item.key)
            return self
        else:
            raise TypeError("Context is only available with group nodes.")

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.is_group:
            self.__stack_item.un_join_last_child()

    def __getitem__(self, item):
        return self.__knobs.get(item)

    def __setitem__(self, key, value):
        self.__knobs[key] = value

    def __repr__(self):
        name = self["name"]
        name = name if name else "None"
        return "<{}({}) at {}>".format(self.__class__.__name__, name, id(self))


class CloneNode(Node):

    def __init__(self, original_node, knobs, stack_item):
        self.original_node = original_node
        super(CloneNode, self).__init__(original_node.get_class(), knobs, original_node.parent_node, None, stack_item)

        # modification needed

    @property
    def name(self):
        return self.original_node.name + "Clone"

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

