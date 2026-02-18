"""
Ağırlıklı Skor Hesaplama Modülü

Bu modül, farklı kalite metriklerini ağırlıklandırarak
genel bir kalite skoru hesaplar.
"""

from typing import Any

# Metrik ağırlıkları (toplam = 1.0)
DEFAULT_WEIGHTS = {
    "commit_frequency": 0.25,    # Commit sıklığı - %25
    "issue_resolution": 0.25,    # Issue çözüm hızı - %25
    "pr_rejection": 0.25,        # PR kalitesi - %25
    "test_ratio": 0.25,          # Test coverage - %25
}

# Not sınırları
GRADE_THRESHOLDS = {
    "A+": 95,
    "A": 90,
    "A-": 85,
    "B+": 80,
    "B": 75,
    "B-": 70,
    "C+": 65,
    "C": 60,
    "C-": 55,
    "D+": 50,
    "D": 45,
    "D-": 40,
    "F": 0
}


def calculate_weighted_score(
    scores: dict[str, float],
    weights: dict[str, float] | None = None
) -> float:
    """
    Metrikleri ağırlıklandırarak genel skor hesaplar.
    
    Args:
        scores: Metrik adı -> skor (0-100) eşleştirmesi
        weights: Metrik adı -> ağırlık eşleştirmesi (opsiyonel)
        
    Returns:
        0-100 arasında ağırlıklı ortalama skor
    """
    if not scores:
        return 0.0
    
    if weights is None:
        weights = DEFAULT_WEIGHTS
    
    total_weight = 0.0
    weighted_sum = 0.0
    
    for metric_name, score in scores.items():
        weight = weights.get(metric_name, 0.0)
        
        # Bilinmeyen metriklere varsayılan ağırlık ata
        if weight == 0.0 and metric_name not in weights:
            # Dinamik olarak eşit ağırlık dağıt
            weight = 1.0 / len(scores)
        
        weighted_sum += score * weight
        total_weight += weight
    
    if total_weight == 0:
        return 0.0
    
    return weighted_sum / total_weight * (total_weight if total_weight <= 1 else 1)


def get_grade(score: float) -> str:
    """
    Sayısal skoru harf notuna çevirir.
    
    Args:
        score: 0-100 arası skor
        
    Returns:
        Harf notu (A+, A, A-, B+, ... F)
    """
    for grade, threshold in GRADE_THRESHOLDS.items():
        if score >= threshold:
            return grade
    return "F"


def get_grade_description(grade: str) -> str:
    """
    Harf notu için açıklama döndürür.
    
    Args:
        grade: Harf notu
        
    Returns:
        Açıklama metni
    """
    descriptions = {
        "A+": "Mükemmel - Örnek alınacak kalitede proje",
        "A": "Çok İyi - Yüksek kalite standartlarına sahip",
        "A-": "İyi - Kalite standartlarının üzerinde",
        "B+": "Ortanın Üstü - Sağlam bir proje",
        "B": "Orta - Kabul edilebilir kalite seviyesi",
        "B-": "Ortanın Altı - İyileştirme alanları mevcut",
        "C+": "Zayıf - Önemli iyileştirmeler gerekli",
        "C": "Yetersiz - Ciddi kalite sorunları var",
        "C-": "Kötü - Acil müdahale gerekli",
        "D+": "Çok Kötü - Kritik sorunlar mevcut",
        "D": "Tehlikeli - Proje risk altında",
        "D-": "Kritik - Acil aksiyon gerekli",
        "F": "Başarısız - Temel kalite kriterlerini karşılamıyor"
    }
    return descriptions.get(grade, "Bilinmeyen not")


def adjust_weights(
    custom_weights: dict[str, float]
) -> dict[str, float]:
    """
    Özel ağırlıkları normalize eder (toplam = 1.0).
    
    Args:
        custom_weights: Kullanıcı tanımlı ağırlıklar
        
    Returns:
        Normalize edilmiş ağırlıklar
    """
    if not custom_weights:
        return DEFAULT_WEIGHTS.copy()
    
    total = sum(custom_weights.values())
    
    if total == 0:
        return DEFAULT_WEIGHTS.copy()
    
    return {k: v / total for k, v in custom_weights.items()}


