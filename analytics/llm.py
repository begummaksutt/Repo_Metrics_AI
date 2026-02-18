"""
LLM Entegrasyon Modülü

Bu modül, kalite metriklerini doğal dil açıklamalarına dönüştürür.
Desteklenen LLM Provider'lar:
- OpenAI (GPT-4, GPT-3.5)
- Google Gemini
- Anthropic Claude
- Ollama (Yerel LLM)

Kullanım:
    from analytics.llm import generate_quality_report, LLMClient
    
    client = LLMClient(provider="openai", api_key="sk-xxx")
    report = generate_quality_report(analysis_result, client)
"""

import os
import json
from typing import Any, Optional, Literal
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from datetime import datetime


# Provider türleri
LLMProvider = Literal["openai", "gemini", "claude", "ollama", "mock"]


@dataclass
class LLMConfig:
    """LLM yapılandırması."""
    provider: LLMProvider = "openai"
    model: str = "gpt-3.5-turbo"
    api_key: Optional[str] = None
    base_url: Optional[str] = None  # Ollama için
    temperature: float = 0.7
    max_tokens: int = 1500
    language: str = "tr"  # Rapor dili


@dataclass
class LLMResponse:
    """LLM yanıt objesi."""
    content: str
    provider: str
    model: str
    tokens_used: int = 0
    success: bool = True
    error: Optional[str] = None


class BaseLLMProvider(ABC):
    """Temel LLM provider sınıfı."""
    
    @abstractmethod
    def generate(self, prompt: str, system_prompt: str = "") -> LLMResponse:
        """Metin üretir."""
        pass


class OpenAIProvider(BaseLLMProvider):
    """OpenAI GPT provider."""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self.api_key = config.api_key or os.getenv("OPENAI_API_KEY")
        
        if not self.api_key:
            raise ValueError("OpenAI API key gerekli. OPENAI_API_KEY env variable veya api_key parametresi kullanın.")
    
    def generate(self, prompt: str, system_prompt: str = "") -> LLMResponse:
        try:
            import openai
            
            client = openai.OpenAI(api_key=self.api_key)
            
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            response = client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens
            )
            
            return LLMResponse(
                content=response.choices[0].message.content,
                provider="openai",
                model=self.config.model,
                tokens_used=response.usage.total_tokens if response.usage else 0
            )
            
        except ImportError:
            return LLMResponse(
                content="",
                provider="openai",
                model=self.config.model,
                success=False,
                error="openai paketi yüklü değil. 'pip install openai' komutunu çalıştırın."
            )
        except Exception as e:
            return LLMResponse(
                content="",
                provider="openai",
                model=self.config.model,
                success=False,
                error=str(e)
            )


class GeminiProvider(BaseLLMProvider):
    """Google Gemini provider."""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self.api_key = config.api_key or os.getenv("GOOGLE_API_KEY")
        
        if not self.api_key:
            raise ValueError("Google API key gerekli. GOOGLE_API_KEY env variable veya api_key parametresi kullanın.")
    
    def generate(self, prompt: str, system_prompt: str = "") -> LLMResponse:
        try:
            import google.generativeai as genai
            
            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel(self.config.model or "gemini-pro")
            
            full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            
            response = model.generate_content(
                full_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=self.config.temperature,
                    max_output_tokens=self.config.max_tokens
                )
            )
            
            return LLMResponse(
                content=response.text,
                provider="gemini",
                model=self.config.model or "gemini-pro"
            )
            
        except ImportError:
            return LLMResponse(
                content="",
                provider="gemini",
                model=self.config.model,
                success=False,
                error="google-generativeai paketi yüklü değil. 'pip install google-generativeai' komutunu çalıştırın."
            )
        except Exception as e:
            return LLMResponse(
                content="",
                provider="gemini",
                model=self.config.model,
                success=False,
                error=str(e)
            )


