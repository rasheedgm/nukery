
NODE_SCRIPT_FORMAT = """{0} {{
 {1}
}}"""

class Node(object):

    def __init__(self, class_, parent_node, user_knobs=None, **knobs):
        self.__class = class_
        self.__inputs = knobs.get("inputs") # TODO manage input separately
        self.__knobs = {}
        self.__user_knobs = user_knobs if user_knobs else []
        for key, value in knobs.items(): # set this sepretely in to knobs
            self.__knobs[key] = value

        self.parent_node = parent_node

    def name(self):
        return self.__knobs.get("name")

    def get_class(self):
        return self.__class

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
        return self["name"] or "None"


class CloneNode(Node):

    def __init__(self, original_node, **kwargs):
        super(CloneNode, self).__init__(original_node.get_class(), original_node.parent_node, **kwargs)
        self.original_node = original_node
        # modification needed

    def __getitem__(self, item):
        if hasattr(self, item):
            return getattr(self, item)
        elif hasattr(self.original_node, item):
            return getattr(self.original_node, item)
        else:
            return None

    def __setitem__(self, key, value):
        return setattr(self, key, value)

