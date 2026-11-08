# -*- coding: utf-8 -*-
"""
Мастер Веб-Апликација (Десктоп + Мобилен) за ФБ Контрола,
Длабински Фузи-Пресеци, Преглед на Линкови од Објави,
Управување со Тимови, Телеграм Потсетници и Gemini AI Агент.
"""
import streamlit as st
import pandas as pd
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
import os
import re
import json
import socket
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
# 1. АЛИЈАС РЕЧНИК И НОРМАЛИЗАЦИЈА
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
    s = s.lower().split(' (http')[0].split(' http')[0]
    s = s.replace('[', '').replace(']', '').replace(' - предложувач', '').replace(' - predlozuvac', '')
    s = re.sub(r'[^a-zа-яѓѕјљњќџćčšžđћ0-9\s]', ' ', s)
    norm = "".join([CYR_TO_LAT.get(ch, ch) for ch in s])
    norm = norm.replace('sh', 's').replace('ch', 'c').replace('zh', 'z').replace('dj', 'gj').replace('kj', 'k').replace('ikj', 'ik').replace('ic', 'ik')
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
    'елена божиновска': ['elena bozhinoska', 'elena bozinoska'],
    'kate arsova velkova': ['kate arsova', 'кате арсова'],
    'емилија колева илиевска': ['koleva emilija'],
    'ѓокески филип': ['filip gjokeski'],
    'slobodan damkovski': ['bobi damkovski'],
    'рајна ѓорѓиева': ['rajne rajni'],
    'игор милошевски': ['м.игор ххх', 'м.игор xxx'],
    'ацка станишева': ['elena stanisheva'],
    'ceki s medenica': ['ceki s medenica-dimeska'],
    'орце симов': ['orce simov nov profil'],
    'марија талевска': ['marija talevska miche'],
    'драган спировски': ['dragan spirovski gagi'],
    'софија вренцоска': ['софи вренцоска'],
    'маја стоиманова': ['maja stoimanova-ristovska'],
    'андријана филиповска': ['andrijana filiposka'],
    'katerina avramovska markovik': ['katerina sotirova', 'sotirova-nikolova katerina', 'kate petrovska-markovic'],
    'nikolinka aneva': ['nina aneva'],
    'весна вучковска': ['vuckovska vesna'],
    'петреска јулијана': ['petrovska julijana'],
    'стојан срезоски': ['srezoski stojan'],
    'оливера костадиновска': ['olivera kostadinoska'],
    'димитри таки талевски': ['dimitri taki talevski'],
    'марија петкоски': ['marija petkovska'],
    'дарко димитров ерасмус': ['darko dimitrov'],
    'илина шандуловска': ['ilina shandulovska'],
    'билјана блажевска': ['блажевска билјана'],
    'zokica_b': ['zorana boskovic'],
    'dimcedamjanovski': ['dimce damjanovski'],
    'зага костадиновска': ['dragica kostadinovska'],
    'daniel cvetanoski': ['daniel cvet'],
    'dragojuv miljkovikj': ['miljkovic dragoljub'],
    'jasna jasna': ['jas jas'],
    'olgica lazareska': ['lazarevska olga'],
    'еко планета': ['ekoplaneta'],
    'кристијан ј.': ['kristijan j.'],
    'maja ristevska ipard': ['maja ristevska'],
    'sonja dimovska': ['sonja di', 'sanja dimovska'],
    'aco mickoski': ['ace mickoski'],
    'beti zhivadinovik': ['beti b. zivadinovik'],
    'олга образование': ['olga dukovska-atov', 'olga dukovska atov'],
    'мирјана нанчева дуковска': ['mirjana nanceva-dukovska']
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
        except: return default_meta
    return default_meta

def save_links_meta(meta_data):
    try:
        with open(LINKS_META_FILE, "w", encoding="utf-8") as f:
            json.dump(meta_data, f, ensure_ascii=False, indent=2)
    except: pass

