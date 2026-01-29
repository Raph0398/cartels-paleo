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

# --- AFFICHAGE VISUEL (HTML/CSS pour l'app) ---
def afficher_cartel_visuel(data):
    """Affiche le cartel tel qu'il apparaîtra, pour vérification visuelle"""
    c1, c2 = st.columns([1, 1])
    
    with c1:
        if data['image_path'] and os.path.exists(data['image_path']):
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

# --- MOTEUR PDF ROBUSTE ---
class PDF(FPDF):
    def __init__(self):
        # Format EXACT A4 Paysage (297mm x 210mm)
        super().__init__(orientation='L', unit='mm', format='A4')
        self.set_auto_page_break(False) # On gère la page nous-mêmes pour éviter les sauts inattendus
        self.set_margins(0, 0, 0) # Pas de marges automatiques
        
        # CHARGEMENT POLICES AVEC FALLBACK DE SÉCURITÉ
        # Si le fichier .ttf n'est pas trouvé, on utilise Helvetica (qui marche toujours)
        self.font_header = 'Helvetica'
        self.font_body = 'Times'
        
        try:
            # On tente de charger vos fichiers (doivent être à la racine)
            if os.path.exists('PTSansNarrow-Bold.ttf'):
                self.add_font('PTSansNarrow', 'B', 'PTSansNarrow-Bold.ttf')
                self.add_font('PTSansNarrow', '', 'PTSansNarrow-Regular.ttf')
                self.font_header = 'PTSansNarrow'
            
            if os.path.exists('PTSerif-Regular.ttf'):
                self.add_font('PTSerif', '', 'PTSerif-Regular.ttf')
                self.font_body = 'PTSerif'
        except Exception as e:
            print(f"Attention: Polices non trouvées, utilisation standard. Erreur: {e}")

    def add_cartel_page(self, data):
        self.add_page()
        
        # Dimensions A4 exactes
        W = 297
        H = 210
        MID = W / 2
        
        # 1. FOND ROSE (Moitié Droite EXACTE)
        self.set_fill_color(PINK_RGB[0], PINK_RGB[1], PINK_RGB[2])
        self.rect(x=MID, y=0, w=MID, h=H, style='F')
        
        # 2. IMAGE (Moitié Gauche)
        # On définit une zone de 15mm de marge
        if data['image_path'] and os.path.exists(data['image_path']):
            try:
                # On place l'image à x=15, y=30, largeur max = (MID - 30)
                self.image(data['image_path'], x=15, y=30, w=MID-30)
            except:
                pass # Évite de planter si l'image est corrompue

        # 3. CRÉDIT (Bas Gauche)
        self.set_xy(15, 185)
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
        # On repositionne le curseur juste après l'année
        self.set_xy(X_TEXT, self.get_y() + 10)
        self.set_font(self.font_header, 'B', 24)
        self.multi_cell(W_TEXT, 10, data['titre'].upper(), align='R')
        
        # 6. DESCRIPTION
        self.set_xy(X_TEXT, self.get_y() + 10)
        self.set_font(self.font_body, '', 11)
        self.set_text_color(20, 20, 20)
        self.multi_cell(W_TEXT, 6, data['description'], align='L')
        
        # 7. FOOTER (Catégories)
        self.set_xy(X_TEXT, 180)
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
    data = data[::-1] # Plus récent en haut
    
    if not data:
        st.info("Aucune archive.")
    else:
        st.subheader(f"🗃️ Archives ({len(data)} fiches)")
        st.caption("Cochez pour générer le PDF.")
        
        with st.form("selection_form"):
            for index, row in enumerate(data):
                cols = st.columns([0.1, 2]) 
                with cols[0]:
                    st.write("") 
                    st.write("")
                    st.write("")
                    st.checkbox("", key=f"chk_{row['id']}")
                with cols[1]:
                    afficher_cartel_visuel(row)
                    st.divider()
            
            submit_selection = st.form_submit_button("GÉNÉRER LE PDF AVEC LA SÉLECTION")

        if submit_selection:
            final_selection = [d for d in data if st.session_state.get(f"chk_{d['id']}")]
            
            if not final_selection:
                st.warning("Cochez au moins un cartel.")
            else:
                pdf = PDF()
                for item in final_selection:
                    pdf.add_cartel_page(item)
                
                # Conversion sécurisée en bytes
                pdf_bytes = bytes(pdf.output())
                
                st.success(f"{len(final_selection)} cartels prêts !")
                st.download_button(
                    label=f"⬇️ TÉLÉCHARGER LE PDF ({len(final_selection)} PAGES)",
                    data=pdf_bytes,
                    file_name=f"Catalogue_Paleo.pdf",
                    mime="application/pdf"
                )
