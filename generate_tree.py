"""Script to generate a visual Graphviz image of the SQLFluff AST."""

from sqlfluff.core import Linter, FluffConfig
from graphviz import Digraph

def draw_node(dot: Digraph, segment, parent_id: str = None):
    """Recursively traverse the segment and add nodes/edges to Graphviz."""
    node_id = str(id(segment))
    
    label = segment.get_type()
    if not segment.segments:
        label += f"\n'{segment.raw}'"
        
    dot.node(node_id, label)
    
    if parent_id:
        dot.edge(parent_id, node_id)
        
    for child in segment.segments:
        draw_node(dot, child, node_id)

def main():
    # 1. Parse the SQL file
    with open("test.sql", "r") as f:
        sql_text = f.read()
        
    # 2. Use SQLFluff Core to get the actual AST objects
    config = FluffConfig(overrides={"dialect": "mysql"})
    linter = Linter(config=config)
    
    # parse_string returns a ParsedString object
    parsed = linter.parse_string(sql_text)
    
    # .tree holds the true root segment of the AST
    root_segment = parsed.tree
    
    if not root_segment:
        print("Error: Could not parse the SQL file. Check your syntax.")
        return

    # 3. Build the Graph
    dot = Digraph(comment='SQL AST', format='png')
    dot.attr(rankdir='TB') # Top to Bottom
    
    draw_node(dot, root_segment)
    
    # 4. Render the image
    dot.render('ast_output', view=False)
    print("AST image successfully generated as ast_output.png!")

if __name__ == "__main__":
    main()