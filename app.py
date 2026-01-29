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
from github import Github, InputGitTreeElement

# --- CONFIGURATION INITIALE ---
st.set_page_config(page_title="Paleo Maker", layout="wide", initial_sidebar_state="collapsed")

DATA_FILE = "db_cartels.json"
DRAFTS_FILE = "db_drafts.json"
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
if not os.path.exists(DRAFTS_FILE):
    with open(DRAFTS_FILE, 'w') as f:
        json.dump([], f)

# --- GESTION DES NOTIFICATIONS ---
if 'flash_msg' in st.session_state and st.session_state.flash_msg:
    st.success(st.session_state.flash_msg)
    if "succès" in st.session_state.flash_msg or "Publié" in st.session_state.flash_msg:
        st.balloons()
    st.session_state.flash_msg = None

# --- NAVIGATION ---
if 'nav_index' not in st.session_state:
    st.session_state.nav_index = 0 

def set_page(index):
    st.session_state.nav_index = index

# --- SAUVEGARDE GITHUB ---
def push_to_github(file_path, content_bytes=None, message="Mise à jour automatique"):
    if "GITHUB_TOKEN" in st.secrets and "GITHUB_REPO" in st.secrets:
        try:
            g = Github(st.secrets["GITHUB_TOKEN"])
            repo = g.get_repo(st.secrets["GITHUB_REPO"])
            if content_bytes is None:
                with open(file_path, 'rb') as f:
                    content_bytes = f.read()
            try:
                contents = repo.get_contents(file_path)
                repo.update_file(contents.path, message, content_bytes, contents.sha)
            except:
                repo.create_file(file_path, message, content_bytes)
            return True
        except Exception as e:
            return False
    return False

# --- GESTION DES DONNÉES ---
def load_json(filename):
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []

def save_entry(entry, filename, msg_prefix="Ajout"):
    data = load_json(filename)
    data.append(entry)
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)
    push_to_github(filename, message=f"{msg_prefix}: {entry.get('titre', 'Sans titre')}")
    
    if entry.get('image_path') and os.path.exists(entry['image_path']):
        push_to_github(entry['image_path'], message=f"Img: {entry.get('titre')}")

def update_entry(updated_entry, filename, msg_prefix="Modif"):
    data = load_json(filename)
    for i, d in enumerate(data):
        if d['id'] == updated_entry['id']:
            data[i] = updated_entry
            break
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)
    push_to_github(filename, message=f"{msg_prefix}: {updated_entry.get('titre')}")
    
    if updated_entry.get('image_path') and os.path.exists(updated_entry['image_path']):
         push_to_github(updated_entry['image_path'], message=f"Img Modif: {updated_entry.get('titre')}")

def delete_entry(entry_id, filename, msg_prefix="Del"):
    data = load_json(filename)
    new_data = [d for d in data if d['id'] != entry_id]
    with open(filename, 'w') as f:
        json.dump(new_data, f, indent=4)
    push_to_github(filename, message=f"{msg_prefix} ID {entry_id}")

def publish_draft(draft_id):
    drafts = load_json(DRAFTS_FILE)
    draft_to_publish = next((d for d in drafts if d['id'] == draft_id), None)
    
    if draft_to_publish:
        draft_to_publish['date'] = datetime.now().strftime("%Y-%m-%d")
        save_entry(draft_to_publish, DATA_FILE, msg_prefix="PUBLICATION")
        delete_entry(draft_id, DRAFTS_FILE, msg_prefix="Archivage Brouillon")
        return True
    return False

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

# --- FONCTION DE TRI ---
def roman_to_int(s):
    roman = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}
    num = 0
    try:
        s = s.upper()
        for i in range(len(s) - 1):
            if roman[s[i]] < roman[s[i + 1]]:
                num -= roman[s[i]]
            else:
                num += roman[s[i]]
        num += roman[s[-1]]
        return num
    except: return 0

