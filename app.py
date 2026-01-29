import streamlit as st
import pandas as pd
import json
import os
from fpdf import FPDF
from datetime import datetime

# --- CONFIGURATION INITIALE ---
st.set_page_config(page_title="Paleo Maker", layout="wide", initial_sidebar_state="collapsed")

DATA_FILE = "db_cartels.json"
IMG_FOLDER = "images_archive"
PINK_HEX = "#FCEDEC"
PINK_RGB = (252, 237, 236)

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
    
    /* Style des Inputs */
    .stTextInput input, .stTextArea textarea {{
        background-color: {PINK_HEX} !important;
        color: black !important;
        border: 1px solid #E0B0B0;
    }}
    
    /* Style des boutons */
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

# --- COMPOSANT D'AFFICHAGE VISUEL (Réutilisable) ---
def afficher_cartel_visuel(data):
    """Affiche le cartel tel qu'il apparaît en PDF, mais en HTML/Streamlit"""
    c1, c2 = st.columns([1, 1])
    
    # Partie Gauche : Image + Crédit
    with c1:
        if data['image_path'] and os.path.exists(data['image_path']):
            st.image(data['image_path'], use_column_width=True)
        else:
            st.markdown("*Image introuvable*")
        st.markdown(f"<div style='font-family:PT Sans Narrow; color:gray; margin-top:5px;'>Exhumé par {data['exhume_par']}</div>", unsafe_allow_html=True)
    
    # Partie Droite : Texte Rose
    with c2:
        cats = " • ".join(data['categories'])
        st.markdown(f"""
        <div style="background-color: {PINK_HEX}; padding: 25px; height: 100%; min-height: 400px; border-radius: 2px; color: black; display: flex; flex-direction: column; justify-content: space-between;">
            <div>
                <div style="text-align: right; font-weight: bold; font-family: 'PT Sans Narrow', sans-serif; font-size: 1.4em;">{data['annee']}</div>
                <div style="text-align: right; font-weight: bold; font-family: 'PT Sans Narrow', sans-serif; font-size: 1.8em; line-height: 1.1; margin-bottom: 20px; text-transform: uppercase;">{data['titre']}</div>
                <div style="font-family: 'PT Serif', serif; font-size: 1.1em; line-height: 1.4; text-align: left;">{data['description'].replace(chr(10), '<br>')}</div>
            </div>
            <div style="margin-top: 30px;">
                <small style="font-family: 'PT Sans Narrow', sans-serif; font-size: 0.9em;">Catégories : {cats}</small><br>
                <b style="font-family: 'PT Sans Narrow', sans-serif; font-size: 1.1em;">← Pour aller plus loin</b>
            </div>
        </div>
        """, unsafe_allow_html=True)

# --- GÉNÉRATEUR PDF ---
class PDF(FPDF):
    def __init__(self):
        super().__init__(orientation='L', unit='mm', format='A4')
        try:
            self.add_font('PTSerif', '', 'PTSerif-Regular.ttf')
            self.add_font('PTSerif', 'B', 'PTSerif-Bold.ttf')
            self.add_font('PTSansNarrow', '', 'PTSansNarrow-Regular.ttf')
            self.add_font('PTSansNarrow', 'B', 'PTSansNarrow-Bold.ttf')
            self.fonts_ok = True
        except:
            self.fonts_ok = False

    def add_cartel_page(self, data):
        self.add_page()
        pw, ph = 297, 210
        mid = pw / 2
        
        # Fond Rose
        self.set_fill_color(PINK_RGB[0], PINK_RGB[1], PINK_RGB[2])
        self.rect(x=mid, y=0, w=mid, h=ph, style='F')
        
        # Image
        if data['image_path'] and os.path.exists(data['image_path']):
            try:
                self.image(data['image_path'], x=15, y=30, w=mid-30)
            except: pass

        # Polices
        f_ti = 'PTSansNarrow' if self.fonts_ok else 'Arial'
        f_txt = 'PTSerif' if self.fonts_ok else 'Times'

        # Crédit
        self.set_xy(15, 185)
        self.set_font(f_ti, 'B', 10) 
        self.set_text_color(80, 80, 80)
        self.cell(100, 10, f"Exhumé par {data['exhume_par']}", new_x="LMARGIN", new_y="NEXT")

        # Contenu Droite
        margin = 15
        x_txt = mid + margin
        w_txt = mid - (margin * 2)

        # Année
        self.set_xy(x_txt, 25)
        self.set_font(f_ti, 'B', 18)
        self.set_text_color(0, 0, 0)
        self.cell(w_txt, 10, str(data['annee']), align='R', new_x="LMARGIN", new_y="NEXT")
        
        # Titre
        self.set_xy(x_txt, self.get_y())
        self.set_font(f_ti, 'B', 24)
        self.multi_cell(w_txt, 10, data['titre'].upper(), align='R')
        self.ln(5)

        # Description
        self.set_xy(x_txt, self.get_y())
        self.set_font(f_txt, '', 11)
        self.set_text_color(20, 20, 20)
        self.multi_cell(w_txt, 6, data['description'], align='L')
        
        # Footer
        self.set_xy(x_txt, 180)
        self.set_font(f_ti, '', 9)
        cats_str = " • ".join(data['categories'])
        self.cell(w_txt, 5, f"Catégories : {cats_str}", new_x="LMARGIN", new_y="NEXT", align='L')
        self.ln(2)
        self.set_font(f_ti, 'B', 10)
        self.cell(w_txt, 5, "← Pour aller plus loin", align='L')

