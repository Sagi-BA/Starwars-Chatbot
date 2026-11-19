import streamlit as st
import base64
from io import BytesIO
import requests
import random
import os
import re
import json
from PIL import Image
from deep_translator import GoogleTranslator, MyMemoryTranslator
import groq
from dotenv import load_dotenv

# Initialize components
from utils.init import initialize
from utils.counter import initialize_user_count, increment_user_count, get_user_count
from utils.character_card import character_card
from utils.gallery import character_gallery
from utils.factions import get_side
from utils.sound import sound_effects

# Set page config at the very beginning
st.set_page_config(
    layout="wide", page_title="צ'אט עם דמויות ממלחמת הכוכבים", page_icon="🌟"
)

# Constants
UPLOAD_FOLDER = "uploads"
DATA_FOLDER = "data"
# Gallery thumbnails are served by Streamlit's static file serving (server.enableStaticServing)
THUMBS_FOLDER = os.path.join("static", "thumbs")
THUMBS_URL = "app/static/thumbs"
THUMB_SIZE = 160
CARDS_FOLDER = os.path.join("static", "cards")
CARDS_URL = "app/static/cards"
CARD_IMAGE_SIZE = 640
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

HOLO_LOADER = """
<div class="holo-loading">
  <span class="holo-bars"><i></i><i></i><i></i><i></i><i></i></span>
  <span>מקבל שידור הולוגרפי...</span>
</div>
"""

# Load environment variables
load_dotenv()

# Groq API setup
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
groq_client = groq.Groq(api_key=GROQ_API_KEY)
# llama-3.1-70b-versatile was decommissioned by Groq; default to currently available models
GROQ_MODELS = [
    m.strip()
    for m in os.getenv("GROQ_MODEL", "openai/gpt-oss-120b,openai/gpt-oss-20b").split(
        ","
    )
    if m.strip()
]
GROQ_MAX_TOKENS = int(os.getenv("GROQ_MAX_TOKENS", 1024))
CHAT_HISTORY_LIMIT = 10  # number of recent messages sent to the model

# Appended to every character prompt so answers stay in natural Hebrew only
HEBREW_ONLY_RULES = """LANGUAGE RULES (mandatory, override anything above):
- Reply ONLY in Hebrew. Never write English words or Latin letters.
- Write every name and term in Hebrew letters, e.g. דארת' ויידר, לורד, ג'דיי, סית', האימפריה, המורדים.
- Use real Hebrew words, not transliterated English (write "משתמש", not "יוזר").
- Keep the answer short and in the character's own voice.

חוקי שפה (חובה): ענה בעברית בלבד, בעברית טבעית ותקנית, בלי אף מילה או אות באנגלית."""

CHARACTER_PROMPTS_FILE = os.path.join(DATA_FOLDER, "character_prompts.json")

GREETING = "הי 👋"

CHAT_SUGGESTIONS = [
    "ספר לי על עצמך",
    "מי האויב הגדול שלך?",
    "מה הרגע הכי חשוב בחייך?",
    "איזו עצה יש לך בשבילי?",
]

# Fields shown on the character card: (Hebrew label, API key, icon)
STAT_FIELDS = [
    ("זן", "species", "🧬"),
    ("עולם הבית", "homeworld", "🪐"),
    ("גובה", "height", "📏"),
    ("משקל", "mass", "⚖️"),
    ("מגדר", "gender", "⚧"),
    ("צבע עיניים", "eyeColor", "👁️"),
    ("צבע שיער", "hairColor", "💇"),
    ("צבע עור", "skinColor", "🎨"),
]


@st.cache_data
def load_character_images():
    try:
        with open(os.path.join(DATA_FOLDER, "character_images.json"), "r") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        st.error(f"Error loading character_images.json: {str(e)}")
        return {}


CHARACTER_IMAGES = load_character_images()


def load_character_prompts():
    if os.path.exists(CHARACTER_PROMPTS_FILE):
        with open(CHARACTER_PROMPTS_FILE, "r") as file:
            return json.load(file)
    return {}


def save_character_prompt(character_name, prompt):
    prompts = load_character_prompts()
    prompts[character_name] = prompt
    with open(CHARACTER_PROMPTS_FILE, "w") as file:
        json.dump(prompts, file, indent=2)


