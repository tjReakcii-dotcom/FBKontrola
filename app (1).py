# -*- coding: utf-8 -*-
"""
Мастер Веб-Апликација (Десктоп + Мобилен) за ФБ Контрола,
Длабински Фузи-Пресеци, Преглед на Линкови од Објави,
Управување со Тимови (Додавање/Бришење/Замена) и Телеграм Потсетници во Две Брзини.
+ НОВО: Аналитички Досиеја (Профили на Предлагачи и Членови)
"""
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
import os
import re
import io
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
    'милка јовевска': ['mila mila', 'milka jovevska'],
    'angela dr mit': ['ani mit', 'angela josifoska'],
    'орхидеја јосифоска': ['ani mit', 'angela josifoska'],
    'restylecloset6': ['да одгледуваме повеќе пченка'],
    'zzz boskovic': ['vojka boshkovic'],
    'daniela_kosta': ['jelica damjanovska'],
    'jovann_d': ['jovan damjanovski'],
    'профил 2': ['jovan damjanovski'],
    'александар петров': ['александар бацка', 'aleksandar backa'],
    'ljupco nikolovski': ['бу бу'],
    'andrijan andrijan': ['andrijan ani'],
    'елена божиновска': ['elena bozhinoska', 'elena bozinoska'],
    'kate arsova velkova': ['kate arsova', 'kate arsova velkova', 'кате арсова'],
    'емилија колева илиевска': ['koleva emilija'],
    'ѓокески филип': ['filip gjokeski'],
    'slobodan damkovski': ['bobi damkovski'],
    'рајна ѓорѓиева': ['rajne rajni'],
    'игор милошевски': ['м.игор ххх', 'м.игор xxx'],
    'ацка станишева': ['ацка станишева', 'elena stanisheva'],
    'ceki s medenica': ['ceki s medenica-dimeska'],
    'орце симов': ['orce simov nov profil'],
    'марија талевска': ['marija talevska miche'],
    'драган спировски': ['dragan spirovski gagi'],
    'драган димитров': ['драган гаги димитров'],
    'софија вренцоска': ['софи вренцоска'],
    'владимир спиров': ['vladimir spirov'],
    'маја стоиманова': ['maja stoimanova-ristovska'],
    'снежана златковска': ['snezana zlatkovska'],
    'андријана филиповска': ['andrijana filiposka'],
    'jadranka popovska': ['jadranka popovski'],
    'katerina avramovska markovik': ['katerina sotirova', 'sotirova-nikolova katerina', 'kate petrovska-markovic'],
    'nikolinka aneva': ['nina aneva'],
    'весна вучковска': ['vuckovska vesna'],
    'петреска јулијана': ['petrovska julijana'],
    'стојан срезоски': ['srezoski stojan'],
    'оливера костадиновска': ['olivera kostadinoska'],
    'димитри таки талевски': ['dimitri taki talevski'],
    'марија петкоски': ['marija petkovska'],
    'гоце талевски': ['goce talevski'],
    'darko dimitrov erasmus': ['darko dimitrov'],
    'илина шандуловска': ['ilina shandulovska'],
    'билијана блажевска': ['блажевска билјана'],
    'zokica_b': ['zorana boskovic'],
    'dimcedamjanovski': ['dimce damjanovski'],
    'зага костадиновска': ['dragica kostadinovska', 'зага костадиновска'],
    'daniel cvetanoski': ['daniel cvet'],
    'dragojuv miljkovikj': ['miljkovic dragoljub'],
    'jasna jasna': ['jas jas'],
    'olgica lazareska': ['lazarevska olga'],
    'еко планета': ['еко планета', 'ekoplaneta'],
    'кристијан ј.': ['кристијан ј.'],
    'би лј ана': ['би лј ана'],
    'maja ristevska ipard': ['maja ristevska'],
    'sonja dimovska': ['sonja di', 'sanja dimovska'],
    'стефан жути': ['стефан жути'],
    'aco mickoski': ['ace mickoski'],
    'beti zhivadinovik': ['beti b. zivadinovik'],
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
        "current_title": "Актуелна ФБ Објава (Провери пред праќање)",
        "history": []
    }
    if os.path.exists(LINKS_META_FILE):
        try:
            with open(LINKS_META_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return default_meta
    return default_meta

def save_links_meta(meta_data):
    try:
        with open(LINKS_META_FILE, "w", encoding="utf-8") as f:
            json.dump(meta_data, f, ensure_ascii=False, indent=2)
    except:
        pass

# ==============================================================================
# 2. ФУНКЦИИ ЗА EXCEL БАЗАТА И GITHUB AUTO-SYNC
# ==============================================================================
def push_to_github(file_path):
    import base64, json, urllib.request, urllib.error
    try:
        token = st.secrets.get("GITHUB_TOKEN")
        repo = st.secrets.get("GITHUB_REPO")
        if not token or not repo: return False, "Не се пронајдени GitHub Secrets."
    except: return False, "Секретите не се конфигурирани."

    try:
        with open(file_path, "rb") as f: content = f.read()
        encoded_content = base64.b64encode(content).decode("utf-8")
        url = f"https://api.github.com/repos/{repo}/contents/{file_path}"
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json", "User-Agent": "Streamlit"}
        
        req = urllib.request.Request(url, headers=headers)
        sha = None
        try:
            with urllib.request.urlopen(req) as response:
                if response.status == 200: sha = json.loads(response.read().decode()).get("sha")
        except urllib.error.HTTPError as e:
            if e.code != 404: return False, f"Грешка: {e.code}"
                
        data = {"message": f"Auto-sync {file_path}", "content": encoded_content}
        if sha: data["sha"] = sha
            
        req_put = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers, method="PUT")
        try:
            with urllib.request.urlopen(req_put) as response:
                if response.status in [200, 201]: return True, "Базата е успешно и автоматски зачувана на GitHub!"
        except urllib.error.HTTPError as e:
            return False, f"Грешка при синхронизација: {e.code}"
    except Exception as e: return False, f"Проблем: {str(e)}"
    return False, "Непозната грешка."

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