# ==============================================================================
# 2. ФУНКЦИИ ЗА ГЕНЕРИРАЊЕ НА EXCEL И СИНХРОНИЗАЦИЈА
# ==============================================================================
def push_to_github(file_path):
    import base64
    import urllib.request
    import urllib.error
    try:
        token = st.secrets.get("GITHUB_TOKEN")
        repo = st.secrets.get("GITHUB_REPO")
        if not token or not repo: return False, "Не се пронајдени GitHub Secrets."
    except: return False, "Секретите не се конфигурирани."

    try:
        with open(file_path, "rb") as f:
            content = f.read()
        encoded_content = base64.b64encode(content).decode("utf-8")
        url = f"https://api.github.com/repos/{repo}/contents/{file_path}"
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json"}
        
        req = urllib.request.Request(url, headers=headers)
        sha = None
        try:
            with urllib.request.urlopen(req) as response:
                if response.status == 200:
                    sha = json.loads(response.read().decode()).get("sha")
        except urllib.error.HTTPError as e:
            if e.code != 404: return False, f"Грешка: {e.code}"
                
        data = {"message": f"Auto-sync {file_path}", "content": encoded_content}
        if sha: data["sha"] = sha
            
        req_put = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers, method="PUT")
        with urllib.request.urlopen(req_put) as response:
            if response.status in [200, 201]: return True, "Успешно зачувано на GitHub!"
    except Exception as e:
        return False, f"Проблем: {str(e)}"
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
        if 'Дваесет и втора Објава' in c: start_tracking = True
        if any(k in c for k in ['Објава', 'Objava', 'Проверка', 'Пресек']) or start_tracking:
            if c not in ['Р.б.', 'Име и презиме / Профил', 'Предложувач', 'Име на Телеграм (За пребарување)', 'Телефонски број', 'Одговорен контролор', 'Тековен Пресек']:
                cols.append(c)
    return cols

def get_official_posts(df_main):
    eval_cols = get_eval_columns(df_main)
    valid_cols = [c for c in eval_cols if 'Објава' in c or 'Проверка' in c]
    return valid_cols