def get_or_create_character_prompt(character_name):
    prompts = load_character_prompts()
    if character_name in prompts:
        return prompts[character_name]

    print("get_or_create_character_prompt")
    # If not found, ask Groq to create a prompt in English
    system_prompt = f"Create a system prompt for a Star Wars chatbot impersonating {character_name}. The prompt should capture the character's personality, speech patterns, and key traits. The response should be in English and start with 'You are {character_name}...'"

    response = groq_client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": "You are an expert on Star Wars characters and their personalities.",
            },
            {"role": "user", "content": system_prompt},
        ],
        model=GROQ_MODELS[0],  # Use the first model in the list
        temperature=0.0,
        max_tokens=GROQ_MAX_TOKENS,
        stream=False,
    )

    new_prompt = response.choices[0].message.content
    save_character_prompt(character_name, new_prompt)
    return new_prompt


# Safety net for the rare English word that slips into an answer
LATIN_WORD = re.compile(r"[A-Za-z][A-Za-z'\-]*")
STAR_WARS_TERMS = {
    "lord": "לורד",
    "darth": "דארת'",
    "vader": "ויידר",
    "sith": "סית'",
    "jedi": "ג'דיי",
    "force": "הכוח",
    "empire": "האימפריה",
    "galactic": "גלקטי",
    "galaxy": "גלקסיה",
    "rebel": "מורד",
    "rebels": "המורדים",
    "emperor": "הקיסר",
    "master": "מאסטר",
    "droid": "דרואיד",
    "droids": "דרואידים",
    "republic": "הרפובליקה",
    "user": "משתמש",
    "ok": "בסדר",
    "okay": "בסדר",
    "hello": "שלום",
    "hi": "היי",
    "yes": "כן",
    "no": "לא",
}


def to_hebrew_word(match):
    word = match.group(0)
    return STAR_WARS_TERMS.get(word.lower()) or translate_to_hebrew(word)


def hebrew_only(tokens):
    """Pass streamed text through, translating any whole word written in Latin letters."""
    buffer = ""
    for token in tokens:
        buffer += token
        cut = max(
            buffer.rfind(" "), buffer.rfind("\n")
        )  # hold back the last, maybe partial, word
        if cut >= 0:
            yield LATIN_WORD.sub(to_hebrew_word, buffer[: cut + 1])
            buffer = buffer[cut + 1 :]
    if buffer:
        yield LATIN_WORD.sub(to_hebrew_word, buffer)


def stream_character_answer(character_name, messages):
    """Stream the character's answer, token by token, using the recent conversation as context."""
    character_prompt = get_or_create_character_prompt(character_name)
    system_prompt = f"{character_prompt}\n\n{HEBREW_ONLY_RULES}"
    conversation = [
        {"role": m["role"], "content": m["content"]}
        for m in messages[-CHAT_HISTORY_LIMIT:]
    ]

    for model in random.sample(GROQ_MODELS, len(GROQ_MODELS)):
        produced_output = False
        try:
            stream = groq_client.chat.completions.create(
                messages=[{"role": "system", "content": system_prompt}, *conversation],
                model=model,
                temperature=0.0,
                max_tokens=GROQ_MAX_TOKENS,
                stream=True,
            )
            for chunk in stream:
                delta = chunk.choices[0].delta.content if chunk.choices else None
                if delta:
                    produced_output = True
                    yield delta
            if produced_output:
                return
            print(f"Empty response from model {model}. Trying next model.")
        except Exception as e:
            if produced_output:
                return  # keep the partial answer rather than mixing in another model's reply
            print(f"Error with model {model}: {str(e)}. Trying next model.")

    yield get_random_response()


def get_random_response(response_type="general"):
    responses = {
        "general": [
            "אין לי מושג!",
            "הם מעולם לא אמרו לי!",
            "איך אני אמור לדעת?",
            "אין לי מושג. מצטער!",
            "למה שלא תשאל אותם?",
            "אממ...",
            "לא בטוח!",
            "ממוצע, אולי? אני לא יודע!",
            "כן",
        ],
        "planet": [
            "איפשהו בגלקסיה רחוקה, רחוקה...",
            "כוכב לכת. כן, אני בטוח שזה היה כוכב לכת.",
            "איפשהו שם בחוץ...",
            "כן",
            "לא היית רוצה לדעת?",
            "אני לא מספר!",
        ],
    }
    return random.choice(responses.get(response_type, responses["general"]))