class ClaudeProvider(BaseLLMProvider):
    """Anthropic Claude provider."""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self.api_key = config.api_key or os.getenv("ANTHROPIC_API_KEY")
        
        if not self.api_key:
            raise ValueError("Anthropic API key gerekli. ANTHROPIC_API_KEY env variable veya api_key parametresi kullanın.")
    
    def generate(self, prompt: str, system_prompt: str = "") -> LLMResponse:
        try:
            import anthropic
            
            client = anthropic.Anthropic(api_key=self.api_key)
            
            message = client.messages.create(
                model=self.config.model or "claude-3-haiku-20240307",
                max_tokens=self.config.max_tokens,
                system=system_prompt if system_prompt else "Sen bir yazılım kalite analiz uzmanısın.",
                messages=[{"role": "user", "content": prompt}]
            )
            
            return LLMResponse(
                content=message.content[0].text,
                provider="claude",
                model=self.config.model or "claude-3-haiku-20240307",
                tokens_used=message.usage.input_tokens + message.usage.output_tokens
            )
            
        except ImportError:
            return LLMResponse(
                content="",
                provider="claude",
                model=self.config.model,
                success=False,
                error="anthropic paketi yüklü değil. 'pip install anthropic' komutunu çalıştırın."
            )
        except Exception as e:
            return LLMResponse(
                content="",
                provider="claude",
                model=self.config.model,
                success=False,
                error=str(e)
            )


class OllamaProvider(BaseLLMProvider):
    """Ollama yerel LLM provider."""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self.base_url = config.base_url or "http://localhost:11434"
    
    def generate(self, prompt: str, system_prompt: str = "") -> LLMResponse:
        try:
            import requests
            
            full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.config.model or "llama2",
                    "prompt": full_prompt,
                    "stream": False,
                    "options": {
                        "temperature": self.config.temperature,
                        "num_predict": self.config.max_tokens
                    }
                },
                timeout=120
            )
            
            if response.status_code == 200:
                data = response.json()
                return LLMResponse(
                    content=data.get("response", ""),
                    provider="ollama",
                    model=self.config.model or "llama2"
                )
            else:
                return LLMResponse(
                    content="",
                    provider="ollama",
                    model=self.config.model,
                    success=False,
                    error=f"Ollama hatası: {response.status_code}"
                )
                
        except Exception as e:
            return LLMResponse(
                content="",
                provider="ollama",
                model=self.config.model,
                success=False,
                error=f"Ollama bağlantı hatası: {str(e)}"
            )


class MockProvider(BaseLLMProvider):
    """Test amaçlı mock provider - LLM olmadan çalışır."""
    
    def __init__(self, config: LLMConfig):
        self.config = config
    
    def generate(self, prompt: str, system_prompt: str = "") -> LLMResponse:
        # Basit kural tabanlı yanıt üret
        return LLMResponse(
            content=self._generate_mock_response(prompt),
            provider="mock",
            model="rule-based"
        )
    
    def _generate_mock_response(self, prompt: str) -> str:
        """Basit kural tabanlı yanıt üretir."""
        # Prompt'tan metrikleri çıkarmaya çalış
        lines = []
        
        if "genel skor" in prompt.lower() or "overall" in prompt.lower():
            lines.append("## 📊 Genel Değerlendirme\n")
            lines.append("Bu repository, yazılım kalite standartları açısından değerlendirilmiştir.")
        
        if "commit" in prompt.lower():
            lines.append("\n### 📝 Commit Analizi")
            lines.append("Commit sıklığı proje aktivitesini göstermektedir. ")
            lines.append("Düzenli commit'ler, aktif geliştirme sürecinin bir göstergesidir.")
        
        if "test" in prompt.lower():
            lines.append("\n### 🧪 Test Durumu")
            lines.append("Test coverage oranı, kod kalitesinin önemli bir göstergesidir. ")
            lines.append("Yüksek test oranı, güvenilir bir kod tabanı anlamına gelir.")
        
        if "issue" in prompt.lower():
            lines.append("\n### 🐛 Issue Yönetimi")
            lines.append("Issue çözüm süresi, ekip verimliliğini yansıtır. ")
            lines.append("Hızlı issue çözümü, iyi bir proje yönetiminin işaretidir.")
        
        if "pr" in prompt.lower() or "pull request" in prompt.lower():
            lines.append("\n### 🔀 Pull Request Kalitesi")
            lines.append("PR kabul oranı, kod review sürecinin etkinliğini gösterir. ")
            lines.append("Düşük red oranı, kaliteli kod submission'larına işaret eder.")
        
        lines.append("\n---")
        lines.append("*Bu rapor otomatik olarak oluşturulmuştur.*")
        
        return "\n".join(lines)


