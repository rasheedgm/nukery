# nukery

##### Nukery: A Lightweight Nuke Scripting Mock

#### What is Nukery?

Nukery is a Python-based mock library that simulates essential functionalities of the Nuke compositing software. It enables you to read Nuke script files (.nk) and perform basic operations commonly used with the Nuke Python library, all without requiring a Nuke license.

#### Why Nukery?

**Accessibility:** Nukery provides an accessible way to work with Nuke scripts even if you don't have access to the full Nuke application.

**Prototyping:** Quickly prototype and test Nuke scripts without the overhead of launching the complete software.

**Learning:** Nukery can be a valuable tool for learning the structure and syntax of Nuke scripts.

#### What Nukery Can Do

Reads and parses Nuke script files.
Provides access to basic script elements like nodes, properties, and connections.
Allows for limited manipulation of script elements (depending on implementation scope).

#### What Nukery Cannot Do

Does not directly render or composite images like Nuke.

<sub>(thanks to gemini)</sub>

### Usage
```python
import nukery

# open nuke script
nukery.script_open("/file/path/file.nk")

# get all nodes in the session
nukery.all_nodes()

# get selected nodes
nukery.selected_nodes()
```
Nukery has most commonly used methods(more to add)

here is the list of methods available.
```python
    'all_nodes',
    'selected_node',
    'selected_nodes',
    'script_open',
    'save_script_as',
    'delete',
    'script_clear',
    'to_node',
    'node_copy',
    'node_paste',
    'create_node',
    'clear_selection',
    'get_script_text',
```

### Example 

```python
import nukery

nukery.create_node("Constant")
nukery.create_node("Grade")
nukery.create_node("Transform")

print(nukery.get_script_text())
```
##### result
```
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
#### connect input
```python
import nukery

constant = nukery.create_node("Constant")
grade = nukery.create_node("Grade")
transform = nukery.create_node("Transform")

transform.set_input(0, constant)
print(nukery.get_script_text())
```
##### result
```
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

### Work in multiple sessions
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
##### result
```
Session1 [<Node(Grade1) at 3003785733008>]
Session2 [<Node(Transform1) at 3003788381712>]
[]
```


### Parsing nuke script
nuke script will be parsed with string parsing using regex. Parser returns dict list as result.

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

the result dict will be something like this

```python
{
    'type': 'node', 
    'class': 'Grade', 
    'knobs': OrderedDict([
        ('name', 'Garde1'), 
        ('xpos', '0'), 
        ('ypos', '0'), 
        ('white', '1.2')
    ]), 
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