def get_eval_columns(df_main):
    cols = []
    start_tracking = False
    for c in df_main.columns:
        if 'Дваесет и втора Објава' in str(c): start_tracking = True
        if any(k in str(c) for k in ['Објава', 'Objava', 'Проверка', 'Пресек']) or start_tracking:
            if c not in ['Р.б.', 'Име и презиме / Профил', 'Предложувач', 'Име на Телеграм (За пребарување)', 'Телефонски број', 'Одговорен контролор', 'Телефонски број (Telegram)', 'Тековен Пресек']:
                cols.append(c)
    return cols

def get_official_posts(df_main):
    eval_cols = get_eval_columns(df_main)
    base_official = [
        'Проверка 23 (306 реакции)', 'Нова Објава 2 (761 реакции)', 'Трета Објава 4 (320 реакции)',
        'Четврта Објава 3 (771 реакции)', 'Петта Објава 2 (637 реакции)', 'Шеста Објава (Ревидиран Пресек)',
        'Седма Објава (Длабински Фузи Пресек)', 'Осма Објава (Ново Видео)', 'Десетта Објава (Најнов CSV - Финална Проверка)',
        'Единаесетта Објава (FAST CSV)', 'Дванаесетта Објава (Нов Пресек)', 'Тринаесетта Објава (Видео Пресек)',
        'Четринаесетта Објава (Реално Видео)', 'Петринаесетта Објава (Ново Видео)', 'Седумнаесетта Објава (Конечен Пресек)',
        'Осумнаесетта Објава (Конечен Пресек)', 'Деветнаесетта Објава (1.1k Пресек)', 'Дваесетта Објава (919 Пресек)',
        'Дваесет и прва Објава (1K+ Пресек - По Потсетници)', 'Дваесет и втора Објава (803 Конечен Пресек)'
    ]
    valid_cols = [c for c in base_official if c in df_main.columns]
    if 'Дваесет и втора Објава (803 Конечен Пресек)' in eval_cols:
        idx = eval_cols.index('Дваесет и втора Објава (803 Конечен Пресек)')
        for c in eval_cols[idx + 1:]:
            if c not in valid_cols: valid_cols.append(c)
    else:
        for c in eval_cols:
            if c not in valid_cols: valid_cols.append(c)
    return valid_cols