def get_year_for_sort(entry):
    text = str(entry.get('annee', '9999')).lower().strip()
    is_bc = 'av' in text or 'bc' in text or 'bef' in text or text.startswith('-')
    
    match_digit = re.search(r'\d+', text)
    if match_digit:
        val = int(match_digit.group())
        if is_bc: val = -abs(val)
        return val

    match_roman = re.search(r'(?i)\b[mdclxvi]+\b', text)
    if match_roman:
        val = roman_to_int(match_roman.group()) * 100
        if is_bc: val = -abs(val)
        return val
    return 9999

# --- OUTILS DE TEXTE PIL ---
def wrap_text_pixel(text, font, max_width, draw):
    """Découpe le texte en lignes selon la largeur en pixels"""
    lines = []
    paragraphs = text.split('\n')
    
    for paragraph in paragraphs:
        if not paragraph:
            lines.append("")
            continue
        words = paragraph.split()
        if not words: continue
        current_line = words[0]
        for word in words[1:]:
            test_line = current_line + " " + word
            bbox = draw.textbbox((0, 0), test_line, font=font)
            w = bbox[2] - bbox[0]
            if w <= max_width:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = word
        lines.append(current_line)
    return lines

# --- GENERATEUR IMAGE OPTIMISÉ ---
def generate_cartel_image(data):
    img = Image.new('RGB', (A4_WIDTH_PX, A4_HEIGHT_PX), color='white')
    draw = ImageDraw.Draw(img)
    mid_x = int(A4_WIDTH_PX / 2)
    draw.rectangle([mid_x, 0, A4_WIDTH_PX, A4_HEIGHT_PX], fill=PINK_RGB)
    
    def load_font(name, size):
        try: return ImageFont.truetype(name, size)
        except: return ImageFont.load_default()

    font_year_size = 90
    font_title_size = 120
    font_body_base_size = 55
    
    font_year = load_font("PTSansNarrow-Bold.ttf", font_year_size)
    font_title = load_font("PTSansNarrow-Bold.ttf", font_title_size)
    font_credit = load_font("PTSansNarrow-Bold.ttf", 45)
    font_cats = load_font("PTSansNarrow-Regular.ttf", 40)

    margin = int(15 * MM_TO_PX)
    
    # IMAGE
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
        except: pass

    # Crédit
    credit_y = int(185 * MM_TO_PX)
    draw.text((margin, credit_y), f"Exhumé par {data.get('exhume_par', '')}", font=font_credit, fill=(80, 80, 80))

    # DROITE
    text_x_start = mid_x + margin
    text_width_limit = A4_WIDTH_PX - text_x_start - margin
    current_y = int(15 * MM_TO_PX) 

    # Année
    year_str = str(data.get('annee', ''))
    bbox_year = draw.textbbox((0, 0), year_str, font=font_year)
    year_w = bbox_year[2] - bbox_year[0]
    draw.text((A4_WIDTH_PX - margin - year_w, current_y), year_str, font=font_year, fill="black")
    current_y += font_year_size + 10

    # Titre
    title_str = data.get('titre', '').upper()
    title_lines = wrap_text_pixel(title_str, font_title, text_width_limit, draw)
    for line in title_lines:
        bbox = draw.textbbox((0, 0), line, font=font_title)
        line_w = bbox[2] - bbox[0]
        draw.text((A4_WIDTH_PX - margin - line_w, current_y), line, font=font_title, fill="black")
        current_y += font_title_size + 15
    current_y += 40

    # Description (Auto-Fit)
    desc_text = data.get('description', '')
    footer_y_start = int(180 * MM_TO_PX)
    available_height = footer_y_start - current_y - 20
    
    font_desc_size = font_body_base_size
    font_body = load_font("PTSerif-Regular.ttf", font_desc_size)
    desc_lines = []
    
    while font_desc_size > 20: 
        font_body = load_font("PTSerif-Regular.ttf", font_desc_size)
        desc_lines = wrap_text_pixel(desc_text, font_body, text_width_limit, draw)
        line_height = font_desc_size + 15
        total_text_height = len(desc_lines) * line_height
        if total_text_height <= available_height:
            break 
        font_desc_size -= 2
    
    for line in desc_lines:
        draw.text((text_x_start, current_y), line, font=font_body, fill=(20, 20, 20))
        current_y += font_desc_size + 15

    # Footer
    cats_str = " • ".join(data.get('categories', []))
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
def afficher_cartel_visuel(data, is_draft=False):
    c1, c2 = st.columns([1, 1])
    with c1:
        if data.get('image_path') and os.path.exists(data['image_path']):
            st.image(data['image_path'], use_column_width=True)
        else:
            st.info("Aucune image")
        st.markdown(f"<div style='color:gray; font-size:0.8em;'>Exhumé par {data.get('exhume_par', '')}</div>", unsafe_allow_html=True)
    with c2:
        cats = " • ".join(data.get('categories', []))
        
        link_html = ""
        if data.get('url_qr'):
            link_html = f'<div style="margin-top:15px; text-align:right;"><a href="{data["url_qr"]}" target="_blank" style="text-decoration:none; background-color:black; color:white; padding:5px 10px; border-radius:4px; font-family:sans-serif; font-size:0.8em;">🔗 LIEN</a></div>'
        
        draft_badge = ""
        if is_draft:
            draft_badge = "<div style='background:gold; color:black; padding:5px; text-align:center; font-weight:bold; margin-bottom:10px;'>⚠️ BROUILLON</div>"

        full_description = data.get('description', '').replace('\n', '<br>')

        st.markdown(f"""
<div style="background-color: {PINK_HEX}; padding: 20px; border-radius: 5px; color: black; min-height: 300px;">
{draft_badge}
<div style="text-align: right; font-weight: bold; font-size: 1.2em;">{data.get('annee', '')}</div>
<div style="text-align: right; font-weight: bold; font-size: 1.5em; line-height: 1.1; margin-bottom: 20px; text-transform: uppercase;">{data.get('titre', '')}</div>
<div style="font-family: serif; font-size: 1em; text-align: left;">{full_description}</div>
<br>
<small>Catégories : {cats}</small>
{link_html}
</div>
""", unsafe_allow_html=True)

