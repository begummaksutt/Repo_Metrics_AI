"""
Streamlit Dashboard Modülü

İnteraktif GitHub kalite analiz dashboard'u.
Özellikler:
- GitHub profil fotoğrafları ile contributor kartları
- Hover'da GitHub profil önizleme
- Dinamik grafikler ve filtreler
- Gerçek zamanlı metrik hesaplama

Çalıştırma: streamlit run analytics/dashboard.py
"""

import streamlit as st
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import Any
import sys
import os
from dotenv import load_dotenv
load_dotenv()

# API Keys from .env
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Modül yolunu ekle
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analytics.utils import GitHubClient, analyze_repository, parse_github_url
from analytics.llm import generate_quality_report, generate_improvement_suggestions, LLMClient

# Sayfa ayarları
st.set_page_config(
    page_title="GitHub Kalite Analizi",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS - GitHub hover kartları için
st.markdown("""
<style>
    /* Ana tema */
    .stApp {
        background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
    }
    
    /* Başlık stilleri */
    .main-title {
        background: linear-gradient(90deg, #6366f1, #8b5cf6, #a855f7);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3rem;
        font-weight: 800;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    
    .subtitle {
        color: #94a3b8;
        text-align: center;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }
    
    /* Contributor kartları */
    .contributor-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
        gap: 1.5rem;
        padding: 1rem 0;
    }
    
    .contributor-card {
        position: relative;
        background: linear-gradient(145deg, #1e293b, #334155);
        border-radius: 16px;
        padding: 1.5rem;
        text-align: center;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        border: 1px solid rgba(99, 102, 241, 0.2);
        cursor: pointer;
    }
    
    .contributor-card:hover {
        transform: translateY(-8px);
        box-shadow: 0 20px 40px rgba(99, 102, 241, 0.3);
        border-color: #6366f1;
    }
    
    .contributor-card:hover .github-preview {
        opacity: 1;
        visibility: visible;
        transform: translateX(-50%) translateY(0);
    }
    
    .avatar-container {
        position: relative;
        width: 80px;
        height: 80px;
        margin: 0 auto 1rem;
    }
    
    .avatar {
        width: 80px;
        height: 80px;
        border-radius: 50%;
        border: 3px solid #6366f1;
        object-fit: cover;
        transition: transform 0.3s ease;
    }
    
    .contributor-card:hover .avatar {
        transform: scale(1.1);
        border-color: #a855f7;
    }
    
    .contributor-name {
        color: #f1f5f9;
        font-size: 1.1rem;
        font-weight: 600;
        margin-bottom: 0.5rem;
    }
    
    .contributor-stats {
        color: #94a3b8;
        font-size: 0.9rem;
    }
    
    .contribution-count {
        color: #6366f1;
        font-weight: 700;
        font-size: 1.5rem;
    }
    
    .contribution-label {
        color: #64748b;
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    /* GitHub Preview Popup */
    .github-preview {
        position: absolute;
        bottom: 100%;
        left: 50%;
        transform: translateX(-50%) translateY(10px);
        background: #0d1117;
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 1rem;
        width: 280px;
        opacity: 0;
        visibility: hidden;
        transition: all 0.3s ease;
        z-index: 1000;
        box-shadow: 0 16px 48px rgba(0,0,0,0.5);
    }
    
    .github-preview::after {
        content: '';
        position: absolute;
        top: 100%;
        left: 50%;
        transform: translateX(-50%);
        border: 8px solid transparent;
        border-top-color: #30363d;
    }
    
    .preview-header {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        margin-bottom: 0.75rem;
    }
    
    .preview-avatar {
        width: 48px;
        height: 48px;
        border-radius: 50%;
    }
    
    .preview-info h4 {
        color: #f0f6fc;
        font-size: 1rem;
        margin: 0;
    }
    
    .preview-info p {
        color: #8b949e;
        font-size: 0.85rem;
        margin: 0;
    }
    
    .preview-stats {
        display: flex;
        gap: 1rem;
        padding: 0.75rem 0;
        border-top: 1px solid #30363d;
        border-bottom: 1px solid #30363d;
        margin: 0.75rem 0;
    }
    
    .preview-stat {
        text-align: center;
        flex: 1;
    }
    
    .preview-stat-value {
        color: #f0f6fc;
        font-weight: 600;
        font-size: 1.1rem;
    }
    
    .preview-stat-label {
        color: #8b949e;
        font-size: 0.75rem;
    }
    
    .view-github-btn {
        display: block;
        background: #238636;
        color: white !important;
        text-decoration: none;
        padding: 0.5rem 1rem;
        border-radius: 6px;
        text-align: center;
        font-size: 0.9rem;
        font-weight: 500;
        transition: background 0.2s;
    }
    
    .view-github-btn:hover {
        background: #2ea043;
        color: white !important;
    }
    
    /* Metrik kartları */
    .metric-card {
        background: linear-gradient(145deg, #1e293b, #334155);
        border-radius: 16px;
        padding: 1.5rem;
        border: 1px solid rgba(99, 102, 241, 0.2);
    }
    
    .metric-value {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(90deg, #6366f1, #a855f7);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    .metric-label {
        color: #94a3b8;
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    /* Progress bar */
    .progress-container {
        background: #1e293b;
        border-radius: 10px;
        height: 12px;
        overflow: hidden;
        margin-top: 0.5rem;
    }
    
    .progress-bar {
        height: 100%;
        border-radius: 10px;
        background: linear-gradient(90deg, #6366f1, #a855f7);
        transition: width 0.5s ease;
    }
    
    /* Grade badge */
    .grade-badge {
        display: inline-block;
        padding: 0.5rem 1.5rem;
        border-radius: 50px;
        font-size: 1.5rem;
        font-weight: 700;
        margin-top: 0.5rem;
    }
    
    .grade-a { background: linear-gradient(90deg, #10b981, #34d399); color: white; }
    .grade-b { background: linear-gradient(90deg, #6366f1, #8b5cf6); color: white; }
    .grade-c { background: linear-gradient(90deg, #f59e0b, #fbbf24); color: #1e293b; }
    .grade-d { background: linear-gradient(90deg, #ef4444, #f87171); color: white; }
    .grade-f { background: linear-gradient(90deg, #dc2626, #ef4444); color: white; }
    
    /* Sidebar */
    .css-1d391kg {
        background: #1e293b;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Grafik container */
    .chart-container {
        background: #1e293b;
        border-radius: 16px;
        padding: 1rem;
        border: 1px solid rgba(99, 102, 241, 0.2);
    }
</style>
""", unsafe_allow_html=True)


def render_contributor_card(contributor: dict[str, Any], rank: int) -> str:
    """
    GitHub profil kartı HTML'i oluşturur.
    Hover'da detaylı preview gösterir.
    """
    login = contributor.get("login", "Unknown")
    avatar_url = contributor.get("avatar_url", "https://github.com/ghost.png")
    html_url = contributor.get("html_url", f"https://github.com/{login}")
    contributions = contributor.get("contributions", 0)
    
    # Ek bilgiler (varsa)
    name = contributor.get("name", login)
    bio = contributor.get("bio", "GitHub Contributor")
    followers = contributor.get("followers", "-")
    repos = contributor.get("public_repos", "-")
    
    # Rank badge rengi
    rank_colors = {1: "#ffd700", 2: "#c0c0c0", 3: "#cd7f32"}
    rank_color = rank_colors.get(rank, "#6366f1")
    rank_emoji = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, f"#{rank}")
    
    return f"""
    <div class="contributor-card">
        <!-- GitHub Preview Popup -->
        <div class="github-preview">
            <div class="preview-header">
                <img src="{avatar_url}" class="preview-avatar" alt="{login}">
                <div class="preview-info">
                    <h4>{name}</h4>
                    <p>@{login}</p>
                </div>
            </div>
            <p style="color: #8b949e; font-size: 0.85rem; margin-bottom: 0.5rem;">
                {bio[:80] + '...' if len(str(bio)) > 80 else bio}
            </p>
            <div class="preview-stats">
                <div class="preview-stat">
                    <div class="preview-stat-value">{contributions}</div>
                    <div class="preview-stat-label">Commits</div>
                </div>
                <div class="preview-stat">
                    <div class="preview-stat-value">{followers}</div>
                    <div class="preview-stat-label">Followers</div>
                </div>
                <div class="preview-stat">
                    <div class="preview-stat-value">{repos}</div>
                    <div class="preview-stat-label">Repos</div>
                </div>
            </div>
            <a href="{html_url}" target="_blank" class="view-github-btn">
                🔗 View on GitHub
            </a>
        </div>
        
        <!-- Main Card Content -->
        <div style="position: absolute; top: 10px; right: 10px; 
                    background: {rank_color}; color: #1e293b; 
                    padding: 2px 10px; border-radius: 20px; 
                    font-weight: 700; font-size: 0.8rem;">
            {rank_emoji}
        </div>
        <div class="avatar-container">
            <img src="{avatar_url}" class="avatar" alt="{login}">
        </div>
        <div class="contributor-name">@{login}</div>
        <div class="contribution-count">{contributions}</div>
        <div class="contribution-label">contributions</div>
    </div>
    """