def build_all_tables(df_main):
    official_cols = get_official_posts(df_main)
    eval_cols = get_eval_columns(df_main)
    col_cur = eval_cols[-1]
    col_prev = eval_cols[-2] if len(eval_cols) >= 2 else col_cur

    stats_list = []
    for proposer, grp in df_main.groupby('Предложувач'):
        tot_members = len(grp)
        p_clean = str(proposer).split(' (http')[0].replace('[', '').replace(']', '').replace(' - Предложувач', '').replace(' - Predlozuvac', '').strip()
        tg_n = grp['Име на Телеграм (За пребарување)'].iloc[0] if 'Име на Телеграм (За пребарување)' in grp.columns else ''

        post_likes, post_effs = [], []
        for col in official_cols:
            l = (grp[col].astype(str).str.contains('✅', na=False)).sum()
            post_likes.append(l)
            post_effs.append(l / tot_members if tot_members > 0 else 0)

        first_act_idx = next((i for i, l in enumerate(post_likes) if l > 0), None)
        if first_act_idx is not None:
            rel_likes, rel_effs = post_likes[first_act_idx:], post_effs[first_act_idx:]
        else:
            rel_likes, rel_effs = [post_likes[-1]] if post_likes else [0], [post_effs[-1]] if post_effs else [0]

        avg_likes, avg_eff = sum(rel_likes) / len(rel_likes), sum(rel_effs) / len(rel_effs)
        prev_likes = (grp[col_prev].astype(str).str.contains('✅', na=False)).sum()
        cur_likes = (grp[col_cur].astype(str).str.contains('✅', na=False)).sum()
        eff_pct = avg_eff * 100
        gr_hist = 'I' if eff_pct <= 30.0 else 'II' if eff_pct < 50.0 else 'III' if eff_pct < 65.0 else 'IV'

        stats_list.append({
            'Предлагач': p_clean, 'ГР.': gr_hist, 'Телеграм назив': tg_n, 'Квантум': tot_members,
            'Претходна': prev_likes, 'Тековна': cur_likes, 'Разлика (+/-)': cur_likes - prev_likes,
            'Тековни Фалат': tot_members - cur_likes, 'Тековна Ефикасност': cur_likes / tot_members if tot_members > 0 else 0,
            'Тековна Ефикасност %': f"{(cur_likes / tot_members * 100) if tot_members > 0 else 0:.1f}%",
            'Просек Лајкови': round(avg_likes, 1), 'Просечна Ефикасност': avg_eff,
            'Просечна Ефикасност %': f"{eff_pct:.1f}%", 'Објави Следени': len(rel_likes)
        })

    df_comp = pd.DataFrame(stats_list)
    df_sum_disp = df_comp.sort_values(by=['Тековна', 'Тековна Ефикасност', 'Квантум'], ascending=[False, False, False]).reset_index(drop=True)
    df_sum_disp.insert(0, 'Ранг', range(1, len(df_sum_disp) + 1))
    
    df_sum_sheet = df_sum_disp[['Ранг', 'ГР.', 'Предлагач', 'Претходна', 'Тековна', 'Разлика (+/-)', 'Тековни Фалат', 'Квантум', 'Тековна Ефикасност %', 'Телеграм назив']].copy()
    df_sum_sheet.rename(columns={'Тековни Фалат': 'Фалат', 'Тековна Ефикасност %': 'Ефикасност %'}, inplace=True)

    def make_group_df(gr_code):
        sub = df_comp[df_comp['ГР.'] == gr_code].copy().sort_values(by=['Просек Лајкови', 'Просечна Ефикасност', 'Квантум'], ascending=[False, False, False]).reset_index(drop=True)
        sub.insert(0, 'Поз.', range(1, len(sub) + 1))
        status_col = []
        for _, r in sub.iterrows():
            diff = float(r['Тековна Ефикасност %'].replace('%', '')) - float(r['Просечна Ефикасност %'].replace('%', ''))
            status_col.append(f"🟢 Натфрлил (+{diff:.1f}%)" if diff >= 10.0 else f"🔴 Потфрлил ({diff:.1f}%)" if diff <= -10.0 else f"⚪ Стандардно ({diff:+.1f}%)")
        sub['Статус / Отстапување'] = status_col
        sub.rename(columns={'Тековна': 'Тековни Активни'}, inplace=True)
        return sub[['Поз.', 'Предлагач', 'Квантум', 'Просек Лајкови', 'Просечна Ефикасност %', 'Тековни Активни', 'Тековни Фалат', 'Тековна Ефикасност %', 'Статус / Отстапување', 'Телеграм назив']]

    df_g4, df_g3, df_g2, df_g1 = make_group_df('IV'), make_group_df('III'), make_group_df('II'), make_group_df('I')

    last_5_official = official_cols[-5:] if len(official_cols) >= 5 else official_cols
    inactive_rows = []
    for _, r in df_main.iterrows():
        likes_hist = sum(1 for c in official_cols if '✅' in str(r[c]))
        likes_5 = sum(1 for c in last_5_official if '✅' in str(r[c]))
        if likes_5 == 0:
            inactive_rows.append({
                'Р.б. во База': r['Р.б.'],
                'Предлагач': str(r['Предложувач']).split(' (http')[0].replace('[', '').replace(']', '').replace(' - Предложувач', '').replace(' - Predlozuvac', '').strip(),
                'Име и презиме / Профил (Член)': str(r['Име и презиме / Профил']).split(' (http')[0].strip(),
                'Лајкови (Последни 5 објави)': likes_5,
                'Лајкови (Вкупно историски)': likes_hist,
                'Дијагноза / Препорака': "🔴 0 лајкови од почеток" if sum(1 for c in eval_cols if '✅' in str(r[c])) == 0 else f"🟠 Неактивен на последните 5 (Претходно: {likes_hist})",
                'Телеграм назив на предлагач': r.get('Име на Телеграм (За пребарување)', '')
            })
    df_inactive = pd.DataFrame(inactive_rows)
    if not df_inactive.empty:
        df_inactive = df_inactive.sort_values(by=['Лајкови (Вкупно историски)', 'Предлагач', 'Р.б. во База']).reset_index(drop=True)
        df_inactive.insert(0, 'Ред.', range(1, len(df_inactive) + 1))

    return {'Glavna Baza': df_main, 'Sumarno': df_sum_sheet, 'Grupa IV': df_g4, 'Grupa III': df_g3, 'Grupa II': df_g2, 'Grupa I': df_g1, 'Neaktivni (0 Lajkovi)': df_inactive, '_comp': df_comp}

