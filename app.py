import streamlit as st
import requests
import json

st.set_page_config(page_title="AI Storyteller", layout="wide")
st.title("📖 AI Story Generator")

topic = st.text_input("Enter a story topic", placeholder="e.g. a robot exploring mars")

if st.button("Generate Story") and topic:
    story_col, images_col = st.columns([1, 1])

    with story_col:
        st.subheader("Story")
        story_placeholder = st.empty()
        scenes_placeholder = st.empty()

    with images_col:
        st.subheader("Scenes")
        image_placeholders = []

    story_text = ""
    scenes_text = []
    image_slots = []

    with requests.post(
    "http://localhost:8000/generate",
    json={"topic": topic},
    stream=True,
    timeout=600
    ) as response:
        try:
            for line in response.iter_lines():
                if line and line.startswith(b"data: "):
                    raw = line[len(b"data: "):]
                    try:
                        data = json.loads(raw)
                    except json.JSONDecodeError:
                        continue

                    if data["type"] == "story":
                        story_text = data["content"]
                        story_placeholder.markdown(story_text)

                    elif data["type"] == "scenes":
                        scenes_text = data["content"]
                        with story_col:
                            scenes_placeholder.markdown(
                                "\n\n".join([f"**Scene {i+1}:** {s}" 
                                            for i, s in enumerate(scenes_text)])
                            )
                        with images_col:
                            for i in range(len(scenes_text)):
                                st.markdown(f"**Scene {i+1}**")
                                image_slots.append(st.empty())

                    elif data["type"] == "image":
                        i = data["index"]
                        img = data["content"]
                        if img and i < len(image_slots):
                            image_slots[i].image(img, use_column_width=True)
                        elif i < len(image_slots):
                            image_slots[i].warning("Image generation failed")

                    elif data["type"] == "status":
                        with story_col:
                            st.info(data["content"])

                    elif data["type"] == "done":
                        st.success("Story complete!")
                        break

        except requests.exceptions.ChunkedEncodingError:
            st.warning("Stream interrupted — showing what was generated so far.")
        except Exception as e:
            st.error(f"Unexpected error: {e}")