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
    """Sauvegarde l'image uploadée et retourne le chemin"""
    if uploaded_file is not None:
        file_path = os.path.join(IMG_FOLDER, uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        return file_path
    return None

class PDF(FPDF):
    """Classe pour générer le design du cartel"""
    def header(self):
        pass # Pas de header global, chaque page est un cartel

    def create_cartel(self, data):
        self.add_page()
        # Marge et configuration
        self.set_margins(10, 10, 10)
        
        # 1. Image (Haut)
        if data['image_path'] and os.path.exists(data['image_path']):
            # On place l'image pour qu'elle prenne le tiers haut environ
            try:
                self.image(data['image_path'], x=10, y=10, w=190) 
            except:
                pass # Si erreur d'image, on continue
        
        # On déplace le curseur sous l'image (position approximative, à ajuster selon ratio)
        self.set_y(120) 

        # 2. Année (Gros, style tampon)
        self.set_font('Arial', 'B', 24)
        self.cell(0, 10, str(data['annee']), ln=True, align='L')
        
        # 3. Titre (Gros, Uppercase)
        self.set_font('Arial', 'B', 18)
        self.multi_cell(0, 10, data['titre'].upper())
        self.ln(5)

        # 4. Description (Corps de texte)
        self.set_font('Arial', '', 12)
        self.multi_cell(0, 6, data['description'])
        self.ln(10)

        # 5. Crédits (Exhumé par...)
        self.set_font('Arial', 'I', 10)
        self.cell(0, 6, f"Exhumé par : {data['exhume_par']}", ln=True)
        self.cell(0, 6, f"Source/Catégorie : {data['categorie']}", ln=True)
        
        # 6. Footer (Pour aller plus loin)
        self.set_y(-20)
        self.set_font('Arial', 'B', 10)
        self.cell(0, 10, "← Pour aller plus loin", align='R')

# --- INTERFACE STREAMLIT ---

st.set_page_config(page_title="Générateur de Cartels Paléo-énergétiques", layout="wide")

st.title("⚡ Archivage & Génération de Cartels")
st.markdown("Outil pour le projet **Paleo-energetique**.")

tab1, tab2 = st.tabs(["➕ Nouveau Cartel", "📂 Consulter l'Archive"])

# --- ONGLET 1 : CRÉATION ---
with tab1:
    st.header("Créer une nouvelle fiche")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        uploaded_file = st.file_uploader("Image du dispositif", type=['png', 'jpg', 'jpeg'])
        if uploaded_file:
            st.image(uploaded_file, caption="Aperçu", use_column_width=True)
    
    with col2:
        with st.form("cartel_form"):
            annee = st.number_input("Année (ex: 2025)", min_value=1900, max_value=2100, step=1, value=2025)
            titre = st.text_input("Titre du cartel (ex: Relamping du tube néon)")
            description = st.text_area("Description complète", height=150)
            exhume_par = st.text_input("Exhumé par (Nom Prénom)")
            categorie = st.selectbox("Catégorie", ["Low-tech", "Rétro-fit", "Hack", "Démarche collective", "Autre"])
            
            submitted = st.form_submit_button("💾 Enregistrer et Générer")
            
            if submitted and titre and description and uploaded_file:
                # 1. Sauvegarde Image
                img_path = save_image(uploaded_file)
                
                # 2. Création Donnée
                entry = {
                    "id": datetime.now().strftime("%Y%m%d%H%M%S"),
                    "annee": annee,
                    "titre": titre,
                    "description": description,
                    "exhume_par": exhume_par,
                    "categorie": categorie,
                    "image_path": img_path,
                    "date_ajout": datetime.now().strftime("%Y-%m-%d")
                }
                
                # 3. Sauvegarde JSON
                save_data(entry)
                st.success(f"Cartel '{titre}' archivé avec succès !")
                
                # 4. Génération PDF unique immédiate
                pdf = PDF()
                pdf.create_cartel(entry)
                pdf_byte = pdf.output(dest='S').encode('latin-1', 'ignore') # Astuce pour streamlit
                
                st.download_button(
                    label="⬇️ Télécharger le PDF de ce cartel",
                    data=pdf_byte,
                    file_name=f"Cartel_{titre.replace(' ', '_')}.pdf",
                    mime='application/pdf',
                )

# --- ONGLET 2 : CONSULTATION ---
with tab2:
    st.header("Archives Chronologiques")
    
    data = load_data()
    
    if not data:
        st.info("Aucun cartel enregistré pour le moment.")
    else:
        df = pd.DataFrame(data)
        
        # Filtres
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            cat_filter = st.multiselect("Filtrer par catégorie", df['categorie'].unique())
        with col_f2:
            sort_order = st.radio("Tri", ["Plus récent au plus ancien", "Chronologique (Année)"])
        
        # Application filtres
        if cat_filter:
            df = df[df['categorie'].isin(cat_filter)]
            
        if sort_order == "Chronologique (Année)":
            df = df.sort_values(by="annee", ascending=True)
        else:
            df = df.sort_values(by="date_ajout", ascending=False)
            
        st.divider()
        
        # Affichage Liste
        for index, row in df.iterrows():
            c1, c2 = st.columns([1, 3])
            with c1:
                if os.path.exists(row['image_path']):
                    st.image(row['image_path'])
                else:
                    st.warning("Image introuvable")
            with c2:
                st.subheader(f"{row['annee']} - {row['titre']}")
                st.markdown(f"**{row['categorie']}** | Exhumé par : *{row['exhume_par']}*")
                st.write(row['description'])
                st.caption(f"Ajouté le {row['date_ajout']}")
            st.divider()
            
        # Export Global
        st.subheader("Export")
        if st.button("Générer un PDF de la sélection actuelle"):
            pdf_global = PDF()
            for index, row in df.iterrows():
                pdf_global.create_cartel(row.to_dict())
            
            pdf_global_byte = pdf_global.output(dest='S').encode('latin-1', 'ignore')
            st.download_button(
                label="⬇️ Télécharger le PDF complet (Liste filtrée)",
                data=pdf_global_byte,
                file_name="Catalogue_Cartels.pdf",
                mime='application/pdf'
            )
