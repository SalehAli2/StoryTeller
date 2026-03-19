from langgraph.graph import StateGraph, START, END
from agents import OrchestraState, story_writer_node, image_generator_node, orchestrator_node

def routing(state: OrchestraState) -> str:
    return state["next"]

def build_graph():
    graph = StateGraph(OrchestraState)

    graph.add_node("orch", orchestrator_node)
    graph.add_node("story_writer", story_writer_node)
    graph.add_node("image_generator", image_generator_node)

    graph.add_edge(START, "orch")
    graph.add_conditional_edges(
        "orch",
        routing,
        {
            "story_writer": "story_writer",
            "image_generator": "image_generator",
            "end": END
        }
    )
    graph.add_edge("story_writer", "orch")
    graph.add_edge("image_generator", "orch")

    return graph.compile()