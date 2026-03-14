import streamlit as st
from graph import build_graph


st.title("🎭 Orchestra Agent")
st.subheader("Story Writer + Image Generator")

topic = st.text_input("Enter a topic:", placeholder="e.g. a lonely astronaut who finds a garden on Mars")

if st.button("Generate"):
    if topic.strip() == "":
        st.warning("Please enter a topic first!")
    else:
        with st.spinner("Writing story and generating image..."):
            graph = build_graph()
            result = graph.invoke({
                "topic": topic,
                "story": "",
                "image_prompt": "",
                "image_url": ""
            })

        st.markdown("## 📖 Story")
        st.write(result["story"])

        st.markdown("## 🎨 Image")
        st.image(result["image_url"], caption=result["image_prompt"])