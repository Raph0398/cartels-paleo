import streamlit as st
import pandas as pd
import json
import os
from fpdf import FPDF
from datetime import datetime
from PIL import Image

# --- CONFIGURATION INITIALE ---
st.set_page_config(page_title="Paleo Maker", layout="wide", initial_sidebar_state="collapsed")

DATA_FILE = "db_cartels.json"
IMG_FOLDER = "images_archive"
PINK_RGB = (252, 237, 236)
PINK_HEX = "#FCEDEC"

# Création des dossiers
if not os.path.exists(IMG_FOLDER):
    os.makedirs(IMG_FOLDER)
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'w') as f:
        json.dump([], f)

# --- STYLE CSS ---
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=PT+Sans+Narrow:wght@400;700&family=PT+Serif:wght@400;700&display=swap');
    
    .stApp {{ background-color: #FAFAFA; font-family: 'PT Serif', serif; color: black; }}
    h1, h2, h3 {{ font-family: 'PT Sans Narrow', sans-serif !important; text-transform: uppercase; }}
    
    .stTextInput input, .stTextArea textarea {{
        background-color: {PINK_HEX} !important;
        color: black !important;
        border: 1px solid #E0B0B0;
    }}
    
    div.stButton > button {{
        background-color: black;
        color: white;
        font-family: 'PT Sans Narrow', sans-serif;
        text-transform: uppercase;
        border-radius: 0px;
        padding: 10px 20px;
    }}
    div.stButton > button:hover {{
        background-color: #D65A5A;
        border-color: #D65A5A;
    }}
</style>
""", unsafe_allow_html=True)

# --- FONCTIONS UTILITAIRES ---
def load_data():
    with open(DATA_FILE, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def save_data(new_entry):
    data = load_data()
    data.append(new_entry)
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def save_image(uploaded_file):
    if uploaded_file is not None:
        file_path = os.path.join(IMG_FOLDER, uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        return file_path
    return None

# --- AFFICHAGE VISUEL ---
def afficher_cartel_visuel(data):
    """Affiche le cartel visuellement dans l'app"""
    c1, c2 = st.columns([1, 1])
    
    with c1:
        if data['image_path'] and os.path.exists(data['image_path']):
            # On simule le centrage vertical
            st.image(data['image_path'], use_column_width=True)
        else:
            st.warning("Image manquante")
        st.markdown(f"<div style='font-family:sans-serif; color:gray; margin-top:5px; font-size:0.8em;'>Exhumé par {data['exhume_par']}</div>", unsafe_allow_html=True)
    
    with c2:
        cats = " • ".join(data['categories'])
        st.markdown(f"""
        <div style="background-color: {PINK_HEX}; padding: 25px; height: 100%; min-height: 400px; border-radius: 2px; color: black; display: flex; flex-direction: column; justify-content: space-between;">
            <div>
                <div style="text-align: right; font-weight: bold; font-family: sans-serif; font-size: 1.4em;">{data['annee']}</div>
                <div style="text-align: right; font-weight: bold; font-family: sans-serif; font-size: 1.8em; line-height: 1.1; margin-bottom: 20px; text-transform: uppercase;">{data['titre']}</div>
                <div style="font-family: serif; font-size: 1.1em; line-height: 1.4; text-align: left;">{data['description'].replace(chr(10), '<br>')}</div>
            </div>
            <div style="margin-top: 30px;">
                <small style="font-family: sans-serif; font-size: 0.9em;">Catégories : {cats}</small><br>
                <b style="font-family: sans-serif; font-size: 1.1em;">← Pour aller plus loin</b>
            </div>
        </div>
        """, unsafe_allow_html=True)

# --- GÉNÉRATEUR PDF OPTIMISÉ ---
class PDF(FPDF):
    def __init__(self):
        super().__init__(orientation='L', unit='mm', format='A4')
        self.set_auto_page_break(False)
        self.set_margins(0, 0, 0)
        
        self.font_header = 'Helvetica'
        self.font_body = 'Times'
        
        try:
            if os.path.exists('PTSansNarrow-Bold.ttf'):
                self.add_font('PTSansNarrow', 'B', 'PTSansNarrow-Bold.ttf')
                self.add_font('PTSansNarrow', '', 'PTSansNarrow-Regular.ttf')
                self.font_header = 'PTSansNarrow'
            if os.path.exists('PTSerif-Regular.ttf'):
                self.add_font('PTSerif', '', 'PTSerif-Regular.ttf')
                self.font_body = 'PTSerif'
        except: pass

    def add_cartel_page(self, data):
        self.add_page()
        
        # Dimensions Page
        W_PAGE = 297
        H_PAGE = 210
        MID = W_PAGE / 2
        
        # 1. FOND ROSE (Droite)
        self.set_fill_color(PINK_RGB[0], PINK_RGB[1], PINK_RGB[2])
        self.rect(x=MID, y=0, w=MID, h=H_PAGE, style='F')

        # 2. IMAGE (CALCUL INTELLIGENT DE LA TAILLE)
        if data['image_path'] and os.path.exists(data['image_path']):
            try:
                # --- ZONE AUTORISÉE POUR L'IMAGE ---
                # On définit une boîte stricte pour que l'image ne dépasse jamais
                BOX_X = 15          # Marge gauche
                BOX_Y = 30          # Marge haute
                BOX_W = MID - 30    # Largeur dispo (Moitié page - 2x15 de marge)
                BOX_H = 145         # Hauteur dispo (Pour s'arrêter avant le texte du bas)

                # Récupération taille réelle image
                with Image.open(data['image_path']) as img:
                    orig_w, orig_h = img.size
                
                # Calcul du facteur de redimensionnement (pour tenir dans la boite)
                ratio_w = BOX_W / orig_w
                ratio_h = BOX_H / orig_h
                scale = min(ratio_w, ratio_h) # On prend le ratio le plus restrictif
                
                new_w = orig_w * scale
                new_h = orig_h * scale

                # Centrage dans la zone autorisée
                offset_x = (BOX_W - new_w) / 2
                offset_y = (BOX_H - new_h) / 2
                
                final_x = BOX_X + offset_x
                final_y = BOX_Y + offset_y

                # Affichage de l'image redimensionnée et centrée
                self.image(data['image_path'], x=final_x, y=final_y, w=new_w, h=new_h)
            except Exception as e:
                print(f"Erreur image: {e}")

        # 3. CRÉDIT (Bas Gauche) - Position fixe
        self.set_xy(15, 185) # Position Y fixe en bas
        self.set_font(self.font_header, 'B', 10) 
        self.set_text_color(80, 80, 80)
        self.cell(100, 10, f"Exhumé par {data['exhume_par']}")

        # --- PARTIE DROITE ---
        MARGIN_R = 15
        X_TEXT = MID + MARGIN_R
        W_TEXT = MID - (MARGIN_R * 2)

        # 4. ANNÉE
        self.set_xy(X_TEXT, 25)
        self.set_font(self.font_header, 'B', 18)
        self.set_text_color(0, 0, 0)
        self.cell(W_TEXT, 10, str(data['annee']), align='R')
        
        # 5. TITRE
        self.set_xy(X_TEXT, self.get_y() + 10)
        self.set_font(self.font_header, 'B', 24)
        self.multi_cell(W_TEXT, 10, data['titre'].upper(), align='R')
        
        # 6. DESCRIPTION
        self.set_xy(X_TEXT, self.get_y() + 10)
        self.set_font(self.font_body, '', 11)
        self.set_text_color(20, 20, 20)
        self.multi_cell(W_TEXT, 6, data['description'], align='L')
        
        # 7. FOOTER (Catégories)
        self.set_xy(X_TEXT, 180) # Position Y fixe en bas
        self.set_font(self.font_header, '', 9)
        cats_str = " • ".join(data['categories'])
        self.cell(W_TEXT, 5, f"Catégories : {cats_str}", align='L', ln=True)
        
        self.ln(1)
        self.set_font(self.font_header, 'B', 10)
        self.cell(W_TEXT, 5, "← Pour aller plus loin", align='L')

# --- INTERFACE ---
st.title("⚡ PALEO-ÉNERGÉTIQUE")

tab_create, tab_library = st.tabs(["NOUVEAU CARTEL", "BIBLIOTHÈQUE & EXPORT"])

# === ONGLET 1 : CRÉATION ===
with tab_create:
    col_input, col_preview = st.columns([1, 1.5])
    preview_data = None

    with col_input:
        st.subheader("1. Saisie")
        with st.form("new_cartel"):
            uploaded_file = st.file_uploader("Image", type=['png', 'jpg', 'jpeg'])
            annee = st.text_input("Année", value="2025")
            titre = st.text_input("Titre")
            description = st.text_area("Description", height=150)
            exhume_par = st.text_input("Exhumé par")
            
            cats_base = ["Énergie", "H2O", "Mobilité", "Alimentation", "Solaire", "Eolien"]
            selected_cats = st.multiselect("Catégories", cats_base)
            new_cat = st.text_input("Autre catégorie")
            
            submit_create = st.form_submit_button("ENREGISTRER LE CARTEL")

    if submit_create and uploaded_file and titre:
        final_cats = selected_cats + ([new_cat] if new_cat else [])
        img_path = save_image(uploaded_file)
        
        entry = {
            "id": datetime.now().strftime("%Y%m%d%H%M%S"),
            "titre": titre, "annee": annee, "description": description,
            "exhume_par": exhume_par, "categories": final_cats,
            "image_path": img_path, "date": datetime.now().strftime("%Y-%m-%d")
        }
        
        save_data(entry)
        st.success("✅ Cartel enregistré !")
        preview_data = entry
    
    with col_preview:
        st.subheader("2. Résultat final")
        if preview_data:
            afficher_cartel_visuel(preview_data)
        else:
            st.info("Remplissez le formulaire à gauche.")

# === ONGLET 2 : BIBLIOTHÈQUE ===
with tab_library:
    data = load_data()
    data = data[::-1]
    
    if not data:
        st.info("Aucune archive.")
    else:
        st.subheader(f"🗃️ Archives ({len(data)} fiches)")
        
        selected_ids_in_form = []

        with st.form("selection_form"):
            for index, row in enumerate(data):
                cols = st.columns([0.1, 2]) 
                with cols[0]:
                    st.write("") 
                    st.write("")
                    st.write("")
                    if st.checkbox("", key=f"chk_{row['id']}"):
                        selected_ids_in_form.append(row['id'])
                
                with cols[1]:
                    afficher_cartel_visuel(row)
                    st.divider()
            
            submit_selection = st.form_submit_button("GÉNÉRER LE PDF AVEC LA SÉLECTION")

        if submit_selection:
            if not selected_ids_in_form:
                st.warning("Veuillez cocher au moins un cartel.")
            else:
                final_selection = [d for d in data if d['id'] in selected_ids_in_form]
                
                pdf = PDF()
                for item in final_selection:
                    pdf.add_cartel_page(item)
                
                try:
                    pdf_bytes = bytes(pdf.output())
                except TypeError:
                    pdf_bytes = pdf.output(dest='S').encode('latin-1')

                st.success(f"PDF généré avec {len(final_selection)} page(s) !")
                
                st.download_button(
                    label=f"⬇️ TÉLÉCHARGER LE PDF ({len(final_selection)} PAGES)",
                    data=pdf_bytes,
                    file_name=f"Catalogue_Paleo_Export.pdf",
                    mime="application/pdf"
                )