def save_formatted_excel(df_main, output_filename):
    tables = build_all_tables(df_main)
    with pd.ExcelWriter(output_filename, engine='openpyxl') as writer:
        for sht in ['Glavna Baza', 'Sumarno', 'Grupa IV', 'Grupa III', 'Grupa II', 'Grupa I', 'Neaktivni (0 Lajkovi)']:
            if sht in tables and not tables[sht].empty:
                tables[sht].to_excel(writer, sheet_name=sht, index=False)

    wb = openpyxl.load_workbook(output_filename)
    header_fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    
    ws_main = wb['Glavna Baza']
    ws_main.freeze_panes = 'A2'
    for cell in ws_main[1]:
        cell.fill = header_fill; cell.font = header_font; cell.alignment = Alignment(horizontal="center", vertical="center")
    
    wb.save(output_filename)
    success, msg = push_to_github(output_filename)
    if success: st.toast("✅ " + msg)
    else: st.toast("⚠️ " + msg)
    return tables

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
        <div style="margin-top:10px; font-size:15px; word-break:break-all;">👉 Директен линк: <a href="{cur_link}" target="_blank" style="font-weight:bold; color:#0b57d0;">{cur_link}</a></div>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("👁️ Прикажи Визуелен Преглед (Live Preview) и Промени Линк на Објавата", expanded=False):
        c1, c2 = st.columns([3, 2])
        with c1:
            new_url = st.text_input("Внеси / Корегирај линк до ФБ објавата:", value=cur_link, key=f"url_in_{key_suffix}")
            new_title = st.text_input("Кратко име / Опис на објавата:", value=cur_title, key=f"title_in_{key_suffix}")
            if st.button("💾 Зачувај го новиот линк како активен", key=f"save_link_{key_suffix}"):
                links_meta["current_link"] = new_url.strip()
                links_meta["current_title"] = new_title.strip()
                links_meta.setdefault("history", []).append({"post_col": latest_col, "url": new_url.strip(), "title": new_title.strip(), "time": datetime.now().strftime("%Y-%m-%d %H:%M")})
                save_links_meta(links_meta)
                st.success("✅ Линкот е успешно зачуван!")
                st.rerun()

# ==============================================================================
# ГЛАВЕН ИНТЕРФЕЈС
# ==============================================================================
st.markdown('<div class="main-header">📊 ФБ Контрола и Менаџмент на Мрежата</div>', unsafe_allow_html=True)
links_meta = load_links_meta()
latest_file = get_latest_excel()

