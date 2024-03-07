from collections import OrderedDict

class Node(object):
    __instances = {}

    def __init__(self, class_, knobs=None, parent_node=None, user_knobs=None, stack_item=None):
        self.__class = class_
        self.__knobs = OrderedDict()
        self.__user_knobs = user_knobs if user_knobs else []
        if knobs:
            for key, value in knobs.items(): # set this sepretely in to knobs
                self.__knobs[key] = value

        self.parent_node = parent_node

        # TODO i need to rethink how to link stack item and node object
        print ("&&&&INIT", self.__class, self.__class__.__name__, stack_item)
        self.__stack_item = stack_item

        key = "{}.{}".format(self.parent_node, self.name)
        if key not in self.__class__.__instances.keys():
            self.__class__.__instances[key] = self


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

    def get_inputs(self):
        nodes = []
        print (self.__stack_item, self.__stack_item.get_previous_stack())
        for item in self.__stack_item.get_previous_stack():
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
        name = name if name else "None"
        return "<{}({}) at {}>".format(self.__class__.__name__, name, id(self))

    def __new__(cls, class_=None, knobs=None, parent_node=None, user_knobs=None, inputs=None):
        name = knobs.get("name") if knobs else "{}_{}".format(class_, len(cls.__instances))
        key = "{}.{}".format(parent_node, name)
        instance = cls.__instances.get(key)
        if not instance:
            instance = super(Node, cls).__new__(cls)

        return instance


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

