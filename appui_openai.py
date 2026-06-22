import streamlit as st
import json
import os
from openai import OpenAI

client = OpenAI()


def generate_ai_content(prompt):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You are a helpful content writer for event-based content."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.7
    )

    return response.choices[0].message.content


st.set_page_config(page_title="Event Content Studio", layout="wide")

if "page" not in st.session_state:
    st.session_state.page = "welcome"

if "generated_data" not in st.session_state:
    st.session_state.generated_data = {}

if "theme_mode" not in st.session_state:
    st.session_state.theme_mode = "Light"

# ---------------- THEME SETTINGS ----------------

st.sidebar.title("Theme Settings")

theme_mode = st.sidebar.selectbox(
    "Choose Theme",
    ["Light", "Dark", "Custom"]
)

background_color = "#FFFFFF"
text_color = "#000000"
button_color = "#4CAF50"

if theme_mode == "Dark":
    background_color = "#0E1117"
    text_color = "#FFFFFF"
    button_color = "#FF4B4B"

elif theme_mode == "Custom":
    background_color = st.sidebar.color_picker(
        "Background Color",
        "#F5F5F5"
    )

    text_color = st.sidebar.color_picker(
        "Text Color",
        "#000000"
    )

    button_color = st.sidebar.color_picker(
        "Button Color",
        "#4CAF50"
    )

st.markdown(
    f"""
    <style>
    .stApp {{
        background-color: {background_color};
        color: {text_color};
    }}

    h1, h2, h3, h4, h5, h6, p, label, div {{
        color: {text_color} !important;
    }}

    .stButton>button {{
        background-color: {button_color};
        color: white;
        border-radius: 10px;
        padding: 0.5em 1em;
        border: none;
    }}
    </style>
    """,
    unsafe_allow_html=True
)

# ---------------- WELCOME PAGE ----------------

if st.session_state.page == "welcome":

    st.title("Event Content Studio")
    st.subheader("Welcome")

    st.write(
        "This app helps create event-based content such as brochure, flyer, caption, report and reel content."
    )

    st.write(
        "Choose a theme from the sidebar and click below to start creating content."
    )

    if st.button("Start Creating"):
        st.session_state.page = "content_creation"
        st.rerun()

# ---------------- CONTENT CREATION PAGE ----------------

