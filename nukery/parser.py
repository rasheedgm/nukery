import os.path
from collections import OrderedDict

import re


class NukeScriptParser:
    knob_pattern = r"(^\s*)(\w+|(?:[\w\.]+)|(?:\"(?:[^\"]*)\"))\s+((?:\{(?:[^{}]*\{[^{}]*\}[^{}]*)*\})|(?:\{[^{}]+\})|(?:[^\n]+))"
    stack_command_pattern = r"\s*(\S+)\s?\$?(?:((?:[\S\s]*\}$)|(?:\S+(?:\sv\d+)?))\s*)?(?:\s*\[stack\s*(\d+)\])?"
    clone_pattern = r"(clone)\s(?:\$(\w*))?|(?:[\w\|*s*]+\s(\w+))$"
    user_knob_pattern = r"\{([\d]+)\s([\w]+)(?:[^\}]*\})"
    node_pattern = r"(?:\s*((?:clone[\s\$\w\|]+)|(?:\b\w+)|(?:[\w\.]+)))(?:\s*\{\n((?:\s*(?:[\w\.\"]+\s)(?:\{{1}[^{}]+\}{1})?(?:.*\n?)+?)+)(?:\s*\}\n*))|((?:\b(?:set|push|add_layer|^version))\s*(?:(?:.*)+?)|(?:end_group))"

    def __init__(self, input_string):
        if os.path.isfile(input_string):
            self.__result = list(self.from_file(input_string))
        elif isinstance(input_string, str):
            self.__result = list(self.parse_nuke_script(input_string))
        else:
            raise Exception("input_string should be either .nk file or string")

    @classmethod
    def parse_nuke_script(cls, script_text):
        script_text = script_text.replace("\r", "")
        last_node_line_end = last_node_content_start = None
        node_data = []
        node_matches = [m for m in re.finditer(cls.node_pattern, script_text, re.MULTILINE)]
        for i, match in enumerate(node_matches):
            node_class, node_content, stack_statement = match.groups()
            this_node_start = match.start()
            if node_data and last_node_line_end != this_node_start:
                last_node_correct_content = script_text[last_node_content_start:this_node_start]
                last = node_data.pop(-1)
                node_data.append((last[0], last_node_correct_content, last[2]))
            node_data.append((node_class, node_content, stack_statement))
            last_node_line_end = match.end()
            last_node_content_start = match.start(2)

        for node_class, node_content, stack_statement in node_data:
            knobs = []
            inputs = ""
            user_knobs = []
            last_knob = None
            last_knob_line_end = last_knob_value_start = None
            if node_content is None:
                node_content = ""
            for knob_match in re.finditer(cls.knob_pattern, node_content, re.MULTILINE):
                _spaces, knob_name, knob_value = knob_match.groups()
                this_knob_line_start = knob_match.start()

                if knob_name == "addUserKnob":
                    user_knob_match = re.match(cls.user_knob_pattern, knob_value)
                    knob_id = user_knob_name = ""
                    if user_knob_match:
                        knob_id, user_knob_name = user_knob_match.groups()
                    user_knobs.append((user_knob_name, knob_id, knob_value))
                else:
                    if knobs:
                        if last_knob_line_end + 1 != this_knob_line_start:
                            last_knob_correct_value = node_content[last_knob_value_start:this_knob_line_start]
                            knobs.pop(-1)
                            knobs.append((last_knob, last_knob_correct_value))
                    else:
                        # if first knob script is inputs then its note knob, but inputs number
                        if knob_name == "inputs":
                            inputs = knob_value
                            continue

                    knobs.append((knob_name, knob_value))

                last_knob = knob_name
                last_knob_line_end = knob_match.end()
                last_knob_value_start = this_knob_line_start + len(_spaces) + len(knob_name)

            type_ = var = stack_index = None
            if not knobs:
                match = re.match(cls.stack_command_pattern, stack_statement)
                if match:
                    type_ = match.group(1)
                    var = match.group(2)
                    stack_index = match.group(3)
                    node_class = None
            else:
                type_ = "node"
                clone_match = re.match(cls.clone_pattern, node_class)
                if clone_match:
                    type_ = "clone"
                    if clone_match.group(2):
                        node_class = None
                        var = clone_match.group(2)
                    elif clone_match.group(3):
                        node_class = clone_match.group(3)
                        var = None

            yield {
                "type": type_,
                "class": node_class,
                "knobs": OrderedDict(knobs),
                "inputs": inputs,
                "user_knobs": user_knobs,
                "var": var,
                "stack_index": stack_index,
                "node_content": node_content
            }

    @classmethod
    def from_text(cls, text):
        return cls.parse_nuke_script(text)

    @classmethod
    def from_file(cls, file_path):
        if not os.path.exists(file_path):
            raise Exception("file {}  not found".format(file_path))

        with open(file_path, "r") as file_open:
            text = file_open.read()
        return cls.parse_nuke_script(text)