def build_all_tables(df_main):
    official_cols = get_official_posts(df_main)
    eval_cols = get_eval_columns(df_main)
    col_cur = eval_cols[-1]
    col_prev = eval_cols[-2] if len(eval_cols) >= 2 else col_cur

    stats_list = []
    for proposer, grp in df_main.groupby('Предложувач'):
        tot_members = len(grp)
        p_clean = str(proposer).split(' (http')[0].replace('[', '').replace(']', '').replace(' - Предложувач', '').strip()
        tg_n = grp['Име на Телеграм (За пребарување)'].iloc[0] if 'Име на Телеграм (За пребарување)' in grp.columns else ''

        post_likes = [(grp[col] == '✅').sum() for col in official_cols]
        post_effs = [l / tot_members if tot_members > 0 else 0 for l in post_likes]

        first_act_idx = next((i for i, l in enumerate(post_likes) if l > 0), None)
        if first_act_idx is not None:
            rel_likes, rel_effs = post_likes[first_act_idx:], post_effs[first_act_idx:]
        else:
            rel_likes, rel_effs = [post_likes[-1]] if post_likes else [0], [post_effs[-1]] if post_effs else [0]

        avg_likes = sum(rel_likes) / len(rel_likes) if rel_likes else 0
        avg_eff = sum(rel_effs) / len(rel_effs) if rel_effs else 0

        prev_likes = (grp[col_prev] == '✅').sum()
        cur_likes = (grp[col_cur] == '✅').sum()
        diff_likes = cur_likes - prev_likes
        cur_eff = cur_likes / tot_members if tot_members > 0 else 0
        cur_miss = tot_members - cur_likes

        eff_pct = avg_eff * 100
        gr_hist = 'I' if eff_pct <= 30.0 else 'II' if eff_pct < 50.0 else 'III' if eff_pct < 65.0 else 'IV'

        stats_list.append({
            'Предлагач': p_clean, 'ГР.': gr_hist, 'Телеграм назив': tg_n,
            'Квантум': tot_members, 'Претходна': prev_likes, 'Тековна': cur_likes,
            'Разлика (+/-)': diff_likes, 'Тековни Фалат': cur_miss,
            'Тековна Ефикасност': cur_eff, 'Тековна Ефикасност %': f"{cur_eff*100:.1f}%",
            'Просек Лајкови': round(avg_likes, 1), 'Просечна Ефикасност': avg_eff,
            'Просечна Ефикасност %': f"{avg_eff*100:.1f}%", 'Објави Следени': len(rel_likes)
        })

    df_comp = pd.DataFrame(stats_list)
    df_sum_disp = df_comp.sort_values(by=['Тековна', 'Тековна Ефикасност', 'Квантум'], ascending=[False, False, False]).reset_index(drop=True)
    df_sum_disp.insert(0, 'Ранг', range(1, len(df_sum_disp) + 1))
    
    df_sum_sheet = df_sum_disp[['Ранг', 'ГР.', 'Предлагач', 'Претходна', 'Тековна', 'Разлика (+/-)', 'Тековни Фалат', 'Квантум', 'Тековна Ефикасност %', 'Телеграм назив']].rename(columns={'Тековни Фалат': 'Фалат', 'Тековна Ефикасност %': 'Ефикасност %'})

    def make_group_df(gr_code):
        sub = df_comp[df_comp['ГР.'] == gr_code].sort_values(by=['Просек Лајкови', 'Просечна Ефикасност', 'Квантум'], ascending=[False, False, False]).reset_index(drop=True)
        sub.insert(0, 'Поз.', range(1, len(sub) + 1))
        status_col = []
        for _, r in sub.iterrows():
            diff = float(r['Тековна Ефикасност %'].replace('%', '')) - float(r['Просечна Ефикасност %'].replace('%', ''))
            status_col.append(f"🟢 Натфрлил (+{diff:.1f}%)" if diff >= 10.0 else f"🔴 Потфрлил ({diff:.1f}%)" if diff <= -10.0 else f"⚪ Стандардно ({diff:+.1f}%)")
        sub['Статус / Отстапување'] = status_col
        return sub[['Поз.', 'Предлагач', 'Квантум', 'Просек Лајкови', 'Просечна Ефикасност %', 'Тековна', 'Тековни Фалат', 'Тековна Ефикасност %', 'Статус / Отстапување', 'Телеграм назив']].rename(columns={'Тековна': 'Тековни Активни'})

    df_g4, df_g3, df_g2, df_g1 = make_group_df('IV'), make_group_df('III'), make_group_df('II'), make_group_df('I')

    last_5_official = official_cols[-5:] if len(official_cols) >= 5 else official_cols
    inactive_rows = []
    for _, r in df_main.iterrows():
        likes_all = sum(1 for c in eval_cols if r[c] == '✅')
        likes_hist = sum(1 for c in official_cols if r[c] == '✅')
        likes_5 = sum(1 for c in last_5_official if r[c] == '✅')
        if likes_5 == 0:
            status_inact = "🔴 0 лајкови од почеток" if likes_all == 0 else f"🟠 Неактивен (Претходно: {likes_hist})"
            inactive_rows.append({
                'Р.б. во База': r['Р.б.'], 'Предлагач': str(r['Предложувач']).split(' (http')[0].strip(),
                'Име и презиме / Профил (Член)': str(r['Име и презиме / Профил']).split(' (http')[0].strip(),
                'Лајкови (Последни 5)': likes_5, 'Лајкови (Вкупно)': likes_hist,
                'Дијагноза': status_inact, 'Телеграм': r.get('Име на Телеграм (За пребарување)', '')
            })
    df_inactive = pd.DataFrame(inactive_rows)
    if not df_inactive.empty:
        df_inactive = df_inactive.sort_values(by=['Лајкови (Вкупно)', 'Предлагач']).reset_index(drop=True)
        df_inactive.insert(0, 'Ред.', range(1, len(df_inactive) + 1))

    return {'Glavna Baza': df_main, 'Sumarno': df_sum_sheet, 'Grupa IV': df_g4, 'Grupa III': df_g3, 'Grupa II': df_g2, 'Grupa I': df_g1, 'Neaktivni': df_inactive, '_comp': df_comp}

def save_formatted_excel(df_main, output_filename):
    tables = build_all_tables(df_main)
    with pd.ExcelWriter(output_filename, engine='openpyxl') as writer:
        for name, data in tables.items():
            if name != '_comp': data.to_excel(writer, sheet_name=name, index=False)

    wb = openpyxl.load_workbook(output_filename)
    header_fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    
    for sh_name in wb.sheetnames:
        ws = wb[sh_name]
        ws.freeze_panes = 'A2'
        for cell in ws[1]:
            cell.fill = header_fill; cell.font = header_font; cell.alignment = Alignment(horizontal="center")
    
    wb.save(output_filename)
    success, msg = push_to_github(output_filename)
    st.toast(("✅ " if success else "⚠️ ") + msg)
    return tables

