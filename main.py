import streamlit as st
import asyncio
from io import BytesIO
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

# Set page config at the very beginning
st.set_page_config(layout="wide", page_title="צ'אט עם דמויות ממלחמת הכוכבים", page_icon="🌟")

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

def fetch_character():
    char_id = random.randint(1, 88)
    print(char_id)
    url = f"https://rawcdn.githack.com/akabab/starwars-api/0.2.1/api/id/{char_id}.json"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        st.error(f"שגיאה בטעינת הדמות: {str(e)}")
        return None

# Add a new function to force a new character fetch
@st.cache_data
def cached_fetch_character(_):
    return fetch_character()

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


def get_image(image, char_id):
    return CHARACTER_IMAGES.get(str(int(char_id)), image)

def display_character(char):
    if not char:
        return

    character_name = char.get('name', 'שם לא ידוע')
    st.session_state['character_name'] = character_name
    
    # Display character name as centered title with gold glow effect
    st.markdown(f"""
        <h1 class="character-title">
            {character_name}
        </h1>
        <style>
            .character-title {{
                text-align: right;
                font-size: 4vw;
                margin-bottom: 1px;
                color: #FFD700; /* Gold color */
                text-shadow: 0 0 10px #FFD700, 0 0 20px #FFD700, 0 0 30px #FFD700; /* Gold glow effect */
                font-family: 'Orbitron', sans-serif;
            }}
            .info h3 {{
                font-size: 100%;
                margin-bottom: 1px;
            }}
            /* Responsive styles */
            @media (min-width: 768px) {{
            .character-name {{
                font-size: 4vw; /* Smaller on larger screens */
            }}
            .info h3 {{
                font-size: 2vw; /* Smaller on larger screens */
            }}
        }}
        /* Ensure minimum font size on very small screens */
        @media (min-width: 768px) {{
            .character-name {{
                font-size: 4vw; /* Smaller on larger screens */
            }}
            .info h3 {{
                font-size: 2vw; /* Smaller on larger screens */
            }}
        }}
        /* Ensure minimum font size on very small screens */
        @media (max-width: 480px) {{
            .character-name {{
                font-size: 2rem !important; /* Use rem for better scaling */
            }}
            .info h3 {{
                font-size: 1rem !important; /* Use rem for better scaling */
            }}
        }}
        </style>
    """, unsafe_allow_html=True)

    # Create two columns
    col1, col2 = st.columns(2)

    # Column 1: Character information
    with col1:
        descriptive_info = "".join([
            create_descriptive_information(title, key, char.get(key))
            for title, key in [
                ('זן', 'species'), ('גובה', 'height'), ('מגדר', 'gender'),
                ('עולם הבית', 'homeworld'), ('צבע שיער', 'hairColor'),
                ('צבע עיניים', 'eyeColor'), ('צבע עור', 'skinColor'),
                ('משקל', 'weight')
            ]
        ])
        st.markdown(f"<div class='info'>{descriptive_info}</div>", unsafe_allow_html=True)

    # Column 2: Images
    with col2:
        image_url = get_image(char.get('image'), char.get('id'))
        st.image(image_url, width=300)
        
        with st.spinner('טוען דמות מצוירת...'):
            generates_hand_drawn_cartoon_style_images(char.get('name'), character_name)

# Update the create_descriptive_information function
def create_descriptive_information(title, key, value):
    
    if key in ['height', 'weight']:
        converted_value = convert_height_weight(key, value)
    else:
        converted_value = translate_to_hebrew(str(value)) if value else ""
    
    return f"<h3>{title}: {converted_value}</h3>" if converted_value else ""


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

def load_new_character():
    # Clear the cache for cached_fetch_character
    cached_fetch_character.clear()
    # Fetch a new character with a random parameter to bypass cache
    st.session_state.character = cached_fetch_character(random.random())
    st.session_state.messages = [{"role": "assistant", "content": "הי 👋"}]

