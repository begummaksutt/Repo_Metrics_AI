"""
GitHub Repository Kalite Metrikleri Hesaplama Modülü

Bu modül, GitHub repository'lerinin kalite metriklerini hesaplar:
- Commit sıklığı
- Issue çözüm süresi
- PR reddetme oranı
- Test dosyası oranı
- Genel kalite skoru
"""

from datetime import datetime, timedelta
from typing import Any
import re


def _normalize_score(value: float, min_val: float, max_val: float, inverse: bool = False) -> float:
    """
    Değeri 0-100 aralığına normalize eder.
    
    Args:
        value: Normalize edilecek değer
        min_val: Minimum değer
        max_val: Maximum değer
        inverse: True ise, düşük değerler yüksek skor alır
        
    Returns:
        0-100 arasında normalize edilmiş skor
    """
    if max_val == min_val:
        return 50.0
    
    normalized = (value - min_val) / (max_val - min_val)
    normalized = max(0.0, min(1.0, normalized))  # 0-1 arasına sınırla
    
    if inverse:
        normalized = 1.0 - normalized
    
    return round(normalized * 100, 2)


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


def compute_commit_frequency(commits: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Commit sıklığını hesaplar ve normalize edilmiş skor döndürür.
    
    Girdi: GitHub commit listesi (her commit'te 'commit.author.date' veya 'date' alanı olmalı)
    Çıktı: 0-100 normalized score
    
    Formül:
        frequency = commits / zaman aralığı (gün başına commit)
        Min-max normalize (0.1 - 5.0 commit/gün arası ideal kabul edilir)
    
    Args:
        commits: GitHub API'den gelen commit listesi
        
    Returns:
        {"raw": günlük_commit_sayısı, "score": normalized_score, "total_commits": toplam_commit}
    """
    if not commits:
        return {"raw": 0.0, "score": 0.0, "total_commits": 0}
    
    # Commit tarihlerini çıkar
    dates = []
    for commit in commits:
        date = None
        if isinstance(commit, dict):
            # GitHub API formatı: commit.commit.author.date
            if 'commit' in commit and isinstance(commit['commit'], dict):
                author_info = commit['commit'].get('author', {})
                date = author_info.get('date')
            # Alternatif format: doğrudan date alanı
            elif 'date' in commit:
                date = commit['date']
            elif 'created_at' in commit:
                date = commit['created_at']
        
        if date:
            dates.append(_parse_datetime(date))
    
    if len(dates) < 2:
        # Tek commit varsa, makul bir skor ver
        return {"raw": 1.0, "score": 25.0, "total_commits": len(commits)}
    
    # Zaman aralığını hesapla
    dates.sort()
    time_span = (dates[-1] - dates[0]).days
    
    if time_span == 0:
        time_span = 1  # Aynı gün içinde yapılan commitler
    
    # Günlük commit sıklığı
    frequency = len(commits) / time_span
    
    # Normalize: 0.1-5.0 commit/gün arası ideal (min-max scaling)
    min_freq = 0.0
    max_freq = 5.0  # Günde 5 commit üstü = maksimum skor
    
    score = _normalize_score(frequency, min_freq, max_freq)
    
    return {
        "raw": round(frequency, 4),
        "score": score,
        "total_commits": len(commits),
        "time_span_days": time_span
    }


def compute_issue_resolution(issues: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Issue çözüm süresini hesaplar ve normalize edilmiş skor döndürür.
    
    Kapanan issue'ların ortalama çözüm zamanı
    Hızlı çözüm = yüksek skor
    
    Args:
        issues: GitHub API'den gelen issue listesi
        
    Returns:
        {"raw": ortalama_çözüm_günü, "score": normalized_score, "resolved_count": çözülen_issue_sayısı}
    """
    if not issues:
        return {"raw": 0.0, "score": 50.0, "resolved_count": 0, "total_issues": 0}
    
    resolution_times = []
    
    for issue in issues:
        if not isinstance(issue, dict):
            continue
        
        # Sadece kapatılmış issue'ları değerlendir
        state = issue.get('state', '').lower()
        if state != 'closed':
            continue
        
        created_at = issue.get('created_at')
        closed_at = issue.get('closed_at')
        
        if created_at and closed_at:
            created = _parse_datetime(created_at)
            closed = _parse_datetime(closed_at)
            
            resolution_days = (closed - created).total_seconds() / (24 * 3600)
            resolution_times.append(max(0, resolution_days))
    
    if not resolution_times:
        return {
            "raw": 0.0,
            "score": 50.0,  # Veri yoksa nötr skor
            "resolved_count": 0,
            "total_issues": len(issues)
        }
    
    # Ortalama çözüm süresi
    avg_resolution = sum(resolution_times) / len(resolution_times)
    
    # Normalize: 0-30 gün arası (inverse - düşük süre = yüksek skor)
    # 0 gün = 100 puan, 30+ gün = 0 puan
    min_days = 0.0
    max_days = 30.0  # 30 gün üstü = minimum skor
    
    score = _normalize_score(avg_resolution, min_days, max_days, inverse=True)
    
    return {
        "raw": round(avg_resolution, 2),
        "score": score,
        "resolved_count": len(resolution_times),
        "total_issues": len(issues)
    }


def compute_pr_rejection(prs: list[dict[str, Any]]) -> dict[str, Any]:
    """
    PR reddetme oranını hesaplar.
    
    PR reddetme oranı = closed_without_merge / total
    Yüksek red oranı = düşük kalite → düşük skor
    
    Args:
        prs: GitHub API'den gelen pull request listesi
        
    Returns:
        {"raw": red_oranı, "score": normalized_score, "rejected": reddedilen_sayısı, "merged": birleştirilen_sayısı}
    """
    if not prs:
        return {
            "raw": 0.0,
            "score": 50.0,  # Veri yoksa nötr skor
            "rejected": 0,
            "merged": 0,
            "total": 0
        }
    
    merged_count = 0
    rejected_count = 0
    open_count = 0
    
    for pr in prs:
        if not isinstance(pr, dict):
            continue
        
        state = pr.get('state', '').lower()
        merged = pr.get('merged', False) or pr.get('merged_at') is not None
        
        if state == 'open':
            open_count += 1
        elif merged:
            merged_count += 1
        elif state == 'closed':
            # Kapatılmış ama merge edilmemiş = reddedilmiş
            rejected_count += 1
    
    total_closed = merged_count + rejected_count
    
    if total_closed == 0:
        return {
            "raw": 0.0,
            "score": 50.0,
            "rejected": 0,
            "merged": 0,
            "open": open_count,
            "total": len(prs)
        }
    
    # Reddetme oranı
    rejection_rate = rejected_count / total_closed
    
    # Normalize: 0-0.5 arası (inverse - düşük red oranı = yüksek skor)
    # %0 red = 100 puan, %50+ red = 0 puan
    min_rate = 0.0
    max_rate = 0.5
    
    score = _normalize_score(rejection_rate, min_rate, max_rate, inverse=True)
    
    return {
        "raw": round(rejection_rate, 4),
        "score": score,
        "rejected": rejected_count,
        "merged": merged_count,
        "open": open_count,
        "total": len(prs)
    }


def compute_test_ratio(files: list[str | dict[str, Any]]) -> dict[str, Any]:
    """
    Test dosyası oranını hesaplar.
    
    Test dosyası sayısı / toplam dosya
    test_*, *_test, /tests klasörünü algıla
    Yüksek test oranı = yüksek skor
    
    Args:
        files: Dosya yolları listesi (string veya dict formatında)
        
    Returns:
        {"raw": test_oranı, "score": normalized_score, "test_files": test_dosya_sayısı, "total_files": toplam_dosya}
    """
    if not files:
        return {
            "raw": 0.0,
            "score": 0.0,
            "test_files": 0,
            "total_files": 0
        }
    
    # Test dosyası pattern'leri
    test_patterns = [
        r'test_.*\.py$',           # test_*.py
        r'.*_test\.py$',           # *_test.py
        r'.*_spec\.py$',           # *_spec.py
        r'.*\.test\.[jt]sx?$',     # *.test.js, *.test.ts, *.test.jsx, *.test.tsx
        r'.*\.spec\.[jt]sx?$',     # *.spec.js, *.spec.ts, *.spec.jsx, *.spec.tsx
        r'tests?/.*',              # tests/ veya test/ klasörü
        r'__tests__/.*',           # __tests__/ klasörü (Jest convention)
        r'.*Test\.(java|kt)$',     # *Test.java, *Test.kt
        r'.*_test\.go$',           # *_test.go
        r'.*_test\.rb$',           # *_test.rb
        r'.*_spec\.rb$',           # *_spec.rb
    ]
    
    combined_pattern = '|'.join(f'({p})' for p in test_patterns)
    test_regex = re.compile(combined_pattern, re.IGNORECASE)
    
    test_file_count = 0
    total_file_count = 0
    
    for file_entry in files:
        # Dosya yolunu çıkar
        if isinstance(file_entry, dict):
            file_path = file_entry.get('path', file_entry.get('name', ''))
        else:
            file_path = str(file_entry)
        
        if not file_path:
            continue
        
        # Sadece kod dosyalarını say (binary, image vb. hariç)
        code_extensions = {
            '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.kt', '.go',
            '.rb', '.rs', '.c', '.cpp', '.h', '.hpp', '.cs', '.php',
            '.swift', '.scala', '.clj', '.ex', '.exs', '.vue', '.svelte'
        }
        
        # Dosya uzantısını kontrol et
        has_code_extension = any(file_path.lower().endswith(ext) for ext in code_extensions)
        
        if has_code_extension:
            total_file_count += 1
            
            # Test dosyası mı kontrol et
            if test_regex.search(file_path):
                test_file_count += 1
    
    if total_file_count == 0:
        return {
            "raw": 0.0,
            "score": 0.0,
            "test_files": 0,
            "total_files": 0
        }
    
    # Test oranı
    test_ratio = test_file_count / total_file_count
    
    # Normalize: 0-0.3 arası (0.3 = %30 test coverage ideal kabul edilir)
    # %0 test = 0 puan, %30+ test = 100 puan
    min_ratio = 0.0
    max_ratio = 0.3
    
    score = _normalize_score(test_ratio, min_ratio, max_ratio)
    
    return {
        "raw": round(test_ratio, 4),
        "score": score,
        "test_files": test_file_count,
        "total_files": total_file_count
    }


def compute_overall_score(metrics_dict: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """
    Tüm metrikleri birleştirip tek bir genel kalite skoru hesaplar.
    
    scoring.py içindeki ağırlıklandırma fonksiyonunu çağırır.
    
    Args:
        metrics_dict: Her metrik için {"raw": ..., "score": ...} içeren dict
            Beklenen anahtarlar:
            - commit_frequency
            - issue_resolution
            - pr_rejection
            - test_ratio
            
    Returns:
        {"overall_score": 0-100 genel skor, "breakdown": detaylı skorlar, "grade": harf notu}
    """
    from .scoring import calculate_weighted_score, get_grade
    
    # Metrikleri çıkar
    scores = {}
    for metric_name, metric_data in metrics_dict.items():
        if isinstance(metric_data, dict) and 'score' in metric_data:
            scores[metric_name] = metric_data['score']
        elif isinstance(metric_data, (int, float)):
            scores[metric_name] = float(metric_data)
    
    # Ağırlıklı skor hesapla
    overall_score = calculate_weighted_score(scores)
    
    # Harf notu
    grade = get_grade(overall_score)
    
    return {
        "overall_score": round(overall_score, 2),
        "breakdown": scores,
        "grade": grade,
        "metrics_count": len(scores)
    }


# Test amaçlı örnek kullanım
if __name__ == "__main__":
    # Örnek commit verisi
    sample_commits = [
        {"commit": {"author": {"date": "2024-01-01T10:00:00Z"}}},
        {"commit": {"author": {"date": "2024-01-05T10:00:00Z"}}},
        {"commit": {"author": {"date": "2024-01-10T10:00:00Z"}}},
    ]
    
    # Örnek issue verisi
    sample_issues = [
        {"state": "closed", "created_at": "2024-01-01T10:00:00Z", "closed_at": "2024-01-03T10:00:00Z"},
        {"state": "closed", "created_at": "2024-01-05T10:00:00Z", "closed_at": "2024-01-06T10:00:00Z"},
        {"state": "open", "created_at": "2024-01-10T10:00:00Z"},
    ]
    
    # Örnek PR verisi
    sample_prs = [
        {"state": "closed", "merged_at": "2024-01-02T10:00:00Z"},
        {"state": "closed", "merged_at": None},  # Reddedilmiş
        {"state": "closed", "merged_at": "2024-01-05T10:00:00Z"},
    ]
    
    # Örnek dosya listesi
    sample_files = [
        "src/main.py",
        "src/utils.py",
        "tests/test_main.py",
        "tests/test_utils.py",
    ]
    
    print("=== Metrik Hesaplamaları ===\n")
    
    commit_result = compute_commit_frequency(sample_commits)
    print(f"Commit Frequency: {commit_result}")
    
    issue_result = compute_issue_resolution(sample_issues)
    print(f"Issue Resolution: {issue_result}")
    
    pr_result = compute_pr_rejection(sample_prs)
    print(f"PR Rejection: {pr_result}")
    
    test_result = compute_test_ratio(sample_files)
    print(f"Test Ratio: {test_result}")

