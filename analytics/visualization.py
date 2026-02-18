"""
Görselleştirme Modülü

Bu modül, GitHub repository kalite metriklerini
interaktif grafiklerle görselleştirir:
- Efor dağılımı (contributor bazlı)
- Commit aktivite heatmap
- Test coverage gauge
- Trend line charts
"""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from typing import Any
from collections import defaultdict
import json


# Renk paleti
COLORS = {
    "primary": "#6366f1",      # Indigo
    "secondary": "#8b5cf6",    # Purple
    "success": "#10b981",      # Emerald
    "warning": "#f59e0b",      # Amber
    "danger": "#ef4444",       # Red
    "info": "#3b82f6",         # Blue
    "dark": "#1e293b",         # Slate 800
    "light": "#f8fafc",        # Slate 50
    "gradient": ["#6366f1", "#8b5cf6", "#a855f7", "#d946ef"],
}

# Grafik teması
CHART_THEME = {
    "paper_bgcolor": "rgba(0,0,0,0)",
    "plot_bgcolor": "rgba(0,0,0,0)",
    "font": {"family": "Inter, system-ui, sans-serif", "color": "#334155"},
}


def create_contributor_effort_chart(
    contributors: list[dict[str, Any]],
    show_avatars: bool = True
) -> go.Figure:
    """
    Contributor bazlı efor dağılımı grafiği oluşturur.
    
    GitHub profil fotoğrafları ile birlikte bar chart.
    Hover'da contributor detayları gösterilir.
    
    Args:
        contributors: Contributor listesi
            [{"login": "username", "avatar_url": "...", "contributions": 50, "html_url": "..."}, ...]
        show_avatars: Avatar gösterilsin mi
        
    Returns:
        Plotly Figure objesi
    """
    if not contributors:
        return _create_empty_chart("Contributor verisi bulunamadı")
    
    # Verileri hazırla
    sorted_contributors = sorted(
        contributors, 
        key=lambda x: x.get("contributions", 0), 
        reverse=True
    )[:10]  # Top 10
    
    names = [c.get("login", "Unknown") for c in sorted_contributors]
    contributions = [c.get("contributions", 0) for c in sorted_contributors]
    avatars = [c.get("avatar_url", "") for c in sorted_contributors]
    profile_urls = [c.get("html_url", f"https://github.com/{c.get('login', '')}") for c in sorted_contributors]
    
    total_contributions = sum(contributions)
    percentages = [round(c / total_contributions * 100, 1) if total_contributions > 0 else 0 for c in contributions]
    
    # Renk gradyanı
    colors = px.colors.sample_colorscale(
        "Viridis", 
        [i / len(names) for i in range(len(names))]
    )
    
    # Custom hover template
    hover_template = (
        "<b>%{customdata[0]}</b><br>"
        "<br>"
        "📊 Contribution: <b>%{y}</b><br>"
        "📈 Oran: <b>%{customdata[1]}%</b><br>"
        "<br>"
        "<i>Profili görüntülemek için tıklayın</i>"
        "<extra></extra>"
    )
    
    fig = go.Figure()
    
    # Bar chart
    fig.add_trace(go.Bar(
        x=names,
        y=contributions,
        marker=dict(
            color=colors,
            line=dict(color="rgba(255,255,255,0.3)", width=1),
            cornerradius=8
        ),
        customdata=list(zip(names, percentages, profile_urls)),
        hovertemplate=hover_template,
        text=[f"{p}%" for p in percentages],
        textposition="outside",
        textfont=dict(size=12, color="#64748b")
    ))
    
    # Layout
    fig.update_layout(
        title=dict(
            text="👥 Contributor Efor Dağılımı",
            font=dict(size=20, color="#1e293b"),
            x=0.5
        ),
        xaxis=dict(
            title="",
            tickangle=-45,
            tickfont=dict(size=11),
            gridcolor="rgba(0,0,0,0.05)"
        ),
        yaxis=dict(
            title="Contributions",
            gridcolor="rgba(0,0,0,0.05)",
            tickfont=dict(size=11)
        ),
        hoverlabel=dict(
            bgcolor="white",
            font_size=13,
            font_family="Inter, system-ui, sans-serif",
            bordercolor="#e2e8f0"
        ),
        **CHART_THEME,
        height=450,
        margin=dict(t=80, b=100, l=60, r=40),
        showlegend=False
    )
    
    # Avatar'ları annotation olarak ekle
    if show_avatars:
        for i, (name, avatar) in enumerate(zip(names, avatars)):
            if avatar:
                fig.add_layout_image(
                    dict(
                        source=avatar,
                        x=i,
                        y=-0.15,
                        xref="x",
                        yref="paper",
                        sizex=0.8,
                        sizey=0.12,
                        xanchor="center",
                        yanchor="top",
                        layer="above"
                    )
                )
    
    return fig


