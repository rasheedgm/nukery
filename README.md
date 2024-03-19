
# Nukery: A Lightweight Nuke Scripting Mock

## Introduction
**Nukery** is a Python library designed to emulate the core features of the Nuke compositing software. It allows users to read and manipulate Nuke script files (.nk) using common operations from the Nuke Python API, all without the need for a Nuke license.

## Why Nukery?
- **Accessibility**: Nukery makes it possible to handle Nuke scripts even without the full Nuke application.
- **Prototyping**: Test and prototype Nuke scripts swiftly, bypassing the need to launch the entire software suite.
- **Education**: An excellent resource for those looking to understand Nuke script structures and syntax.

## Capabilities of Nukery
- Reads and interprets Nuke script files.
- Grants access to script components such as nodes, properties, and connections.
- Permits elementary script element manipulation within the scope of implementation.

## Limitations of Nukery
- Nukery is not equipped to render or composite images as Nuke does.

## Getting Started
```python
import nukery

# Load a Nuke script
nukery.script_open("/path/to/script.nk")

# Retrieve all nodes in the current session
nodes = nukery.all_nodes()

# Fetch selected nodes
selected = nukery.selected_nodes()
```

## Available Methods
Nukery includes the following commonly used methods, with more on the horizon:
- `all_nodes`
- `selected_node`
- `selected_nodes`
- `script_open`
- `save_script_as`
- `delete`
- `script_clear`
- `to_node`
- `node_copy`
- `node_paste`
- `create_node`
- `clear_selection`
- `get_script_text`

## Examples 
### Creating Nodes 
```python
import nukery

nukery.create_node("Constant")
nukery.create_node("Grade")
nukery.create_node("Transform")

print(nukery.get_script_text())
```
#### result
```tcl
Constant {
 inputs 0
 ypos 0
 xpos 0
 name Constant1
}
Grade {
 ypos 50
 xpos 0
 name Grade1
}
Transform {
 ypos 100
 xpos 0
 name Transform1
 selected true
}
```
### Connecting Input
```python
import nukery

constant = nukery.create_node("Constant")
grade = nukery.create_node("Grade")
transform = nukery.create_node("Transform")

transform.set_input(0, constant)
print(nukery.get_script_text())
```
#### result
```tcl
Constant {
 inputs 0
 ypos 0
 xpos 0
 name Constant1
}
set Nc019c415 [stack 0]
Grade {
 ypos 50
 xpos 0
 name Grade1
}
push $Nc019c415
Transform {
 ypos 100
 xpos 0
 name Transform1
 selected true
}
```

### Working Across Multiple Sessions
```python
import nukery
from nukery.stack import StackStore

session1 = StackStore("Session1")
session2 = StackStore("Session2")

with session1:
    nukery.create_node("Grade")
    print("Session1", nukery.all_nodes())

with session2:
    nukery.create_node("Transform")
    print("Session2", nukery.all_nodes())

#default session
print(nukery.all_nodes())
```
#### result
```
Session1 [<Node(Grade1) at 3003785733008>]
Session2 [<Node(Transform1) at 3003788381712>]
[]
```


## Parsing Nuke Scripts
Nuke scripts are parsed using regex-based string parsing, returning a list of dictionaries as the result.
```python
from nukery.parser import NukeScriptParser

# to parse from file
NukeScriptParser.from_file("/file/path")

# to parse from string
text = """
Grade {
 name Garde1
 xpos 0
 ypos 0
 white 1.2
}
"""
NukeScriptParser.from_text(text)
```

The resulting dictionary structure is as follows:


```json
{
    'type': 'node', 
    'class': 'Grade', 
    'knobs': {
        'name': 'Grade1',
        'xpos': '0',
        'ypos': '0',
        'white': '1.2'
    }, 
    'inputs': '', 
    'user_knobs': [], 
    'var': None, 
    'stack_index': None, 
    'node_content': ' name Garde1\n xpos 0\n ypos 0\n white 1.2\n'
}
```
here type represent what type of script line is this, there are many types as below

`node` `set` `push` `add_layer` `end_group` `clone`

```
these are types i noticed in nuke script so far
```

... writing more



## Conclusion
Nukery is not foolproof, I have only tested it in basic scripts, I hope you find Nukery to be a useful addition to your toolkit. Happy scripting!