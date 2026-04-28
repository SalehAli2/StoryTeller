from langgraph.graph import add_messages
from typing_extensions import List, Optional, TypedDict
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langchain_core.messages import (
    SystemMessage,
    HumanMessage,
    AnyMessage
)
from typing import Literal

from dotenv import load_dotenv
import urllib.parse
import requests
import base64
import random
import time
import os
load_dotenv()

class StoryState(TypedDict):
    topic: str
    story: str
    scenes: list[str]
    character_sheet: str
    image_prompts: list[str]
    images: list[str]
    current_scene_index: int
    _current_image_index: int  # 👈 add this
    next: str  


from langchain_groq import ChatGroq
llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.7)
# Story writer agent
class Story(BaseModel):
    title: str = Field(description="Story title")
    content: str = Field(description="Full Story content")


story_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a creative story writer. write vivid, visual stories"),
    ("human", "Write a short story about: {topic}")
])

story_writer = story_prompt | llm.with_structured_output(Story)


def story_writer_node(state: StoryState):
    topic = state["topic"]
    story = story_writer.invoke({"topic": topic})
    return {"story": story.content}


#Story Segmentation Agent

class StorySegments(BaseModel):
    scenes: list[str] = Field(
        description="List of 3-5 scenes from the story, each self-contained"
    )

segmentation_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a story segmentation expert. 
     Split stories into distinct visual scenes."""),
    ("human", """Split this story into 3-5 distinct visual scenes.
     Each scene should be self-contained and visually descriptive.
     STORY: {story}""")
])

segmentation_agent = segmentation_prompt | llm.with_structured_output(StorySegments)

def segmentation_node(state: StoryState):
    result = segmentation_agent.invoke({"story": state["story"]})
    return {"scenes": result.scenes, "current_scene_index": 0}

#Story Segmentation Agent

class ImagePrompt(BaseModel):
    image_prompts: list[str] = Field(
        description="List of image generation prompts, one per scene"
    )
image_prompt_template = ChatPromptTemplate.from_messages([
    ("system", """You are an expert at writing prompts for FLUX image generation.
     
     Rules for good prompts:
     - Keep prompts under 200 characters
     - Lead with the most important visual element
     - Include art style in every prompt
     - Be specific about lighting, mood, composition
     - Weave character descriptors naturally, don't just prepend them
     - Format: [art style], [main subject + action], [setting], [lighting], [mood]
     """),
    ("human", """CHARACTER SHEET (weave into each prompt naturally):
     {character_sheet}
     
     Generate one focused image prompt per scene.
     Each prompt should feel like a movie frame description.
     
     SCENES:
     {scenes}
     
     Return one prompt per scene.""")  # removed {num_scenes}
])

image_prompt_agent = image_prompt_template | llm.with_structured_output(ImagePrompt)



def image_prompt_node(state: StoryState) -> StoryState:
    result = image_prompt_agent.invoke({"scenes": state["scenes"],"story": state["story"],"character_sheet": state["character_sheet"]})
    return {"image_prompts": result.image_prompts}








HF_API_KEY = os.getenv("HF_API_KEY")

story_seed = random.randint(1, 9999)
def image_generator_node(state: StoryState) -> StoryState:
    images = []
    seed = state.get("story_seed", random.randint(1, 9999))
    negative = "blurry, low quality, distorted, deformed, ugly, text, watermark"
    for i, prompt in enumerate(state["image_prompts"]):
        try:
            encoded_prompt = urllib.parse.quote(prompt[:300])
            encoded_negative = urllib.parse.quote(negative)
            url = (
                f"https://image.pollinations.ai/prompt/{encoded_prompt}"
                f"?model=flux"
                f"&negative={encoded_negative}"
                f"&nologo=true"
                f"&seed={seed}"  # same seed for consistency
                f"&width=768&height=512"  # better aspect ratio
            )
            response = requests.get(url, timeout=120)
            if response.status_code == 200:
                img_b64 = base64.b64encode(response.content).decode("utf-8")
                images.append(f"data:image/jpeg;base64,{img_b64}")
            else:
                images.append(None)
        except Exception as e:
            print(f"Image generation failed: {e}")
            images.append(None)
    return {"images": images}





class CharacterSheet(BaseModel):
    descriptors: str = Field(
        description="A single detailed visual description string covering all main characters, art style, color palette, and setting aesthetic. Will be prepended to every image prompt."
    )

character_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are an expert at creating style guides for AI image generation.
     Create a compact visual consistency descriptor."""),
    ("human", """Analyze the story and create a visual consistency guide.

     Include:
     - Art style (e.g. 'digital painting, cinematic', 'watercolor illustration', 'anime style')
     - Color palette (e.g. 'warm golden tones', 'cool blues and purples')  
     - Main character appearance (be very specific — hair, eyes, clothing, build)
     - Setting aesthetic (e.g. 'cyberpunk city', 'enchanted forest')
     - Lighting style (e.g. 'soft diffused light', 'dramatic side lighting')
     
     Keep it under 100 words. This will be used in every image prompt.
     
     STORY: {story}""")
])

character_extractor = character_prompt | llm.with_structured_output(CharacterSheet)
def character_extractor_node(state: StoryState) -> StoryState:
    result = character_extractor.invoke({"story": state["story"]})
    return {"character_sheet": result.descriptors}


class OrchestratorDecision(BaseModel):
    next: Literal["story_writer", "segmentation", "character_extractor", "image_prompt", "image_generator", "end"]
    reasoning: str = Field(description="Why this next step was chosen")


orchestrator_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are an orchestrator managing a story generation pipeline.
     The pipeline order is: story_writer → segmentation → character_extractor 
     → image_prompt → image_generator → end.
     Always follow this exact order based on what's missing."""),
    ("human", """Current state:
     - Story written: {has_story}
     - Scenes segmented: {has_scenes}
     - Character sheet extracted: {has_character_sheet}
     - Image prompts generated: {has_prompts}
     - Images generated: {has_images}
     
     What should be the next step?""")
])

orchestrator = orchestrator_prompt | llm.with_structured_output(OrchestratorDecision)

def orchestrator_node(state: StoryState) -> StoryState:
    decision = orchestrator.invoke({
        "has_story": bool(state.get("story")),
        "has_scenes": bool(state.get("scenes")),
        "has_character_sheet": bool(state.get("character_sheet")),  
        "has_prompts": bool(state.get("image_prompts")),
        "has_images": bool(state.get("images"))
    })
    return {"next": decision.next}


