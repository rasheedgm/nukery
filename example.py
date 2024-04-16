import nukery

file_path = "C:\\nukery\\scripts\\temp.nk"

# open a nuke script to the session
nukery.script_open(file_path)

# get all nodes in the script, from current context and current session.
nukery.all_nodes()
# context and session example can be found in the page.

# get all nodes of type 'Read'
nukery.all_nodes('Read')

# get all nodes form a group
nukery.all_nodes(group='Group1')
# or
nukery.all_nodes(group='root.Group1')

# get all nodes recursively
nukery.all_nodes(recursive=True)

# get one node by name
grade1 = nukery.to_node('Grade1')

# set a node selected
grade1.set_selected(True)

# get all selected nodes from the session and context
nukery.selected_nodes()

# get last selected node, this will return last in the selected list equal to selected_nodes()[-1]
nukery.selected_node()

# save script to file
nukery.save_script_as(file_path)
# note nukery doesn't have scrip_save intentionally, I don't want to override actual file.
# save_script_as will not check file exits, it will override if exists.

# copy selected nodes to a file
nukery.node_copy(file_path)
# if file path is not provided selected nodes will be copied to clipboard

# paste nodes from a file, this will paste nodes form clipboard if file_path is not provided
nukery.node_paste(file_path)

# set input to node
grade = nukery.to_node('Grade1')
merge = nukery.to_node('Grade2')
merge.set_input(0, grade)

# delete node
grade = nukery.to_node('Grade1')
nukery.delete(grade)

# create node
nukery.create_node('Grade')

# create node with knob values
nukery.create_node('Grade', white=1.2, xpos=101)

# all of these can be done in multiple sessions
session1 = nukery.SessionStore("Session1")
with session1:
    nukery.script_open(file_path)
    for node in nukery.all_nodes():
        print(node.name)

session2 = nukery.SessionStore("Session2")
with session2:
    nukery.script_open(file_path)
    for node in nukery.all_nodes():
        print(node.name)

# you can also run all methods in different node context as well.
# to run in Group1
group1 = nukery.create_node('Group')
with group1:
    for node in nukery.all_nodes():
        print(node.name)

    # create new node within group
    nukery.create_node("Transform")


# let's see how can I build a fresh nuke script, from scratch.
root = nukery.create_node(
    "Root",
    first=1,
    last=1001,
    format="1920 1080 0 0 1920 1080 1 HD_1080"
)
read = nukery.create_node(
    "Read",
    file="/file/path/file.###.exr",
    first=1,
    last=1001,
)

nukery.script_clear()
transform = nukery.create_node("Transform")
grade = nukery.create_node("Grade")
merge = nukery.create_node("Merge2", operation="plus")
# when you are creating nodes in sequence by default input zero will be connected to last node
# but if you want to connect other inputs then you will connect like this.
merge.set_input(1, read)
write = nukery.create_node(
    "Write",
    file="/file/path/file.####.exr",
    file_type="exr",
    channels="rgba"
)
print(nukery.get_script_text())

#  this will create a script like below
"""
Root {
 inputs 0
 first 1
 last 1001
 format 1920 1080 0 0 1920 1080 1 HD_1080
 ypos 0
 xpos 0
}
Read {
 inputs 0
 file /file/path/file.###.exr
 first 1
 last 1001
 ypos 50
 xpos 0
 name Read1
}
set N4dd60ff0 [stack 0]
push $N4dd60ff0
Transform {
 ypos 100
 xpos 0
 name Transform1
}
Grade {
 ypos 150
 xpos 0
 name Grade1
}
Merge2 {
 inputs 2
 operation plus
 ypos 200
 xpos 0
 name Merge21
}
Write {
 file /file/path/file.####.exr
 file_type exr
 channels rgba
 ypos 250
 xpos 0
 selected true
 name Write1
}
"""