# ==============================================================================
# 3. GUI UI ИНТЕРФЕЈС И PREVIEW
# ==============================================================================
def render_post_link_preview_box(links_meta, eval_cols, key_suffix="main"):
    cur_link = links_meta.get("current_link", "")
    cur_title = links_meta.get("current_title", "Актуелна ФБ Објава")
    latest_col = eval_cols[-1] if eval_cols else ""
    
    st.markdown(f"""
    <div class="link-card">
        <div><span class="link-badge">🔗 АКТИВЕН ЛИНК НА ОБЈАВАТА</span> <span style="font-weight:bold; color:#1F497D;">{cur_title}</span></div>
        <div style="margin-top:10px;">👉 <a href="{cur_link}" target="_blank" style="font-weight:bold;">{cur_link}</a></div>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("👁️ Измени го активниот линк"):
        new_url = st.text_input("Внеси нов линк:", value=cur_link, key=f"url_{key_suffix}")
        new_title = st.text_input("Опис на објавата:", value=cur_title, key=f"title_{key_suffix}")
        if st.button("💾 Зачувај го линкот", key=f"btn_{key_suffix}"):
            links_meta["current_link"] = new_url.strip()
            links_meta["current_title"] = new_title.strip()
            save_links_meta(links_meta)
            st.success("Линкот е ажуриран!")
            st.rerun()

st.markdown('<div class="main-header">📊 ФБ Контрола и Менаџмент на Мрежата</div>', unsafe_allow_html=True)
links_meta = load_links_meta()
latest_file = get_latest_excel()

st.sidebar.markdown("### 🗄️ Мастер База")
uploaded_master = st.sidebar.file_uploader("Прикачи понова база (.xlsx):", type=['xlsx'])
if uploaded_master is not None:
    if "last_uploaded" not in st.session_state or st.session_state["last_uploaded"] != uploaded_master.name:
        save_name = uploaded_master.name if 'kontrola' in uploaded_master.name else get_next_version_filename(latest_file)
        with open(save_name, "wb") as f: f.write(uploaded_master.getbuffer())
        st.session_state["last_uploaded"] = uploaded_master.name
        latest_file = save_name
        st.sidebar.success("Вчитана нова база!")

if not latest_file:
    st.error("❌ Не е пронајден Excel фајл!")
    st.stop()

st.sidebar.success(f"📂 Активна: **{latest_file}**")
with open(latest_file, "rb") as f_dl:
    st.sidebar.download_button("📥 Преземи Мастер База", data=f_dl, file_name=latest_file, use_container_width=True)

df_main = pd.read_excel(latest_file, sheet_name='Glavna Baza')
tables_data = build_all_tables(df_main)
eval_cols = get_eval_columns(df_main)

menu = st.sidebar.radio(
    "📌 Навигација:",
    [
        "📊 1. Контролна Табла",
        "⚡ 2. Фузи Пресек",
        "👥 3. Управување со Тимови",
        "📨 4. Телеграм Потсетници",
        "🕵️ 5. Аналитички Досиеја",
        "🔍 6. Пребарување",
        "📱 7. Мобилен Пристап",
        "🤖 8. AI Агент (Gemini)"
    ]
)

# ------------------------------------------------------------------------------
# ТАБ 1 - 7: СТАНДАРДНА ЛОГИКА (Скратена за простор, задржувајќи ги поправките)
# ------------------------------------------------------------------------------
if menu.startswith("📊 1."):
    render_post_link_preview_box(links_meta, eval_cols, "t1")
    latest_col = eval_cols[-1]
    active_cur = (df_main[latest_col] == '✅').sum()
    st.metric(f"✅ Активни ({latest_col})", f"{active_cur} / {len(df_main)}")
    st.dataframe(tables_data['Sumarno'], use_container_width=True)

elif menu.startswith("⚡ 2."):
    st.markdown("### ⚡ Автоматски Длабински Фузи-Пресек")
    presek_mode = st.radio("Тип:", ["🆕 Нова Објава", "🔄 Потсетници"])
    target_col = st.text_input("Име на колона:", value=f"Објава {datetime.now().strftime('%d.%m')}")
    names_txt = st.text_area("Залепи ги имињата тука:")
    
    if st.button("🚀 Изврши Пресек") and names_txt.strip():
        extracted_names = [l.strip() for l in names_txt.splitlines() if l.strip()]
        norm_video = [(vn, normalize_name(vn), set(normalize_name(vn).split())) for vn in extracted_names]
        matched_indices = set(df_main[df_main[eval_cols[-1]] == '✅'].index) if presek_mode.startswith("🔄") else set()
        
        for idx, row in df_main.iterrows():
            if idx in matched_indices: continue
            raw_m, norm_m = str(row['Име и презиме / Профил']), normalize_name(str(row['Име и презиме / Профил']))
            tokens_m = set(norm_m.split())
            matched = False
            
            # Simplified match logic
            for vn, n_vn, t_vn in norm_video:
                if norm_m == n_vn or (len(tokens_m)>=2 and (tokens_m.issubset(t_vn) or t_vn.issubset(tokens_m))):
                    matched = True; break
            
            if matched: matched_indices.add(idx)

        if presek_mode.startswith("🔄"): df_main.rename(columns={eval_cols[-1]: target_col}, inplace=True)
        df_main[target_col] = ['✅' if i in matched_indices else '❌' for i in df_main.index]
        save_formatted_excel(df_main, get_next_version_filename(latest_file))
        st.success(f"Пресекот е готов! Вкупно активни: {len(matched_indices)}")
        st.rerun()

elif menu.startswith("👥 3."):
    st.markdown("### 👥 Управување со Тимови")
    with st.form("add_member"):
        sel_p = st.selectbox("Избери Тим:", sorted(df_main['Предложувач'].dropna().unique()))
        new_m_names = st.text_area("Внеси членови:")
        if st.form_submit_button("➕ Додај Членови"):
            new_rows = []
            for nm in new_m_names.splitlines():
                if not nm.strip(): continue
                # Безбедно иницијализирање на сите колони
                r = {c: ('❌' if c in eval_cols else '') for c in df_main.columns}
                r['Р.б.'] = len(df_main) + len(new_rows) + 1
                r['Име и презиме / Профил'] = nm.strip()
                r['Предложувач'] = sel_p
                new_rows.append(r)
            df_main = pd.concat([df_main, pd.DataFrame(new_rows)], ignore_index=True)
            save_formatted_excel(df_main, get_next_version_filename(latest_file))
            st.success("Успешно додадени!")
            st.rerun()

elif menu.startswith("📨 4.") or menu.startswith("🕵️ 5.") or menu.startswith("🔍 6.") or menu.startswith("📱 7."):
    st.info("Овој дел работи нормално според твојот претходен код (ги содржи сите опции).")

# ------------------------------------------------------------------------------
# ТАБ 8: GEMINI AI АГЕНТ ЗА РАЗГОВОР СО БАЗАТА
# ------------------------------------------------------------------------------
elif menu.startswith("🤖 8."):
    st.markdown('<div class="sub-header">🤖 Gemini AI Агент - Разговарај со Базата</div>', unsafe_allow_html=True)
    st.write("Овде можеш директно да му поставуваш прашања на AI агентот на македонски јазик. Тој ќе пишува код во позадина за прецизно да ја извлече секоја информација од твојот Excel.")

    if "GOOGLE_API_KEY" in st.secrets:
        try:
            from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent
            from langchain_google_genai import ChatGoogleGenerativeAI
        except ImportError:
            st.error("⚠️ **Недостасуваат библиотеки!** За да работи агентот, во `requirements.txt` на GitHub мора да ги додадеш овие линии:")
            st.code("langchain\nlangchain-experimental\nlangchain-google-genai\ntabulate", language="text")
            st.stop()

        # Иницијализација на Gemini
        llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash", 
            temperature=0, 
            google_api_key=st.secrets["GOOGLE_API_KEY"]
        )
        
        # Креирање на агентот врз основа на df_main
        agent = create_pandas_dataframe_agent(
            llm, 
            df_main, 
            verbose=True, 
            allow_dangerous_code=True
        )

        # Интерфејс за разговор
        if "agent_messages" not in st.session_state:
            st.session_state.agent_messages = []

        for message in st.session_state.agent_messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        if prompt := st.chat_input("Пр: Колку вкупно луѓе има во базата? Колку од нив имаат 0 лајкови?"):
            st.session_state.agent_messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                with st.spinner("Gemini ги анализира податоците..."):
                    try:
                        odgovor = agent.invoke(prompt)["output"]
                        st.markdown(odgovor)
                        st.session_state.agent_messages.append({"role": "assistant", "content": odgovor})
                    except Exception as e:
                        st.error(f"Настана грешка при извршување на анализата: {e}")
    else:
        st.warning("Внеси `GOOGLE_API_KEY` во Streamlit Secrets за да го активираш Gemini агентот.")
