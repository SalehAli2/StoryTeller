from langgraph.graph import add_messages
from typing_extensions import List, Optional, TypedDict
from langchain_core.messages import (
    SystemMessage,
    HumanMessage,
    AnyMessage
)

from dotenv import load_dotenv
import urllib.parse
import os

class OrchestraState(TypedDict):
    topic: str #user input
    story: str #filled by story writer node
    image_prompt: str #extracted from story
    image_url: str #filled by image generator node

load_dotenv()
print("API KEY:", os.getenv("GOOGLE_API_KEY"))
from langchain_google_genai import ChatGoogleGenerativeAI
llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.7)
def story_writer_node(state: OrchestraState) -> OrchestraState:
    response = llm.invoke([
        SystemMessage(content = "You are a creative story writer."),
        HumanMessage(content = f"""Write a short story about: {state['topic']}
    At the end, on a new line write:
    IMAGE_PROMPT: <a vivid one-sentence visual scene from the story>""")
    ])

    full_text = response.content
    if "IMAGE_PROMPT:" in full_text:
        story, image_part = full_text.split("IMAGE_PROMPT:")
        image_prompt = image_part.strip()
    else:
        story = full_text
        image_prompt = state["topic"]
        
    return {**state, "story": story.strip(), "image_prompt": image_prompt}


def image_generator_node(state: OrchestraState) -> OrchestraState:
    encoded_prompt = urllib.parse.quote(state["image_prompt"])
    image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=768&height=512&nologo=true"
    return {**state, "image_url": image_url}
