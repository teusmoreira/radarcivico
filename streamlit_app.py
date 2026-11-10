"""
Radar Cívico - Aplicação Principal Streamlit
Sistema de Inteligência Pública, Processamento de Linguagem Natural (NLP) e Alinhamento Político.
Permite hospedar diretamente no Streamlit Community Cloud (streamlit_app.py).
"""

import os
import json
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd

# Configuração de página do Streamlit
st.set_page_config(
    page_title="Radar Cívico - Inteligência Pública e Alinhamento Político",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilização CSS para o Streamlit
st.markdown("""
<style>
    /* Ajustes para imersão e responsividade */
    .block-container {
        padding-top: 1rem;
        padding-bottom: 1.5rem;
        padding-left: 1.5rem;
        padding-right: 1.5rem;
        max-width: 100%;
    }
    iframe {
        border-radius: 12px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.06);
    }
    .stMetric {
        background: #f8fafc;
        padding: 12px;
        border-radius: 8px;
        border: 1px solid #e2e8f0;
    }
    [data-testid="stSidebar"] {
        background-color: #0F1C2B;
        color: #E5ECF3;
    }
    [data-testid="stSidebar"] * {
        color: #E5ECF3 !important;
    }
    [data-testid="stSidebar"] .stSelectbox label, 
    [data-testid="stSidebar"] .stRadio label {
        color: #92A3B5 !important;
    }
</style>
""", unsafe_allow_html=True)

# Helper para carregar arquivos
@st.cache_data
def load_candidates():
    candidates_file = os.path.join(os.path.dirname(__file__), "candidates.json")
    if os.path.exists(candidates_file):
        with open(candidates_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

@st.cache_data
def load_html_app():
    html_file = os.path.join(os.path.dirname(__file__), "Radar Cívico.html")
    if os.path.exists(html_file):
        with open(html_file, "r", encoding="utf-8") as f:
            return f.read()
    return None

candidates = load_candidates()
html_content = load_html_app()

# ================= SIDEBAR =================
with st.sidebar:
    st.title("📡 Radar Cívico")
    st.caption("Inteligência Pública & Alinhamento Político")
    
    st.markdown("---")
    
    # Navegação entre visões
    view_mode = st.radio(
        "Navegação:",
        ["🌐 Radar Interativo (Aplicação Web)", 
         "👥 Explorador de Candidatos (Nativo)", 
         "📊 Métricas & Estatísticas",
         "💾 Exportar Base de Dados"],
        index=0
    )
    
    st.markdown("---")
    
    # Resumo Geral
    st.subheader("📌 Visão Geral")
    col_sb1, col_sb2 = st.columns(2)
    with col_sb1:
        st.metric("Candidatos", len(candidates))
        st.metric("Municípios", "8")
    with col_sb2:
        st.metric("Eixos Temáticos", "8")
        st.metric("Estados", "6")
        
    st.markdown("---")
    st.caption("🔍 **Fontes Oficiais**: TSE (DivulgaCandContas), Planos de Governo Oficiais, Portais Legislativos e Wikimedia Commons.")
    st.caption("⚡ Hospedado via **Streamlit Cloud**")

# ================= CONTEÚDO PRINCIPAL =================

if view_mode == "🌐 Radar Interativo (Aplicação Web)":
    # Visão principal: Renderiza a aplicação web completa e interativa
    if html_content:
        # Altura dinâmica para acomodar filtros e listagens confortavelmente
        components.html(html_content, height=1350, scrolling=True)
    else:
        st.error("Arquivo 'Radar Cívico.html' não encontrado na pasta do projeto.")

elif view_mode == "👥 Explorador de Candidatos (Nativo)":
    st.header("👥 Explorador Nativo de Candidatos e Propostas")
    st.write("Filtre e consulte os candidatos oficiais com suas fotos reais, partidos, cargos e compromissos prioritários.")
    
    if not candidates:
        st.warning("Nenhum candidato carregado da base 'candidates.json'.")
    else:
        # Filtros no topo
        c1, c2, c3, c4 = st.columns([2, 2, 2, 3])
        
        cargos = sorted(list({c.get('cargo', '').capitalize() for c in candidates if c.get('cargo')}))
        ufs = sorted(list({c.get('uf', '') for c in candidates if c.get('uf')}))
        partidos = sorted(list({c.get('partido', '') for c in candidates if c.get('partido')}))
        
        with c1:
            sel_cargo = st.selectbox("Cargo:", ["Todos"] + cargos)
        with c2:
            sel_uf = st.selectbox("Estado (UF):", ["Todos"] + ufs)
        with c3:
            sel_partido = st.selectbox("Partido:", ["Todos"] + partidos)
        with c4:
            search_query = st.text_input("Buscar por nome ou palavra-chave:", "")

        # Aplicação dos filtros
        filtered = candidates
        if sel_cargo != "Todos":
            filtered = [c for c in filtered if c.get('cargo', '').lower() == sel_cargo.lower()]
        if sel_uf != "Todos":
            filtered = [c for c in filtered if c.get('uf', '') == sel_uf]
        if sel_partido != "Todos":
            filtered = [c for c in filtered if c.get('partido', '') == sel_partido]
        if search_query.strip():
            sq = search_query.lower()
            filtered = [
                c for c in filtered 
                if sq in c.get('n', '').lower() 
                or sq in c.get('perfil', '').lower() 
                or any(sq in str(v).lower() for v in c.get('p', {}).values())
            ]

        st.info(f"Exibindo **{len(filtered)}** candidatos encontrados.")

        # Grid de cards dos candidatos
        cols_per_row = 3
        for i in range(0, len(filtered), cols_per_row):
            row_candidates = filtered[i:i + cols_per_row]
            cols = st.columns(cols_per_row)
            for col, cand in zip(cols, row_candidates):
                with col:
                    with st.container(border=True):
                        # Cabeçalho com foto e info básica
                        col_img, col_info = st.columns([1, 2])
                        with col_img:
                            foto_url = cand.get('foto')
                            if foto_url:
                                st.image(foto_url, use_container_width=True)
                            else:
                                st.write("👤")
                        with col_info:
                            st.subheader(cand.get('n', 'Sem Nome'))
                            st.caption(f"**{cand.get('partido', '')}** · Nº {cand.get('numero', '-')}")
                            loc = f"{cand.get('cidade', '')} - {cand.get('uf', '')}" if cand.get('cidade') else cand.get('uf', '')
                            st.markdown(f"*{cand.get('cargo', '').upper()}* · {loc}")
                        
                        st.markdown(f"**Perfil**: {cand.get('perfil', '-')}")
                        
                        # Propostas em destaque
                        propostas = cand.get('p', {})
                        with st.expander("Ver Propostas Oficiais (NLP)"):
                            if 'saude' in propostas:
                                st.markdown(f"🏥 **Saúde**: {propostas['saude']}")
                            if 'seguranca' in propostas:
                                st.markdown(f"🛡️ **Segurança**: {propostas['seguranca']}")
                            if 'educacao' in propostas:
                                st.markdown(f"🎓 **Educação**: {propostas['educacao']}")
                            for k, v in propostas.items():
                                if k not in ['saude', 'seguranca', 'educacao']:
                                    st.markdown(f"📌 **{k.capitalize()}**: {v}")

elif view_mode == "📊 Métricas & Estatísticas":
    st.header("📊 Análise Quantitativa e Cobertura Temática")
    
    if candidates:
        df = pd.DataFrame(candidates)
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Candidatos", len(df))
        m2.metric("Cargos Mapeados", df['cargo'].nunique() if 'cargo' in df else 0)
        m3.metric("Partidos Registrados", df['partido'].nunique() if 'partido' in df else 0)
        m4.metric("Estados (UFs)", df['uf'].nunique() if 'uf' in df else 0)
        
        st.markdown("---")
        
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.subheader("Distribuição por Cargo")
            if 'cargo' in df:
                cargo_counts = df['cargo'].value_counts()
                st.bar_chart(cargo_counts)
        
        with col_g2:
            st.subheader("Distribuição por Partido")
            if 'partido' in df:
                partido_counts = df['partido'].value_counts().head(10)
                st.bar_chart(partido_counts)
                
        st.markdown("---")
        st.subheader("Tabela Consolidada de Candidatos")
        df_display = df[['n', 'cargo', 'partido', 'numero', 'uf', 'cidade', 'perfil']].copy()
        df_display.columns = ['Nome', 'Cargo', 'Partido', 'Número', 'UF', 'Cidade', 'Perfil']
        st.dataframe(df_display, use_container_width=True)

elif view_mode == "💾 Exportar Base de Dados":
    st.header("💾 Exportação e Dados Abertos")
    st.write("Baixe a base de dados tratada com todos os 66 candidatos, vetores de dores, propostas oficiais classificadas por NLP e links para fotos reais.")
    
    col_d1, col_d2 = st.columns(2)
    
    with col_d1:
        st.subheader("📄 candidates.json")
        st.write("Arquivo JSON contendo a lista completa de candidatos estruturada para frontend e APIs.")
        candidates_json_str = json.dumps(candidates, ensure_ascii=False, indent=2)
        st.download_button(
            label="⬇️ Baixar candidates.json",
            data=candidates_json_str,
            file_name="candidates.json",
            mime="application/json"
        )
        
    with col_d2:
        st.subheader("🍃 mongodb_seed.json")
        st.write("Dump compatível com importação no MongoDB (mongorestore / mongoimport / Atlas).")
        seed_file = os.path.join(os.path.dirname(__file__), "mongodb_seed.json")
        seed_data = ""
        if os.path.exists(seed_file):
            with open(seed_file, "r", encoding="utf-8") as f:
                seed_data = f.read()
        st.download_button(
            label="⬇️ Baixar mongodb_seed.json",
            data=seed_data,
            file_name="mongodb_seed.json",
            mime="application/json"
        )

