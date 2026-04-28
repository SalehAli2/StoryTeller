from langgraph.graph import StateGraph, START, END
from agents import (StoryState, orchestrator_node, story_writer_node, 
                    image_generator_node, segmentation_node, 
                    image_prompt_node, character_extractor_node)

def routing(state: StoryState) -> str:
    return state["next"]

def build_graph():
    graph = StateGraph(StoryState)

    graph.add_node("orchestrator", orchestrator_node)
    graph.add_node("story_writer", story_writer_node)
    graph.add_node("segmentation", segmentation_node)
    graph.add_node("character_extractor", character_extractor_node)

    graph.add_node("image_prompt", image_prompt_node)
    graph.add_node("image_generator", image_generator_node)

    graph.add_edge(START, "orchestrator")
    graph.add_conditional_edges(
        "orchestrator",
        routing,
        {
            "story_writer": "story_writer",
            "segmentation": "segmentation",
            "character_extractor": "character_extractor",
            "image_prompt": "image_prompt",
            "image_generator": "image_generator",
            "end": END
        }
    )

    # All agents report back to orchestrator
    graph.add_edge("story_writer", "orchestrator")
    graph.add_edge("segmentation", "orchestrator")
    graph.add_edge("image_prompt", "orchestrator")
    graph.add_edge("character_extractor", "orchestrator")
    graph.add_edge("image_generator", "orchestrator")

    return graph.compile()