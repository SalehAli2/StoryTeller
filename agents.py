from langgraph.graph import add_messages
from typing_extensions import List, Optional, TypedDict
from langchain_core.messages import (
    SystemMessage,
    HumanMessage,
    AnyMessage
)

from dotenv import load_dotenv
import urllib.parse
import requests
import base64
import random
import time
import os

class OrchestraState(TypedDict):
    topic: str #user input
    story: str #filled by story writer node
    image_prompt: str #extracted from story
    image_url: str #filled by image generator node
    next: str

    
def orchestrator_node(state: OrchestraState) -> OrchestraState:
    if not state["story"]:
        state["next"] = "story_writer"
    elif not state["image_url"]:
        state["next"] = "image_generator"
    else:
        state["next"] = "end"
    return state

load_dotenv()
from langchain_groq import ChatGroq
llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0.7)
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


HF_API_KEY = os.getenv("HF_API_KEY")

def image_generator_node(state: OrchestraState) -> OrchestraState:
    prompt = state.get("image_prompt") or state.get("topic") or "a magical story scene"
    prompt_short = prompt[:300].replace("\n", " ").strip()

    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    payload = {"inputs": prompt_short}

    try:
        response = requests.post(
                "https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-schnell",
                headers=headers,
                json=payload,
                timeout=60
                )
        if response.status_code == 200:
            img_b64 = base64.b64encode(response.content).decode("utf-8")
            state["image_url"] = f"data:image/jpeg;base64,{img_b64}"
        else:
            print(f"HF error: {response.status_code} - {response.text}")
            state["image_url"] = None
    except Exception as e:
        print(f"Image generation failed: {e}")
        state["image_url"] = None

    return state