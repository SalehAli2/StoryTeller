from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from graph import build_graph
from dotenv import load_dotenv
import json
load_dotenv()

app = FastAPI()
graph = build_graph()

class StoryRequest(BaseModel):
    topic: str

import requests as http_requests
import urllib.parse
import random
import base64
import os

import asyncio

async def event_stream(topic: str):
    state = {"topic": topic}
    image_prompts = []

    for step in graph.stream(state):
        node_name = list(step.keys())[0]
        node_output = step[node_name]

        if node_name == "story_writer":
            yield f"data: {json.dumps({'type': 'story', 'content': node_output.get('story')})}\n\n"

        elif node_name == "segmentation":
            yield f"data: {json.dumps({'type': 'scenes', 'content': node_output.get('scenes')})}\n\n"

        elif node_name == "image_prompt":
            image_prompts = node_output.get("image_prompts", [])
            # Send keepalive immediately before slow image generation starts
            yield f"data: {json.dumps({'type': 'status', 'content': 'Generating images...'})}\n\n"

        elif node_name == "image_generator":
            pass

        else:
            yield f": keepalive\n\n"

        # Stream images one by one with keepalives between them
        if node_name == "image_prompt" and image_prompts:
            for i, prompt in enumerate(image_prompts):
                # Send status before each image so connection stays alive
                yield f"data: {json.dumps({'type': 'status', 'content': f'Generating image {i+1} of {len(image_prompts)}...'})}\n\n"
                
                try:
                    encoded = urllib.parse.quote(prompt[:300])
                    url = f"https://image.pollinations.ai/prompt/{encoded}?model=flux&nologo=true&seed={random.randint(1,9999)}"
                    resp = http_requests.get(url, timeout=120)
                    
                    if resp.status_code == 200:
                        img_b64 = base64.b64encode(resp.content).decode("utf-8")
                        yield f"data: {json.dumps({'type': 'image', 'index': i, 'content': f'data:image/jpeg;base64,{img_b64}'})}\n\n"
                    else:
                        yield f"data: {json.dumps({'type': 'image', 'index': i, 'content': None})}\n\n"
                        
                except Exception as e:
                    print(f"Image {i} failed: {e}")
                    yield f"data: {json.dumps({'type': 'image', 'index': i, 'content': None})}\n\n"

    yield f"data: {json.dumps({'type': 'done'})}\n\n"


@app.post("/generate")
async def generate(request: StoryRequest):
    return StreamingResponse(
        event_stream(request.topic),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # prevents nginx from buffering the stream
        }
    )