class LLMClient:
    """
    Birleşik LLM Client.
    
    Farklı provider'ları tek bir arayüz üzerinden kullanmayı sağlar.
    
    Kullanım:
        # OpenAI
        client = LLMClient(provider="openai", api_key="sk-xxx")
        
        # Gemini
        client = LLMClient(provider="gemini", api_key="xxx")
        
        # Yerel Ollama
        client = LLMClient(provider="ollama", model="llama2")
        
        # Mock (test için)
        client = LLMClient(provider="mock")
    """
    
    PROVIDERS = {
        "openai": OpenAIProvider,
        "gemini": GeminiProvider,
        "claude": ClaudeProvider,
        "ollama": OllamaProvider,
        "mock": MockProvider
    }
    
    def __init__(
        self,
        provider: LLMProvider = "mock",
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs
    ):
        """
        LLMClient oluşturur.
        
        Args:
            provider: LLM provider ("openai", "gemini", "claude", "ollama", "mock")
            api_key: API anahtarı
            model: Model adı
            **kwargs: Ek yapılandırma parametreleri
        """
        # Varsayılan modeller
        default_models = {
            "openai": "gpt-3.5-turbo",
            "gemini": "gemini-pro",
            "claude": "claude-3-haiku-20240307",
            "ollama": "llama2",
            "mock": "rule-based"
        }
        
        self.config = LLMConfig(
            provider=provider,
            api_key=api_key,
            model=model or default_models.get(provider, ""),
            **kwargs
        )
        
        provider_class = self.PROVIDERS.get(provider)
        if not provider_class:
            raise ValueError(f"Desteklenmeyen provider: {provider}")
        
        self.provider = provider_class(self.config)
    
    def generate(self, prompt: str, system_prompt: str = "") -> LLMResponse:
        """Metin üretir."""
        return self.provider.generate(prompt, system_prompt)
    
    def generate_report(self, analysis: dict[str, Any]) -> LLMResponse:
        """Analiz sonuçlarından rapor üretir."""
        prompt = _build_analysis_prompt(analysis, self.config.language)
        system_prompt = _get_system_prompt(self.config.language)
        return self.generate(prompt, system_prompt)


def _get_system_prompt(language: str = "tr") -> str:
    """Sistem prompt'u döndürür."""
    if language == "tr":
        return """Sen deneyimli bir yazılım kalite güvence uzmanısın. 
GitHub repository metriklerini analiz edip, anlaşılır ve actionable raporlar üretiyorsun.

Raporlarında:
- Teknik terimleri açık bir dille anlat
- Güçlü ve zayıf yönleri belirt
- Somut iyileştirme önerileri sun
- Profesyonel ama samimi bir ton kullan
- Emoji kullanarak raporları görsel olarak zenginleştir"""
    else:
        return """You are an experienced software quality assurance expert.
You analyze GitHub repository metrics and produce clear, actionable reports.

In your reports:
- Explain technical terms in plain language
- Highlight strengths and weaknesses
- Provide concrete improvement suggestions
- Use a professional but friendly tone
- Use emojis to visually enrich reports"""


