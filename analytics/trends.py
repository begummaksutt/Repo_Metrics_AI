"""
Trend Analizi Modülü

Bu modül, GitHub repository verilerinin zaman içindeki
değişimini analiz eder:
- Commit sıklığı trendi
- Issue çözüm süresi trendi
- Hareketli ortalama (MA) hesaplamaları
- Linear regression ile eğim analizi
"""

from datetime import datetime, timedelta
from typing import Any
from collections import defaultdict


def _parse_datetime(date_str: str | datetime) -> datetime:
    """
    String veya datetime objesini datetime'a çevirir.
    
    Args:
        date_str: ISO format tarih string'i veya datetime objesi
        
    Returns:
        datetime objesi
    """
    if isinstance(date_str, datetime):
        return date_str
    
    # ISO format: 2024-01-15T10:30:00Z
    date_str = date_str.replace('Z', '+00:00')
    try:
        return datetime.fromisoformat(date_str)
    except ValueError:
        # Alternatif formatları dene
        for fmt in ['%Y-%m-%dT%H:%M:%S', '%Y-%m-%d']:
            try:
                return datetime.strptime(date_str.split('+')[0], fmt)
            except ValueError:
                continue
    return datetime.now()


def _calculate_moving_average(values: list[float], window: int = 7) -> list[float]:
    """
    Hareketli ortalama hesaplar.
    
    Args:
        values: Değerler listesi
        window: Pencere boyutu (varsayılan 7 gün)
        
    Returns:
        Hareketli ortalama listesi
    """
    if not values or window <= 0:
        return []
    
    if len(values) < window:
        # Pencereden küçükse, kümülatif ortalama kullan
        result = []
        cumsum = 0.0
        for i, val in enumerate(values):
            cumsum += val
            result.append(cumsum / (i + 1))
        return result
    
    # Hareketli ortalama hesapla
    result = []
    window_sum = sum(values[:window])
    result.append(window_sum / window)
    
    for i in range(window, len(values)):
        window_sum = window_sum - values[i - window] + values[i]
        result.append(window_sum / window)
    
    # Başlangıç değerlerini de ekle (partial window)
    prefix = []
    cumsum = 0.0
    for i in range(min(window - 1, len(values))):
        cumsum += values[i]
        prefix.append(cumsum / (i + 1))
    
    return prefix + result


def _calculate_linear_regression(x: list[float], y: list[float]) -> dict[str, float]:
    """
    Basit linear regression hesaplar (y = mx + b).
    
    Args:
        x: Bağımsız değişken (zaman indeksi)
        y: Bağımlı değişken (değerler)
        
    Returns:
        {"slope": eğim, "intercept": kesişim, "r_squared": R² değeri}
    """
    n = len(x)
    
    if n < 2:
        return {"slope": 0.0, "intercept": 0.0, "r_squared": 0.0}
    
    # Ortalamalar
    mean_x = sum(x) / n
    mean_y = sum(y) / n
    
    # Varyans ve kovaryans
    ss_xx = sum((xi - mean_x) ** 2 for xi in x)
    ss_yy = sum((yi - mean_y) ** 2 for yi in y)
    ss_xy = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
    
    # Eğim ve kesişim
    if ss_xx == 0:
        slope = 0.0
        intercept = mean_y
    else:
        slope = ss_xy / ss_xx
        intercept = mean_y - slope * mean_x
    
    # R² (determinasyon katsayısı)
    if ss_yy == 0:
        r_squared = 1.0 if ss_xy == 0 else 0.0
    else:
        r_squared = (ss_xy ** 2) / (ss_xx * ss_yy) if ss_xx > 0 else 0.0
    
    return {
        "slope": round(slope, 6),
        "intercept": round(intercept, 4),
        "r_squared": round(r_squared, 4)
    }


def _get_trend_direction(slope: float, threshold: float = 0.01) -> str:
    """
    Eğime göre trend yönünü belirler.
    
    Args:
        slope: Hesaplanan eğim değeri
        threshold: Eşik değeri (bu değerin altındaki eğimler "sabit" kabul edilir)
        
    Returns:
        "artan", "azalan" veya "sabit"
    """
    if slope > threshold:
        return "artan"
    elif slope < -threshold:
        return "azalan"
    else:
        return "sabit"


def _get_trend_strength(r_squared: float) -> str:
    """
    R² değerine göre trend gücünü belirler.
    
    Args:
        r_squared: Determinasyon katsayısı
        
    Returns:
        "güçlü", "orta", "zayıf" veya "belirsiz"
    """
    if r_squared >= 0.7:
        return "güçlü"
    elif r_squared >= 0.4:
        return "orta"
    elif r_squared >= 0.2:
        return "zayıf"
    else:
        return "belirsiz"


