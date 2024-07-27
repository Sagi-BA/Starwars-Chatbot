import streamlit as st
import requests
import random
import os
import re
import json
from PIL import Image
from gradio_client import Client
from deep_translator import GoogleTranslator
import groq
from functools import lru_cache
from dotenv import load_dotenv

# Initialize components
from utils.init import initialize
from utils.counter import initialize_user_count, increment_user_count, get_user_count
from utils.TelegramSender import TelegramSender

# Constants
UPLOAD_FOLDER = "uploads"
DATA_FOLDER = "data"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Load environment variables
load_dotenv()

# Groq API setup
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
groq_client = groq.Groq(api_key=GROQ_API_KEY)
GROQ_MODELS = os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile").split(",")

@st.cache_data
def load_character_images():
    try:
        with open(os.path.join(DATA_FOLDER, 'character_images.json'), 'r') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        st.error(f"Error loading character_images.json: {str(e)}")
        return {}

CHARACTER_IMAGES = load_character_images()

@lru_cache(maxsize=100)
def ask_groq(character_name, question):
    system_prompt = "You are an expert star wars guide. You always answer only in the context of Star Wars! The answers you return must be short and in Hebrew!"
    user_prompt = f"Your name is: {character_name} and I wanted to ask you:{question}"
    
    random.shuffle(GROQ_MODELS)
    
    for model in GROQ_MODELS:
        try:
            response = groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                model=model,
                temperature=0.0,
                max_tokens=int(os.getenv("GROQ_MAX_TOKENS", 1024)),
                stream=False,
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error with model {model}: {str(e)}. Trying next model.")
    
    return get_random_response()

@st.cache_data
def get_random_response(response_type="general"):
    responses = {
        "general": [
            'אין לי מושג!', 'הם מעולם לא אמרו לי!', 'איך אני אמור לדעת?',
            'אין לי מושג. מצטער!', "למה שלא תשאל אותם?", 'אממ...',
            'לא בטוח!', 'ממוצע, אולי? אני לא יודע!', 'כן'
        ],
        "planet": [
            'איפשהו בגלקסיה רחוקה, רחוקה...', 'כוכב לכת. כן, אני בטוח שזה היה כוכב לכת.',
            'איפשהו שם בחוץ...', 'כן', 'לא היית רוצה לדעת?', 'אני לא מספר!'
        ]
    }
    return random.choice(responses.get(response_type, responses["general"]))

def convert_height_weight(type_value, value):
    if not value:
        return get_random_response()
    unit = 'מטר' if type_value == 'height' else 'ק"ג'
    return f"{value} {unit}"

@st.cache_data
def fetch_character():
    char_id = random.randint(1, 88)
    url = f"https://rawcdn.githack.com/akabab/starwars-api/0.2.1/api/id/{char_id}.json"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        st.error(f"שגיאה בטעינת הדמות: {str(e)}")
        return None

@st.cache_resource
def get_translator():
    return GoogleTranslator(source='auto', target='iw')

def translate_to_hebrew(text):
    try:
        translator = get_translator()
        return translator.translate(text)
    except Exception as e:
        st.error(f"שגיאה בתרגום: {str(e)}")
        return text

def create_descriptive_information(title, value):
    translated_value = translate_to_hebrew(str(value)) if value else ""
    return f"<h3 id='{title}'>{title}: {translated_value}</h3>" if value else ""

def get_image(image, char_id):
    return CHARACTER_IMAGES.get(str(int(char_id)), image)

def display_character(char):
    if not char:
        return

    character_name = char.get('name', 'שם לא ידוע')
    st.session_state['character_name'] = character_name
    
    descriptive_info = "".join([
        create_descriptive_information(title, char.get(key))
        for title, key in [
            ('זן', 'species'), ('גובה', 'height'), ('מגדר', 'gender'),
            ('עולם הבית', 'homeworld'), ('צבע שיער', 'hairColor'),
            ('צבע עיניים', 'eyeColor'), ('צבע עור', 'skinColor'),
            ('משקל', 'weight')
        ]
    ])

    image_url = get_image(char.get('image'), char.get('id'))

    col1, col2 = st.columns([1, 1])
    with col1:
        st.markdown(f"<div class='info'><h1 id='name'>{character_name}</h1>{descriptive_info}</div>", unsafe_allow_html=True)

    with col2:
        st.markdown(f"<div class='image'><img src='{image_url}' width='300px'/></div>", unsafe_allow_html=True)
        with st.spinner('טוען דמות מצוירת...'):
            generates_hand_drawn_cartoon_style_images(char.get('name'), character_name)

def generates_hand_drawn_cartoon_style_images(prompt, character_name):
    filename = re.sub(r'[^\w\s]', '', character_name).replace(' ', '_') + ".jpg"
    dest_path = os.path.join(UPLOAD_FOLDER, filename)

    if not os.path.isfile(dest_path):
        prompt = f"{prompt} from Star Wars"
        client = Client("fujohnwang/alvdansen-littletinies")
        cartoon_style_image = client.predict(prompt, api_name="/predict")
        process_result(cartoon_style_image, dest_path)

    st.image(dest_path, width=300)

def process_result(result, filename):
    if isinstance(result, str):
        if os.path.isfile(result):
            img = Image.open(result)
        elif result.startswith(('http://', 'https://')):
            response = requests.get(result)
            if response.status_code == 200:
                img = Image.open(BytesIO(response.content))
            else:
                raise Exception(f"Failed to download image from URL: {result}")
        elif result.lower().endswith('.webp'):
            img = Image.open(result)
        else:
            raise Exception(f"Invalid result format: {result}")
    elif isinstance(result, Image.Image):
        img = result
    else:
        raise Exception(f"Unexpected result format: {type(result)}")

    img = img.convert('RGB')
    img.save(filename, 'JPEG')

def create_chatbot():
    character_name = st.session_state.get('character_name', "Echo")

    for message in st.session_state.get('messages', []):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    prompt = st.chat_input("מה שלומך?")

    if prompt:
        st.chat_message("user").markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("assistant"):
            with st.spinner('מחפש תשובה...'):
                response = ask_groq(character_name, prompt)
            st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})

def main():
    title, image_path, footer_content = initialize()

    st.title(title)

    if image_path:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.image(image_path, use_column_width=True)

    if st.button("טען דמות חדשה"):
        st.session_state.clear()
        st.session_state.character = fetch_character()
        st.session_state.messages = [{"role": "assistant", "content": "הי 👋"}]
        st.experimental_rerun()

    if 'character' not in st.session_state or not st.session_state.character:
        with st.spinner('טוען דמות ראשונית...'):
            st.session_state.character = fetch_character()
        if st.session_state.character:
            display_character(st.session_state.character)
            if "messages" not in st.session_state:
                st.session_state.messages = [{"role": "assistant", "content": "הי 👋"}]
    elif st.session_state.character:
        display_character(st.session_state.character)

    # Display footer content
    st.markdown(footer_content, unsafe_allow_html=True)

    # Display update information after the buttons
    st.markdown("<p style='text-align: center; color: #888;'>🖖 עודכן על ידי שגיא בר און ב 27/7/2024</p>", unsafe_allow_html=True)

    # Display user count after the chatbot
    user_count = get_user_count(formatted=True)
    st.markdown(f"<p class='user-count' style='color: #4B0082;'>סה\"כ משתמשים: {user_count}</p>", unsafe_allow_html=True)

    create_chatbot()
if __name__ == "__main__":
    main()