elif st.session_state.page == "content_creation":

    st.title("Content Creation Page")

    st.header("Event Details")

    organization_name = st.text_input("Organization Name")
    event_name = st.text_input("Event Name")

    start_date = st.date_input("Start Date")
    end_date = st.date_input("End Date")

    location = st.text_input("Location Name")
    location_map_link = st.text_input("Location Map Link")

    event_description = st.text_area("Event Description")
    event_type = st.text_input("Event Type")

    event_status = st.selectbox(
        "Event Status",
        ["Upcoming", "Completed"]
    )

    # ---------------- MEDIA ----------------

    st.header("Media Uploads")

    photos = st.file_uploader(
        "Upload Photos",
        accept_multiple_files=True,
        type=["jpg", "jpeg", "png"]
    )

    videos = st.file_uploader(
        "Upload Videos",
        accept_multiple_files=True,
        type=["mp4", "mov"]
    )

    # ---------------- FEEDBACK ----------------

    st.header("Feedback")

    audio_comments = st.text_area("Audio Comments")

    feedback_document = st.file_uploader(
        "Upload Feedback Document",
        type=["pdf"]
    )

    feedback_summary = st.text_area("Feedback Summary")

    # ---------------- OUTPUT ----------------

    st.header("Output Selection")

    expected_output = st.multiselect(
        "Expected Output",
        ["Brochure", "Flyer", "Caption", "Report", "Reel Content"]
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Back"):
            st.session_state.page = "welcome"
            st.rerun()

    with col2:

        if st.button("Generate Output"):

            if not organization_name or not event_name or not location or not event_type:

                st.error(
                    "Please fill in all required fields: Organization Name, Event Name, Location Name and Event Type."
                )

            else:

                os.makedirs("outputs", exist_ok=True)
                os.makedirs("assets/photos", exist_ok=True)
                os.makedirs("assets/videos", exist_ok=True)
                os.makedirs("assets/documents", exist_ok=True)

                photo_names = []

                if photos:
                    for photo in photos:

                        photo_path = os.path.join(
                            "assets/photos",
                            photo.name
                        )

                        with open(photo_path, "wb") as file:
                            file.write(photo.getbuffer())

                        photo_names.append(photo.name)

                video_names = []

                if videos:
                    for video in videos:

                        video_path = os.path.join(
                            "assets/videos",
                            video.name
                        )

                        with open(video_path, "wb") as file:
                            file.write(video.getbuffer())

                        video_names.append(video.name)

                feedback_doc_name = ""

                if feedback_document:

                    feedback_doc_path = os.path.join(
                        "assets/documents",
                        feedback_document.name
                    )

                    with open(feedback_doc_path, "wb") as file:
                        file.write(feedback_document.getbuffer())

                    feedback_doc_name = feedback_document.name

                data = {
                    "organization_name": organization_name,
                    "event_name": event_name,
                    "start_date": str(start_date),
                    "end_date": str(end_date),
                    "location": location,
                    "location_map_link": location_map_link,
                    "event_description": event_description,
                    "event_type": event_type,
                    "event_status": event_status,
                    "photos": photo_names,
                    "videos": video_names,
                    "audio_comments": audio_comments,
                    "feedback_document": feedback_doc_name,
                    "feedback_summary": feedback_summary,
                    "expected_output": expected_output
                }

                with open(
                    "outputs/event_data.json",
                    "w",
                    encoding="utf-8"
                ) as file:
                    json.dump(data, file, indent=4)

                generated_outputs = {}

                # ---------------- BROCHURE ----------------

                if "Brochure" in expected_output:

                    brochure = f"""
{event_name}

Join us for {event_type.lower()} at {location} from {start_date} to {end_date}.

{event_description}

Organized by: {organization_name}

Location Map: {location_map_link}
"""

                    with open(
                        "outputs/brochure.txt",
                        "w",
                        encoding="utf-8"
                    ) as file:
                        file.write(brochure)

                    generated_outputs["Brochure"] = brochure

                # ---------------- FLYER ----------------

                if "Flyer" in expected_output:

                    flyer = f"""
FLYER

{event_name}

Date: {start_date} to {end_date}
Location: {location}

{event_description}

Organized by: {organization_name}
"""

                    with open(
                        "outputs/flyer.txt",
                        "w",
                        encoding="utf-8"
                    ) as file:
                        file.write(flyer)

                    generated_outputs["Flyer"] = flyer

                # ---------------- CAPTION ----------------

                if "Caption" in expected_output:

                    caption_prompt = f"""
Create a social media caption for this event.

Organization Name: {organization_name}
Event Name: {event_name}
Start Date: {start_date}
End Date: {end_date}
Location: {location}
Location Map Link: {location_map_link}
Event Description: {event_description}
Event Type: {event_type}
Event Status: {event_status}

Feedback Summary: {feedback_summary}

Audio Comments: {audio_comments}
"""

                    caption = generate_ai_content(caption_prompt)

                    with open(
                        "outputs/caption.txt",
                        "w",
                        encoding="utf-8"
                    ) as file:
                        file.write(caption)

                    generated_outputs["Caption"] = caption

                # ---------------- REPORT ----------------

                if "Report" in expected_output:

                    report = f"""
Event Report

Organization Name: {organization_name}
Event Name: {event_name}
Start Date: {start_date}
End Date: {end_date}
Location: {location}
Location Map: {location_map_link}
Event Type: {event_type}
Status: {event_status}

Description:
{event_description}

Feedback Summary:
{feedback_summary}

Audio Comments:
{audio_comments}
"""

                    with open(
                        "outputs/report.txt",
                        "w",
                        encoding="utf-8"
                    ) as file:
                        file.write(report)

                    generated_outputs["Report"] = report

                # ---------------- REEL CONTENT ----------------

                if "Reel Content" in expected_output:

                    reel = f"""
Reel Content Idea

Highlights from {event_name}

Location: {location}
Date: {start_date} to {end_date}

Key Message:
{event_description}

Feedback Highlight:
{feedback_summary}
"""

                    with open(
                        "outputs/reel_content.txt",
                        "w",
                        encoding="utf-8"
                    ) as file:
                        file.write(reel)

                    generated_outputs["Reel Content"] = reel

                st.session_state.generated_data = generated_outputs
                st.session_state.page = "output"
                st.rerun()