def _build_analysis_prompt(analysis: dict[str, Any], language: str = "tr") -> str:
    """Analiz verilerinden prompt oluşturur."""
    
    if not analysis.get("success"):
        return "Analiz başarısız oldu, rapor üretilemedi."
    
    repo = analysis.get("repository", {})
    metrics = analysis.get("metrics", {})
    trends = analysis.get("trends", {})
    overall = analysis.get("overall", {})
    stats = analysis.get("stats", {})
    
    # Metrik detayları
    commit_freq = metrics.get("commit_frequency", {})
    issue_res = metrics.get("issue_resolution", {})
    pr_rej = metrics.get("pr_rejection", {})
    test_ratio = metrics.get("test_ratio", {})
    
    # Trend detayları
    commit_trend = trends.get("commit_trend", {})
    issue_trend = trends.get("issue_trend", {})
    
    if language == "tr":
        prompt = f"""Aşağıdaki GitHub repository analiz sonuçlarını değerlendirip detaylı bir kalite raporu oluştur:

## Repository Bilgileri
- **Ad:** {repo.get('full_name', 'Bilinmiyor')}
- **Açıklama:** {repo.get('description', 'Açıklama yok')}
- **Ana Dil:** {repo.get('language', 'Bilinmiyor')}
- **Stars:** {repo.get('stars', 0):,}
- **Forks:** {repo.get('forks', 0):,}

## Genel Skor
- **Puan:** {overall.get('overall_score', 0):.1f}/100
- **Not:** {overall.get('grade', 'N/A')}

## Metrik Detayları

### 1. Commit Sıklığı
- Günlük ortalama: {commit_freq.get('raw', 0):.2f} commit
- Skor: {commit_freq.get('score', 0):.0f}/100
- Toplam commit (son 90 gün): {stats.get('total_commits', 0)}
- Trend: {commit_trend.get('trend_direction', 'bilinmiyor')} ({commit_trend.get('trend_strength', 'belirsiz')})

### 2. Issue Çözüm Süresi
- Ortalama çözüm: {issue_res.get('raw', 0):.1f} gün
- Skor: {issue_res.get('score', 0):.0f}/100
- Çözülen issue sayısı: {issue_res.get('resolved_count', 0)}
- Trend: {issue_trend.get('trend_direction', 'bilinmiyor')}

### 3. PR Kalitesi
- Red oranı: %{pr_rej.get('raw', 0)*100:.1f}
- Skor: {pr_rej.get('score', 0):.0f}/100
- Merge edilen: {pr_rej.get('merged', 0)}
- Reddedilen: {pr_rej.get('rejected', 0)}

### 4. Test Coverage
- Test dosyası oranı: %{test_ratio.get('raw', 0)*100:.1f}
- Skor: {test_ratio.get('score', 0):.0f}/100
- Test dosyası sayısı: {test_ratio.get('test_files', 0)}
- Toplam kod dosyası: {test_ratio.get('total_files', 0)}

---

Bu verilere dayanarak:
1. Projenin genel durumunu özetle
2. En güçlü 2-3 yönünü belirt
3. İyileştirme gereken 2-3 alanı tespit et
4. Her alan için somut öneriler sun
5. Sonuç olarak projenin potansiyelini değerlendir

Raporu Markdown formatında, başlıklar ve bullet point'ler kullanarak oluştur."""

    else:
        prompt = f"""Evaluate the following GitHub repository analysis results and create a detailed quality report:

## Repository Information
- **Name:** {repo.get('full_name', 'Unknown')}
- **Description:** {repo.get('description', 'No description')}
- **Main Language:** {repo.get('language', 'Unknown')}
- **Stars:** {repo.get('stars', 0):,}
- **Forks:** {repo.get('forks', 0):,}

## Overall Score
- **Score:** {overall.get('overall_score', 0):.1f}/100
- **Grade:** {overall.get('grade', 'N/A')}

## Metric Details

### 1. Commit Frequency
- Daily average: {commit_freq.get('raw', 0):.2f} commits
- Score: {commit_freq.get('score', 0):.0f}/100
- Total commits (last 90 days): {stats.get('total_commits', 0)}
- Trend: {commit_trend.get('trend_direction', 'unknown')} ({commit_trend.get('trend_strength', 'uncertain')})

### 2. Issue Resolution Time
- Average resolution: {issue_res.get('raw', 0):.1f} days
- Score: {issue_res.get('score', 0):.0f}/100
- Resolved issues: {issue_res.get('resolved_count', 0)}
- Trend: {issue_trend.get('trend_direction', 'unknown')}

### 3. PR Quality
- Rejection rate: {pr_rej.get('raw', 0)*100:.1f}%
- Score: {pr_rej.get('score', 0):.0f}/100
- Merged: {pr_rej.get('merged', 0)}
- Rejected: {pr_rej.get('rejected', 0)}

### 4. Test Coverage
- Test file ratio: {test_ratio.get('raw', 0)*100:.1f}%
- Score: {test_ratio.get('score', 0):.0f}/100
- Test files: {test_ratio.get('test_files', 0)}
- Total code files: {test_ratio.get('total_files', 0)}

---

Based on this data:
1. Summarize the overall project status
2. Identify the 2-3 strongest aspects
3. Identify 2-3 areas needing improvement
4. Provide concrete suggestions for each area
5. Evaluate the project's potential

Create the report in Markdown format using headings and bullet points."""

    return prompt