def convert_height_weight(type_value, value):
    if not value:
        return get_random_response()
    unit = "מטר" if type_value == "height" else 'ק"ג'
    return f"{value} {unit}"


CHARACTER_API_URLS = [
    "https://cdn.jsdelivr.net/gh/akabab/starwars-api@0.2.1/api/id/{}.json",
    "https://rawcdn.githack.com/akabab/starwars-api/0.2.1/api/id/{}.json",
]
ALL_CHARACTERS_URLS = [
    "https://cdn.jsdelivr.net/gh/akabab/starwars-api@0.2.1/api/all.json",
    "https://rawcdn.githack.com/akabab/starwars-api/0.2.1/api/all.json",
]
# IDs 1-88, except 17 which does not exist in the API
CHARACTER_IDS = [i for i in range(1, 89) if i != 17]


@st.cache_data(ttl=24 * 60 * 60, show_spinner=False)
def load_all_characters():
    """All characters in one request (used by the gallery); empty list if the API is unreachable."""
    for url in ALL_CHARACTERS_URLS:
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Failed to fetch all characters from {url}: {e}")
    return []


def fetch_character(char_id=None):
    """Fetch a character by id, or a random one (different from the current character)."""
    characters = {c["id"]: c for c in load_all_characters()}
    if char_id is None:
        current = (st.session_state.get("character") or {}).get("id")
        candidates = [i for i in (list(characters) or CHARACTER_IDS) if i != current]
        char_id = random.choice(candidates)
    print(char_id)
    if char_id in characters:
        return characters[char_id]

    last_error = None
    for url_template in CHARACTER_API_URLS:
        try:
            response = requests.get(url_template.format(char_id), timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            last_error = e
            print(f"Failed to fetch character {char_id} from {url_template}: {e}")
    st.error(f"שגיאה בטעינת הדמות: {str(last_error)}")
    return None


@st.cache_resource
def get_translators():
    return [
        GoogleTranslator(source="auto", target="iw"),
        MyMemoryTranslator(source="en-GB", target="he-IL"),
    ]


@st.cache_resource
def load_translations():
    """Reviewed Hebrew translations of every species/gender/color value in the API (instant, no network)."""
    try:
        with open(
            os.path.join(DATA_FOLDER, "translations.json"), "r", encoding="utf-8"
        ) as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading translations.json: {e}")
        return {}


@st.cache_data(show_spinner=False)
def translate_to_hebrew(text):
    known = load_translations().get(text.strip().lower())
    if known:
        return known
    # Unknown value: try each online translator in turn; if all fail, show the original English text
    for translator in get_translators():
        try:
            translated = translator.translate(text)
            if translated:
                return translated
        except Exception as e:
            print(f"Translation with {type(translator).__name__} failed: {e}")
    return text


def get_image(image, char_id):
    override = CHARACTER_IMAGES.get(str(int(char_id)))
    if override and override.startswith(("http://", "https://")):
        return override
    return image


def format_stat_value(key, value):
    if isinstance(value, list):
        value = ", ".join(str(v) for v in value)

    if key in ["height", "mass"]:
        return convert_height_weight(key, value)
    if key == "homeworld":
        return value.title() if value else ""
    return translate_to_hebrew(str(value)) if value else ""


@st.cache_data(show_spinner=False)
def build_character_stats(char):
    """Stats for the character card. Cached per character so random fallback answers stay stable."""
    stats = []
    for label, key, icon in STAT_FIELDS:
        value = format_stat_value(key, char.get(key))
        if value:
            stats.append({"label": label, "value": str(value), "icon": icon})
    return stats


def card_image_url(char_id, cartoon_path):
    """URL of a web-sized copy of the cartoon, served as a static file (falls back to an inline image)."""
    dest_path = os.path.join(CARDS_FOLDER, f"{char_id}.jpg")
    try:
        if not os.path.isfile(dest_path):
            os.makedirs(CARDS_FOLDER, exist_ok=True)
            with Image.open(cartoon_path) as img:
                img = img.convert("RGB")
                img.thumbnail((CARD_IMAGE_SIZE, CARD_IMAGE_SIZE), Image.LANCZOS)
                img.save(dest_path, "JPEG", quality=85, optimize=True)
        return f"{CARDS_URL}/{char_id}.jpg"
    except OSError as e:
        print(f"Failed to create card image for {cartoon_path}: {e}")
        with open(cartoon_path, "rb") as f:
            return "data:image/jpeg;base64," + base64.b64encode(f.read()).decode(
                "ascii"
            )


def cartoon_image_path(character_name):
    filename = re.sub(r"[^\w\s]", "", character_name).replace(" ", "_") + ".jpg"
    return os.path.join(UPLOAD_FOLDER, filename)


def display_character(char):
    if not char:
        return

    character_name = char.get("name", "שם לא ידוע")
    st.session_state["character_name"] = character_name
    _, side_label, accent = get_side(char)

    with st.spinner("טוען דמות מצוירת..."):
        cartoon_path = generates_hand_drawn_cartoon_style_images(
            character_name, character_name
        )

    character_card(
        char_id=int(char.get("id", 0)),
        name=character_name,
        kicker=f"HOLOCRON · #{int(char.get('id', 0)):03d}",
        side=side_label,
        accent=accent,
        stats=build_character_stats(char),
        real_image=get_image(char.get("image"), char.get("id")),
        cartoon_image=card_image_url(int(char.get("id", 0)), cartoon_path)
        if cartoon_path
        else None,
        on_new_character=load_new_character,
    )


def make_thumbnail(source_path, dest_path):
    with Image.open(source_path) as img:
        img = img.convert("RGB")
        side = min(img.size)
        img = img.crop(
            ((img.width - side) // 2, 0, (img.width + side) // 2, side)
        )  # square, keep the top
        img = img.resize((THUMB_SIZE, THUMB_SIZE), Image.LANCZOS)
        img.save(dest_path, "JPEG", quality=82, optimize=True)


@st.cache_resource(show_spinner=False)
def build_gallery_items(character_ids):
    """Gallery entries for all characters. Thumbnails of the cartoon images are created once on disk."""
    os.makedirs(THUMBS_FOLDER, exist_ok=True)
    characters = {c["id"]: c for c in load_all_characters()}
    items = []
    for char_id in character_ids:
        char = characters[char_id]
        _, side_label, color = get_side(char)
        cartoon_path = cartoon_image_path(char["name"])
        thumb_path = os.path.join(THUMBS_FOLDER, f"{char_id}.jpg")
        thumb_url = get_image(char.get("image"), char_id)  # fallback: the real photo
        if os.path.isfile(cartoon_path):
            try:
                if not os.path.isfile(thumb_path):
                    make_thumbnail(cartoon_path, thumb_path)
                thumb_url = f"{THUMBS_URL}/{char_id}.jpg"
            except OSError as e:
                print(f"Failed to create thumbnail for {char['name']}: {e}")
        items.append(
            {
                "id": char_id,
                "name": char["name"],
                "thumb": thumb_url,
                "color": color,
                "side": side_label,
            }
        )
    return items


def select_character_from_gallery():
    char_id = st.session_state["character_gallery"].selected
    if char_id is not None:
        st.session_state.character = fetch_character(int(char_id))
        st.session_state.messages = [{"role": "assistant", "content": GREETING}]


def display_gallery(accent):
    character_ids = tuple(sorted(c["id"] for c in load_all_characters()))
    if not character_ids:
        return  # API unreachable: the random button on the card still works
    current = (st.session_state.get("character") or {}).get("id")
    character_gallery(
        items=build_gallery_items(character_ids),
        selected=current,
        accent=accent,
        on_select=select_character_from_gallery,
        on_random=load_new_character,
    )


def generates_hand_drawn_cartoon_style_images(prompt, character_name):
    """Return the path of the cartoon image, generating it if needed (None if generation fails)."""
    dest_path = cartoon_image_path(character_name)

    if not os.path.isfile(dest_path):
        try:
            prompt = f"{prompt} from Star Wars"
            from gradio_client import (
                Client,
            )  # heavy import, only needed when a cartoon is missing

            client = Client("fujohnwang/alvdansen-littletinies")
            cartoon_style_image = client.predict(prompt, api_name="/predict")
            process_result(cartoon_style_image, dest_path)
        except Exception as e:
            print(f"Failed to generate cartoon image for {character_name}: {e}")
            return None

    return dest_path


def process_result(result, filename):
    if isinstance(result, str):
        if os.path.isfile(result):
            img = Image.open(result)
        elif result.startswith(("http://", "https://")):
            response = requests.get(result)
            if response.status_code == 200:
                img = Image.open(BytesIO(response.content))
            else:
                raise Exception(f"Failed to download image from URL: {result}")
        elif result.lower().endswith(".webp"):
            img = Image.open(result)
        else:
            raise Exception(f"Invalid result format: {result}")
    elif isinstance(result, Image.Image):
        img = result
    else:
        raise Exception(f"Unexpected result format: {type(result)}")

    img = img.convert("RGB")
    img.save(filename, "JPEG")


def create_chatbot():
    character_name = st.session_state.get("character_name", "Echo")
    cartoon_path = cartoon_image_path(character_name)
    assistant_avatar = (
        cartoon_path if os.path.isfile(cartoon_path) else ":material/smart_toy:"
    )
    user_avatar = ":material/person:"
    messages = st.session_state.setdefault(
        "messages", [{"role": "assistant", "content": GREETING}]
    )

    st.subheader(f":material/forum: שיחה עם {character_name}", anchor=False)

    for message in messages:
        avatar = assistant_avatar if message["role"] == "assistant" else user_avatar
        with st.chat_message(message["role"], avatar=avatar):
            st.markdown(message["content"])

    prompt = st.chat_input(f"כתבו הודעה ל־{character_name}...", submit_mode="disable")

    # Offer conversation starters until the user sends a first message
    if len(messages) <= 1:
        suggestions = st.empty()
        selected = suggestions.pills(
            "רעיונות לשאלות",
            CHAT_SUGGESTIONS,
            label_visibility="collapsed",
            key=f"suggestions_{character_name}",
        )
        if selected:
            prompt = selected
        if prompt:
            suggestions.empty()

    if prompt:
        messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar=user_avatar):
            st.markdown(prompt)

        with st.chat_message("assistant", avatar=assistant_avatar):
            # Hologram "incoming transmission" animation until the first words arrive
            loader = st.empty()
            loader.html(HOLO_LOADER)

            def answer_tokens():
                first = True
                for token in hebrew_only(
                    stream_character_answer(character_name, messages)
                ):
                    if first:
                        loader.empty()
                        first = False
                    yield token

            response = st.write_stream(answer_tokens())
        messages.append({"role": "assistant", "content": response})


def load_new_character():
    st.session_state.character = fetch_character()
    st.session_state.messages = [{"role": "assistant", "content": GREETING}]


def hide_streamlit_header_footer():
    hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            footer:after {
                content:'goodbye';
                visibility: visible;
                display: block;
                position: relative;
                #background-color: red;
                padding: 5px;
                top: 2px;
            }
            header {visibility: hidden;}
            #root > div:nth-child(1) > div > div > div > div > section > div {padding-top: 0rem;}
            </style>
            """
    st.markdown(hide_st_style, unsafe_allow_html=True)


def render_hero(title, accent):
    # The <style> tints the whole page with the character's side color (see --force in styles.css).
    # It lives here, next to real content, because style-only st.html calls replace each other.
    st.html(f"""
    <style>:root {{ --force: {accent}; }}</style>
    <div class="sw-hero">
        <div class="sw-hero-kicker">A long time ago in a galaxy far, far away....</div>
        <h1 class="sw-hero-title">{title}</h1>
        <p class="sw-hero-sub">פגשו דמות אקראית מהגלקסיה, גלו עליה פרטים ושוחחו איתה בעברית</p>
    </div>
    """)


def main():
    title, image_path, footer_content = initialize()
    hide_streamlit_header_footer()

    if "character" not in st.session_state or not st.session_state.character:
        with st.spinner("טוען דמות ראשונית..."):
            st.session_state.character = fetch_character()

    character = st.session_state.character
    accent = get_side(character)[2] if character else "#FFE81F"
    render_hero(title, accent)
    sound_effects(accent)

    if image_path:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.image(image_path, width="stretch")

    display_gallery(accent)

    if character:
        display_character(character)
        if "messages" not in st.session_state:
            st.session_state.messages = [{"role": "assistant", "content": GREETING}]

    create_chatbot()

    # Display footer content
    st.markdown(
        f"<div class='sw-footer'>\n\n{footer_content}\n\n</div>", unsafe_allow_html=True
    )

    # Display user count after the chatbot
    user_count = get_user_count(formatted=True)
    st.html(f"<p class='user-count'>סה\"כ משתמשים: <b>{user_count}</b></p>")


if __name__ == "__main__":
    if "counted" not in st.session_state:
        st.session_state.counted = True
        increment_user_count()
    initialize_user_count()
    main()