def create_effort_pie_chart(contributors: list[dict[str, Any]]) -> go.Figure:
    """
    Efor dağılımı pasta grafiği.
    
    Args:
        contributors: Contributor listesi
        
    Returns:
        Plotly Figure objesi
    """
    if not contributors:
        return _create_empty_chart("Contributor verisi bulunamadı")
    
    sorted_contributors = sorted(
        contributors,
        key=lambda x: x.get("contributions", 0),
        reverse=True
    )
    
    # Top 8 + Others
    top_contributors = sorted_contributors[:8]
    others = sorted_contributors[8:]
    
    labels = [c.get("login", "Unknown") for c in top_contributors]
    values = [c.get("contributions", 0) for c in top_contributors]
    avatars = [c.get("avatar_url", "") for c in top_contributors]
    
    if others:
        labels.append("Diğerleri")
        values.append(sum(c.get("contributions", 0) for c in others))
        avatars.append("")
    
    # Custom hover
    hover_template = (
        "<b>%{label}</b><br>"
        "Contributions: %{value}<br>"
        "Oran: %{percent}"
        "<extra></extra>"
    )
    
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.5,
        marker=dict(
            colors=px.colors.qualitative.Set3[:len(labels)],
            line=dict(color="white", width=2)
        ),
        textinfo="label+percent",
        textposition="outside",
        textfont=dict(size=11),
        hovertemplate=hover_template,
        pull=[0.02] * len(labels)
    )])
    
    fig.update_layout(
        title=dict(
            text="📊 Efor Dağılımı",
            font=dict(size=20, color="#1e293b"),
            x=0.5
        ),
        annotations=[
            dict(
                text=f"<b>{sum(values)}</b><br>Toplam",
                x=0.5, y=0.5,
                font_size=16,
                showarrow=False,
                font=dict(color="#64748b")
            )
        ],
        **CHART_THEME,
        height=450,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.2,
            xanchor="center",
            x=0.5
        )
    )
    
    return fig


