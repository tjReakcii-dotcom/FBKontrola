# -*- coding: utf-8 -*-
"""
Мастер Веб-Апликација (Десктоп + Мобилен) за ФБ Контрола,
Длабински Фузи-Пресеци, Преглед на Линкови од Објави,
Управување со Тимови (Додавање/Бришење/Замена) и Телеграм Потсетници во Две Брзини.
[ОПТИМИЗИРАНА ВЕРЗИЈА: @st.cache_data + @st.fragment + Бекап Заштита]
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
import warnings
from datetime import datetime
from difflib import SequenceMatcher

# Исклучување на непотребни Pandas / OpenPyXL системски линии со предупредувања
warnings.filterwarnings("ignore")

st.set_page_config(
    page_title="ФБ Контрола - Мастер Систем",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Безбеден декоратор за @st.fragment (компатибилен со сите верзии на Streamlit)
fragment_decorator = getattr(st, "fragment", getattr(st, "experimental_fragment", lambda f: f))

# Стилизирање за Десктоп и Мобилен приказ + Елиминација на сивите линии (Skeleton UI) при апдејт
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
    /* Спречување на сиви линии (Skeleton) и трепкање при секоја интеракција */
    [data-testid="stSkeleton"] { display: none !important; }
    div[data-stale="true"] { opacity: 1 !important; transition: none !important; }
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
# 1. КОМПЛЕТЕН АЛИЈАС РЕЧНИК И НОРМАЛИЗАЦИЈА (Сите одлуки од разговорите)
# ==============================================================================
CYR_TO_LAT = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'ѓ': 'gj', 'е': 'e', 'ж': 'z',
    'з': 'z', 'ѕ': 'dz', 'и': 'i', 'ј': 'j', 'к': 'k', 'л': 'l', 'љ': 'lj', 'м': 'm',
    'н': 'n', 'њ': 'nj', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'ќ': 'k',
    'у': 'u', 'ф': 'f', 'х': 'h', 'ц': 'c', 'ч': 'c', 'џ': 'dz', 'ш': 's',
    'ć': 'c', 'č': 'c', 'š': 's', 'ž': 'z', 'đ': 'dj', 'ћ': 'c'
}

def normalize_name(s):
    if not isinstance(s, str):
        return ""
    s = s.lower()
    s = s.split(' (http')[0].split(' http')[0]
    s = s.replace('[', '').replace(']', '').replace(' - предложувач', '').replace(' - predlozuvac', '')
    s = re.sub(r'[^a-zа-яѓѕјљњќџćčšžđћ0-9\s]', ' ', s)
    res = [CYR_TO_LAT.get(ch, ch) for ch in s]
    norm = "".join(res)
    norm = norm.replace('sh', 's').replace('ch', 'c').replace('zh', 'z').replace('dj', 'gj').replace('kj', 'k').replace('ikj', 'ik').replace('ic', 'ik')
    return re.sub(r'\s+', ' ', norm).strip()

ALIAS_MAP = {
    'милка јовевска': ['mila mila', 'milka jovevska'],
    'milka jovevska': ['mila mila', 'milka jovevska'],
    'angela dr mit': ['ani mit', 'angela josifoska'],
    'орхидеја јосифоска': ['ani mit', 'angela josifoska'],
    'restylecloset6': ['да одгледуваме повеќе пченка'],
    'да одгледуваме повеќе пченка': ['да одгледуваме повеќе пченка'],
    'zzz boskovic': ['vojka boshkovic'],
    'vojka boshkovic': ['vojka boshkovic'],
    'daniela_kosta': ['jelica damjanovska'],
    'jelica damjanovska': ['jelica damjanovska'],
    'jovann_d': ['jovan damjanovski'],
    'профил 2': ['jovan damjanovski'],
    'александар петров': ['александар бацка', 'aleksandar backa'],
    'ljupco nikolovski': ['бу бу'],
    'andrijan andrijan': ['andrijan ani'],
    'елена божиновска': ['elena bozhinoska', 'elena bozinoska'],
    'elena bozinovska': ['elena bozhinoska', 'elena bozinoska'],
    'kate arsova velkova': ['kate arsova', 'kate arsova velkova', 'кате арсова'],
    'kate arsova': ['kate arsova', 'kate arsova velkova', 'кате арсова'],
    'емилија колева илиевска': ['koleva emilija'],
    'ѓокески филип': ['filip gjokeski'],
    'slobodan damkovski': ['bobi damkovski'],
    'рајна ѓорѓиева': ['rajne rajni'],
    'rajna gjorgjieva': ['rajne rajni'],
    'игор милошевски': ['м.игор ххх', 'м.игор xxx'],
    'igor milosevski': ['м.игор ххх', 'м.игор xxx'],
    'ацка станишева': ['ацка станишева', 'elena stanisheva'],
    'elena stanisheva': ['ацка станишева'],
    'ceki s medenica': ['ceki s medenica-dimeska'],
    'орце симов': ['orce simov nov profil'],
    'orce simov': ['orce simov nov profil'],
    'марија талевска': ['marija talevska miche'],
    'marija talevska': ['marija talevska miche'],
    'драган спировски': ['dragan spirovski gagi'],
    'драган димитров': ['драган гаги димитров'],
    'софија вренцоска': ['софи вренцоска'],
    'sofi vrencoska': ['софи вренцоска'],
    'владимир спиров': ['vladimir spirov'],
    'маја стоиманова': ['maja stoimanova-ristovska'],
    'снежана златковска': ['snezana zlatkovska'],
    'андријана филиповска': ['andrijana filiposka'],
    'andrijana filipovska': ['andrijana filiposka'],
    'jadranka popovska': ['jadranka popovski'],
    'јадранка поповска': ['jadranka popovski'],
    'katerina avramovska markovik': ['katerina sotirova', 'sotirova-nikolova katerina', 'kate petrovska-markovic'],
    'катерина аврамовска марковиќ': ['kate petrovska-markovic', 'sotirova-nikolova katerina'],
    'катерина сотирова': ['sotirova-nikolova katerina'],
    'nikolinka aneva': ['nina aneva'],
    'весна вучковска': ['vuckovska vesna'],
    'петреска јулијана': ['petrovska julijana'],
    'јулијана петровска': ['petrovska julijana'],
    'стојан срезоски': ['srezoski stojan'],
    'оливера костадиновска': ['olivera kostadinoska'],
    'димитри таки талевски': ['dimitri taki talevski'],
    'марија петкоски': ['marija petkovska'],
    'гоце талевски': ['goce talevski'],
    'дарко димитров ерасмус': ['darko dimitrov'],
    'darko dimitrov erasmus': ['darko dimitrov'],
    'илина шандуловска': ['ilina shandulovska'],
    'билијана блажевска': ['блажевска билјана'],
    'билјана блажевска': ['блажевска билјана'],
    'zokica_b': ['zorana boskovic'],
    'zorana': ['zorana boskovic'],
    'dimcedamjanovski': ['dimce damjanovski'],
    'зага костадиновска': ['dragica kostadinovska', 'зага костадиновска'],
    'daniel cvetanoski': ['daniel cvet'],
    'dragojuv miljkovikj': ['miljkovic dragoljub'],
    'jasna jasna': ['jas jas'],
    'olgica lazareska': ['lazarevska olga'],
    'еко планета': ['еко планета', 'ekoplaneta'],
    'кристијан ј.': ['кристијан ј.'],
    'kristijan j.': ['кристијан ј.'],
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
        "history": [
            {"post_col": "Дваесет и втора Објава (803 Конечен Пресек)", "url": "https://www.facebook.com/share/18VUNHn6g6/", "time": "2026-10-21"},
            {"post_col": "Дваесет и трета Објава (463 Пресек)", "url": "https://www.facebook.com/share/18VUNHn6g6/", "time": "2026-10-22"}
        ]
    }
    if os.path.exists(LINKS_META_FILE):
        try:
            with open(LINKS_META_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default_meta
    return default_meta

def save_links_meta(meta_data):
    try:
        with open(LINKS_META_FILE, "w", encoding="utf-8") as f:
            json.dump(meta_data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

# ==============================================================================
# 2. ФУНКЦИИ ЗА НАОЃАЊЕ, КЕШИРАЊЕ И ГЕНЕРИРАЊЕ НА EXCEL БАЗАТА (7 ЛИСТОВИ)
# ==============================================================================
def push_to_github(file_path):
    import base64
    import urllib.request
    import urllib.error

    try:
        token = st.secrets.get("GITHUB_TOKEN")
        repo = st.secrets.get("GITHUB_REPO")
        if not token or not repo:
            return False, "Не се пронајдени GitHub Secrets."
    except Exception:
        return False, "Секретите не се конфигурирани."

    try:
        with open(file_path, "rb") as f:
            content = f.read()
        encoded_content = base64.b64encode(content).decode("utf-8")
        
        url = f"https://api.github.com/repos/{repo}/contents/{file_path}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Streamlit-Auto-Sync"
        }
        
        req = urllib.request.Request(url, headers=headers)
        sha = None
        try:
            with urllib.request.urlopen(req) as response:
                if response.status == 200:
                    resp_data = json.loads(response.read().decode())
                    sha = resp_data.get("sha")
        except urllib.error.HTTPError as e:
            if e.code != 404:
                return False, f"Грешка при проверка на фајлот: {e.code}"
                
        data = {
            "message": f"Автоматска синхронизација на {file_path} преку Streamlit",
            "content": encoded_content
        }
        if sha:
            data["sha"] = sha
            
        req_put = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers, method="PUT")
        try:
            with urllib.request.urlopen(req_put) as response:
                if response.status in [200, 201]:
                    return True, "Базата е успешно и автоматски зачувана на GitHub!"
        except urllib.error.HTTPError as e:
            return False, f"Грешка при синхронизација: {e.code} - {e.read().decode()}"
            
    except Exception as e:
        return False, f"Проблем: {str(e)}"
    
    return False, "Непозната грешка при GitHub синхронизација."

def get_all_excel_versions():
    files = [f for f in os.listdir() if f.endswith('.xlsx') and 'kontrola' in f and not f.startswith('~$')]
    def get_ver(fn):
        nums = re.findall(r'\d+', fn)
        return int(nums[-1]) if nums else 0
    files.sort(key=get_ver)
    return files

def get_latest_excel():
    files = get_all_excel_versions()
    return files[-1] if files else None

def get_next_version_filename(current_file):
    if not current_file:
        return "kontrola_klik_najnova_final_219.xlsx"
    nums = re.findall(r'\d+', current_file)
    next_ver = (int(nums[-1]) + 1) if nums else 219
    return f"kontrola_klik_najnova_final_{next_ver}.xlsx"

def get_eval_columns(df_main):
    cols = []
    keywords = ['Објава', 'Objava', 'Проверка', 'Пресек']
    start_tracking = False
    for c in df_main.columns:
        if 'Дваесет и втора Објава' in c:
            start_tracking = True
        if any(k in c for k in keywords) or start_tracking:
            if c not in ['Р.б.', 'Име и презиме / Профил', 'Предложувач', 'Име на Телеграм (За пребарување)', 'Телефонски број', 'Одговорен контролор', 'Телефонски број (Telegram)', 'Тековен Пресек']:
                cols.append(c)
    return cols

def get_official_posts(df_main):
    eval_cols = get_eval_columns(df_main)
    base_official = [
        'Проверка 23 (306 реакции)',
        'Нова Објава 2 (761 реакции)',
        'Трета Објава 4 (320 реакции)',
        'Четврта Објава 3 (771 реакции)',
        'Петта Објава 2 (637 реакции)',
        'Шеста Објава (Ревидиран Пресек)',
        'Седма Објава (Длабински Фузи Пресек)',
        'Осма Објава (Ново Видео)',
        'Десетта Објава (Најнов CSV - Финална Проверка)',
        'Единаесетта Објава (FAST CSV)',
        'Дванаесетта Објава (Нов Пресек)',
        'Тринаесетта Објава (Видео Пресек)',
        'Четринаесетта Објава (Реално Видео)',
        'Петринаесетта Објава (Ново Видео)',
        'Седумнаесетта Објава (Конечен Пресек)',
        'Осумнаесетта Објава (Конечен Пресек)',
        'Деветнаесетта Објава (1.1k Пресек)',
        'Дваесетта Објава (919 Пресек)',
        'Дваесет и прва Објава (1K+ Пресек - По Потсетници)',
        'Дваесет и втора Објава (803 Конечен Пресек)'
    ]
    valid_cols = [c for c in base_official if c in df_main.columns]
    if 'Дваесет и втора Објава (803 Конечен Пресек)' in eval_cols:
        idx_22 = eval_cols.index('Дваесет и втора Објава (803 Конечен Пресек)')
        for c in eval_cols[idx_22 + 1:]:
            if c not in valid_cols:
                valid_cols.append(c)
    else:
        for c in eval_cols:
            if c not in valid_cols:
                valid_cols.append(c)
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

        post_likes = []
        post_effs = []
        for col in official_cols:
            l = (grp[col].astype(str).str.contains('✅', na=False)).sum()
            post_likes.append(l)
            post_effs.append(l / tot_members if tot_members > 0 else 0)

        first_act_idx = next((i for i, l in enumerate(post_likes) if l > 0), None)
        if first_act_idx is not None:
            rel_likes = post_likes[first_act_idx:]
            rel_effs = post_effs[first_act_idx:]
        else:
            rel_likes = [post_likes[-1]] if post_likes else [0]
            rel_effs = [post_effs[-1]] if post_effs else [0]

        avg_likes = sum(rel_likes) / len(rel_likes)
        avg_eff = sum(rel_effs) / len(rel_effs)

        prev_likes = (grp[col_prev].astype(str).str.contains('✅', na=False)).sum()
        cur_likes = (grp[col_cur].astype(str).str.contains('✅', na=False)).sum()
        diff_likes = cur_likes - prev_likes
        cur_eff = cur_likes / tot_members if tot_members > 0 else 0
        cur_miss = tot_members - cur_likes

        eff_pct = avg_eff * 100
        if eff_pct <= 30.0:
            gr_hist = 'I'
        elif eff_pct < 50.0:
            gr_hist = 'II'
        elif eff_pct < 65.0:
            gr_hist = 'III'
        else:
            gr_hist = 'IV'

        stats_list.append({
            'Предлагач': p_clean,
            'ГР.': gr_hist,
            'Телеграм назив': tg_n,
            'Квантум': tot_members,
            'Претходна': prev_likes,
            'Тековна': cur_likes,
            'Разлика (+/-)': diff_likes,
            'Тековни Фалат': cur_miss,
            'Тековна Ефикасност': cur_eff,
            'Тековна Ефикасност %': f"{cur_eff*100:.1f}%",
            'Просек Лајкови': round(avg_likes, 1),
            'Просечна Ефикасност': avg_eff,
            'Просечна Ефикасност %': f"{avg_eff*100:.1f}%",
            'Објави Следени': len(rel_likes)
        })

    df_comp = pd.DataFrame(stats_list)

    # 1. Sumarno
    df_sum_disp = df_comp.sort_values(
        by=['Тековна', 'Тековна Ефикасност', 'Квантум'],
        ascending=[False, False, False]
    ).reset_index(drop=True)
    df_sum_disp.insert(0, 'Ранг', range(1, len(df_sum_disp) + 1))

    df_sum_sheet = pd.DataFrame({
        'Ранг': df_sum_disp['Ранг'],
        'ГР.': df_sum_disp['ГР.'],
        'Предлагач': df_sum_disp['Предлагач'],
        'Претходна': df_sum_disp['Претходна'],
        'Тековна': df_sum_disp['Тековна'],
        'Разлика (+/-)': df_sum_disp['Разлика (+/-)'],
        'Фалат': df_sum_disp['Тековни Фалат'],
        'Квантум': df_sum_disp['Квантум'],
        'Ефикасност %': df_sum_disp['Тековна Ефикасност %'],
        'Телеграм назив': df_sum_disp['Телеграм назив']
    })

    # 2. Групи IV - I
    def make_group_df(gr_code):
        sub = df_comp[df_comp['ГР.'] == gr_code].copy()
        sub = sub.sort_values(by=['Просек Лајкови', 'Просечна Ефикасност', 'Квантум'], ascending=[False, False, False]).reset_index(drop=True)
        sub.insert(0, 'Поз.', range(1, len(sub) + 1))
        status_col = []
        for _, r in sub.iterrows():
            cur_v = float(r['Тековна Ефикасност %'].replace('%', ''))
            avg_v = float(r['Просечна Ефикасност %'].replace('%', ''))
            diff = cur_v - avg_v
            if diff >= 10.0:
                status_col.append(f"🟢 Натфрлил (+{diff:.1f}%)")
            elif diff <= -10.0:
                status_col.append(f"🔴 Потфрлил ({diff:.1f}%)")
            else:
                status_col.append(f"⚪ Стандардно ({diff:+.1f}%)")
        return pd.DataFrame({
            'Поз.': sub['Поз.'],
            'Предлагач': sub['Предлагач'],
            'Квантум': sub['Квантум'],
            'Просек Лајкови': sub['Просек Лајкови'],
            'Просечна Ефикасност %': sub['Просечна Ефикасност %'],
            'Тековни Активни': sub['Тековна'],
            'Тековни Фалат': sub['Тековни Фалат'],
            'Тековна Ефикасност %': sub['Тековна Ефикасност %'],
            'Статус / Отстапување': status_col,
            'Телеграм назив': sub['Телеграм назив']
        })

    df_g4 = make_group_df('IV')
    df_g3 = make_group_df('III')
    df_g2 = make_group_df('II')
    df_g1 = make_group_df('I')

    # 3. Неактивни (0 Лајкови на последните 5 објави)
    last_5_official = official_cols[-5:] if len(official_cols) >= 5 else official_cols
inactive_rows = []
for _, r in df_main.iterrows():
    likes_all = sum(1 for c in eval_cols if '✅' in str(r[c]))
