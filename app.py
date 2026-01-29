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
# Codes couleurs
PINK_RGB = (252, 237, 236)
PINK_HEX = "#FCEDEC"

# Création des dossiers
if not os.path.exists(IMG_FOLDER):
    os.makedirs(IMG_FOLDER)
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'w') as f:
        json.dump([], f)

# --- STYLE CSS (INTERFACE) ---
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=PT+Sans+Narrow:wght@400;700&family=PT+Serif:wght@400;700&display=swap');
    
    .stApp {{ background-color: #FAFAFA; font-family: 'PT Serif', serif; color: black; }}
    h1, h2, h3 {{ font-family: 'PT Sans Narrow', sans-serif !important; text-transform: uppercase; }}
    
    /* Style des Inputs pour ressembler au design */
    .stTextInput input, .stTextArea textarea {{
        background-color: {PINK_HEX} !important;
        color: black !important;
        border: 1px solid #E0B0B0;
    }}
    
    /* Bouton principal */
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

# --- FONCTIONS DONNÉES ---
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

# --- GÉNÉRATEUR PDF (NOUVELLE VERSION FPDF2) ---
class PDF(FPDF):
    def __init__(self):
        super().__init__(orientation='L', unit='mm', format='A4')
        
        # Chargement des polices (Chemins directs)
        # On utilise try/except pour éviter le crash si une police manque
        try:
            self.add_font('PTSerif', '', 'PTSerif-Regular.ttf')
            self.add_font('PTSerif', 'B', 'PTSerif-Bold.ttf')
            self.add_font('PTSansNarrow', '', 'PTSansNarrow-Regular.ttf')
            self.add_font('PTSansNarrow', 'B', 'PTSansNarrow-Bold.ttf')
            self.fonts_ok = True
        except Exception as e:
            self.fonts_ok = False
            print(f"Erreur police: {e}")

    def add_cartel_page(self, data):
        self.add_page()
        page_width = 297
        page_height = 210
        mid_point = page_width / 2
        
        # 1. Fond Rose (Moitié Droite)
        self.set_fill_color(PINK_RGB[0], PINK_RGB[1], PINK_RGB[2])
        self.rect(x=mid_point, y=0, w=mid_point, h=page_height, style='F')
        
        # 2. Image (Moitié Gauche)
        if data['image_path'] and os.path.exists(data['image_path']):
            # On essaie de placer l'image proprement
            # Max width = mid_point - marge(30)
            try:
                self.image(data['image_path'], x=15, y=30, w=mid_point-30)
            except:
                pass

        # Choix des polices (Fallback Arial si fichiers manquants)
        f_title = 'PTSansNarrow' if self.fonts_ok else 'Arial'
        f_body = 'PTSerif' if self.fonts_ok else 'Times'

        # 3. Crédit (Bas Gauche)
        self.set_xy(15, 185)
        self.set_font(f_title, 'B', 10) 
        self.set_text_color(80, 80, 80)
        self.cell(100, 10, f"Exhumé par {data['exhume_par']}", new_x="LMARGIN", new_y="NEXT")

        # --- PARTIE DROITE ---
        margin_right = 15
        x_text = mid_point + margin_right
        w_text = mid_point - (margin_right * 2)

        # 4. Année (Haut Droite)
        self.set_xy(x_text, 25)
        self.set_font(f_title, 'B', 18)
        self.set_text_color(0, 0, 0)
        self.cell(w_text, 10, str(data['annee']), align='R', new_x="LMARGIN", new_y="NEXT")
        
        # 5. Titre
        self.set_xy(x_text, self.get_y())
        self.set_font(f_title, 'B', 24)
        self.multi_cell(w_text, 10, data['titre'].upper(), align='R')
        self.ln(5)

        # 6. Description
        self.set_xy(x_text, self.get_y())
        self.set_font(f_body, '', 11)
        self.set_text_color(20, 20, 20)
        self.multi_cell(w_text, 6, data['description'], align='L')
        
        # 7. Catégories & Footer
        self.set_xy(x_text, 180)
        self.set_font(f_title, '', 9)
        cats_str = " • ".join(data['categories'])
        self.cell(w_text, 5, f"Catégories : {cats_str}", new_x="LMARGIN", new_y="NEXT", align='L')
        
        self.ln(2)
        self.set_font(f_title, 'B', 10)
        self.cell(w_text, 5, "← Pour aller plus loin", align='L')

# --- FONCTION DE PRÉVISUALISATION HTML ---
def render_preview(data):
    """Crée une fausse page web qui ressemble exactement au PDF"""
    
    # On récupère l'image en base64 ou chemin relatif pour l'afficher
    # Streamlit gère bien les chemins locaux
    
    img_html = ""
    if data['image_path'] and os.path.exists(data['image_path']):
        # Astuce : on utilise st.image plus bas, ici on fait juste la structure
        pass 

    cats = " • ".join(data['categories'])
    
    # Structure HTML Flexbox (Gauche Blanc / Droite Rose)
    html = f"""
    <div style="display: flex; width: 100%; height: 600px; border: 1px solid #ddd; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
        <div style="width: 50%; background-color: white; padding: 20px; position: relative; display: flex; flex-direction: column; justify-content: center; align-items: center;">
            <div style="flex-grow: 1; display: flex; align-items: center; justify-content: center; width: 100%;">
                <img src="app/static/{data['image_path']}" style="max-width: 90%; max-height: 400px; object-fit: contain;" />
            </div>
            <div style="width: 100%; text-align: left; margin-top: 20px; color: #666; font-family: 'PT Sans Narrow'; font-weight: bold; font-size: 14px;">
                Exhumé par {data['exhume_par']}
            </div>
        </div>
        
        <div style="width: 50%; background-color: {PINK_HEX}; padding: 40px; font-family: 'PT Serif'; color: black; position: relative;">
            <div style="text-align: right; font-family: 'PT Sans Narrow'; font-weight: bold; font-size: 24px; margin-bottom: 10px;">
                {data['annee']}
            </div>
            <div style="text-align: right; font-family: 'PT Sans Narrow'; font-weight: bold; font-size: 32px; line-height: 1.1; margin-bottom: 30px; text-transform: uppercase;">
                {data['titre']}
            </div>
            <div style="font-size: 16px; line-height: 1.5; text-align: left;">
                {data['description'].replace(chr(10), '<br>')}
            </div>
            
            <div style="position: absolute; bottom: 30px; left: 40px; width: 80%;">
                <div style="font-family: 'PT Sans Narrow'; font-size: 12px; margin-bottom: 5px;">
                    Catégories : {cats}
                </div>
                <div style="font-family: 'PT Sans Narrow'; font-weight: bold; font-size: 14px;">
                    ← Pour aller plus loin
                </div>
            </div>
        </div>
    </div>
    """
    return html


# --- INTERFACE ---

st.title("⚡ PALEO-ÉNERGÉTIQUE")
st.caption("Archive & Générateur de Cartels")

tab_create, tab_library = st.tabs(["NOUVEAU CARTEL", "BIBLIOTHÈQUE & EXPORT"])

# === ONGLET 1 : CRÉATION ===
with tab_create:
    col_input, col_preview = st.columns([1, 1.5])
    
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
            
            submit = st.form_submit_button("PRÉVISUALISER & ENREGISTRER")
            
    if submit and uploaded_file and titre:
        # Traitement Données
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
        
        # Affichage Prévisualisation
        with col_preview:
            st.subheader("2. Résultat final")
            # Affichage "fait main" pour simuler le PDF
            
            # Conteneur simulant le design
            c1, c2 = st.columns([1, 1])
            with c1: # Partie Blanche
                st.image(img_path)
                st.caption(f"Exhumé par {exhume_par}")
            with c2: # Partie Rose (On triche avec st.info ou success mais couleur custom impossible ici simplement)
                # On utilise du Markdown HTML pour forcer le design rose
                st.markdown(f"""
                <div style="background-color: {PINK_HEX}; padding: 20px; height: 100%; border-radius: 5px; color: black;">
                    <div style="text-align: right; font-weight: bold; font-family: sans-serif; font-size: 1.2em;">{annee}</div>
                    <div style="text-align: right; font-weight: bold; font-family: sans-serif; font-size: 1.5em; line-height: 1.1; margin-bottom: 20px;">{titre.upper()}</div>
                    <div style="font-family: serif; font-size: 1em; text-align: left;">{description}</div>
                    <br><br>
                    <small>Catégories : {" • ".join(final_cats)}</small><br>
                    <b>← Pour aller plus loin</b>
                </div>
                """, unsafe_allow_html=True)


# === ONGLET 2 : BIBLIOTHÈQUE ===
with tab_library:
    data = load_data()
    if not data:
        st.info("Aucune archive pour le moment.")
    else:
        df = pd.DataFrame(data)
        st.subheader(f"🗃️ Archives ({len(data)} fiches)")
        
        # Formulaire de sélection pour export groupé
        with st.form("export_form"):
            # On crée une liste pour stocker les IDs sélectionnés
            selected_ids = []
            
            # En-têtes colonnes
            h1, h2, h3, h4 = st.columns([0.5, 1, 3, 1])
            h1.write("Selec.")
            h2.write("Image")
            h3.write("Infos")
            h4.write("Actions")
            
            st.divider()
            
            # Affichage de la liste avec Checkbox
            for index, row in df.iterrows():
                c1, c2, c3, c4 = st.columns([0.5, 1, 3, 1])
                
                with c1:
                    # La checkbox ajoute l'ID à la liste si cochée
                    if st.checkbox("", key=f"chk_{row['id']}"):
                        selected_ids.append(row['id'])
                
                with c2:
                    if os.path.exists(row['image_path']):
                        st.image(row['image_path'], use_column_width=True)
                
                with c3:
                    st.markdown(f"**{row['titre'].upper()}** ({row['annee']})")
                    st.caption(" • ".join(row['categories']))
                    st.write(row['description'][:150] + "...")
                
                st.divider()
            
            # Bouton d'action global
            submitted = st.form_submit_button("📄 GÉNÉRER LE PDF DES ÉLÉMENTS SÉLECTIONNÉS")
            
            if submitted:
                if not selected_ids:
                    st.warning("Veuillez sélectionner au moins un cartel.")
                else:
                    # On filtre les données
                    items_to_print = [d for d in data if d['id'] in selected_ids]
                    
                    # Génération du PDF multipage
                    pdf = PDF()
                    for item in items_to_print:
                        pdf.add_cartel_page(item)
                    
                    # Output
                    pdf_bytes = pdf.output() # FPDF2 retourne des bytes directement
                    
                    st.download_button(
                        label=f"⬇️ TÉLÉCHARGER LE CATALOGUE ({len(items_to_print)} PAGES)",
                        data=pdf_bytes,
                        file_name=f"Catalogue_Paleo_{datetime.now().strftime('%H%M')}.pdf",
                        mime="application/pdf"
                    )