def create_commit_heatmap(commits: list[dict[str, Any]], weeks: int = 12) -> go.Figure:
    """
    GitHub tarzı commit aktivite heatmap'i oluşturur.
    
    Args:
        commits: Commit listesi
        weeks: Gösterilecek hafta sayısı
        
    Returns:
        Plotly Figure objesi
    """
    if not commits:
        return _create_empty_chart("Commit verisi bulunamadı")
    
    # Commit tarihlerini çıkar
    commit_dates = []
    for commit in commits:
        date = None
        if isinstance(commit, dict):
            if 'commit' in commit and isinstance(commit['commit'], dict):
                author_info = commit['commit'].get('author', {})
                date = author_info.get('date')
            elif 'date' in commit:
                date = commit['date']
            elif 'created_at' in commit:
                date = commit['created_at']
        
        if date:
            if isinstance(date, str):
                date = date.replace('Z', '+00:00')
                try:
                    dt = datetime.fromisoformat(date.split('+')[0])
                    commit_dates.append(dt.date())
                except:
                    pass
            elif isinstance(date, datetime):
                commit_dates.append(date.date())
    
    if not commit_dates:
        return _create_empty_chart("Geçerli commit tarihi bulunamadı")
    
    # Günlük commit sayısını hesapla
    daily_counts = defaultdict(int)
    for d in commit_dates:
        daily_counts[d] += 1
    
    # Son N hafta için grid oluştur
    end_date = max(commit_dates)
    start_date = end_date - timedelta(weeks=weeks)
    
    # Haftanın günleri (Pazartesi=0, Pazar=6)
    days = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]
    
    # Grid verisi oluştur
    z_data = []
    x_labels = []
    hover_texts = []
    
    current_date = start_date
    # Pazartesi'ye hizala
    while current_date.weekday() != 0:
        current_date += timedelta(days=1)
    
    week_num = 0
    while current_date <= end_date:
        week_data = []
        week_hover = []
        
        for day in range(7):
            d = current_date + timedelta(days=day)
            count = daily_counts.get(d, 0)
            week_data.append(count)
            week_hover.append(f"{d.strftime('%d %b %Y')}<br>{count} commit")
        
        z_data.append(week_data)
        hover_texts.append(week_hover)
        x_labels.append(current_date.strftime("%d %b"))
        
        current_date += timedelta(weeks=1)
        week_num += 1
    
    # Transpose (günler satırlarda, haftalar sütunlarda)
    z_transposed = list(map(list, zip(*z_data)))
    hover_transposed = list(map(list, zip(*hover_texts)))
    
    # Renk skalası (GitHub tarzı)
    colorscale = [
        [0, "#ebedf0"],
        [0.25, "#9be9a8"],
        [0.5, "#40c463"],
        [0.75, "#30a14e"],
        [1, "#216e39"]
    ]
    
    fig = go.Figure(data=go.Heatmap(
        z=z_transposed,
        x=x_labels,
        y=days,
        colorscale=colorscale,
        showscale=True,
        hovertemplate="%{customdata}<extra></extra>",
        customdata=hover_transposed,
        xgap=3,
        ygap=3,
        colorbar=dict(
            title="Commits",
            tickvals=[0, max(max(row) for row in z_transposed) // 2, max(max(row) for row in z_transposed)],
            len=0.5,
            thickness=15
        )
    ))
    
    fig.update_layout(
        title=dict(
            text="📅 Commit Aktivite Haritası",
            font=dict(size=20, color="#1e293b"),
            x=0.5
        ),
        xaxis=dict(
            title="",
            side="top",
            tickangle=0,
            tickfont=dict(size=10)
        ),
        yaxis=dict(
            title="",
            tickfont=dict(size=11),
            autorange="reversed"
        ),
        **CHART_THEME,
        height=280,
        margin=dict(t=80, b=20, l=50, r=40)
    )
    
    return fig


def create_test_coverage_gauge(test_ratio: float, target: float = 0.3) -> go.Figure:
    """
    Test coverage gauge chart.
    
    Args:
        test_ratio: Test dosyası oranı (0-1)
        target: Hedef oran (varsayılan 0.3 = %30)
        
    Returns:
        Plotly Figure objesi
    """
    percentage = test_ratio * 100
    target_percentage = target * 100
    
    # Renk belirleme
    if percentage >= target_percentage:
        color = COLORS["success"]
        status = "✅ Hedef Aşıldı"
    elif percentage >= target_percentage * 0.7:
        color = COLORS["warning"]
        status = "⚠️ Hedefe Yakın"
    else:
        color = COLORS["danger"]
        status = "❌ İyileştirme Gerekli"
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=percentage,
        number={"suffix": "%", "font": {"size": 40, "color": "#1e293b"}},
        delta={
            "reference": target_percentage,
            "increasing": {"color": COLORS["success"]},
            "decreasing": {"color": COLORS["danger"]},
            "suffix": "%"
        },
        gauge={
            "axis": {
                "range": [0, 100],
                "tickwidth": 1,
                "tickcolor": "#e2e8f0",
                "tickvals": [0, 25, 50, 75, 100],
                "ticktext": ["0%", "25%", "50%", "75%", "100%"]
            },
            "bar": {"color": color, "thickness": 0.8},
            "bgcolor": "#f1f5f9",
            "borderwidth": 0,
            "steps": [
                {"range": [0, target_percentage * 0.7], "color": "#fee2e2"},
                {"range": [target_percentage * 0.7, target_percentage], "color": "#fef3c7"},
                {"range": [target_percentage, 100], "color": "#d1fae5"}
            ],
            "threshold": {
                "line": {"color": "#64748b", "width": 3},
                "thickness": 0.8,
                "value": target_percentage
            }
        },
        title={"text": f"🧪 Test Coverage<br><span style='font-size:14px;color:#64748b'>{status}</span>"}
    ))
    
    fig.update_layout(
        **CHART_THEME,
        height=300,
        margin=dict(t=80, b=20, l=30, r=30)
    )
    
    return fig


