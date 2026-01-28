import streamlit as st
import pandas as pd
import json
import os
from PIL import Image
from fpdf import FPDF
from datetime import datetime

# --- CONFIGURATION ---
DATA_FILE = "db_cartels.json"
IMG_FOLDER = "images_archive"
PALEO_PINK = (252, 237, 236) # Code RGB du rose pâle des images (approx)

# Création des dossiers si inexistants
if not os.path.exists(IMG_FOLDER):
    os.makedirs(IMG_FOLDER)

if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'w') as f:
        json.dump([], f)

# --- FONCTIONS UTILITAIRES ---

def load_data():
    """Charge la base de données JSON"""
    with open(DATA_FILE, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def save_data(new_entry):
    """Ajoute une entrée et sauvegarde"""
    data = load_data()
    data.append(new_entry)
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def save_image(uploaded_file):
    """Sauvegarde l'image uploadée"""
    if uploaded_file is not None:
        file_path = os.path.join(IMG_FOLDER, uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        return file_path
    return None

class PDF(FPDF):
    """Classe pour générer le design EXACT des images fournies"""
    def header(self):
        pass 

    def create_cartel(self, data):
        # Format A4 Paysage (Landscape)
        self.add_page(orientation='L')
        
        # Dimensions A4 Paysage : 297mm x 210mm
        page_width = 297
        page_height = 210
        mid_point = page_width / 2
        
        # --- FOND ---
        # Partie Droite (Rose)
        self.set_fill_color(PALEO_PINK[0], PALEO_PINK[1], PALEO_PINK[2])
        self.rect(x=mid_point, y=0, w=mid_point, h=page_height, style='F')
        
        # --- PARTIE GAUCHE (IMAGE + CREDIT) ---
        # Image
        if data['image_path'] and os.path.exists(data['image_path']):
            # On essaie de centrer l'image dans la moitié gauche
            # Marge de 15mm
            img_x = 15
            img_y = 30
            img_w = mid_point - 30
            try:
                self.image(data['image_path'], x=img_x, y=img_y, w=img_w)
            except:
                pass
        
        # Crédit "Exhumé par" (En bas à gauche, sous l'image)
        self.set_xy(15, 175)
        self.set_font('Arial', 'B', 10)
        self.set_text_color(80, 80, 80) # Gris foncé
        self.cell(100, 10, f"Exhumé par {data['exhume_par']}", ln=False)

        # --- PARTIE DROITE (TEXTE) ---
        # On travaille avec une marge interne à droite
        margin_right_block = 15
        x_start_text = mid_point + margin_right_block
        width_text = mid_point - (margin_right_block * 2)

        # 1. Année (Haut Droite)
        self.set_xy(x_start_text, 25)
        self.set_font('Arial', 'B', 18)
        self.set_text_color(0, 0, 0)
        # Alignement à Droite comme sur l'image
        self.cell(width_text, 10, str(data['annee']), ln=True, align='R')
        
        # 2. Titre (Gros, Uppercase, Alignement Droite)
        self.set_x(x_start_text)
        self.set_font('Arial', 'B', 24)
        self.multi_cell(width_text, 10, data['titre'].upper(), align='R')
        self.ln(10)

        # 3. Description (Corps de texte, Justifié ou Gauche, Serif)
        self.set_x(x_start_text)
        self.set_font('Times', '', 11) # Times pour imiter le sérif du corps de texte
        self.set_text_color(20, 20, 20)
        self.multi_cell(width_text, 6, data['description'], align='L')
        
        # 4. Catégories / Source (Bas de page Droite)
        self.set_xy(x_start_text, 180)
        self.set_font('Arial', '', 8)
        
        # Affichage des catégories jointes
        cats_str = " • ".join(data['categories'])
        self.cell(width_text, 5, f"Catégories : {cats_str}", ln=True, align='L')
        
        self.ln(2)
        self.set_font('Arial', 'B', 9)
        self.cell(width_text, 5, "← Pour aller plus loin", ln=True, align='L')

# --- INTERFACE STREAMLIT ---

st.set_page_config(page_title="Paleo-énergétique Maker", layout="wide")

# CSS personnalisé pour l'esthétique
st.markdown("""
<style>
    .stApp {
        background-color: #FAFAFA;
    }
    h1 {
        color: #D65A5A;
    }
    div.stButton > button {
        background-color: #F2EDEC;
        color: black;
        border: 1px solid #D65A5A;
    }
    div.stButton > button:hover {
        background-color: #D65A5A;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

st.title("⚡ Atelier Cartels Paleo-énergétique")

tab1, tab2 = st.tabs(["✍️ Édition", "📚 Bibliothèque"])

# --- ONGLET 1 : CRÉATION ---
with tab1:
    col1, col2 = st.columns([1, 1.5])
    
    with col1:
        st.subheader("Visuel")
        uploaded_file = st.file_uploader("Image du dispositif", type=['png', 'jpg', 'jpeg'])
        if uploaded_file:
            st.image(uploaded_file, caption="Aperçu", use_column_width=True)
        else:
            st.info("Veuillez charger une image pour commencer.")
    
    with col2:
        st.subheader("Informations")
        with st.form("cartel_form"):
            # Année
            annee = st.text_input("Année / Époque (ex: 1206 ou 20 ap. J.-C.)", value="2025")
            
            # Titre
            titre = st.text_input("Titre du cartel (ex: HYDRO POMPE DE SAQIYA)")
            
            # Description
            description = st.text_area("Description complète", height=200, help="Le texte explicatif qui sera sur le fond rose.")
            
            # Crédit
            exhume_par = st.text_input("Exhumé par (Nom Prénom)")
            
            st.markdown("---")
            st.markdown("**Catégorisation**")
            
            # Liste imposée
            categories_base = ["Énergie", "H2O", "Mobilité", "Alimentation", "Solaire", "Eolien"]
            
            # Multiselect pour les catégories de base
            selected_cats = st.multiselect("Choisir les catégories", categories_base)
            
            # Ajout catégorie personnalisée
            new_cat_input = st.text_input("Ajouter une autre catégorie (optionnel)")
            
            submitted = st.form_submit_button("🚀 Créer le Cartel")
            
            if submitted and titre and uploaded_file:
                # Gestion des catégories
                final_cats = selected_cats.copy()
                if new_cat_input:
                    final_cats.append(new_cat_input)
                
                # 1. Sauvegarde Image
                img_path = save_image(uploaded_file)
                
                # 2. Création Donnée
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
                
                # 3. Sauvegarde JSON
                save_data(entry)
                st.success(f"Cartel '{titre}' créé !")
                
                # 4. Génération PDF
                pdf = PDF()
                pdf.create_cartel(entry)
                pdf_byte = pdf.output(dest='S').encode('latin-1', 'ignore')
                
                st.download_button(
                    label="⬇️ Télécharger le PDF (Design Officiel)",
                    data=pdf_byte,
                    file_name=f"Cartel_{titre.replace(' ', '_')}.pdf",
                    mime='application/pdf',
                )

# --- ONGLET 2 : CONSULTATION ---
with tab2:
    st.header("Bibliothèque des Inventions")
    
    data = load_data()
    
    if not data:
        st.info("La bibliothèque est vide.")
    else:
        df = pd.DataFrame(data)
        
        # Filtres
        all_cats_recorded = set()
        for cats in df['categories']:
            for c in cats:
                all_cats_recorded.add(c)
                
        cat_filter = st.multiselect("Filtrer par catégorie", list(all_cats_recorded))
        
        # Filtrage logique
        if cat_filter:
            # On garde les lignes où AU MOINS UNE des catégories sélectionnées est présente
            mask = df['categories'].apply(lambda x: any(item in cat_filter for item in x))
            df = df[mask]
            
        st.write(f"Nombre de fiches trouvées : {len(df)}")
        st.divider()
        
        for index, row in df.iterrows():
            with st.container():
                c1, c2 = st.columns([1, 4])
                with c1:
                    if os.path.exists(row['image_path']):
                        st.image(row['image_path'])
                with c2:
                    st.subheader(f"{row['titre']} ({row['annee']})")
                    # Affichage des tags
                    st.caption(" • ".join(row['categories']))
                    st.write(row['description'][:200] + "...")
                    st.markdown(f"*Exhumé par : {row['exhume_par']}*")
                    
                    # Bouton pour ré-générer le PDF de cette archive précise
                    if st.button(f"📄 PDF: {row['titre']}", key=row['id']):
                        pdf_single = PDF()
                        pdf_single.create_cartel(row.to_dict())
                        pdf_single_byte = pdf_single.output(dest='S').encode('latin-1', 'ignore')
                        # Note: st.download_button ne peut pas être déclenché dans une boucle conditionnelle simple sans recharger
                        # Astuce Streamlit: on affiche un lien de téléchargement unique si cliqué
                        st.download_button(
                            label="Télécharger maintenant",
                            data=pdf_single_byte,
                            file_name=f"Re_Cartel_{row['id']}.pdf",
                            mime='application/pdf',
                            key=f"dl_{row['id']}"
                        )
                st.divider()
