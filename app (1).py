# -*- coding: utf-8 -*-
"""
Мастер Веб-Апликација (Десктоп + Мобилен) за ФБ Контрола,
Длабински Фузи-Пресеци, Преглед на Линкови од Објави,
Управување со Тимови (Додавање/Бришење/Замена) и Телеграм Потсетници во Две Брзини.
"""
import streamlit as st
import pandas as pd
import numpy as np
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
import os
import re
import json
import socket
import urllib.parse
from datetime import datetime
from difflib import SequenceMatcher

st.set_page_config(
    page_title="ФБ Контрола - Мастер Систем",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Стилизирање за Десктоп и Мобилен приказ
st.markdown("""
<style>
    .main-header { font-size: 26px; font-weight: 800; color: #1F497D; margin-bottom: 6px; }
    .sub-header { font-size: 19px; font-weight: 700; color: #274E13; margin-top: 12px; margin-bottom: 8px; }
    .link-card {
        background: linear-gradient(135deg, #f0f4ff 0%, #e4ecfa 100%);
        border: 2px solid #1F497D;
        border-radius: 10px;
        padding: 14px 18px;
        margin-bottom: 14px;
    }
    .link-badge {
        background-color: #1F497D;
        color: white;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 13px;
        font-weight: bold;
    }
    .warn-badge {
        background-color: #990000;
        color: white;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 13px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 0. ЗАШТИТА СО ЛОЗИНКА (LOGIN SYSTEM)
# ==============================================================================
USER_CREDENTIALS = {
    "admin": "admin123",
    "toni": "skopje2026"
}

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

def logout():
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.markdown('<div class="main-header">🔒 Безбедносна Најава</div>', unsafe_allow_html=True)
    st.info("Апликацијата е заштитена. Внесете корисничко име и лозинка за пристап.")
    
    with st.form("login_form"):
        username = st.text_input("Корисничко име:")
        password = st.text_input("Лозинка:", type="password")
        submit_btn = st.form_submit_button("Најави се")
        
        if submit_btn:
            if username in USER_CREDENTIALS and USER_CREDENTIALS[username] == password:
                st.session_state["authenticated"] = True
                st.success("Успешна најава! Се вчитува системот...")
                st.rerun()
            else:
                st.error("❌ Погрешно корисничко име или лозинка!")
    st.stop()

st.sidebar.button("🚪 Одјави се", on_click=logout)
st.sidebar.markdown("---")

# ==============================================================================
# 1. КОМПЛЕТЕН АЛИЈАС РЕЧНИК И НОРМАЛИЗАЦИЈА
# ==============================================================================
CYR_TO_LAT = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'ѓ': 'gj', 'е': 'e', 'ж': 'z',
    'з': 'z', 'ѕ': 'dz', 'и': 'i', 'ј': 'j', 'к': 'k', 'л': 'l', 'љ': 'lj', 'м': 'm',
    'н': 'n', 'њ': 'nj', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'ќ': 'k',
    'у': 'u', 'ф': 'f', 'х': 'h', 'ц': 'c', 'ч': 'c', 'џ': 'dz', 'ш': 's',
    'ć': 'c', 'č': 'c', 'š': 's', 'ž': 'z', 'đ': 'dj', 'ћ': 'c'
}

def normalize_name(s):
    if not isinstance(s, str): return ""
    s = s.lower().split(' (http')[0].split(' http')[0].replace('[', '').replace(']', '').replace(' - предложувач', '').replace(' - predlozuvac', '')
    s = re.sub(r'[^a-zа-яѓѕјљњќџćčšžđћ0-9\s]', ' ', s)
    res = [CYR_TO_LAT.get(ch, ch) for ch in s]
    norm = "".join(res).replace('sh', 's').replace('ch', 'c').replace('zh', 'z').replace('dj', 'gj').replace('kj', 'k').replace('ikj', 'ik').replace('ic', 'ik')
    return re.sub(r'\s+', ' ', norm).strip()

ALIAS_MAP = {
    'милка јовевска': ['mila mila', 'milka jovevska'], 'milka jovevska': ['mila mila', 'milka jovevska'],
    'angela dr mit': ['ani mit', 'angela josifoska'], 'орхидеја јосифоска': ['ani mit', 'angela josifoska'],
    'restylecloset6': ['да одгледуваме повеќе пченка'], 'да одгледуваме повеќе пченка': ['да одгледуваме повеќе пченка'],
    'zzz boskovic': ['vojka boshkovic'], 'vojka boshkovic': ['vojka boshkovic'],
    'daniela_kosta': ['jelica damjanovska'], 'jelica damjanovska': ['jelica damjanovska'],
    'jovann_d': ['jovan damjanovski'], 'профил 2': ['jovan damjanovski'],
    'александар петров': ['александар бацка', 'aleksandar backa'], 'ljupco nikolovski': ['бу бу'],
    'andrijan andrijan': ['andrijan ani'], 'елена божиновска': ['elena bozhinoska', 'elena bozinoska'],
    'elena bozinovska': ['elena bozhinoska', 'elena bozinoska'], 'kate arsova velkova': ['kate arsova', 'kate arsova velkova', 'кате арсова'],
    'kate arsova': ['kate arsova', 'kate arsova velkova', 'кате арсова'], 'емилија колева илиевска': ['koleva emilija'],
    'ѓокески филип': ['filip gjokeski'], 'slobodan damkovski': ['bobi damkovski'],
    'рајна ѓорѓиева': ['rajne rajni'], 'rajna gjorgjieva': ['rajne rajni'],
    'игор милошевски': ['м.игор ххх', 'м.игор xxx'], 'igor milosevski': ['м.игор ххх', 'м.игор xxx'],
    'ацка станишева': ['ацка станишева', 'elena stanisheva'], 'elena stanisheva': ['ацка станишева'],
    'ceki s medenica': ['ceki s medenica-dimeska'], 'орце симов': ['orce simov nov profil'],
    'orce simov': ['orce simov nov profil'], 'марија талевска': ['marija talevska miche'],
    'marija talevska': ['marija talevska miche'], 'драган спировски': ['dragan spirovski gagi'],
    'драган димитров': ['драган гаги димитров'], 'софија вренцоска': ['софи вренцоска'],
    'sofi vrencoska': ['софи вренцоска'], 'владимир спиров': ['vladimir spirov'],
    'маја стоиманова': ['maja stoimanova-ristovska'], 'снежана златковска': ['snezana zlatkovska'],
    'андријана филиповска': ['andrijana filiposka'], 'andrijana filipovska': ['andrijana filiposka'],
    'jadranka popovska': ['jadranka popovski'], 'јадранка поповска': ['jadranka popovski'],
    'katerina avramovska markovik': ['katerina sotirova', 'sotirova-nikolova katerina', 'kate petrovska-markovic'],
    'катерина аврамовска марковиќ': ['kate petrovska-markovic', 'sotirova-nikolova katerina'],
    'катерина сотирова': ['sotirova-nikolova katerina'], 'nikolinka aneva': ['nina aneva'],
    'весна вучковска': ['vuckovska vesna'], 'петреска јулијана': ['petrovska julijana'],
    'јулијана петровска': ['petrovska julijana'], 'стојан срезоски': ['srezoski stojan'],
    'оливера костадиновска': ['olivera kostadinoska'], 'димитри таки талевски': ['dimitri taki talevski'],
    'марија петкоски': ['marija petkovska'], 'гоце талевски': ['goce talevski'],
    'дарко димитров ерасмус': ['darko dimitrov'], 'darko dimitrov erasmus': ['darko dimitrov'],
    'илина шандуловска': ['ilina shandulovska'], 'билијана блажевска': ['блажевска билјана'],
    'билјана блажевска': ['блажевска билјана'], 'zokica_b': ['zorana boskovic'],
    'zorana': ['zorana boskovic'], 'dimcedamjanovski': ['dimce damjanovski'],
    'зага костадиновска': ['dragica kostadinovska', 'зага костадиновска'], 'daniel cvetanoski': ['daniel cvet'],
    'dragojuv miljkovikj': ['miljkovic dragoljub'], 'jasna jasna': ['jas jas'],
    'olgica lazareska': ['lazarevska olga'], 'еко планета': ['еко планета', 'ekoplaneta'],
    'кристијан ј.': ['кристијан ј.'], 'kristijan j.': ['кристијан ј.'],
    'би лј ана': ['би лј ана'], 'maja ristevska ipard': ['maja ristevska'],
    'sonja dimovska': ['sonja di', 'sanja dimovska'], 'стефан жути': ['стефан жути'],
    'aco mickoski': ['ace mickoski'], 'beti zhivadinovik': ['beti b. zivadinovik'],
    'олга образование': ['olga dukovska-atov', 'olga dukovska atov'],
    'мирјана нанчева дуковска': ['mirjana nanceva-dukovska', 'olga dukovska-atov']
}

NAME_MAP_CYR = {
    "Boro": "Боро", "Predrag": "Предраг", "Andrijan": "Андријан", 
    "Darko": "Дарко", "Daniela": "Даниела", "Beti": "Бети", 
    "Nadica": "Надица", "Jadranka": "Јадранка", "Maja": "Маја", 
    "Biljana": "Билјана", "Anita": "Анита", "Vlatce": "Влатче",
    "Goran": "Горан", "Dejan": "Дејан", "Emilija": "Емилија",
    "Katerina": "Катерина", "Kristina": "Кристина", "Olga": "Олга",
    "Olgica": "Олгица", "Rajna": "Рајна", "Cvetanka": "Цветанка",
    "Andrej": "Андреј", "Mihail": "Михаил", "Elena": "Елена",
    "Spiro": "Спиро", "Mitko": "Митко", "Vlatko": "Влатко",
    "Lara": "Лара", "Damjan": "Дамјан", "Petar": "Петар",
    "Martina": "Мартина", "Slavica": "Славица", "Dali": "Дали",
    "Gorgi": "Ѓорѓи", "Dimitar": "Димитар", "Teona": "Теона"
}

LINKS_META_FILE = "post_links_meta.json"

def load_links_meta():
    default_meta = {
        "current_link": "https://www.facebook.com/share/18VUNHn6g6/",
        "current_title": "Актуелна ФБ Објава",
        "history": []
    }
    if os.path.exists(LINKS_META_FILE):
        try:
            with open(LINKS_META_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: return default_meta
    return default_meta

def save_links_meta(meta_data):
    try:
        with open(LINKS_META_FILE, "w", encoding="utf-8") as f:
            json.dump(meta_data, f, ensure_ascii=False, indent=2)
    except: pass

# ==============================================================================
# 2. ФУНКЦИИ ЗА EXCEL БАЗА
# ==============================================================================
def push_to_github(file_path):
    import base64, urllib.request, urllib.error
    try:
        token = st.secrets.get("GITHUB_TOKEN")
        repo = st.secrets.get("GITHUB_REPO")
        if not token or not repo: return False, "Не се пронајдени GitHub Secrets."
    except: return False, "Секретите не се конфигурирани."

    try:
        with open(file_path, "rb") as f: content = f.read()
        encoded_content = base64.b64encode(content).decode("utf-8")
        url = f"https://api.github.com/repos/{repo}/contents/{file_path}"
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json"}
        req = urllib.request.Request(url, headers=headers)
        sha = None
        try:
            with urllib.request.urlopen(req) as response:
                if response.status == 200: sha = json.loads(response.read().decode()).get("sha")
        except urllib.error.HTTPError as e:
            if e.code != 404: return False, f"Грешка: {e.code}"
        data = {"message": f"Автоматска синхронизација {file_path}", "content": encoded_content}
        if sha: data["sha"] = sha
        req_put = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers, method="PUT")
        try:
            with urllib.request.urlopen(req_put) as response:
                if response.status in [200, 201]: return True, "Успешно зачувано на GitHub!"
        except urllib.error.HTTPError as e:
            return False, f"Грешка при синхронизација: {e.code}"
    except Exception as e: return False, f"Проблем: {str(e)}"
    return False, "Непозната грешка."

@st.cache_data(ttl=60, max_entries=5)
def get_latest_excel():
    files = [f for f in os.listdir() if f.endswith('.xlsx') and 'kontrola' in f and not f.startswith('~$')]
    if not files: return None
    files.sort(key=lambda fn: int(re.findall(r'\d+', fn)[-1]) if re.findall(r'\d+', fn) else 0)
    return files[-1]

def get_next_version_filename(current_file):
    if not current_file: return "kontrola_klik_najnova_final_219.xlsx"
    nums = re.findall(r'\d+', current_file)
    next_ver = (int(nums[-1]) + 1) if nums else 219
    return f"kontrola_klik_najnova_final_{next_ver}.xlsx"

@st.cache_data(ttl=600, max_entries=5)
def get_eval_columns(_df_main):
    cols = []
    start_tracking = False
    for c in _df_main.columns:
        if 'Дваесет и втора Објава' in c: start_tracking = True
        if any(k in c for k in ['Објава', 'Objava', 'Проверка', 'Пресек']) or start_tracking:
            if c not in ['Р.б.', 'Име и презиме / Профил', 'Предложувач', 'Име на Телеграм (За пребарување)', 'Телефонски број', 'Одговорен контролор', 'Телефонски број (Telegram)', 'Тековен Пресек']:
                cols.append(c)
    return cols

@st.cache_data(ttl=600, max_entries=5)
def build_all_tables(_df_main):
    eval_cols = get_eval_columns(_df_main)
    col_cur = eval_cols[-1]
    col_prev = eval_cols[-2] if len(eval_cols) >= 2 else col_cur
    stats_list = []
    
    for proposer, grp in _df_main.groupby('Предложувач'):
        tot_members = len(grp)
        p_clean = str(proposer).split(' (http')[0].replace('[', '').replace(']', '').replace(' - Предложувач', '').replace(' - Predlozuvac', '').strip()
        tg_n = grp['Име на Телеграм (За пребарување)'].iloc[0] if 'Име на Телеграм (За пребарување)' in grp.columns else ''
        
        prev_likes = (grp[col_prev].astype(str).str.contains('✅', na=False)).sum()
        cur_likes = (grp[col_cur].astype(str).str.contains('✅', na=False)).sum()
        diff_likes = cur_likes - prev_likes
        cur_eff = cur_likes / tot_members if tot_members > 0 else 0
        
        eff_pct = cur_eff * 100
        gr_hist = 'I' if eff_pct <= 30 else 'II' if eff_pct < 50 else 'III' if eff_pct < 65 else 'IV'
        
        stats_list.append({
            'Предлагач': p_clean, 'ГР.': gr_hist, 'Телеграм назив': tg_n, 'Квантум': tot_members,
            'Претходна': prev_likes, 'Тековна': cur_likes, 'Разлика (+/-)': diff_likes,
            'Тековни Фалат': tot_members - cur_likes, 'Тековна Ефикасност': cur_eff,
            'Тековна Ефикасност %': f"{eff_pct:.1f}%", 'Просек Лајкови': cur_likes, 
            'Просечна Ефикасност': cur_eff, 'Просечна Ефикасност %': f"{eff_pct:.1f}%"
        })

    df_comp = pd.DataFrame(stats_list)
    df_sum_disp = df_comp.sort_values(by=['Тековна', 'Тековна Ефикасност', 'Квантум'], ascending=[False, False, False]).reset_index(drop=True)
    df_sum_disp.insert(0, 'Ранг', range(1, len(df_sum_disp) + 1))
    
    return {'Glavna Baza': _df_main, 'Sumarno': df_sum_disp, '_comp': df_comp}

def save_formatted_excel(df_main, output_filename):
    with pd.ExcelWriter(output_filename, engine='openpyxl') as writer:
        df_main.to_excel(writer, sheet_name='Glavna Baza', index=False)
    push_to_github(output_filename)

# ==============================================================================
# UI FRAGMENTS (ЗА ИЗОЛАЦИЈА И СПРЕЧУВАЊЕ НА ТРЕПКАЊЕ / ЛИНИИ)
# ==============================================================================
@st.fragment
def render_post_link_preview_box(links_meta, eval_cols, key_suffix="main"):
    cur_link = links_meta.get("current_link", "https://www.facebook.com/share/18VUNHn6g6/")
    cur_title = links_meta.get("current_title", "Актуелна ФБ Објава")
    latest_col = eval_cols[-1] if eval_cols else "Нема колона"

    st.markdown(f"""
    <div class="link-card">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
            <div><span class="link-badge">🔗 АКТИВЕН ЛИНК НА ОБЈАВАТА</span> <span style="margin-left:8px; font-weight:bold; color:#1F497D;">{cur_title}</span></div>
            <div style="font-size:13px; color:#333;">📌 Поврзана колона во база: <b>{latest_col}</b></div>
        </div>
        <div style="margin-top:10px; font-size:15px; word-break:break-all;">
            👉 Директен линк: <a href="{cur_link}" target="_blank" style="font-weight:bold; color:#0b57d0;">{cur_link}</a>
        </div>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("👁️ Промени Линк или Прикачи Слика", expanded=False):
        c1, c2 = st.columns([3, 2])
        with c1:
            with st.form(f"form_link_{key_suffix}"):
                new_url = st.text_input("Внеси линк:", value=cur_link, key=f"url_{key_suffix}")
                new_title = st.text_input("Опис:", value=cur_title, key=f"tit_{key_suffix}")
                if st.form_submit_button("💾 Зачувај нов линк"):
                    links_meta["current_link"] = new_url.strip()
                    links_meta["current_title"] = new_title.strip()
                    save_links_meta(links_meta)
                    st.success("✅ Зачувано!")
                    st.rerun()
        with c2:
            st.caption("Прикачи скриншот од објавата.")
            uploaded_img = st.file_uploader("Upload", type=['png', 'jpg', 'jpeg'], key=f"img_{key_suffix}")
            if uploaded_img:
                with open("active_post_preview.png", "wb") as f: f.write(uploaded_img.getbuffer())
                st.success("Сликата е зачувана!")
                st.rerun()
            if os.path.exists("active_post_preview.png"):
                st.image("active_post_preview.png", use_container_width=True)

@st.fragment
def tab2_fuzi_presek(df_main, eval_cols, latest_file, links_meta):
    st.markdown('<div class="sub-header">⚡ Автоматски Длабински Фузи-Пресек (Без Ограничувања)</div>', unsafe_allow_html=True)
    render_post_link_preview_box(links_meta, eval_cols, key_suffix="tab2")

    c_mode1, c_mode2 = st.columns(2)
    with c_mode1: presek_mode = st.radio("Избери тип на пресек:", ["🆕 Нова Објава", "🔄 Пресек По Потсетници"])
    with c_mode2:
        default_col_name = "Дваесет и четврта Објава (Нов Пресек)" if presek_mode.startswith("🆕") else f"{eval_cols[-1]} - По Потсетници"
        target_col_name = st.text_input("Назив на колоната:", value=default_col_name)
    
    st.markdown("#### 📥 Внеси ги имињата од објавата:")
    pasted_text = st.text_area("Залепи ги имињата тука (по едно име во секој ред):", height=180)
    
    extracted_names = [l.strip() for l in pasted_text.splitlines() if l.strip() and not re.match(r'^(\d+\s+mutual\s+friends|mention|add\s+friend|invite|following|confirm|cancel\s+request)$', l.strip().lower())]
    
    if extracted_names:
        st.success(f"✅ Вчитани се **{len(extracted_names)}** реакции.")
        if st.button("🚀 Изврши Пресек и Зачувај", type="primary"):
            norm_video = [(vn, normalize_name(vn), set(normalize_name(vn).split())) for vn in extracted_names]
            last_col = eval_cols[-1]
            matched_indices = set(df_main[df_main[last_col] == '✅'].index) if presek_mode.startswith("🔄") else set()

            for idx, row in df_main.iterrows():
                if idx in matched_indices: continue
                raw_m = str(row['Име и презиме / Профил'])
                norm_m = normalize_name(raw_m)
                tokens_m = set(norm_m.split())
                
                matched = False
                if norm_m:
                    for vn, n_vn, t_vn in norm_video:
                        if norm_m == n_vn or (len(tokens_m) >= 2 and len(t_vn) >= 2 and (tokens_m == t_vn or tokens_m.issubset(t_vn) or t_vn.issubset(tokens_m))):
                            matched = True; break
                
                if matched: matched_indices.add(idx)

            df_updated = df_main.copy()
            if presek_mode.startswith("🔄"): df_updated.rename(columns={last_col: target_col_name}, inplace=True)
            df_updated[target_col_name] = ['✅' if i in matched_indices else '❌' for i in df_updated.index]

            next_file = get_next_version_filename(latest_file)
            save_formatted_excel(df_updated, next_file)
            st.cache_data.clear(); st.cache_resource.clear()
            st.success(f"🎉 Успешно! Зачувана е верзија: **{next_file}**.")
            st.rerun()

@st.fragment
def tab3_team_management(df_main, eval_cols, latest_file):
    st.markdown('<div class="sub-header">👥 Управување со Тимови</div>', unsafe_allow_html=True)
    crud_tabs = st.tabs(["➕ Додај Член", "🆕 Нов Тим", "🔄 Измени Член", "🗑️ Избриши"])
    proposers = sorted(df_main['Предложувач'].dropna().unique().tolist())
    latest_col = eval_cols[-1]

    with crud_tabs[2]:
        sel_p_edit = st.selectbox("Избери Тим за измена:", proposers, key="edit_prop_sel")
        team_sub = df_main[df_main['Предложувач'] == sel_p_edit]
        st.dataframe(team_sub[['Р.б.', 'Име и презиме / Профил', latest_col]], use_container_width=True)
        member_options = {f"[{r['Р.б.']}] {r['Име и презиме / Профил']}": idx for idx, r in team_sub.iterrows()}
        chosen_label = st.selectbox("Избери член:", list(member_options.keys()))
        
        with st.form("form_edit_member"):
            chosen_idx = member_options[chosen_label]
            updated_name = st.text_input("Ново име:", value=str(df_main.loc[chosen_idx, 'Име и презиме / Профил']))
            updated_status = st.selectbox("Статус:", ['✅', '❌'], index=0 if '✅' in str(df_main.loc[chosen_idx, latest_col]) else 1)
            if st.form_submit_button("💾 Зачувај Измена"):
                df_updated = df_main.copy()
                df_updated.loc[chosen_idx, 'Име и презиме / Профил'] = updated_name.strip()
                df_updated.loc[chosen_idx, latest_col] = updated_status
                next_file = get_next_version_filename(latest_file)
                save_formatted_excel(df_updated, next_file)
                st.cache_data.clear(); st.cache_resource.clear()
                st.rerun()

@st.fragment
def tab4_telegram_messages(df_main, eval_cols, links_meta, tables_data):
    st.markdown('<div class="sub-header">📨 Телеграм Потсетници</div>', unsafe_allow_html=True)
    st.info("Контрола: Провери го линкот пред пуштање!")
    
    col_new = eval_cols[-1]
    messages_data = []
    
    for proposer, group in df_main.groupby('Предложувач'):
        active = len(group[group[col_new] == '✅'])
        missing = len(group) - active
        tg_name = group['Име на Телеграм (За пребарување)'].iloc[0]
        if missing > 2 and pd.notna(tg_name):
            messages_data.append({'Предлагач': proposer, 'Телеграм': tg_name, 'Фалат': missing, 'Порака': "Автоматски генерирана порака..."})
            
    if messages_data:
        st.dataframe(pd.DataFrame(messages_data), use_container_width=True)
    else:
        st.info("Сите тимови се супер, нема потреба од потсетници!")

# ==============================================================================
# 4. ГЛАВЕН ИНТЕРФЕЈС
# ==============================================================================
st.markdown('<div class="main-header">📊 ФБ Контрола и Менаџмент на Мрежата</div>', unsafe_allow_html=True)

links_meta = load_links_meta()
latest_file = get_latest_excel()

st.sidebar.markdown("### 🗄️ Мастер База")
if not latest_file: st.stop()
st.sidebar.success(f"📂 Активна верзија: \n**{latest_file}**")

@st.cache_resource
def load_master_data(file_path):
    return pd.read_excel(pd.ExcelFile(file_path), sheet_name='Glavna Baza')

df_main = load_master_data(latest_file)
tables_data = build_all_tables(df_main)
eval_cols = get_eval_columns(df_main)

menu = st.sidebar.radio("📌 Навигација:", ["📊 1. Контролна Табла", "⚡ 2. Фузи Пресек", "👥 3. Управување со Тимови", "📨 4. Телеграм Потсетници"])

if menu.startswith("📊 1."):
    render_post_link_preview_box(links_meta, eval_cols, key_suffix="tab1")
    st.dataframe(tables_data['Sumarno'], use_container_width=True)
elif menu.startswith("⚡ 2."):
    tab2_fuzi_presek(df_main, eval_cols, latest_file, links_meta)
elif menu.startswith("👥 3."):
    tab3_team_management(df_main, eval_cols, latest_file)
elif menu.startswith("📨 4."):
    tab4_telegram_messages(df_main, eval_cols, links_meta, tables_data)