def calculate_improvement_potential(
    scores: dict[str, float],
    weights: dict[str, float] | None = None
) -> dict[str, Any]:
    """
    Her metrik için iyileştirme potansiyelini hesaplar.
    
    Args:
        scores: Metrik skorları
        weights: Ağırlıklar
        
    Returns:
        Her metrik için iyileştirme potansiyeli ve öneri
    """
    if weights is None:
        weights = DEFAULT_WEIGHTS
    
    improvements = {}
    
    for metric_name, score in scores.items():
        weight = weights.get(metric_name, 0.25)
        potential = (100 - score) * weight
        
        improvements[metric_name] = {
            "current_score": score,
            "potential_gain": round(potential, 2),
            "priority": _get_priority(score, weight),
            "recommendation": _get_recommendation(metric_name, score)
        }
    
    # Öncelik sırasına göre sırala
    sorted_improvements = dict(
        sorted(
            improvements.items(),
            key=lambda x: x[1]["potential_gain"],
            reverse=True
        )
    )
    
    return sorted_improvements


def _get_priority(score: float, weight: float) -> str:
    """İyileştirme önceliğini belirler."""
    impact = (100 - score) * weight
    
    if impact > 15:
        return "Yüksek"
    elif impact > 8:
        return "Orta"
    else:
        return "Düşük"


def _get_recommendation(metric_name: str, score: float) -> str:
    """Metrik bazında öneri döndürür."""
    recommendations = {
        "commit_frequency": {
            "low": "Daha sık commit yapın. Küçük, atomik commitler tercih edin.",
            "medium": "Commit sıklığı kabul edilebilir. Düzenli geliştirme sürdürün.",
            "high": "Mükemmel commit sıklığı! Bu tempoyu koruyun."
        },
        "issue_resolution": {
            "low": "Issue'ları daha hızlı çözün. Önceliklendirme yapın.",
            "medium": "Issue çözüm süresi kabul edilebilir. SLA tanımlayın.",
            "high": "Harika issue yönetimi! Hızlı yanıt veriyorsunuz."
        },
        "pr_rejection": {
            "low": "PR kalitesini artırın. Code review süreçlerini iyileştirin.",
            "medium": "PR kalitesi kabul edilebilir. Standartları belirleyin.",
            "high": "Yüksek PR kalitesi! İyi code review pratikleri uyguluyorsunuz."
        },
        "test_ratio": {
            "low": "Test coverage'ı artırın. Unit testler ekleyin.",
            "medium": "Test oranı kabul edilebilir. Kritik alanları test edin.",
            "high": "Mükemmel test coverage! TDD pratiklerini sürdürün."
        }
    }
    
    metric_recs = recommendations.get(metric_name, {
        "low": "Bu metriği iyileştirin.",
        "medium": "Kabul edilebilir seviye.",
        "high": "Mükemmel performans!"
    })
    
    if score < 40:
        return metric_recs["low"]
    elif score < 70:
        return metric_recs["medium"]
    else:
        return metric_recs["high"]


# Test amaçlı örnek kullanım
if __name__ == "__main__":
    sample_scores = {
        "commit_frequency": 75.0,
        "issue_resolution": 60.0,
        "pr_rejection": 85.0,
        "test_ratio": 45.0
    }
    
    weighted = calculate_weighted_score(sample_scores)
    grade = get_grade(weighted)
    description = get_grade_description(grade)
    
    print(f"Ağırlıklı Skor: {weighted:.2f}")
    print(f"Not: {grade}")
    print(f"Açıklama: {description}")
    print("\nİyileştirme Potansiyeli:")
    
    improvements = calculate_improvement_potential(sample_scores)
    for metric, data in improvements.items():
        print(f"  {metric}: {data['potential_gain']} puan kazanılabilir ({data['priority']} öncelik)")
        print(f"    Öneri: {data['recommendation']}")

