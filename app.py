import streamlit as st
import pandas as pd
import json
import os
import urllib.request
from fpdf import FPDF
from datetime import datetime

# --- CONFIGURATION INITIALE ---
st.set_page_config(page_title="Paleo Maker", layout="wide", initial_sidebar_state="collapsed")

DATA_FILE = "db_cartels.json"
IMG_FOLDER = "images_archive"
FONT_FOLDER = "fonts"
PALEO_PINK = (252, 237, 236) 

# Création des dossiers
if not os.path.exists(IMG_FOLDER):
    os.makedirs(IMG_FOLDER)
if not os.path.exists(FONT_FOLDER):
    os.makedirs(FONT_FOLDER)
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'w') as f:
        json.dump([], f)

# --- TÉLÉCHARGEMENT AUTOMATIQUE DES POLICES ---
# Cette fonction récupère les fichiers .ttf pour éviter les erreurs Unicode et respecter le design
def download_fonts():
    fonts = {
        "PTSerif-Regular.ttf": "https://github.com/google/fonts/raw/main/ofl/ptserif/PTSerif-Regular.ttf",
        "PTSerif-Bold.ttf": "https://github.com/google/fonts/raw/main/ofl/ptserif/PTSerif-Bold.ttf",
        "PTSansNarrow-Regular.ttf": "https://github.com/google/fonts/raw/main/ofl/ptsansnarrow/PTSansNarrow-Regular.ttf",
        "PTSansNarrow-Bold.ttf": "https://github.com/google/fonts/raw/main/ofl/ptsansnarrow/PTSansNarrow-Bold.ttf"
    }
    
    for filename, url in fonts.items():
        path = os.path.join(FONT_FOLDER, filename)
        if not os.path.exists(path):
            print(f"Téléchargement de {filename}...")
            try:
                urllib.request.urlretrieve(url, path)
            except Exception as e:
                st.error(f"Erreur téléchargement police {filename}: {e}")

# On lance le téléchargement au démarrage
download_fonts()