def create_trend_line_chart(
    time_series: list[dict[str, Any]],
    ma_series: list[dict[str, Any]] | None = None,
    title: str = "📈 Trend Analizi",
    y_label: str = "Değer"
) -> go.Figure:
    """
    Trend line chart with moving average.
    
    Args:
        time_series: [{"date": "2024-01-01", "value": 5}, ...]
        ma_series: Hareketli ortalama serisi
        title: Grafik başlığı
        y_label: Y ekseni etiketi
        
    Returns:
        Plotly Figure objesi
    """
    if not time_series:
        return _create_empty_chart("Trend verisi bulunamadı")
    
    dates = [entry.get("date", "") for entry in time_series]
    values = [entry.get("value", entry.get("count", 0)) for entry in time_series]
    
    fig = go.Figure()
    
    # Ana veri
    fig.add_trace(go.Scatter(
        x=dates,
        y=values,
        mode="lines+markers",
        name="Günlük",
        line=dict(color=COLORS["primary"], width=2),
        marker=dict(size=6, color=COLORS["primary"]),
        hovertemplate="<b>%{x}</b><br>%{y}<extra></extra>"
    ))
    
    # Hareketli ortalama
    if ma_series:
        ma_dates = [entry.get("date", "") for entry in ma_series]
        ma_values = [entry.get("ma7", entry.get("ma", 0)) for entry in ma_series]
        
        fig.add_trace(go.Scatter(
            x=ma_dates,
            y=ma_values,
            mode="lines",
            name="MA7",
            line=dict(color=COLORS["secondary"], width=3, dash="dot"),
            hovertemplate="<b>%{x}</b><br>MA7: %{y:.1f}<extra></extra>"
        ))
    
    # Trend çizgisi (linear regression)
    if len(values) >= 2:
        import numpy as np
        x_numeric = list(range(len(values)))
        z = np.polyfit(x_numeric, values, 1)
        p = np.poly1d(z)
        trend_values = [p(x) for x in x_numeric]
        
        fig.add_trace(go.Scatter(
            x=dates,
            y=trend_values,
            mode="lines",
            name="Trend",
            line=dict(color=COLORS["danger"], width=2, dash="dash"),
            opacity=0.7
        ))
    
    fig.update_layout(
        title=dict(
            text=title,
            font=dict(size=20, color="#1e293b"),
            x=0.5
        ),
        xaxis=dict(
            title="Tarih",
            gridcolor="rgba(0,0,0,0.05)",
            tickangle=-45
        ),
        yaxis=dict(
            title=y_label,
            gridcolor="rgba(0,0,0,0.05)"
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        hovermode="x unified",
        **CHART_THEME,
        height=400,
        margin=dict(t=80, b=80, l=60, r=40)
    )
    
    return fig


def create_quality_radar_chart(metrics: dict[str, float]) -> go.Figure:
    """
    Kalite metrikleri radar chart.
    
    Args:
        metrics: {"commit_frequency": 75, "test_ratio": 60, ...}
        
    Returns:
        Plotly Figure objesi
    """
    if not metrics:
        return _create_empty_chart("Metrik verisi bulunamadı")
    
    # Türkçe etiketler
    label_map = {
        "commit_frequency": "Commit Sıklığı",
        "issue_resolution": "Issue Çözümü",
        "pr_rejection": "PR Kalitesi",
        "test_ratio": "Test Coverage"
    }
    
    categories = [label_map.get(k, k) for k in metrics.keys()]
    values = list(metrics.values())
    
    # Kapatmak için ilk değeri sona ekle
    categories.append(categories[0])
    values.append(values[0])
    
    fig = go.Figure()
    
    # Radar alanı
    fig.add_trace(go.Scatterpolar(
        r=values,
        theta=categories,
        fill="toself",
        fillcolor=f"rgba(99, 102, 241, 0.3)",
        line=dict(color=COLORS["primary"], width=2),
        marker=dict(size=8, color=COLORS["primary"]),
        hovertemplate="<b>%{theta}</b><br>Skor: %{r}<extra></extra>"
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                tickvals=[20, 40, 60, 80, 100],
                gridcolor="rgba(0,0,0,0.1)"
            ),
            angularaxis=dict(
                gridcolor="rgba(0,0,0,0.1)"
            ),
            bgcolor="rgba(0,0,0,0)"
        ),
        title=dict(
            text="🎯 Kalite Metrikleri",
            font=dict(size=20, color="#1e293b"),
            x=0.5
        ),
        **CHART_THEME,
        height=400,
        margin=dict(t=80, b=40, l=80, r=80),
        showlegend=False
    )
    
    return fig


