from langgraph.graph import StateGraph, END
from agents import OrchestraState, story_writer_node, image_generator_node

def build_graph():
    graph = StateGraph(OrchestraState)
    
    graph.add_node("story_writer", story_writer_node)
    graph.add_node("image_generator", image_generator_node)
    
    graph.set_entry_point("story_writer")
    graph.add_edge("story_writer", "image_generator")
    graph.add_edge("image_generator", END)
    
    return graph.compile()