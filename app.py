import streamlit as st
import pandas as pd
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import re

# ==========================================
# 1. НАСТРОЙКИ СТРАНИЦЫ И СТИЛИ
# ==========================================
st.set_page_config(page_title="Smart Ads.txt Validator", layout="wide", page_icon="🛡️")

st.markdown("""
    <style>
    .valid { color: #28a745; font-weight: bold; }
    .partial { color: #ffc107; font-weight: bold; }
    .error { color: #dc3545; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

st.title("🛡️ Smart Ads.txt / App-ads.txt Validator")
st.markdown("Проверка наличия записей с учетом типа (DIRECT/RESELLER) и игнорированием комментариев.")

# ==========================================
# 2. ФУНКЦИИ ЛОГИКИ (BACKEND)
# ==========================================

# Конфигурация сессии (как в примере коллеги)
LIVE_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
session = requests.Session()
session.headers.update({
    'User-Agent': LIVE_UA,
    'Accept': 'text/plain,text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
})

def fetch_file_content(domain, filename):
    """
    Скачивает файл с домена. Пробует HTTPS, затем HTTP.
    Возвращает (content, status_message, error_bool)
    """
    domain = domain.strip().replace("https://", "").replace("http://", "").split("/")[0]
    urls = [f"https://{domain}/{filename}", f"http://{domain}/{filename}"]
    
    for url in urls:
        try:
            response = session.get(url, timeout=10, allow_redirects=True)
            if response.status_code == 200:
                return response.text, "OK", False
            elif response.status_code == 403:
                # Иногда 403 значит, что бот заблокирован, но файл есть.
                # Но для валидатора это ошибка.
                continue
        except requests.exceptions.SSLError:
            try:
                # Пробуем без верификации SSL (как в скрипте коллеги)
                response = session.get(url, timeout=10, allow_redirects=True, verify=False)
                if response.status_code == 200:
                    return response.text, "OK (SSL warning)", False
            except:
                continue
        except Exception:
            continue
            
    return None, "File unreachable or 404", True

def parse_ads_file(content):
    """
    Превращает текст ads.txt в список словарей для поиска.
    Игнорирует комментарии (#).
    """
    parsed_lines = []
    if not content:
        return parsed_lines

    for line in content.splitlines():
        # Удаляем комментарии и лишние пробелы
        clean_line = line.split('#')[0].strip()
        if not clean_line:
            continue
        
        parts = [p.strip() for p in clean_line.split(',')]
        if len(parts) >= 3:
            parsed_lines.append({
                'domain': parts[0].lower(),
                'id': parts[1].lower(), # ID приводим к нижнему регистру для сверки
                'type': parts[2].upper(),
                # Authority ID (4-й параметр) опционален, здесь не критичен для матчинга
            })
    return parsed_lines

def parse_reference_line(line):
    """
    Парсит строку пользователя (эталон)
    Пример: google.com, pub-8309773808661346, RESELLER, f08c47fec0942fa0
    """
    parts = [p.strip() for p in line.split(',')]
    if len(parts) < 2:
        return None
    
    return {
        'domain': parts[0].lower(),
        'id': parts[1].lower(),
        'type': parts[2].upper() if len(parts) > 2 else None,
        'original': line
    }

def validate_domain(target_domain, filename, references):
    """
    Основная логика сверки
    """
    content, status_msg, is_error = fetch_file_content(target_domain, filename)
    
    results = []
    
    # Если файл не скачался
    if is_error:
        for ref in references:
            results.append({
                "URL": target_domain,
                "File": filename,
                "Result": "Error",
                "Details": status_msg,
                "Reference": ref['original']
            })
        return results

    # Парсим скачанный файл
    file_records = parse_ads_file(content)
    
    for ref in references:
        ref_domain = ref['domain']
        ref_id = ref['id']
        ref_type = ref['type'] # Может быть None, если юзер не указал
        
        match_found = False
        match_status = "Not found"
        details = "No matching Domain+ID pair found"
        
        # ЛОГИКА ПОИСКА (Priority Match)
        for record in file_records:
            # 1. Сверяем Домен и ID
            if record['domain'] == ref_domain and record['id'] == ref_id:
                # Пара найдена! Теперь проверяем тип.
                
                # Если тип в эталоне не указан, считаем валидным совпадение по ID
                if not ref_type:
                    match_status = "Valid"
                    details = "Matched by Domain + ID (Type not specified)"
                    match_found = True
                    break
                
                # Если тип указан, сверяем
                if record['type'] == ref_type:
                    match_status = "Valid"
                    details = "Full match"
                    match_found = True
                    break
                else:
                    match_status = "Partially matched"
                    details = f"Type mismatch: found {record['type']}, expected {ref_type}"
                    match_found = True
                    # Не делаем break, вдруг дальше в файле есть правильная строка с нужным типом?
                    # Но если не найдем полную, оставим Partial.
        
        results.append({
            "URL": target_domain,
            "File": filename,
            "Result": match_status,
            "Details": details,
            "Reference": ref['original']
        })
        
    return results

# ==========================================
# 3. ИНТЕРФЕЙС (UI)
# ==========================================

# --- Окно 1: Выбор файла ---
col1, col2 = st.columns([1, 3])
with col1:
    st.subheader("1. Settings")
    file_type = st.radio(
        "Select file to check:",
        ("ads.txt", "app-ads.txt"),
        index=0 # По дефолту ads.txt, но выбор виден явно
    )
    
    threads = st.slider("Threads (Speed)", min_value=1, max_value=50, value=20)

# --- Окно 2: Входные данные ---
with col2:
    st.subheader("2. Input Data")
    
    tab_targets, tab_refs = st.tabs(["🌐 Target Websites", "📝 Reference Lines (Rules)"])
    
    with tab_targets:
        target_input = st.text_area(
            "Sites to check (URLs or Domains)", 
            height=150,
            placeholder="example.com\nmygame.site\nhttps://news-portal.org"
        )
        
    with tab_refs:
        ref_input = st.text_area(
            "Reference Lines (What to look for)", 
            height=150, 
            placeholder="google.com, pub-8309773808661346, RESELLER\nonetag.com, 5d0d72448d8bfb0, DIRECT"
        )
        st.caption("Format: `domain, id, type` (comma separated)")

# --- Кнопка запуска ---
start_btn = st.button("🚀 Start Validation", type="primary", use_container_width=True)

# ==========================================
# 4. ОБРАБОТКА И ВЫВОД (EXECUTION)
# ==========================================

if start_btn:
    if not target_input or not ref_input:
        st.error("Please provide both Target Websites and Reference Lines.")
    else:
        # Подготовка данных
        targets = [t.strip() for t in target_input.splitlines() if t.strip()]
        
        # Парсинг эталонных строк
        references = []
        raw_refs = [r.strip() for r in ref_input.splitlines() if r.strip()]
        for r in raw_refs:
            parsed = parse_reference_line(r)
            if parsed:
                references.append(parsed)
            else:
                st.warning(f"Skipping invalid reference format: {r}")

        if not references:
            st.stop()

        # Прогресс бар
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        all_results = []
        
        # Многопоточный запуск
        with ThreadPoolExecutor(max_workers=threads) as executor:
            future_to_url = {
                executor.submit(validate_domain, url, file_type, references): url 
                for url in targets
            }
            
            for i, future in enumerate(as_completed(future_to_url)):
                url = future_to_url[future]
                try:
                    data = future.result()
                    all_results.extend(data)
                except Exception as e:
                    # Ловим критические ошибки потока
                    all_results.append({
                        "URL": url, "File": file_type, 
                        "Result": "System Error", "Details": str(e), 
                        "Reference": "-"
                    })
                
                # Обновление прогресса
                progress = (i + 1) / len(targets)
                progress_bar.progress(progress)
                status_text.text(f"Processed {i + 1}/{len(targets)} sites")

        progress_bar.empty()
        status_text.empty()
        
        # --- Окно 3: Вывод результатов ---
        st.divider()
        st.subheader("3. Results")
        
        df = pd.DataFrame(all_results)
        
        # Упорядочим колонки как ты просил
        # 1. URL, 2. File, 3. Result, 4. Details + (Reference для ясности)
        cols_order = ["URL", "File", "Result", "Details", "Reference"]
        df = df[cols_order]

        # Стилизация таблицы (раскраска статусов)
        def color_status(val):
            if val == "Valid":
                return 'background-color: #d4edda; color: #155724' # Green
            elif val == "Partially matched":
                return 'background-color: #fff3cd; color: #856404' # Yellow
            elif val == "Not found":
                return 'background-color: #f8d7da; color: #721c24' # Red
            return ''

        st.dataframe(
            df.style.map(color_status, subset=['Result']),
            use_container_width=True,
            height=600
        )
        
        # Кнопка скачивания
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="💾 Download Report (CSV)",
            data=csv,
            file_name=f"ads_txt_validation_{file_type}.csv",
            mime="text/csv",
        )
        
        # Статистика
        st.write("---")
        col_stat1, col_stat2, col_stat3 = st.columns(3)
        col_stat1.metric("Valid", len(df[df['Result'] == 'Valid']))
        col_stat2.metric("Partial Matches", len(df[df['Result'] == 'Partially matched']))
        col_stat3.metric("Not Found / Errors", len(df[df['Result'].isin(['Not found', 'Error'])]))