def create_weekly_comparison_chart(weekly_data: list[dict[str, Any]]) -> go.Figure:
    """
    Haftalık karşılaştırma bar chart.
    
    Args:
        weekly_data: [{"week": "2024-W01", "commits": 25}, ...]
        
    Returns:
        Plotly Figure objesi
    """
    if not weekly_data:
        return _create_empty_chart("Haftalık veri bulunamadı")
    
    weeks = [d.get("week", "") for d in weekly_data]
    commits = [d.get("commits", 0) for d in weekly_data]
    
    # Son haftayı vurgula
    colors = [COLORS["primary"]] * len(weeks)
    if len(colors) > 0:
        colors[-1] = COLORS["success"]
    
    fig = go.Figure(data=[go.Bar(
        x=weeks,
        y=commits,
        marker=dict(
            color=colors,
            cornerradius=6
        ),
        text=commits,
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>%{y} commit<extra></extra>"
    )])
    
    fig.update_layout(
        title=dict(
            text="📊 Haftalık Commit Dağılımı",
            font=dict(size=20, color="#1e293b"),
            x=0.5
        ),
        xaxis=dict(
            title="Hafta",
            tickangle=-45
        ),
        yaxis=dict(
            title="Commits",
            gridcolor="rgba(0,0,0,0.05)"
        ),
        **CHART_THEME,
        height=350,
        margin=dict(t=80, b=80, l=60, r=40)
    )
    
    return fig


def _create_empty_chart(message: str) -> go.Figure:
    """Boş veri için placeholder chart."""
    fig = go.Figure()
    fig.add_annotation(
        text=f"📭 {message}",
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
        showarrow=False,
        font=dict(size=16, color="#94a3b8")
    )
    fig.update_layout(
        **CHART_THEME,
        height=300,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False)
    )
    return fig


def export_charts_to_html(
    charts: dict[str, go.Figure],
    output_path: str = "report.html"
) -> str:
    """
    Tüm grafikleri tek bir HTML dosyasına export eder.
    
    Args:
        charts: {"chart_name": figure, ...}
        output_path: Çıktı dosya yolu
        
    Returns:
        Oluşturulan dosya yolu
    """
    html_content = """
    <!DOCTYPE html>
    <html lang="tr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>GitHub Kalite Analiz Raporu</title>
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Inter', system-ui, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 2rem;
            }
            .container {
                max-width: 1400px;
                margin: 0 auto;
            }
            h1 {
                color: white;
                text-align: center;
                margin-bottom: 2rem;
                font-size: 2.5rem;
                text-shadow: 0 2px 10px rgba(0,0,0,0.2);
            }
            .chart-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
                gap: 1.5rem;
            }
            .chart-card {
                background: white;
                border-radius: 16px;
                padding: 1.5rem;
                box-shadow: 0 10px 40px rgba(0,0,0,0.1);
                transition: transform 0.3s ease;
            }
            .chart-card:hover {
                transform: translateY(-5px);
            }
            .full-width {
                grid-column: 1 / -1;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📊 GitHub Kalite Analiz Raporu</h1>
            <div class="chart-grid">
    """
    
    for name, fig in charts.items():
        chart_html = fig.to_html(full_html=False, include_plotlyjs=False)
        full_width = "full-width" if name in ["heatmap", "trend"] else ""
        html_content += f"""
                <div class="chart-card {full_width}">
                    {chart_html}
                </div>
        """
    
    html_content += """
            </div>
        </div>
    </body>
    </html>
    """
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    return output_path


# Test
if __name__ == "__main__":
    # Örnek veri
    sample_contributors = [
        {"login": "ahmet", "avatar_url": "https://github.com/ahmet.png", "contributions": 150, "html_url": "https://github.com/ahmet"},
        {"login": "mehmet", "avatar_url": "https://github.com/mehmet.png", "contributions": 120, "html_url": "https://github.com/mehmet"},
        {"login": "ayse", "avatar_url": "https://github.com/ayse.png", "contributions": 85, "html_url": "https://github.com/ayse"},
    ]
    
    fig = create_contributor_effort_chart(sample_contributors)
    fig.show()