# --- INIT DATA ---
full_data = load_json(DATA_FILE)
drafts_data = load_json(DRAFTS_FILE)

categories_pool = set(["Énergie", "H2O", "Mobilité", "Alimentation", "Solaire", "Eolien"])
for entry in full_data + drafts_data:
    for c in entry.get('categories', []):
        categories_pool.add(c)
dynamic_cats_list = sorted(list(categories_pool))

full_data.sort(key=get_year_for_sort)
drafts_data.sort(key=lambda x: x.get('date', ''), reverse=True)

# --- INTERFACE ---
st.title("⚡ PALEO-ÉNERGÉTIQUE")

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=PT+Sans+Narrow:wght@400;700&family=PT+Serif:wght@400;700&display=swap');
    
    .stApp {{ background-color: #FAFAFA; font-family: 'PT Serif', serif; color: black; }}
    h1, h2, h3 {{ font-family: 'PT Sans Narrow', sans-serif !important; text-transform: uppercase; }}
    
    .stTextInput input, .stTextArea textarea, .stMultiSelect {{
        background-color: {PINK_HEX} !important;
        color: black !important;
        border: 1px solid #E0B0B0;
    }}
    
    /* STYLE DES BOUTONS REVU - MINIMALISTE */
    div.stButton > button {{
        background-color: transparent;
        color: black;
        border: 2px solid black;
        border-radius: 0px; /* Angles droits */
        font-family: 'PT Sans Narrow', sans-serif;
        text-transform: uppercase;
        padding: 5px 15px;
        transition: all 0.2s;
    }}
    div.stButton > button:hover {{
        background-color: black;
        color: white;
        border-color: black;
    }}
    
    div[data-testid="column"] button {{ width: 100%; }}
    .edit-box {{ border: 2px solid #D65A5A; padding: 15px; border-radius: 5px; background-color: white; margin-top: 10px; }}
    div[role="radiogroup"] {{ flex-direction: row; width: 100%; justify-content: center; }}
</style>
""", unsafe_allow_html=True)

menu_options = ["📚 BIBLIOTHÈQUE", "➕ NOUVEAU CARTEL", "💡 IDÉES & BROUILLONS"]
selected_page = st.radio("", menu_options, index=st.session_state.nav_index, horizontal=True, label_visibility="collapsed")

# === 1. BIBLIOTHÈQUE ===
if selected_page == "📚 BIBLIOTHÈQUE":
    if 'selection_active' not in st.session_state: st.session_state.selection_active = set()
    if 'editing_id' not in st.session_state: st.session_state.editing_id = None
    if 'confirm_bulk_del' not in st.session_state: st.session_state.confirm_bulk_del = False

    if not full_data:
        st.info("La bibliothèque est vide.")
    else:
        st.markdown("### Filtres & Actions")
        cat_filter = st.multiselect("Filtrer par catégorie", dynamic_cats_list, key="biblio_filter")
        filtered_data = full_data
        if cat_filter:
            filtered_data = [d for d in full_data if any(cat in d['categories'] for cat in cat_filter)]

        # BOUTONS SELECTION
        col_sel_all, col_desel_all, col_spacer = st.columns([1, 1, 2])
        if col_sel_all.button("✅ Tout sélectionner"):
            for d in filtered_data:
                st.session_state.selection_active.add(d['id'])
            st.rerun()
        if col_desel_all.button("❌ Tout désélectionner"):
            for d in filtered_data:
                if d['id'] in st.session_state.selection_active:
                    st.session_state.selection_active.remove(d['id'])
            st.rerun()

        count_sel = len(st.session_state.selection_active)
        
        col_inf, col_exp, col_del_bulk = st.columns([2, 1, 1])
        with col_inf:
            st.caption(f"{len(filtered_data)} publiés | {count_sel} sélectionnés")
        
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

        with col_del_bulk:
            if count_sel > 0:
                if st.button("🗑️ SUPPRIMER SÉLECTION", use_container_width=True):
                    st.session_state.confirm_bulk_del = True
        
        if st.session_state.confirm_bulk_del:
            st.warning("Attention : Suppression définitive.")
            col_y, col_n = st.columns(2)
            if col_y.button("CONFIRMER SUPPRESSION", key="conf_bulk"):
                with st.spinner('Suppression...'):
                    for id_to_del in list(st.session_state.selection_active):
                        delete_entry(id_to_del, DATA_FILE)
                    st.session_state.selection_active = set()
                    st.session_state.confirm_bulk_del = False
                    st.session_state.flash_msg = "🗑️ Sélection supprimée."
                    set_page(0) 
                    st.rerun()
            if col_n.button("ANNULER", key="canc_bulk"):
                st.session_state.confirm_bulk_del = False
                st.rerun()

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
                            e_de = st.text_area("Description (Max 1500)", value=row['description'], max_chars=1500)
                            cur_cats = [c for c in row['categories'] if c in dynamic_cats_list]
                            e_ca = st.multiselect("Catégories", dynamic_cats_list, default=cur_cats)
                            e_qr = st.text_input("QR Link", value=row.get('url_qr',''))
                        
                        col_save, col_cancel = st.columns([1, 1])
                        with col_save:
                            if st.form_submit_button("💾 SAUVEGARDER"):
                                with st.spinner('Mise à jour...'):
                                    n_path = row.get('image_path')
                                    if e_im: n_path = save_image(e_im)
                                    up_entry = row.copy()
                                    up_entry.update({"titre":e_ti, "annee":e_an, "description":e_de, "exhume_par":e_ex, "categories":e_ca, "url_qr":e_qr, "image_path":n_path})
                                    update_entry(up_entry, DATA_FILE)
                                    st.session_state.editing_id = None
                                    st.session_state.flash_msg = "✅ Modifié !"
                                    set_page(0) 
                                    st.rerun()
                        with col_cancel:
                            if st.form_submit_button("ANNULER"):
                                st.session_state.editing_id = None
                                st.rerun()

            with c_act:
                st.write("")
                st.write("") 
                act_edit, act_del = st.columns(2)
                with act_edit:
                    if st.button("✏️", key=f"btn_edit_{row['id']}", help="Modifier"):
                        st.session_state.editing_id = row['id'] if st.session_state.editing_id != row['id'] else None
                        st.rerun()
                with act_del:
                    if st.button("🗑️", key=f"btn_del_{row['id']}", help="Supprimer"):
                        st.session_state[f"confirm_del_{row['id']}"] = True
                
                if st.session_state.get(f"confirm_del_{row['id']}"):
                    st.markdown("<small style='color:red;'>Supprimer ?</small>", unsafe_allow_html=True)
                    if st.button("OUI", key=f"yes_del_{row['id']}"):
                        with st.spinner('Suppression...'):
                            delete_entry(row['id'], DATA_FILE)
                        st.session_state.flash_msg = "🗑️ Supprimé."
                        set_page(0)
                        st.rerun()
                    if st.button("NON", key=f"no_del_{row['id']}"):
                        st.session_state[f"confirm_del_{row['id']}"] = False
                        st.rerun()
            st.divider()

# === 2. CRÉATION ===
elif selected_page == "➕ NOUVEAU CARTEL":
    st.subheader("Créer une nouvelle fiche officielle")
    with st.form("new_cartel"):
        col_gauche, col_droite = st.columns(2)
        with col_gauche:
            uploaded_file = st.file_uploader("Image (Optionnel)", type=['png', 'jpg', 'jpeg'])
            exhume_par = st.text_input("Exhumé par")
        with col_droite:
            titre = st.text_input("Titre (Obligatoire)")
            annee = st.text_input("Année", value="2025")
        
        description = st.text_area("Description (Max 1500 caractères)", height=150, max_chars=1500)
        
        c_cat, c_qr = st.columns(2)
        with c_cat:
            selected_cats = st.multiselect("Catégories", dynamic_cats_list)
            new_cat = st.text_input("Autre catégorie (Ajout)")
        with c_qr:
            url_qr = st.text_input("Lien QR Code (Optionnel)")
        submit_create = st.form_submit_button("ENREGISTRER LE CARTEL")

    if submit_create:
        if not titre:
            st.error("Le titre est obligatoire.")
        else:
            with st.spinner('Envoi vers la bibliothèque...'):
                final_cats = selected_cats + ([new_cat] if new_cat else [])
                img_path = save_image(uploaded_file)
                entry = {
                    "id": datetime.now().strftime("%Y%m%d%H%M%S"),
                    "titre": titre, "annee": annee, "description": description,
                    "exhume_par": exhume_par, "categories": final_cats,
                    "url_qr": url_qr, "image_path": img_path, "date": datetime.now().strftime("%Y-%m-%d")
                }
                save_entry(entry, DATA_FILE)
            st.session_state.flash_msg = f"✅ Cartel '{titre}' publié !"
            set_page(0) 
            st.rerun()

# === 3. IDÉES & BROUILLONS ===
elif selected_page == "💡 IDÉES & BROUILLONS":
    if st.session_state.nav_index != 2:
        st.session_state.nav_index = 2

    st.subheader("💡 Boîte à idées & Brouillons")
    
    with st.expander("➕ Ajouter une idée / un brouillon", expanded=False):
        with st.form("new_draft"):
            d_titre = st.text_input("Titre (Obligatoire)")
            # MODIFICATION : Limite caractères + Compteur
            d_desc = st.text_area("Notes / Description (Max 1500 caractères)", max_chars=1500)
            
            c_img_d, c_opt_d = st.columns([1, 2])
            with c_img_d:
                d_img = st.file_uploader("Image (Optionnel)", type=['png', 'jpg'], key="draft_img")
            with c_opt_d:
                d_cats = st.multiselect("Catégories", dynamic_cats_list, key="draft_cats")
                d_new_cat = st.text_input("Autre catégorie (Ajout)", key="draft_new_cat")
                d_qr = st.text_input("Lien QR Code (Optionnel)", key="draft_qr")
            
            d_submit = st.form_submit_button("SAUVEGARDER BROUILLON")
            
            if d_submit:
                if not d_titre:
                    st.error("Titre obligatoire")
                else:
                    d_path = save_image(d_img)
                    final_draft_cats = d_cats + ([d_new_cat] if d_new_cat else [])
                    
                    draft_entry = {
                        "id": "draft_" + datetime.now().strftime("%Y%m%d%H%M%S"),
                        "titre": d_titre, "annee": "2025", "description": d_desc,
                        "exhume_par": "", "categories": final_draft_cats, "url_qr": d_qr, 
                        "image_path": d_path, "date": datetime.now().strftime("%Y-%m-%d")
                    }
                    save_entry(draft_entry, DRAFTS_FILE, msg_prefix="Brouillon")
                    st.session_state.flash_msg = "💡 Idée sauvegardée !"
                    set_page(2) 
                    st.rerun()
    
    st.divider()
    
    if not drafts_data:
        st.info("Aucun brouillon.")
    else:
        for d_row in drafts_data:
            c_d_vis, c_d_act = st.columns([2, 1])
            with c_d_vis:
                afficher_cartel_visuel(d_row, is_draft=True)
                if st.session_state.get(f"edit_draft_{d_row['id']}"):
                    st.markdown(f"<div class='edit-box'>Édition Brouillon</div>", unsafe_allow_html=True)
                    with st.form(f"form_edit_draft_{d_row['id']}"):
                        ed_ti = st.text_input("Titre", value=d_row['titre'])
                        ed_an = st.text_input("Année", value=d_row.get('annee', ''))
                        ed_ex = st.text_input("Exhumé par", value=d_row.get('exhume_par', ''))
                        ed_im = st.file_uploader("Image", type=['png', 'jpg'])
                        # MODIFICATION : Limite caractères + Compteur
                        ed_de = st.text_area("Desc (Max 1500 caractères)", value=d_row.get('description', ''), max_chars=1500)
                        
                        cur_cats = [c for c in d_row.get('categories', []) if c in dynamic_cats_list]
                        ed_ca = st.multiselect("Catégories", dynamic_cats_list, default=cur_cats)
                        ed_qr = st.text_input("QR Link", value=d_row.get('url_qr', ''))
                        
                        if st.form_submit_button("💾 METTRE À JOUR"):
                            n_p = d_row.get('image_path')
                            if ed_im: n_p = save_image(ed_im)
                            up_dr = d_row.copy()
                            up_dr.update({"titre":ed_ti, "annee":ed_an, "exhume_par":ed_ex, "description":ed_de, "categories":ed_ca, "url_qr":ed_qr, "image_path":n_p})
                            update_entry(up_dr, DRAFTS_FILE, msg_prefix="Modif Brouillon")
                            st.session_state[f"edit_draft_{d_row['id']}"] = False
                            set_page(2) 
                            st.rerun()

            with c_d_act:
                st.write("")
                if st.button("🚀 PUBLIER EN BIBLIOTHÈQUE", key=f"pub_{d_row['id']}", use_container_width=True):
                    with st.spinner("Publication officielle..."):
                        publish_draft(d_row['id'])
                    st.session_state.flash_msg = f"🎉 '{d_row['titre']}' est maintenant publié !"
                    set_page(0) 
                    st.rerun()
                st.write("")
                c_edit, c_del = st.columns(2)
                with c_edit:
                    if st.button("✏️", key=f"btn_ed_dr_{d_row['id']}", help="Modifier"):
                        st.session_state[f"edit_draft_{d_row['id']}"] = not st.session_state.get(f"edit_draft_{d_row['id']}", False)
                        set_page(2)
                        st.rerun()
                with c_del:
                    if st.button("🗑️", key=f"btn_del_dr_{d_row['id']}", help="Jeter"):
                        delete_entry(d_row['id'], DRAFTS_FILE, msg_prefix="Del Brouillon")
                        set_page(2)
                        st.rerun()
            st.divider()