def generate_quality_report(
    analysis: dict[str, Any],
    client: Optional[LLMClient] = None,
    provider: LLMProvider = "mock",
    api_key: Optional[str] = None,
    language: str = "tr"
) -> dict[str, Any]:
    """
    Analiz sonuçlarından LLM destekli kalite raporu üretir.
    
    Args:
        analysis: analyze_repository() çıktısı
        client: Mevcut LLMClient (opsiyonel)
        provider: LLM provider (client yoksa kullanılır)
        api_key: API anahtarı (client yoksa kullanılır)
        language: Rapor dili ("tr" veya "en")
        
    Returns:
        {
            "success": bool,
            "report": str (Markdown formatında rapor),
            "provider": str,
            "model": str,
            "tokens_used": int,
            "error": str | None
        }
    """
    if not analysis.get("success"):
        return {
            "success": False,
            "report": "",
            "provider": "",
            "model": "",
            "tokens_used": 0,
            "error": f"Analiz başarısız: {analysis.get('error', 'Bilinmeyen hata')}"
        }
    
    # Client oluştur veya mevcut olanı kullan
    if not client:
        try:
            client = LLMClient(provider=provider, api_key=api_key, language=language)
        except ValueError as e:
            return {
                "success": False,
                "report": "",
                "provider": provider,
                "model": "",
                "tokens_used": 0,
                "error": str(e)
            }
    
    # Rapor üret
    response = client.generate_report(analysis)
    
    if not response.success:
        return {
            "success": False,
            "report": "",
            "provider": response.provider,
            "model": response.model,
            "tokens_used": 0,
            "error": response.error
        }
    
    return {
        "success": True,
        "report": response.content,
        "provider": response.provider,
        "model": response.model,
        "tokens_used": response.tokens_used,
        "error": None
    }


def generate_metric_explanation(
    metric_name: str,
    metric_data: dict[str, Any],
    client: Optional[LLMClient] = None,
    language: str = "tr"
) -> str:
    """
    Tek bir metrik için kısa açıklama üretir.
    
    Args:
        metric_name: Metrik adı (commit_frequency, issue_resolution, vb.)
        metric_data: Metrik verisi {"raw": ..., "score": ...}
        client: LLMClient instance
        language: Dil
        
    Returns:
        Açıklama metni
    """
    if not client:
        client = LLMClient(provider="mock", language=language)
    
    score = metric_data.get("score", 0)
    raw = metric_data.get("raw", 0)
    
    metric_names_tr = {
        "commit_frequency": "Commit Sıklığı",
        "issue_resolution": "Issue Çözüm Süresi",
        "pr_rejection": "PR Kalitesi",
        "test_ratio": "Test Coverage"
    }
    
    metric_name_display = metric_names_tr.get(metric_name, metric_name)
    
    if language == "tr":
        prompt = f"""'{metric_name_display}' metriği için kısa (2-3 cümle) bir değerlendirme yaz:
- Skor: {score:.0f}/100
- Ham değer: {raw}

Değerlendirme pozitif veya negatif olsun, skora göre. Somut ve anlaşılır ol."""
    else:
        prompt = f"""Write a brief (2-3 sentences) evaluation for the '{metric_name}' metric:
- Score: {score:.0f}/100
- Raw value: {raw}

The evaluation should be positive or negative based on the score. Be concrete and clear."""
    
    response = client.generate(prompt)
    return response.content if response.success else f"Skor: {score:.0f}/100"