def compute_commit_trend(commits: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Commit sıklığı trendini hesaplar.
    
    - Timestamp listesi üzerinden zaman serisi oluşturur
    - 7 günlük hareketli ortalama (MA7) hesaplar
    - Linear regression ile slope (eğim) hesaplar
    - Trendin artan/azalan/sabit olduğunu belirler
    
    Args:
        commits: GitHub API'den gelen commit listesi
        
    Returns:
        {
            "time_series": günlük commit sayıları,
            "moving_average": MA7 değerleri,
            "regression": {slope, intercept, r_squared},
            "trend_direction": "artan" | "azalan" | "sabit",
            "trend_strength": "güçlü" | "orta" | "zayıf" | "belirsiz",
            "summary": özet metin
        }
    """
    if not commits:
        return {
            "time_series": [],
            "moving_average": [],
            "regression": {"slope": 0.0, "intercept": 0.0, "r_squared": 0.0},
            "trend_direction": "sabit",
            "trend_strength": "belirsiz",
            "summary": "Yeterli commit verisi yok."
        }
    
    # Commit tarihlerini çıkar
    dates = []
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
            dates.append(_parse_datetime(date))
    
    if len(dates) < 2:
        return {
            "time_series": [{"date": dates[0].strftime("%Y-%m-%d"), "count": 1}] if dates else [],
            "moving_average": [1.0] if dates else [],
            "regression": {"slope": 0.0, "intercept": 0.0, "r_squared": 0.0},
            "trend_direction": "sabit",
            "trend_strength": "belirsiz",
            "summary": "Trend analizi için yeterli veri yok."
        }
    
    # Tarihleri sırala ve günlük commit sayısını hesapla
    dates.sort()
    daily_counts: dict[str, int] = defaultdict(int)
    
    for date in dates:
        day_key = date.strftime("%Y-%m-%d")
        daily_counts[day_key] += 1
    
    # Tüm günleri dahil et (commit olmayan günler = 0)
    start_date = min(dates).date()
    end_date = max(dates).date()
    
    time_series = []
    current_date = start_date
    
    while current_date <= end_date:
        day_key = current_date.strftime("%Y-%m-%d")
        count = daily_counts.get(day_key, 0)
        time_series.append({
            "date": day_key,
            "count": count
        })
        current_date += timedelta(days=1)
    
    # Değerler listesi
    values = [entry["count"] for entry in time_series]
    
    # Hareketli ortalama (MA7)
    ma7 = _calculate_moving_average(values, window=7)
    
    # Linear regression
    x = list(range(len(values)))
    regression = _calculate_linear_regression(x, values)
    
    # Trend yönü ve gücü
    trend_direction = _get_trend_direction(regression["slope"])
    trend_strength = _get_trend_strength(regression["r_squared"])
    
    # Özet metin
    avg_commits = sum(values) / len(values) if values else 0
    direction_text = {
        "artan": "artış gösteriyor",
        "azalan": "düşüş gösteriyor",
        "sabit": "sabit seyrediyor"
    }
    
    summary = (
        f"Günlük ortalama {avg_commits:.1f} commit. "
        f"Trend {trend_strength} şekilde {direction_text[trend_direction]}. "
        f"(Eğim: {regression['slope']:.4f}, R²: {regression['r_squared']:.2f})"
    )
    
    # MA7 değerlerini time series ile eşleştir
    ma7_series = []
    for i, entry in enumerate(time_series):
        ma7_series.append({
            "date": entry["date"],
            "ma7": round(ma7[i], 2) if i < len(ma7) else None
        })
    
    return {
        "time_series": time_series,
        "moving_average": ma7_series,
        "daily_values": values,
        "ma7_values": [round(v, 2) for v in ma7],
        "regression": regression,
        "trend_direction": trend_direction,
        "trend_strength": trend_strength,
        "average_daily_commits": round(avg_commits, 2),
        "total_days": len(time_series),
        "summary": summary
    }


def compute_issue_trend(issues: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Issue çözüm süresi trendini hesaplar.
    
    - Issue çözüm süresinin zaman içinde nasıl değiştiğini analiz eder
    - Linear regression ile trend eğimini hesaplar
    - Çözüm süresi azalıyorsa = iyileşme, artıyorsa = kötüleşme
    
    Args:
        issues: GitHub API'den gelen issue listesi
        
    Returns:
        {
            "resolution_series": çözüm süreleri zaman serisi,
            "moving_average": MA7 değerleri,
            "regression": {slope, intercept, r_squared},
            "trend_direction": "iyileşiyor" | "kötüleşiyor" | "sabit",
            "trend_strength": "güçlü" | "orta" | "zayıf" | "belirsiz",
            "summary": özet metin
        }
    """
    if not issues:
        return {
            "resolution_series": [],
            "moving_average": [],
            "regression": {"slope": 0.0, "intercept": 0.0, "r_squared": 0.0},
            "trend_direction": "sabit",
            "trend_strength": "belirsiz",
            "summary": "Yeterli issue verisi yok."
        }
    
    # Kapatılmış issue'ları çözüm süreleriyle birlikte topla
    resolved_issues = []
    
    for issue in issues:
        if not isinstance(issue, dict):
            continue
        
        state = issue.get('state', '').lower()
        if state != 'closed':
            continue
        
        created_at = issue.get('created_at')
        closed_at = issue.get('closed_at')
        
        if created_at and closed_at:
            created = _parse_datetime(created_at)
            closed = _parse_datetime(closed_at)
            
            resolution_hours = (closed - created).total_seconds() / 3600
            resolution_days = resolution_hours / 24
            
            resolved_issues.append({
                "closed_date": closed,
                "resolution_days": max(0, resolution_days),
                "resolution_hours": max(0, resolution_hours)
            })
    
    if len(resolved_issues) < 2:
        return {
            "resolution_series": resolved_issues,
            "moving_average": [],
            "regression": {"slope": 0.0, "intercept": 0.0, "r_squared": 0.0},
            "trend_direction": "sabit",
            "trend_strength": "belirsiz",
            "summary": "Trend analizi için yeterli çözülmüş issue yok."
        }
    
    # Kapatılma tarihine göre sırala
    resolved_issues.sort(key=lambda x: x["closed_date"])
    
    # Zaman serisi oluştur
    resolution_series = []
    values = []
    
    for issue in resolved_issues:
        resolution_series.append({
            "date": issue["closed_date"].strftime("%Y-%m-%d"),
            "resolution_days": round(issue["resolution_days"], 2),
            "resolution_hours": round(issue["resolution_hours"], 1)
        })
        values.append(issue["resolution_days"])
    
    # Hareketli ortalama (MA7 veya mevcut veri sayısı kadar)
    window = min(7, len(values))
    ma = _calculate_moving_average(values, window=window)
    
    # Linear regression
    x = list(range(len(values)))
    regression = _calculate_linear_regression(x, values)
    
    # Trend yönü (issue için tersine çevir: negatif eğim = iyileşme)
    slope = regression["slope"]
    
    if slope < -0.01:
        trend_direction = "iyileşiyor"  # Çözüm süresi azalıyor
    elif slope > 0.01:
        trend_direction = "kötüleşiyor"  # Çözüm süresi artıyor
    else:
        trend_direction = "sabit"
    
    trend_strength = _get_trend_strength(regression["r_squared"])
    
    # İstatistikler
    avg_resolution = sum(values) / len(values) if values else 0
    min_resolution = min(values) if values else 0
    max_resolution = max(values) if values else 0
    
    # Özet metin
    direction_text = {
        "iyileşiyor": "azalma eğiliminde (iyileşiyor)",
        "kötüleşiyor": "artma eğiliminde (kötüleşiyor)",
        "sabit": "sabit seyrediyor"
    }
    
    summary = (
        f"Ortalama çözüm süresi: {avg_resolution:.1f} gün. "
        f"Çözüm süreleri {trend_strength} şekilde {direction_text[trend_direction]}. "
        f"(Min: {min_resolution:.1f}, Max: {max_resolution:.1f} gün)"
    )
    
    # MA değerlerini series ile eşleştir
    ma_series = []
    for i, entry in enumerate(resolution_series):
        ma_series.append({
            "date": entry["date"],
            "ma": round(ma[i], 2) if i < len(ma) else None
        })
    
    return {
        "resolution_series": resolution_series,
        "moving_average": ma_series,
        "resolution_values": [round(v, 2) for v in values],
        "ma_values": [round(v, 2) for v in ma],
        "regression": regression,
        "trend_direction": trend_direction,
        "trend_strength": trend_strength,
        "statistics": {
            "average_days": round(avg_resolution, 2),
            "min_days": round(min_resolution, 2),
            "max_days": round(max_resolution, 2),
            "total_resolved": len(resolved_issues)
        },
        "summary": summary
    }


def compute_weekly_summary(
    commits: list[dict[str, Any]],
    issues: list[dict[str, Any]]
) -> dict[str, Any]:
    """
    Haftalık özet trend raporu oluşturur.
    
    Args:
        commits: Commit listesi
        issues: Issue listesi
        
    Returns:
        Haftalık bazda özet istatistikler
    """
    # Commit trendini hesapla
    commit_trend = compute_commit_trend(commits)
    issue_trend = compute_issue_trend(issues)
    
    # Haftalık gruplandırma
    weekly_commits: dict[str, int] = defaultdict(int)
    
    for entry in commit_trend.get("time_series", []):
        date = datetime.strptime(entry["date"], "%Y-%m-%d")
        week_key = date.strftime("%Y-W%W")
        weekly_commits[week_key] += entry["count"]
    
    # Haftalık commit listesi
    weekly_summary = []
    for week, count in sorted(weekly_commits.items()):
        weekly_summary.append({
            "week": week,
            "commits": count
        })
    
    return {
        "commit_trend": commit_trend,
        "issue_trend": issue_trend,
        "weekly_commits": weekly_summary,
        "overall_health": _calculate_health_indicator(commit_trend, issue_trend)
    }


def _calculate_health_indicator(
    commit_trend: dict[str, Any],
    issue_trend: dict[str, Any]
) -> dict[str, Any]:
    """
    Genel proje sağlık göstergesi hesaplar.
    """
    commit_direction = commit_trend.get("trend_direction", "sabit")
    issue_direction = issue_trend.get("trend_direction", "sabit")
    
    # Skor hesaplama
    score = 50  # Başlangıç
    
    # Commit trendi
    if commit_direction == "artan":
        score += 15
    elif commit_direction == "azalan":
        score -= 10
    
    # Issue trendi
    if issue_direction == "iyileşiyor":
        score += 15
    elif issue_direction == "kötüleşiyor":
        score -= 15
    
    # Trend gücü bonusu
    commit_strength = commit_trend.get("trend_strength", "belirsiz")
    issue_strength = issue_trend.get("trend_strength", "belirsiz")
    
    if commit_strength == "güçlü" and commit_direction == "artan":
        score += 10
    if issue_strength == "güçlü" and issue_direction == "iyileşiyor":
        score += 10
    
    # Sınırla
    score = max(0, min(100, score))
    
    # Durum belirleme
    if score >= 70:
        status = "sağlıklı"
        emoji = "✅"
    elif score >= 50:
        status = "stabil"
        emoji = "➖"
    elif score >= 30:
        status = "dikkat"
        emoji = "⚠️"
    else:
        status = "kritik"
        emoji = "🚨"
    
    return {
        "score": score,
        "status": status,
        "emoji": emoji,
        "factors": {
            "commit_trend": commit_direction,
            "issue_trend": issue_direction
        }
    }


# Test amaçlı örnek kullanım
if __name__ == "__main__":
    from datetime import datetime, timedelta
    
    # Örnek commit verisi (son 30 gün)
    sample_commits = []
    base_date = datetime.now() - timedelta(days=30)
    
    # Artan trend simülasyonu
    for i in range(30):
        commit_date = base_date + timedelta(days=i)
        # Her gün 1-3 commit (zamanla artış)
        num_commits = 1 + (i // 10)
        for _ in range(num_commits):
            sample_commits.append({
                "commit": {
                    "author": {
                        "date": commit_date.isoformat() + "Z"
                    }
                }
            })
    
    # Örnek issue verisi
    sample_issues = []
    for i in range(20):
        created = base_date + timedelta(days=i)
        # Çözüm süresi zamanla azalıyor (iyileşme)
        resolution_days = 5 - (i * 0.15)
        closed = created + timedelta(days=max(0.5, resolution_days))
        
        sample_issues.append({
            "state": "closed",
            "created_at": created.isoformat() + "Z",
            "closed_at": closed.isoformat() + "Z"
        })
    
    print("=== Commit Trend Analizi ===\n")
    commit_result = compute_commit_trend(sample_commits)
    print(f"Trend Yönü: {commit_result['trend_direction']}")
    print(f"Trend Gücü: {commit_result['trend_strength']}")
    print(f"Özet: {commit_result['summary']}")
    
    print("\n=== Issue Trend Analizi ===\n")
    issue_result = compute_issue_trend(sample_issues)
    print(f"Trend Yönü: {issue_result['trend_direction']}")
    print(f"Trend Gücü: {issue_result['trend_strength']}")
    print(f"Özet: {issue_result['summary']}")
    
    print("\n=== Haftalık Özet ===\n")
    weekly = compute_weekly_summary(sample_commits, sample_issues)
    health = weekly["overall_health"]
    print(f"Proje Sağlığı: {health['emoji']} {health['status']} (Skor: {health['score']})")