# --- INTERFACE ---
st.title("⚡ PALEO-ÉNERGÉTIQUE")

tab_create, tab_library = st.tabs(["NOUVEAU CARTEL", "BIBLIOTHÈQUE & EXPORT"])

# === ONGLET 1 : CRÉATION ===
with tab_create:
    col_input, col_preview = st.columns([1, 1.5])
    
    # Init variables pour prévisualisation
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
        st.success("✅ Cartel enregistré avec succès !")
        preview_data = entry
    
    # Affichage Prévisualisation (Colonne de droite)
    with col_preview:
        st.subheader("2. Résultat final")
        if preview_data:
            afficher_cartel_visuel(preview_data)
        else:
            st.info("Remplissez le formulaire à gauche pour créer un cartel.")

# === ONGLET 2 : BIBLIOTHÈQUE ===
with tab_library:
    data = load_data()
    # Inversion de l'ordre pour avoir les plus récents en haut
    data = data[::-1] 
    
    if not data:
        st.info("Aucune archive pour le moment.")
    else:
        st.subheader(f"🗃️ Archives ({len(data)} fiches)")
        st.caption("Cochez les cases à gauche des cartels pour les inclure dans le PDF final.")
        
        # Le formulaire englobe toute la liste pour permettre la sélection multiple
        with st.form("selection_form"):
            selected_ids = []
            
            for index, row in enumerate(data):
                # Layout : Checkbox (petit) | Cartel Visuel (Grand)
                cols = st.columns([0.1, 2]) 
                
                with cols[0]:
                    # Checkbox centrée verticalement (astuce visuelle)
                    st.write("") 
                    st.write("")
                    st.write("")
                    if st.checkbox("", key=f"chk_{row['id']}"):
                        selected_ids.append(row['id'])
                
                with cols[1]:
                    # On appelle notre fonction visuelle ici !
                    afficher_cartel_visuel(row)
                    st.divider() # Ligne de séparation entre chaque cartel
            
            # Bouton de validation du formulaire
            submit_selection = st.form_submit_button("GÉNÉRER LE PDF AVEC LA SÉLECTION")

        # LOGIQUE HORS FORMULAIRE (Pour éviter l'erreur de nesting)
        if submit_selection:
            # Récupération des IDs cochés via session_state
            final_selection_ids = []
            for d in data:
                if st.session_state.get(f"chk_{d['id']}"):
                    final_selection_ids.append(d['id'])
            
            if not final_selection_ids:
                st.warning("Veuillez cocher au moins un cartel dans la liste.")
            else:
                # Filtrage des données complètes
                items_to_print = [d for d in data if d['id'] in final_selection_ids]
                
                # Génération PDF
                pdf = PDF()
                for item in items_to_print:
                    pdf.add_cartel_page(item)
                
                # CORRECTION BUG : Conversion explicite en bytes
                pdf_bytes = bytes(pdf.output())
                
                st.success(f"{len(items_to_print)} cartels générés !")
                
                # Bouton de téléchargement
                st.download_button(
                    label=f"⬇️ TÉLÉCHARGER LE FICHIER PDF ({len(items_to_print)} PAGES)",
                    data=pdf_bytes,
                    file_name=f"Catalogue_Paleo_{datetime.now().strftime('%H%M')}.pdf",
                    mime="application/pdf"
                )