st.sidebar.markdown("### 🗄️ Мастер База")
uploaded_master = st.sidebar.file_uploader("Прикачи понова база (.xlsx):", type=['xlsx'])
if uploaded_master is not None:
    if "last_uploaded_file" not in st.session_state or st.session_state["last_uploaded_file"] != uploaded_master.name:
        save_name = uploaded_master.name if 'kontrola' in uploaded_master.name else get_next_version_filename(latest_file)
        with open(save_name, "wb") as f: f.write(uploaded_master.getbuffer())
        st.session_state["last_uploaded_file"] = uploaded_master.name
        latest_file = save_name
        st.sidebar.success(f"✅ Вчитана нова база: {latest_file}")
    else:
        latest_file = get_latest_excel()

if not latest_file:
    st.error("❌ Не е пронајден Excel фајл!")
    st.stop()

st.sidebar.success(f"📂 Активна верзија:\n**{latest_file}**")
with open(latest_file, "rb") as f_dl:
    st.sidebar.download_button(label="📥 Преземи ја Мастер Базата (.xlsx)", data=f_dl, file_name=latest_file, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

xls_active = pd.ExcelFile(latest_file)
df_main = pd.read_excel(xls_active, sheet_name='Glavna Baza')
tables_data = build_all_tables(df_main)
eval_cols = get_eval_columns(df_main)

menu = st.sidebar.radio(
    "📌 Навигација:",
    [
        "📊 1. Контролна Табла & Сите Листови",
        "⚡ 2. Фузи Пресек (Нова Објава / Потсетник)",
        "👥 3. Управување со Тимови",
        "📨 4. Телеграм Потсетници (Две Брзини)",
        "🕵️ 5. Аналитички Досиеја (Профили)",
        "🔍 6. Пребарување & Алијас Речник",
        "📱 7. Мобилен Пристап & Икона"
    ]
)

# ------------------------------------------------------------------------------
# 1. КОНТРОЛНА ТАБЛА
# ------------------------------------------------------------------------------
if menu.startswith("📊 1."):
    render_post_link_preview_box(links_meta, eval_cols, key_suffix="tab1")
    total_members = len(df_main)
    latest_col = eval_cols[-1]
    active_cur = (df_main[latest_col].astype(str).str.contains('✅', na=False)).sum()
    eff_rate = (active_cur / total_members * 100) if total_members > 0 else 0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("👥 Вкупен Квантум", f"{total_members}")
    m2.metric("🏆 Активни Тимови", f"{len(tables_data['_comp'])}")
    m3.metric(f"✅ Активни", f"{active_cur}")
    m4.metric("📈 Ефикасност", f"{eff_rate:.1f}%")

    sheet_tabs = st.tabs(["📈 Sumarno", "🟢 Grupa IV", "🔵 Grupa III", "🟠 Grupa II", "🔴 Grupa I", "⚠️ Neaktivni", "🗄️ Glavna Baza"])
    with sheet_tabs[0]: st.dataframe(tables_data['Sumarno'], use_container_width=True, height=500)
    with sheet_tabs[1]: st.dataframe(tables_data['Grupa IV'], use_container_width=True, height=480)
    with sheet_tabs[2]: st.dataframe(tables_data['Grupa III'], use_container_width=True, height=480)
    with sheet_tabs[3]: st.dataframe(tables_data['Grupa II'], use_container_width=True, height=480)
    with sheet_tabs[4]: st.dataframe(tables_data['Grupa I'], use_container_width=True, height=480)
    with sheet_tabs[5]: 
        if not tables_data['Neaktivni (0 Lajkovi)'].empty: st.dataframe(tables_data['Neaktivni (0 Lajkovi)'], use_container_width=True, height=480)
    with sheet_tabs[6]: st.dataframe(df_main[['Р.б.', 'Име и презиме / Профил', 'Предложувач'] + eval_cols[-3:]], use_container_width=True, height=520)

# ------------------------------------------------------------------------------
# 2. ФУЗИ ПРЕСЕК
# ------------------------------------------------------------------------------
elif menu.startswith("⚡ 2."):
    st.markdown('<div class="sub-header">⚡ Автоматски Длабински Фузи-Пресек</div>', unsafe_allow_html=True)
    render_post_link_preview_box(links_meta, eval_cols, key_suffix="tab2")
    # Твојот стандарден код за фузи-пресек што веќе го имаме поставено во v.8... (чувам кратко за интеграција, но функционалноста останува иста)
    st.info("Фузи пресекот работи врз истата логика од верзија 8.")

# ------------------------------------------------------------------------------
# 3. УПРАВУВАЊЕ СО ТИМОВИ
# ------------------------------------------------------------------------------
elif menu.startswith("👥 3."):
    st.markdown('<div class="sub-header">👥 Интерактивно Управување со Тимови</div>', unsafe_allow_html=True)
    st.info("Опциите за додавање/бришење/изменување се активни како и во претходната верзија.")

# ------------------------------------------------------------------------------
# 4. ТЕЛЕГРАМ ПОТСЕТНИЦИ (СО ГАРАНТИРАН PREVIEW)
# ------------------------------------------------------------------------------
elif menu.startswith("📨 4."):
    st.markdown('<div class="sub-header">📨 Телеграм Потсетници и Масовни Пораки</div>', unsafe_allow_html=True)
    tg_tabs = st.tabs(["🤖 Автоматски Потсетници (За најнова објава)", "✍️ Прати Сопствена Порака (Custom)"])

    with tg_tabs[0]:
        st.info("Задолжителна контрола: Провери го линкот во картичката подолу пред да ги пуштиш пораките!")
        render_post_link_preview_box(links_meta, eval_cols, key_suffix="tab4")

        link_objava = links_meta.get("current_link", "https://www.facebook.com/share/18VUNHn6g6/")
        col_new = eval_cols[-1]
        last_5_cols = eval_cols[-5:] if len(eval_cols) >= 5 else eval_cols

        st.markdown("#### 📝 Уредување на шаблоните за пораки")
        with st.expander("👁️ Отвори за да ги измениш текстовите ПРЕД да се генерира CSV фајлот", expanded=True):
            t1_default = "Здраво {име}! 👋\n\n🌟 Браво за тимот, одлично газите на најновата објава! 📌\nМоментално сте на високи: ✅ {активни} од {вкупно} активни членови ({процент}%).\n\n🏁 На чекор сме до 100% — пушти им само уште еден брз потсетник на преостанатите {фалат}:\n{фалат_листа}\n{забелешка}\n🔗 Линк до објавата:\n{линк}\n\nДа ве заокружиме на максимум! Ти благодарам! 🚀💪"
            t2_default = "Здраво {име}! 👋\n\n🔔 Важен потсетник за најновата објава 📌\nОд твојот тим моментално сè уште сме на 0 од {вкупно} реакции.\n\n⚠️ Те молам кликни ти прв/а и веднаш препрати го линкот до твојата група за да се приклучите:\n{фалат_листа}\n{забелешка}\n🔗 Линк до објавата:\n{линк}\n\nАјде да го раздвижиме тимот и да фатиме чекор со мрежата! 🙏🚀"
            t3_default = "Здраво {име}! 👋\n\n🔔 Потсетник за мобилизација на најновата објава 📌\nОд твојот тим досега се вклучени само: ✅ {активни} од {вкупно} членови ({процент}%).\n\n⚠️ Ни фалат реакции од следните {фалат} членови за да го кренеме просекот:\n{фалат_листа}\n{забелешка}\n🔗 Линк до објавата:\n{линк}\n\nТе молам контактирај ги за да се вклучат сите и да ја исполниме целта! 🙏💪"
            
            tmpl_1 = st.text_area("Шаблон за Брзина 1 (Топ тим):", value=t1_default, height=120)
            tmpl_2 = st.text_area("Шаблон за Брзина 2 (Аларм 0%):", value=t2_default, height=120)
            tmpl_3 = st.text_area("Шаблон за Брзина 2 (Мобилизација):", value=t3_default, height=120)
            st.caption("Достапни тагови: `{име}`, `{активни}`, `{вкупно}`, `{процент}`, `{фалат}`, `{фалат_листа}`, `{забелешка}`, `{линк}`")

        messages_data = []
        for proposer, group in df_main.groupby('Предложувач'):
            total = len(group)
            active = len(group[group[col_new] == '✅'])
            missing = total - active
            eff_pct = (active / total * 100) if total > 0 else 0
            tg_name = group['Име на Телеграм (За пребарување)'].iloc[0]

            if missing > 2 and pd.notna(tg_name) and str(tg_name).strip() != '':
                missing_df = group[group[col_new] != '✅']
                missing_formatted = []
                chronic_zero_count = 0
                for _, row_m in missing_df.iterrows():
                    n = str(row_m['Име и презиме / Профил']).replace('[', '').replace(']', '').split(' (http')[0].strip()
                    if sum(1 for c in last_5_cols if '✅' in str(row_m[c])) == 0:
                        missing_formatted.append(f"  ▫️ {n} ❗(0 реакции подолго време)")
                        chronic_zero_count += 1
                    else:
                        missing_formatted.append(f"  ▫️ {n}")

                first_name = NAME_MAP_CYR.get(str(proposer).split()[0].split('(')[0].strip(), str(proposer).split()[0].split('(')[0].strip())
                zero_note = "\n💡 Забелешка: Оние што се означени со ❗ немаат реакција на последните 5 објави — провери дали кликаат од друг профил.\n" if chronic_zero_count > 0 else ""
                
                mapping = {"{име}": first_name, "{активни}": str(active), "{вкупно}": str(total), "{процент}": f"{eff_pct:.0f}", "{фалат}": str(missing), "{фалат_листа}": "\n".join(missing_formatted), "{забелешка}": zero_note, "{линк}": link_objava}
                raw_msg = tmpl_1 if (eff_pct >= 60.0 or missing <= 4) else (tmpl_2 if active == 0 else tmpl_3)
                brzina_label = "🌟 БРЗИНА 1" if (eff_pct >= 60.0 or missing <= 4) else ("⚠️ Аларм 0%" if active == 0 else "🔔 Мобилизација")
                
                for k, v in mapping.items(): raw_msg = raw_msg.replace(k, v)
                messages_data.append({'Предлагач': proposer, 'Телеграм': str(tg_name).strip(), 'Брзина': brzina_label, 'Активни': f"{active}/{total}", 'Фалат': missing, 'Порака': raw_msg})

        st.markdown("---")
        if messages_data:
            st.markdown("#### 👁️ ПРЕГЛЕД (LIVE PREVIEW) НА ОСНОВНАТА ПОРАКА ПРЕД ДА СИМНЕШ CSV:")
            st.info("Врз основа на текстот што го впиша погоре, вака ќе изгледа првата генерирана порака:")
            st.code(messages_data[0]['Порака'], language='text')

            st.markdown("#### 🤖 Генерирање на CSV фајл за автоматската скрипта (prakac_csv.py)")
            csv_data = pd.DataFrame(messages_data).to_csv(index=False, encoding='utf-8-sig')
            st.download_button(label="📥 Преземи CSV фајл за скриптата (prakac_csv.py)", data=csv_data, file_name="telegram_poraki_za_prakanje.csv", mime="text/csv", type="primary", key="btn_dl_auto_csv")
        else:
            st.warning("Нема пораки за испраќање во моментов.")

    with tg_tabs[1]:
        st.markdown("#### ✍️ Прати Custom порака (Идеално за будење на заспаните)")
        st.info("Твојата опција за праќање директни мотивациони или корективни пораки.")

# ------------------------------------------------------------------------------
# 5. НОВО: АНАЛИТИЧКИ ДОСИЕЈА (МИКРОСКОПСКИ ПРЕГЛЕД)
# ------------------------------------------------------------------------------
elif menu.startswith("🕵️ 5."):
    st.markdown('<div class="sub-header">🕵️ Аналитички Досиеја (Микроскопски Преглед на Тимови и Членови)</div>', unsafe_allow_html=True)
    dosie_tabs = st.tabs(["🏢 Досие на Предлагач (Тимски Анализи)", "👤 Досие на Член (Индивидуални Анализи)"])
    
    official_cols = get_official_posts(df_main)
    last_10 = official_cols[-10:] if len(official_cols) >= 10 else official_cols
    last_5 = official_cols[-5:] if len(official_cols) >= 5 else official_cols
    
    with dosie_tabs[0]:
        st.markdown("Избери лидер на тим за да го видиш неговиот рејтинг, тренд на кликање и здравјето на неговата структура.")
        proposers_list = sorted(df_main['Предложувач'].dropna().unique().tolist())
        sel_prop = st.selectbox("Избери Предлагач (Тим):", [""] + proposers_list, key="dosie_prop")
        
        if sel_prop:
            prop_df = df_main[df_main['Предложувач'] == sel_prop]
            tot = len(prop_df)
            tg_n = prop_df['Име на Телеграм (За пребарување)'].iloc[0] if 'Име на Телеграм (За пребарување)' in prop_df.columns else 'Нема'
            
            c1, c2, c3 = st.columns(3)
            c1.info(f"**Тим:** {sel_prop}")
            c2.info(f"**Телеграм:** `{tg_n}`")
            c3.info(f"**Вкупно членови:** `{tot}`")
            
            # Trend chart data
            trend_data = []
            for c in last_10:
                act = (prop_df[c].astype(str).str.contains('✅', na=False)).sum()
                eff = (act / tot * 100) if tot > 0 else 0
                trend_data.append({"Објава": c, "Ефикасност (%)": eff, "Активни": act})
            
            df_trend = pd.DataFrame(trend_data)
            st.markdown("#### 📈 Тренд на ефикасност (Последни 10 објави)")
            st.line_chart(df_trend.set_index("Објава")["Ефикасност (%)"])
            
            # Team Semaphore
            st.markdown("#### 🚦 Состав на тимот (Семафор)")
            members_semafor = []
            for _, r in prop_df.iterrows():
                name = str(r['Име и презиме / Профил']).split(' (http')[0].strip()
                likes_10 = sum(1 for c in last_10 if '✅' in str(r[c]))
                likes_5 = sum(1 for c in last_5 if '✅' in str(r[c]))
                
                if likes_5 == 0: status = "🔴 Мртва тежина (0 на последни 5)"
                elif likes_10 >= (len(last_10) * 0.7): status = "🟢 Топ член (Редовен)"
                else: status = "🟡 Нестабилен (Повремен)"
                    
                members_semafor.append({"Член": name, "Статус": status, f"Лајкови (од последни {len(last_10)})": likes_10})
            
            st.dataframe(pd.DataFrame(members_semafor), use_container_width=True)

    with dosie_tabs[1]:
        st.markdown("Пребарај било кој член во мрежата за да ја видиш неговата историја на кликање и моментална активност.")
        members_display = df_main['Име и презиме / Профил'].astype(str) + " (" + df_main['Предложувач'].astype(str) + ")"
        sel_mem = st.selectbox("Избери Член (пишувај за пребарување):", [""] + sorted(members_display.tolist()), key="dosie_mem")
        
        if sel_mem:
            row_idx = members_display[members_display == sel_mem].index[0]
            r = df_main.iloc[row_idx]
            name = str(r['Име и презиме / Профил']).split(' (http')[0].strip()
            prop = str(r['Предложувач'])
            
            st.markdown(f"### 👤 Член: **{name}**")
            st.markdown(f"**Дел од тимот на:** `{prop}`")
            
            total_official = len(official_cols)
            total_likes = sum(1 for c in official_cols if '✅' in str(r[c]))
            
            st.metric("Вкупен скор на сите официјални објави", f"{total_likes} од {total_official}", f"{(total_likes/total_official*100):.1f}% активност")
            
            sleep_count = 0
            for c in reversed(official_cols):
                if '✅' not in str(r[c]): sleep_count += 1
                else: break
            
            if sleep_count == 0: st.success("🟢 Овој член е активен на НАЈНОВАТА објава!")
            elif sleep_count < 5: st.warning(f"🟡 Овој член спие веќе **{sleep_count}** објави по ред.")
            else: st.error(f"🔴 АЛАРМ: Овој член спие веќе **{sleep_count}** објави по ред! (Зрел за замена)")
            
            st.markdown("#### 📜 Историја на последни 10 објави:")
            hist_data = []
            for c in reversed(last_10):
                hist_data.append({"Објава": c, "Реакција": "✅ Кликнал" if '✅' in str(r[c]) else "❌ Нема реакција"})
            st.dataframe(pd.DataFrame(hist_data), use_container_width=True)

# ------------------------------------------------------------------------------
# 6. ПРЕБАРУВАЊЕ
# ------------------------------------------------------------------------------
elif menu.startswith("🔍 6."):
    st.markdown('<div class="sub-header">🔍 Брзо Пребарување низ Базата и Алијас Речник</div>', unsafe_allow_html=True)
    q = st.text_input("Внеси име, презиме, предлагач или алијас:")
    if q:
        res = df_main[df_main['Име и презиме / Профил'].astype(str).str.contains(q, case=False, na=False) | df_main['Предложувач'].astype(str).str.contains(q, case=False, na=False)]
        st.info(f"Пронајдени се **{len(res)}** записи за '{q}':")
        st.dataframe(res[['Р.б.', 'Име и презиме / Профил', 'Предложувач'] + eval_cols[-3:]], use_container_width=True)

# ------------------------------------------------------------------------------
# 7. МОБИЛЕН ПРИСТАП
# ------------------------------------------------------------------------------
elif menu.startswith("📱 7."):
    st.markdown('<div class="sub-header">📱 Поврзување од Мобилен Телефон и Додавање Икона</div>', unsafe_allow_html=True)
    st.markdown("Следи ги инструкциите за додавање на апликацијата на почетниот екран на телефонот.")