def generate_improvement_suggestions(
    analysis: dict[str, Any],
    client: Optional[LLMClient] = None,
    language: str = "tr"
) -> list[dict[str, str]]:
    """
    İyileştirme önerileri üretir.
    
    Args:
        analysis: analyze_repository() çıktısı
        client: LLMClient instance
        language: Dil
        
    Returns:
        [{"area": "...", "suggestion": "...", "priority": "high/medium/low"}, ...]
    """
    if not client:
        client = LLMClient(provider="mock", language=language)
    
    metrics = analysis.get("metrics", {})
    
    # En düşük skorlu metrikleri bul
    metric_scores = []
    for name, data in metrics.items():
        if isinstance(data, dict) and "score" in data:
            metric_scores.append((name, data.get("score", 0)))
    
    metric_scores.sort(key=lambda x: x[1])
    
    suggestions = []
    
    # Düşük skorlu metrikler için öneri oluştur
    priority_map = {0: "high", 1: "high", 2: "medium", 3: "low"}
    
    suggestion_templates_tr = {
        "commit_frequency": {
            "area": "Commit Sıklığı",
            "low": "Daha sık ve küçük commit'ler yapın. Atomic commit prensibi uygulayın.",
            "medium": "Commit sıklığını artırın. Günlük en az 1-2 commit hedefleyin.",
            "high": "Mevcut commit sıklığınız iyi. Kaliteyi koruyun."
        },
        "issue_resolution": {
            "area": "Issue Yönetimi",
            "low": "Issue'ları önceliklendirin ve SLA tanımlayın. Sprint planlaması yapın.",
            "medium": "Issue çözüm süresini kısaltmak için triage süreci oluşturun.",
            "high": "Issue yönetiminiz başarılı. Best practice'leri dokümante edin."
        },
        "pr_rejection": {
            "area": "PR Kalitesi",
            "low": "PR şablonu oluşturun. Code review checklist'i tanımlayın.",
            "medium": "PR açmadan önce self-review yapın. Test coverage'ı kontrol edin.",
            "high": "PR kalitesi yüksek. Pair programming ile daha da geliştirin."
        },
        "test_ratio": {
            "area": "Test Coverage",
            "low": "Unit test eklemeye başlayın. Kritik fonksiyonları önceliklendirin.",
            "medium": "Test coverage'ı artırın. CI/CD'ye test gate ekleyin.",
            "high": "Test coverage iyi. Integration ve E2E testleri değerlendirin."
        }
    }
    
    for i, (metric_name, score) in enumerate(metric_scores):
        templates = suggestion_templates_tr.get(metric_name, {})
        
        if score < 40:
            level = "low"
        elif score < 70:
            level = "medium"
        else:
            level = "high"
        
        suggestions.append({
            "area": templates.get("area", metric_name),
            "suggestion": templates.get(level, "İyileştirme önerisi mevcut değil."),
            "priority": priority_map.get(i, "low"),
            "current_score": score
        })
    
    return suggestions


# CLI ve test
if __name__ == "__main__":
    # Mock client ile test
    print("🤖 LLM Modülü Test\n")
    
    # Örnek analiz verisi
    sample_analysis = {
        "success": True,
        "repository": {
            "full_name": "test/repo",
            "description": "Test repository",
            "language": "Python",
            "stars": 100,
            "forks": 25
        },
        "metrics": {
            "commit_frequency": {"raw": 2.5, "score": 65},
            "issue_resolution": {"raw": 5.2, "score": 45},
            "pr_rejection": {"raw": 0.15, "score": 70},
            "test_ratio": {"raw": 0.18, "score": 35}
        },
        "trends": {
            "commit_trend": {"trend_direction": "artan", "trend_strength": "orta"},
            "issue_trend": {"trend_direction": "iyileşiyor"}
        },
        "overall": {
            "overall_score": 54,
            "grade": "C+"
        },
        "stats": {
            "total_commits": 150,
            "total_issues": 45
        }
    }
    
    # Mock provider ile rapor üret
    result = generate_quality_report(sample_analysis, provider="mock")
    
    if result["success"]:
        print("✅ Rapor üretildi:\n")
        print(result["report"])
        print(f"\nProvider: {result['provider']}")
    else:
        print(f"❌ Hata: {result['error']}")
    
    # İyileştirme önerileri
    print("\n" + "="*50)
    print("📋 İyileştirme Önerileri:\n")
    
    suggestions = generate_improvement_suggestions(sample_analysis)
    for s in suggestions:
        priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(s["priority"], "⚪")
        print(f"{priority_emoji} **{s['area']}** (Skor: {s['current_score']:.0f})")
        print(f"   {s['suggestion']}\n")