def render_contributors_grid(contributors: list[dict[str, Any]]) -> None:
    """Contributor grid'ini render eder."""
    if not contributors:
        st.warning("Contributor verisi bulunamadı.")
        return
    
    sorted_contributors = sorted(
        contributors,
        key=lambda x: x.get("contributions", 0),
        reverse=True
    )[:12]  # Top 12
    
    cards_html = '<div class="contributor-grid">'
    for i, contributor in enumerate(sorted_contributors, 1):
        cards_html += render_contributor_card(contributor, i)
    cards_html += '</div>'
    
    st.markdown(cards_html, unsafe_allow_html=True)


def render_metric_card(value: str, label: str, progress: float = None, delta: str = None) -> str:
    """Metrik kartı HTML'i."""
    progress_html = ""
    if progress is not None:
        progress_html = f"""
        <div class="progress-container">
            <div class="progress-bar" style="width: {min(100, progress)}%"></div>
        </div>
        """
    
    delta_html = ""
    if delta:
        delta_color = "#10b981" if delta.startswith("+") or delta.startswith("↑") else "#ef4444"
        delta_html = f'<div style="color: {delta_color}; font-size: 0.9rem;">{delta}</div>'
    
    return f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{value}</div>
        {delta_html}
        {progress_html}
    </div>
    """


def get_grade_class(grade: str) -> str:
    """Not için CSS class döndürür."""
    if grade.startswith('A'):
        return 'grade-a'
    elif grade.startswith('B'):
        return 'grade-b'
    elif grade.startswith('C'):
        return 'grade-c'
    elif grade.startswith('D'):
        return 'grade-d'
    return 'grade-f'




def main():
    """Ana dashboard fonksiyonu."""
    
    # Başlık
    st.markdown('<h1 class="main-title">📊 GitHub Kalite Analizi</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Repository kalite metriklerini analiz edin ve görselleştirin</p>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.markdown("### ⚙️ Ayarlar")
        
        repo_url = st.text_input(
            "GitHub Repository URL",
            placeholder="https://github.com/owner/repo",
            help="Analiz etmek istediğiniz repo URL'sini girin"
        )
        
        github_token = st.text_input(
            "GitHub Token (Opsiyonel)",
            type="password",
            help="Rate limit için personal access token"
        )
        
        analyze_btn = st.button("🔍 Analiz Et", type="primary", use_container_width=True)
        
        st.markdown("---")
        
        # Tarih filtresi
        st.markdown("### 📅 Tarih Aralığı")
        date_range = st.selectbox(
            "Dönem",
            ["Son 7 gün", "Son 30 gün", "Son 90 gün", "Tüm zamanlar"],
            index=1
        )
        
        st.markdown("---")
        st.markdown("""
        ### 📖 Kullanım
        1. GitHub repo URL'sini girin
        2. Analiz Et butonuna tıklayın
        3. Metrikleri inceleyin
        
        **İpucu:** Özel repolar için token gerekir.
        """)
    
    # Demo verileri (API çağrısı olmadan)
    demo_contributors = [
        {"login": "torvalds", "avatar_url": "https://avatars.githubusercontent.com/u/1024025", 
         "contributions": 1250, "html_url": "https://github.com/torvalds",
         "name": "Linus Torvalds", "bio": "Linux kernel developer", "followers": 180000, "public_repos": 7},
        {"login": "gaearon", "avatar_url": "https://avatars.githubusercontent.com/u/810438", 
         "contributions": 890, "html_url": "https://github.com/gaearon",
         "name": "Dan Abramov", "bio": "Working on React", "followers": 75000, "public_repos": 250},
        {"login": "sindresorhus", "avatar_url": "https://avatars.githubusercontent.com/u/170270", 
         "contributions": 750, "html_url": "https://github.com/sindresorhus",
         "name": "Sindre Sorhus", "bio": "Full-Time Open-Sourcerer", "followers": 50000, "public_repos": 1100},
        {"login": "tj", "avatar_url": "https://avatars.githubusercontent.com/u/25254", 
         "contributions": 620, "html_url": "https://github.com/tj",
         "name": "TJ Holowaychuk", "bio": "Founder of Apex", "followers": 35000, "public_repos": 280},
        {"login": "yyx990803", "avatar_url": "https://avatars.githubusercontent.com/u/499550", 
         "contributions": 580, "html_url": "https://github.com/yyx990803",
         "name": "Evan You", "bio": "Creator of Vue.js", "followers": 85000, "public_repos": 150},
        {"login": "getify", "avatar_url": "https://avatars.githubusercontent.com/u/150330", 
         "contributions": 420, "html_url": "https://github.com/getify",
         "name": "Kyle Simpson", "bio": "Author of YDKJS", "followers": 28000, "public_repos": 90},
    ]
    
    # Session state
    if "analysis" not in st.session_state:
        st.session_state.analysis = None
    if "llm_report" not in st.session_state:
        st.session_state.llm_report = None
    if "suggestions" not in st.session_state:
        st.session_state.suggestions = None
    
    # Analiz butonu
    if analyze_btn and repo_url:
        with st.spinner("🔄 Veriler çekiliyor ve analiz ediliyor..."):
            st.session_state.analysis = analyze_repository(repo_url, token=github_token)
            
            # LLM Raporu üret (analiz başarılıysa)
            if st.session_state.analysis and st.session_state.analysis.get("success"):
                with st.spinner("🤖 LLM raporu oluşturuluyor..."):
                    # Gemini API key varsa gemini kullan, yoksa mock
                    llm_provider = "gemini" if GOOGLE_API_KEY else "mock"
                    st.session_state.llm_report = generate_quality_report(
                        st.session_state.analysis,
                        provider=llm_provider,
                        api_key=GOOGLE_API_KEY
                    )
                    st.session_state.suggestions = generate_improvement_suggestions(
                        st.session_state.analysis
                    )
    
    # Veri varsa göster, yoksa demo
    analysis = st.session_state.analysis
    
    if analysis and not analysis.get("success"):
        st.error(f"❌ Hata: {analysis.get('error', 'Bilinmeyen hata')}")
        st.info("Demo veriler gösteriliyor...")
        contributors = demo_contributors
        use_demo = True
        metrics_data = None
    elif analysis and analysis.get("success"):
        contributors = analysis.get("contributors", [])
        metrics_data = analysis.get("metrics", {})
        overall_data = analysis.get("overall", {})
        trends_data = analysis.get("trends", {})
        repo_info = analysis.get("repository", {})
        use_demo = False
        
        # Repo bilgisi göster
        st.success(f"✅ **{repo_info.get('full_name', 'Repository')}** analiz edildi!")
    else:
        contributors = demo_contributors
        use_demo = True
        metrics_data = None
    
    if use_demo:
        st.info("💡 Demo modunda çalışıyor. Gerçek veriler için bir GitHub repo URL'si girin.")
    
    # Metrik kartları
    st.markdown("### 📈 Özet Metrikler")
    
    # Gerçek veya demo metrikler
    if not use_demo and metrics_data:
        overall_score = overall_data.get("overall_score", 0)
        grade = overall_data.get("grade", "N/A")
        commit_freq = metrics_data.get("commit_frequency", {})
        test_ratio = metrics_data.get("test_ratio", {})
        issue_res = metrics_data.get("issue_resolution", {})
        pr_rej = metrics_data.get("pr_rejection", {})
    else:
        overall_score = 78
        grade = "B+"
        commit_freq = {"raw": 4.2, "score": 65}
        test_ratio = {"raw": 0.23, "score": 23}
        issue_res = {"raw": 3.5, "score": 70}
        pr_rej = {"raw": 0.1, "score": 85}
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(render_metric_card(
            f"{overall_score:.0f}", "Genel Skor", progress=overall_score
        ), unsafe_allow_html=True)
    
    with col2:
        st.markdown(render_metric_card(
            grade, "Kalite Notu"
        ), unsafe_allow_html=True)
    
    with col3:
        commit_raw = commit_freq.get("raw", 0)
        commit_score = commit_freq.get("score", 0)
        st.markdown(render_metric_card(
            f"{commit_raw:.2f}", "Commit/Gün", progress=commit_score
        ), unsafe_allow_html=True)
    
    with col4:
        test_raw = test_ratio.get("raw", 0) * 100
        test_score = test_ratio.get("score", 0)
        st.markdown(render_metric_card(
            f"%{test_raw:.1f}", "Test Coverage", progress=test_score
        ), unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Contributor Grid
    st.markdown("### 👥 Top Contributors")
    st.markdown("*Profil kartlarının üzerine gelerek detayları görüntüleyin*")
    
    render_contributors_grid(contributors)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Grafikler
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.markdown("### 📊 Efor Dağılımı")
        
        # Import visualization
        try:
            from analytics.visualization import create_effort_pie_chart
            fig = create_effort_pie_chart(contributors)
        except Exception as e:
            # Fallback
            import plotly.express as px
            names = [c.get("login") for c in contributors[:8]]
            values = [c.get("contributions", 0) for c in contributors[:8]]
            fig = px.pie(values=values, names=names, hole=0.5)
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#94a3b8")
            )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with col_right:
        st.markdown("### 🎯 Kalite Metrikleri")
        
        # Radar chart - gerçek veya demo metrikler
        if not use_demo and metrics_data:
            radar_metrics = {
                "commit_frequency": metrics_data.get("commit_frequency", {}).get("score", 0),
                "issue_resolution": metrics_data.get("issue_resolution", {}).get("score", 0),
                "pr_rejection": metrics_data.get("pr_rejection", {}).get("score", 0),
                "test_ratio": metrics_data.get("test_ratio", {}).get("score", 0)
            }
        else:
            radar_metrics = {
                "commit_frequency": 75,
                "issue_resolution": 60,
                "pr_rejection": 85,
                "test_ratio": 45
            }
        
        try:
            from analytics.visualization import create_quality_radar_chart
            fig = create_quality_radar_chart(radar_metrics)
        except Exception as e:
            fig = go.Figure(data=go.Scatterpolar(
                r=list(radar_metrics.values()) + [list(radar_metrics.values())[0]],
                theta=['Commit', 'Issue', 'PR', 'Test', 'Commit'],
                fill='toself',
                fillcolor='rgba(99, 102, 241, 0.3)',
                line=dict(color='#6366f1')
            ))
            fig.update_layout(
                polar=dict(
                    radialaxis=dict(visible=True, range=[0, 100]),
                    bgcolor="rgba(0,0,0,0)"
                ),
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#94a3b8")
            )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Commit Heatmap
    st.markdown("### 📅 Commit Aktivitesi")
    
    try:
        from analytics.visualization import create_commit_heatmap
        
        # Gerçek commit verisi varsa kullan
        if not use_demo and analysis and analysis.get("success"):
            # Commits trends verisinden al
            commit_trend = analysis.get("trends", {}).get("commit_trend", {})
            time_series = commit_trend.get("time_series", [])
            
            # Dummy commits oluştur (heatmap için)
            commits_for_heatmap = []
            for entry in time_series:
                date = entry.get("date", "")
                count = entry.get("count", 0)
                for _ in range(count):
                    commits_for_heatmap.append({
                        "commit": {"author": {"date": f"{date}T12:00:00Z"}}
                    })
            
            if commits_for_heatmap:
                fig = create_commit_heatmap(commits_for_heatmap)
            else:
                raise ValueError("No commits")
        else:
            raise ValueError("Demo mode")
            
    except Exception as e:
        # Demo heatmap
        import random
        days = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]
        weeks = [f"Hafta {i}" for i in range(1, 13)]
        z = [[random.randint(0, 8) for _ in weeks] for _ in days]
        
        fig = go.Figure(data=go.Heatmap(
            z=z, x=weeks, y=days,
            colorscale=[[0, "#ebedf0"], [0.25, "#9be9a8"], [0.5, "#40c463"], [0.75, "#30a14e"], [1, "#216e39"]],
            xgap=3, ygap=3
        ))
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#94a3b8"),
            height=250
        )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Ek metrik detayları (gerçek veri varsa)
    if not use_demo and analysis and analysis.get("success"):
        st.markdown("### 📋 Detaylı Analiz")
        
        stats = analysis.get("stats", {})
        trends = analysis.get("trends", {})
        
        detail_col1, detail_col2, detail_col3 = st.columns(3)
        
        with detail_col1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">📝 Toplam Commit (90 gün)</div>
                <div class="metric-value">{stats.get('total_commits', 0)}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with detail_col2:
            commit_trend = trends.get("commit_trend", {})
            trend_dir = commit_trend.get("trend_direction", "sabit")
            trend_emoji = {"artan": "📈", "azalan": "📉", "sabit": "➡️"}.get(trend_dir, "➡️")
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">📊 Commit Trendi</div>
                <div class="metric-value">{trend_emoji} {trend_dir.capitalize()}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with detail_col3:
            issue_trend = trends.get("issue_trend", {})
            issue_dir = issue_trend.get("trend_direction", "sabit")
            issue_emoji = {"iyileşiyor": "✅", "kötüleşiyor": "⚠️", "sabit": "➡️"}.get(issue_dir, "➡️")
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">🐛 Issue Trendi</div>
                <div class="metric-value">{issue_emoji} {issue_dir.capitalize()}</div>
            </div>
            """, unsafe_allow_html=True)
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #64748b; padding: 1rem;">
        <p>🚀 GitHub Kalite Analiz Dashboard v1.0</p>
        <p style="font-size: 0.8rem;">Built with Streamlit & Plotly</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()

