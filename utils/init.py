import streamlit as st
from streamlit.components.v1 import html
import os

def initialize():    
    # Load header content
    header_file_path = os.path.join('utils', 'header.md')
    try:
        with open(header_file_path, 'r', encoding='utf-8') as header_file:
            header_content = header_file.read()
    except FileNotFoundError:
        st.error("header.md file not found in utils folder.")
        header_content = ""  # Provide a default empty header

    # Extract title and image path from header content
    header_lines = header_content.split('\n')
    title = header_lines[0].strip('# ')
    image_path = None    
    for line in header_lines:
        if line.startswith('!['):
            image_path = line.split('(')[1].split(')')[0]
            break
    
    # Load external CSS
    css_file_path = os.path.join('utils', 'styles.css')
    with open(css_file_path, 'r') as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)    
    
    # Load footer content
    footer_file_path = os.path.join('utils', 'footer.md')
    try:
        with open(footer_file_path, 'r', encoding='utf-8') as footer_file:
            footer_content = footer_file.read()
    except FileNotFoundError:
        st.error("footer.md file not found in utils folder.")
        footer_content = ""  # Provide a default empty footer    

    # Load external CSS
    css_file_path = os.path.join('utils', 'styles.css')
    with open(css_file_path, 'r') as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)    

    with st.expander('אודות האפליקציה - נוצרה ע"י שגיא בר און'):
        st.markdown('''
         אפליקציית Star Wars Chat & Art מציעה חוויה ייחודית של שילוב בין עולם הדמיון והמציאות. 
                    
תהנו מתמונות אמיתיות של דמויות מ-Star Wars, לצד תמונות מצוירות בסגנון וינטג' המעניקות תחושה קלאסית ומעוררת נוסטלגיה. 
                    
אך זה לא הכל – תוכלו לשוחח עם הדמויות האהובות דרך צ'אט, ולקבל תשובות ישירות מהן! 
                    
האפליקציה מציעה חווית שימוש אינטראקטיבית ומרהיבה, המשלבת אומנות וחדשנות בתקשורת עם הדמויות האייקוניות של סדרת סרטי המדע הבדיוני המפורסמת בעולם.
        ''')

    return title, image_path, footer_content