import streamlit as st
import pandas as pd
import json
import os
import zipfile
import io
import textwrap
import qrcode
import re
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from github import Github, InputGitTreeElement # Nouvelle librairie pour sauvegarder

# --- CONFIGURATION INITIALE ---
st.set_page_config(page_title="Paleo Maker", layout="wide", initial_sidebar_state="collapsed")

DATA_FILE = "db_cartels.json"
IMG_FOLDER = "images_archive"
PINK_RGB = (252, 237, 236)
PINK_HEX = "#FCEDEC"

# Configuration DPI pour impression (A4 à 300 DPI)
DPI = 300
A4_WIDTH_PX = 3508
A4_HEIGHT_PX = 2480
MM_TO_PX = A4_WIDTH_PX / 297

# Création des dossiers locaux
if not os.path.exists(IMG_FOLDER):
    os.makedirs(IMG_FOLDER)
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'w') as f:
        json.dump([], f)

# --- FONCTION DE SAUVEGARDE GITHUB (CLOUD) ---
def push_to_github(file_path, content_bytes=None, message="Mise à jour automatique"):
    """Envoie un fichier vers GitHub pour le rendre permanent"""
    # On vérifie si les secrets sont configurés (pour éviter de planter en local si pas configuré)
    if "GITHUB_TOKEN" in st.secrets and "GITHUB_REPO" in st.secrets:
        try:
            g = Github(st.secrets["GITHUB_TOKEN"])
            repo = g.get_repo(st.secrets["GITHUB_REPO"])
            
            # Si content_bytes est None, on lit le fichier local
            if content_bytes is None:
                with open(file_path, 'rb') as f:
                    content_bytes = f.read()
            
            # On essaie de récupérer le fichier s'il existe déjà (pour update)
            try:
                contents = repo.get_contents(file_path)
                repo.update_file(contents.path, message, content_bytes, contents.sha)
                # print(f"GitHub: {file_path} mis à jour.")
            except:
                # Sinon on le crée
                repo.create_file(file_path, message, content_bytes)
                # print(f"GitHub: {file_path} créé.")
            return True
        except Exception as e:
            st.error(f"Erreur de sauvegarde GitHub : {e}")
            return False
    else:
        # Si on est en local sans secrets, on ne fait rien (juste sauvegarde locale)
        return False

# --- FONCTIONS UTILITAIRES ---
def load_data():
    # Au démarrage, on pourrait idéalement télécharger le JSON depuis GitHub 
    # pour être sûr d'avoir la dernière version, mais pour l'instant on lit le local.
    # Si l'app redémarre, Streamlit remet les fichiers du repo, donc le JSON sera à jour.
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []

def save_data(new_entry):
    # 1. Sauvegarde Locale
    data = load_data()
    data.append(new_entry)
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)
    
    # 2. Sauvegarde Cloud (JSON)
    push_to_github(DATA_FILE, message=f"Ajout cartel: {new_entry['titre']}")
    
    # 3. Sauvegarde Cloud (Image)
    if new_entry.get('image_path') and os.path.exists(new_entry['image_path']):
        push_to_github(new_entry['image_path'], message=f"Ajout image: {new_entry['titre']}")

def update_data(updated_entry):
    # 1. Update Local
    data = load_data()
    for i, d in enumerate(data):
        if d['id'] == updated_entry['id']:
            data[i] = updated_entry
            break
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)
        
    # 2. Update Cloud
    push_to_github(DATA_FILE, message=f"Modif cartel: {updated_entry['titre']}")
    # Si l'image a changé, on la push aussi
    if updated_entry.get('image_path') and os.path.exists(updated_entry['image_path']):
         push_to_github(updated_entry['image_path'], message=f"Modif image: {updated_entry['titre']}")

def delete_data(cartel_id):
    # 1. Delete Local
    data = load_data()
    # On trouve le cartel pour savoir s'il y a une image à supprimer (optionnel, on garde l'image par sécurité)
    new_data = [d for d in data if d['id'] != cartel_id]
    with open(DATA_FILE, 'w') as f:
        json.dump(new_data, f, indent=4)
    
    # 2. Update Cloud (On met à jour le JSON pour retirer l'entrée)
    push_to_github(DATA_FILE, message=f"Suppression cartel ID {cartel_id}")