async def main():
    title, image_path, footer_content = initialize()
    
    st.markdown(f"""
    <h1 class="character-name">
        {title}
    </h1>
    <style>
        @keyframes sparkle-red {{
            0% {{ text-shadow: 0 0 10px #FF0000, 0 0 20px #FF0000, 0 0 30px #FF0000; }}
            25% {{ text-shadow: 0 0 10px #DC143C, 0 0 20px #DC143C, 0 0 30px #DC143C; }}
            50% {{ text-shadow: 0 0 10px #B22222, 0 0 20px #B22222, 0 0 30px #B22222; }}
            75% {{ text-shadow: 0 0 10px #8B0000, 0 0 20px #8B0000, 0 0 30px #8B0000; }}
            100% {{ text-shadow: 0 0 10px #FF0000, 0 0 20px #FF0000, 0 0 30px #FF0000; }}
        }}
        
        .character-name {{
            text-align: right;
            font-size: 8vw; /* Default to a responsive size */
            margin-bottom: 1px;
            font-family: 'Orbitron', sans-serif;
            font-weight: 600;
            color: #FF0000;
            animation: sparkle-red 2s infinite alternate;
        }}
        .info h3 {{
            font-size: 4vw; /* Default to a responsive size */
            margin-bottom: 1px;
        }}
        /* Responsive styles */
        @media (min-width: 768px) {{
            .character-name {{
                font-size: 4vw; /* Smaller on larger screens */
            }}
            .info h3 {{
                font-size: 2vw; /* Smaller on larger screens */
            }}
        }}
        /* Ensure minimum font size on very small screens */
        @media (max-width: 480px) {{
            .character-name {{
                font-size: 2rem !important; /* Use rem for better scaling */
            }}
            .info h3 {{
                font-size: 1rem !important; /* Use rem for better scaling */
            }}
        }}
    </style>
""", unsafe_allow_html=True)

    with st.expander('אודות האפליקציה - נוצרה ע"י שגיא בר און'):
        st.markdown('''
         אפליקציית Star Wars Chat & Art מציעה חוויה ייחודית של שילוב בין עולם הדמיון והמציאות. 
                    
        תהנו מתמונות אמיתיות של דמויות מ-Star Wars, לצד תמונות מצוירות בסגנון וינטג' המעניקות תחושה קלאסית ומעוררת נוסטלגיה. 
                            
        אך זה לא הכל – תוכלו לשוחח עם הדמויות האהובות דרך צ'אט, ולקבל תשובות ישירות מהן! 
                            
        האפליקציה מציעה חווית שימוש אינטראקטיבית ומרהיבה, המשלבת אומנות וחדשנות בתקשורת עם הדמויות האייקוניות של סדרת סרטי המדע הבדיוני המפורסמת בעולם.
        ''')        

    if image_path:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.image(image_path, use_column_width=True)

    if st.button("טען דמות חדשה"):
        load_new_character()
        st.rerun()

    if 'character' not in st.session_state or not st.session_state.character:
        with st.spinner('טוען דמות ראשונית...'):
            st.session_state.character = cached_fetch_character(random.random())
    
    if st.session_state.character:
        display_character(st.session_state.character)
        if "messages" not in st.session_state:
            st.session_state.messages = [{"role": "assistant", "content": "הי 👋"}]
    
    create_chatbot()

    # Display footer content
    st.markdown(footer_content, unsafe_allow_html=True)    

    # Display user count after the chatbot
    user_count = get_user_count(formatted=True)
    st.markdown(f"<p class='user-count' style='color: #4B0082;'>סה\"כ משתמשים: {user_count}</p>", unsafe_allow_html=True)

async def send_telegram_message_and_file(message, file_path):
    sender = st.session_state.telegram_sender
    try:
        await sender.send_document(file_path, message)
    finally:
        await sender.close_session()

if __name__ == "__main__":
    if 'telegram_sender' not in st.session_state:
        st.session_state.telegram_sender = TelegramSender()
    if 'counted' not in st.session_state:
        st.session_state.counted = True
        increment_user_count()
    initialize_user_count()
    asyncio.run(main())