# --- STYLE CSS (DESIGN WEB) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=PT+Sans+Narrow:wght@400;700&family=PT+Serif:wght@400;700&display=swap');
    .stApp { background-color: #FAFAFA; font-family: 'PT Serif', serif; color: #000000 !important; }
    h1, h2, h3, .stHeader { font-family: 'PT Sans Narrow', sans-serif !important; color: #000000 !important; text-transform: uppercase; font-weight: 700; }
    .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] { background-color: #FCEDEC !important; color: #000000 !important; border: 1px solid #E0B0B0 !important; font-family: 'PT Serif', serif !important; }
    div[data-baseweb="input"] { background-color: #FCEDEC !important; }
    .stTextInput label, .stTextArea label, .stSelectbox label, .stFileUploader label { color: #333333 !important; font-family: 'PT Sans Narrow', sans-serif !important; font-size: 1.1rem !important; text-transform: uppercase; }
    div.stButton > button { background-color: #000000; color: white; font-family: 'PT Sans Narrow', sans-serif !important; border: none; text-transform: uppercase; padding: 0.5rem 1rem; }
    div.stButton > button:hover { background-color: #D65A5A; color: white; border: none; }
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

# --- CLASSE PDF AVEC SUPPOPRT UNICODE ET DESIGN ---
class PDF(FPDF):
    def __init__(self):
        super().__init__()
        # On charge les polices téléchargées en mode Unicode (uni=True)
        # Cela corrige l'erreur UnicodeEncodeError
        self.add_font('PTSerif', '', os.path.join(FONT_FOLDER, 'PTSerif-Regular.ttf'), uni=True)
        self.add_font('PTSerif', 'B', os.path.join(FONT_FOLDER, 'PTSerif-Bold.ttf'), uni=True)
        self.add_font('PTSansNarrow', '', os.path.join(FONT_FOLDER, 'PTSansNarrow-Regular.ttf'), uni=True)
        self.add_font('PTSansNarrow', 'B', os.path.join(FONT_FOLDER, 'PTSansNarrow-Bold.ttf'), uni=True)

    def header(self):
        pass 

    def create_cartel(self, data):
        self.add_page(orientation='L')
        page_width = 297
        page_height = 210
        mid_point = page_width / 2
        
        # Fond Rose Droite
        self.set_fill_color(PALEO_PINK[0], PALEO_PINK[1], PALEO_PINK[2])
        self.rect(x=mid_point, y=0, w=mid_point, h=page_height, style='F')
        
        # Image Gauche
        if data['image_path'] and os.path.exists(data['image_path']):
            img_x = 15
            img_y = 30
            img_w = mid_point - 30
            try:
                self.image(data['image_path'], x=img_x, y=img_y, w=img_w)
            except:
                pass
        
        # Crédit (Gauche) - Utilise PT Sans Narrow Bold
        self.set_xy(15, 185)
        self.set_font('PTSansNarrow', 'B', 10) 
        self.set_text_color(80, 80, 80)
        self.cell(100, 10, f"Exhumé par {data['exhume_par']}", ln=False)

        # Contenu Droite
        margin_right_block = 15
        x_start_text = mid_point + margin_right_block
        width_text = mid_point - (margin_right_block * 2)

        # Année (Haut Droite) - PT Sans Narrow Bold
        self.set_xy(x_start_text, 25)
        self.set_font('PTSansNarrow', 'B', 18)
        self.set_text_color(0, 0, 0)
        self.cell(width_text, 10, str(data['annee']), ln=True, align='R')
        
        # Titre - PT Sans Narrow Bold (Gros)
        self.set_x(x_start_text)
        self.set_font('PTSansNarrow', 'B', 24)
        self.multi_cell(width_text, 10, data['titre'].upper(), align='R')
        self.ln(10)

        # Description - PT Serif Regular
        self.set_x(x_start_text)
        self.set_font('PTSerif', '', 11)
        self.set_text_color(20, 20, 20)
        self.multi_cell(width_text, 6, data['description'], align='L')
        
        # Catégories - PT Sans Narrow
        self.set_xy(x_start_text, 180)
        self.set_font('PTSansNarrow', '', 9)
        cats_str = " • ".join(data['categories'])
        self.cell(width_text, 5, f"Catégories : {cats_str}", ln=True, align='L')
        
        self.ln(2)
        self.set_font('PTSansNarrow', 'B', 10)
        self.cell(width_text, 5, "← Pour aller plus loin", ln=True, align='L')

# --- INTERFACE ---
st.title("⚡ PALEO-ÉNERGÉTIQUE")

tab1, tab2 = st.tabs(["✍️ ÉDITION", "📚 BIBLIOTHÈQUE"])

# ONGLET 1 : CRÉATION
with tab1:
    col1, col2 = st.columns([1, 1.5])
    
    with col1:
        st.markdown("### VISUEL")
        uploaded_file = st.file_uploader("Image du dispositif", type=['png', 'jpg', 'jpeg'])
        if uploaded_file:
            st.image(uploaded_file, use_column_width=True)
    
    with col2:
        st.markdown("### INFORMATIONS")
        with st.form("cartel_form"):
            annee = st.text_input("Année / Époque", value="2025")
            titre = st.text_input("Titre du cartel")
            description = st.text_area("Description complète", height=200)
            exhume_par = st.text_input("Exhumé par")
            
            st.markdown("<br><b>CATÉGORISATION</b>", unsafe_allow_html=True)
            categories_base = ["Énergie", "H2O", "Mobilité", "Alimentation", "Solaire", "Eolien"]
            selected_cats = st.multiselect("Choisir les catégories", categories_base)
            new_cat_input = st.text_input("Autre catégorie (optionnel)")
            
            submitted = st.form_submit_button("VALIDER ET CRÉER")
            
            if submitted and titre and uploaded_file:
                final_cats = selected_cats.copy()
                if new_cat_input:
                    final_cats.append(new_cat_input)
                
                img_path = save_image(uploaded_file)
                entry = {
                    "id": datetime.now().strftime("%Y%m%d%H%M%S"),
                    "annee": annee,
                    "titre": titre,
                    "description": description,
                    "exhume_par": exhume_par,
                    "categories": final_cats,
                    "image_path": img_path,
                    "date_ajout": datetime.now().strftime("%Y-%m-%d")
                }
                save_data(entry)
                st.success(f"Cartel '{titre}' archivé !")
                
                # Génération PDF
                try:
                    pdf = PDF()
                    pdf.create_cartel(entry)
                    # Note: Avec uni=True, l'encodage 'latin-1' dans .output() n'est plus nécessaire/souhaité de la même manière
                    # On utilise output(dest='S') qui retourne une chaine, puis on encode en latin-1 pour que streamlit puisse le lire en bytes
                    # C'est une astuce spécifique à FPDF 1.7
                    pdf_byte = pdf.output(dest='S').encode('latin-1')
                    
                    st.download_button("⬇️ TÉLÉCHARGER LE PDF", data=pdf_byte, file_name=f"Cartel_{titre}.pdf", mime='application/pdf')
                except Exception as e:
                    st.error(f"Erreur lors de la création du PDF : {e}")

# ONGLET 2 : CONSULTATION
with tab2:
    data = load_data()
    if not data:
        st.info("Aucune archive.")
    else:
        df = pd.DataFrame(data)
        
        all_cats = set()
        for c in df['categories']: all_cats.update(c)
        cat_filter = st.multiselect("FILTRER PAR CATÉGORIE", list(all_cats))
        
        if cat_filter:
            mask = df['categories'].apply(lambda x: any(item in cat_filter for item in x))
            df = df[mask]
            
        for index, row in df.iterrows():
            with st.container():
                c1, c2 = st.columns([1, 4])
                with c1:
                    if os.path.exists(row['image_path']): st.image(row['image_path'])
                with c2:
                    st.markdown(f"### {row['titre'].upper()} ({row['annee']})")
                    st.caption(" • ".join(row['categories']))
                    st.write(row['description'])
                    st.markdown(f"**Exhumé par : {row['exhume_par']}**")
                    
                    if st.button(f"📄 PDF", key=row['id']):
                        try:
                            pdf = PDF()
                            pdf.create_cartel(row.to_dict())
                            b = pdf.output(dest='S').encode('latin-1')
                            st.download_button("TÉLÉCHARGER", data=b, file_name=f"Cartel_{row['id']}.pdf", mime='application/pdf', key=f"d{row['id']}")
                        except Exception as e:
                            st.error(f"Erreur PDF : {e}")
                st.divider()