def save_image(uploaded_file):
    if uploaded_file is not None:
        file_path = os.path.join(IMG_FOLDER, uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        return file_path
    return None

def toggle_selection(cartel_id):
    if cartel_id in st.session_state.selection_active:
        st.session_state.selection_active.remove(cartel_id)
    else:
        st.session_state.selection_active.add(cartel_id)

def get_year_for_sort(entry):
    annee_text = str(entry.get('annee', '9999'))
    match = re.search(r'-?\d+', annee_text)
    if match:
        return int(match.group())
    return 9999

# --- GENERATEUR IMAGE ---
def generate_cartel_image(data):
    img = Image.new('RGB', (A4_WIDTH_PX, A4_HEIGHT_PX), color='white')
    draw = ImageDraw.Draw(img)
    mid_x = int(A4_WIDTH_PX / 2)
    draw.rectangle([mid_x, 0, A4_WIDTH_PX, A4_HEIGHT_PX], fill=PINK_RGB)
    
    try:
        font_year = ImageFont.truetype("PTSansNarrow-Bold.ttf", 90)
        font_title = ImageFont.truetype("PTSansNarrow-Bold.ttf", 120)
        font_body = ImageFont.truetype("PTSerif-Regular.ttf", 55)
        font_credit = ImageFont.truetype("PTSansNarrow-Bold.ttf", 45)
        font_cats = ImageFont.truetype("PTSansNarrow-Regular.ttf", 40)
    except:
        font_year = ImageFont.load_default()
        font_title = font_year
        font_body = font_year
        font_credit = font_year
        font_cats = font_year

    margin = int(15 * MM_TO_PX)
    
    if data.get('image_path') and os.path.exists(data['image_path']):
        try:
            pil_img = Image.open(data['image_path'])
            box_x = margin
            box_y = int(30 * MM_TO_PX)
            box_w = mid_x - (2 * margin)
            box_h = int(145 * MM_TO_PX)
            
            img_ratio = pil_img.width / pil_img.height
            box_ratio = box_w / box_h
            
            if img_ratio > box_ratio:
                new_w = box_w
                new_h = int(box_w / img_ratio)
            else:
                new_h = box_h
                new_w = int(box_h * img_ratio)
                
            pil_img = pil_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            pos_x = box_x + (box_w - new_w) // 2
            pos_y = box_y + (box_h - new_h) // 2
            img.paste(pil_img, (pos_x, pos_y))
        except Exception as e:
            print(f"Erreur image: {e}")

    credit_y = int(185 * MM_TO_PX)
    draw.text((margin, credit_y), f"Exhumé par {data['exhume_par']}", font=font_credit, fill=(80, 80, 80))

    text_x_start = mid_x + margin
    year_str = str(data['annee'])
    bbox = draw.textbbox((0, 0), year_str, font=font_year)
    text_w = bbox[2] - bbox[0]
    draw.text((A4_WIDTH_PX - margin - text_w, int(25 * MM_TO_PX)), year_str, font=font_year, fill="black")
    
    title_str = data['titre'].upper()
    title_lines = textwrap.wrap(title_str, width=18) 
    current_y = int(50 * MM_TO_PX)
    for line in title_lines:
        bbox = draw.textbbox((0, 0), line, font=font_title)
        line_w = bbox[2] - bbox[0]
        line_h = bbox[3] - bbox[1]
        draw.text((A4_WIDTH_PX - margin - line_w, current_y), line, font=font_title, fill="black")
        current_y += line_h + 20
    current_y += 60

    desc_lines = textwrap.wrap(data['description'], width=50)
    for line in desc_lines:
        draw.text((text_x_start, current_y), line, font=font_body, fill=(20, 20, 20))
        bbox = draw.textbbox((0, 0), line, font=font_body)
        line_h = bbox[3] - bbox[1]
        current_y += line_h + 15

    cats_str = " • ".join(data['categories'])
    cat_y = int(180 * MM_TO_PX)
    draw.text((text_x_start, cat_y), f"Catégories : {cats_str}", font=font_cats, fill="black")
    
    if data.get('url_qr'):
        try:
            qr = qrcode.QRCode(version=1, box_size=10, border=1)
            qr.add_data(data['url_qr'])
            qr.make(fit=True)
            qr_img = qr.make_image(fill_color="black", back_color=PINK_RGB)
            qr_size_px = int(30 * MM_TO_PX)
            qr_img = qr_img.resize((qr_size_px, qr_size_px), Image.Resampling.NEAREST)
            qr_x = A4_WIDTH_PX - margin - qr_size_px
            qr_y = A4_HEIGHT_PX - margin - qr_size_px
            img.paste(qr_img, (qr_x, qr_y))
        except: pass
    
    return img

# --- PREVIEW HTML ---
def afficher_cartel_visuel(data):
    c1, c2 = st.columns([1, 1])
    with c1:
        if data.get('image_path') and os.path.exists(data['image_path']):
            st.image(data['image_path'], use_column_width=True)
        else:
            st.info("Aucune image")
        st.markdown(f"<div style='color:gray; font-size:0.8em;'>Exhumé par {data['exhume_par']}</div>", unsafe_allow_html=True)
    with c2:
        cats = " • ".join(data['categories'])
        qr_html = ""
        if data.get('url_qr'):
            qr_html = f"""
            <div style="margin-top:10px; text-align:right;">
                <div style="display:inline-block; border:1px solid black; padding:5px; background-color:{PINK_HEX};">
                    <small>QR CODE ACTIF</small><br>
                    <small style="font-size:0.6em;">{data['url_qr'][:30]}...</small>
                </div>
            </div>
            """
        st.markdown(f"""
        <div style="background-color: {PINK_HEX}; padding: 20px; border-radius: 5px; color: black; min-height: 300px;">
            <div style="text-align: right; font-weight: bold; font-size: 1.2em;">{data['annee']}</div>
            <div style="text-align: right; font-weight: bold; font-size: 1.5em; line-height: 1.1; margin-bottom: 20px; text-transform: uppercase;">{data['titre']}</div>
            <div style="font-family: serif; font-size: 1em; text-align: left;">{data['description'][:250]}...</div>
            <br>
            <small>Catégories : {cats}</small>
            {qr_html}
        </div>
        """, unsafe_allow_html=True)

# --- INIT DATA ---
full_data = load_data()
categories_pool = set(["Énergie", "H2O", "Mobilité", "Alimentation", "Solaire", "Eolien"])
for entry in full_data:
    for c in entry.get('categories', []):
        categories_pool.add(c)
dynamic_cats_list = sorted(list(categories_pool))
full_data.sort(key=get_year_for_sort)


# --- INTERFACE ---
st.title("⚡ PALEO-ÉNERGÉTIQUE")

tab_create, tab_library = st.tabs(["NOUVEAU CARTEL", "BIBLIOTHÈQUE & EXPORT"])

# === ONGLET 1 : CRÉATION ===
with tab_create:
    st.subheader("Créer une nouvelle fiche")
    with st.form("new_cartel"):
        col_gauche, col_droite = st.columns(2)
        with col_gauche:
            uploaded_file = st.file_uploader("Image (Optionnel)", type=['png', 'jpg', 'jpeg'])
            exhume_par = st.text_input("Exhumé par")
        with col_droite:
            titre = st.text_input("Titre (Obligatoire)")
            annee = st.text_input("Année", value="2025")
        
        description = st.text_area("Description", height=150)
        c_cat, c_qr = st.columns(2)
        with c_cat:
            selected_cats = st.multiselect("Catégories", dynamic_cats_list)
            new_cat = st.text_input("Autre catégorie (Ajout)")
        with c_qr:
            url_qr = st.text_input("Lien QR Code (Optionnel)")
        
        submit_create = st.form_submit_button("ENREGISTRER LE CARTEL", type="primary")

    if submit_create:
        if not titre:
            st.error("Le titre est obligatoire.")
        else:
            with st.spinner('Sauvegarde vers GitHub...'): # Feedback visuel
                final_cats = selected_cats + ([new_cat] if new_cat else [])
                img_path = save_image(uploaded_file)
                entry = {
                    "id": datetime.now().strftime("%Y%m%d%H%M%S"),
                    "titre": titre, "annee": annee, "description": description,
                    "exhume_par": exhume_par, "categories": final_cats,
                    "url_qr": url_qr, "image_path": img_path, "date": datetime.now().strftime("%Y-%m-%d")
                }
                save_data(entry)
            st.success("✅ Cartel enregistré et sécurisé sur GitHub !")
            st.rerun()

# === ONGLET 2 : BIBLIOTHÈQUE ===
with tab_library:
    if 'selection_active' not in st.session_state: st.session_state.selection_active = set()
    if 'editing_id' not in st.session_state: st.session_state.editing_id = None

    if not full_data:
        st.info("Aucune archive.")
    else:
        st.markdown("### Filtres & Actions")
        cat_filter = st.multiselect("Filtrer par catégorie", dynamic_cats_list)
        filtered_data = full_data
        if cat_filter:
            filtered_data = [d for d in full_data if any(cat in d['categories'] for cat in cat_filter)]

        count_sel = len(st.session_state.selection_active)
        col_inf, col_exp = st.columns([2, 1])
        with col_inf:
            st.caption(f"{len(filtered_data)} affichés | {count_sel} sélectionnés")
        with col_exp:
            if st.button(f"GÉNÉRER LE ZIP ({count_sel})", use_container_width=True):
                if count_sel == 0:
                    st.error("Sélection vide.")
                else:
                    final_selection = [d for d in full_data if d['id'] in st.session_state.selection_active]
                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, "w") as zf:
                        prog = st.progress(0)
                        for i, item in enumerate(final_selection):
                            img = generate_cartel_image(item)
                            buf = io.BytesIO()
                            img.save(buf, format='JPEG', quality=95)
                            fname = f"Cartel_{item['titre'].replace(' ','_')}_{item['id']}.jpg"
                            zf.writestr(fname, buf.getvalue())
                            prog.progress((i+1)/len(final_selection))
                    st.download_button("⬇️ TÉLÉCHARGER ZIP", zip_buffer.getvalue(), "Cartels.zip", "application/zip")

        st.divider()
        
        for row in filtered_data:
            c_chk, c_vis, c_act = st.columns([0.1, 2, 0.4]) 
            
            with c_chk:
                st.write("")
                st.write("")
                is_sel = row['id'] in st.session_state.selection_active
                st.checkbox("", key=f"chk_{row['id']}", value=is_sel, on_change=toggle_selection, args=(row['id'],))
            
            with c_vis:
                afficher_cartel_visuel(row)
                
                if st.session_state.editing_id == row['id']:
                    st.markdown(f"<div class='edit-box'>Modification : <b>{row['titre']}</b></div>", unsafe_allow_html=True)
                    with st.form(f"edit_form_{row['id']}"):
                        e_c1, e_c2 = st.columns(2)
                        with e_c1:
                            e_ti = st.text_input("Titre", value=row['titre'])
                            e_an = st.text_input("Année", value=row['annee'])
                            e_ex = st.text_input("Exhumé par", value=row['exhume_par'])
                            e_im = st.file_uploader("Nouvelle image ?", type=['png', 'jpg'])
                        with e_c2:
                            e_de = st.text_area("Description", value=row['description'])
                            cur_cats = [c for c in row['categories'] if c in dynamic_cats_list]
                            e_ca = st.multiselect("Catégories", dynamic_cats_list, default=cur_cats)
                            e_qr = st.text_input("QR Link", value=row.get('url_qr',''))
                        
                        col_save, col_cancel = st.columns([1, 1])
                        with col_save:
                            if st.form_submit_button("💾 Sauvegarder"):
                                with st.spinner('Mise à jour sur GitHub...'):
                                    n_path = row.get('image_path')
                                    if e_im: n_path = save_image(e_im)
                                    up_entry = row.copy()
                                    up_entry.update({"titre":e_ti, "annee":e_an, "description":e_de, "exhume_par":e_ex, "categories":e_ca, "url_qr":e_qr, "image_path":n_path})
                                    update_data(up_entry)
                                st.session_state.editing_id = None
                                st.success("Modifié !")
                                st.rerun()
                        with col_cancel:
                            if st.form_submit_button("Annuler"):
                                st.session_state.editing_id = None
                                st.rerun()

            with c_act:
                st.write("")
                st.write("") 
                act_edit, act_del = st.columns(2)
                with act_edit:
                    if st.button("✏️", key=f"btn_edit_{row['id']}", help="Modifier"):
                        if st.session_state.editing_id == row['id']:
                            st.session_state.editing_id = None
                        else:
                            st.session_state.editing_id = row['id']
                        st.rerun()
                with act_del:
                    if st.button("🗑️", key=f"btn_del_{row['id']}", help="Supprimer"):
                        st.session_state[f"confirm_del_{row['id']}"] = True
                
                if st.session_state.get(f"confirm_del_{row['id']}"):
                    st.markdown("<small style='color:red; font-weight:bold;'>Supprimer ?</small>", unsafe_allow_html=True)
                    if st.button("OUI", key=f"yes_del_{row['id']}"):
                        with st.spinner('Suppression sur GitHub...'):
                            delete_data(row['id'])
                        st.rerun()
                    if st.button("NON", key=f"no_del_{row['id']}"):
                        st.session_state[f"confirm_del_{row['id']}"] = False
                        st.rerun()

            st.divider()
