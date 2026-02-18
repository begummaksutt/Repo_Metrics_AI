"""
GitHub API Utility Modülü

Bu modül, GitHub API ile etkileşim için merkezi bir client sağlar.
Tüm veri çekme ve analiz işlemleri bu modül üzerinden yapılır.

Kullanım:
    from analytics.utils import GitHubClient, analyze_repository
    
    client = GitHubClient(token="ghp_xxx")
    result = analyze_repository("https://github.com/owner/repo", client)
"""

import requests
from datetime import datetime, timedelta
from typing import Any, Optional
from dataclasses import dataclass, field
import time
import re


@dataclass
class GitHubConfig:
    """GitHub API yapılandırması."""
    base_url: str = "https://api.github.com"
    timeout: int = 30
    per_page: int = 100
    max_retries: int = 3
    retry_delay: float = 1.0


@dataclass
class RepositoryData:
    """Repository verilerini tutan veri sınıfı."""
    repo_info: dict = field(default_factory=dict)
    contributors: list = field(default_factory=list)
    commits: list = field(default_factory=list)
    issues: list = field(default_factory=list)
    pull_requests: list = field(default_factory=list)
    files: list = field(default_factory=list)
    languages: dict = field(default_factory=dict)
    error: Optional[str] = None
    
    @property
    def is_valid(self) -> bool:
        """Veri geçerli mi kontrol eder."""
        return self.error is None and bool(self.repo_info)


class GitHubClient:
    """
    GitHub API Client.
    
    Özellikler:
        - Rate limiting yönetimi
        - Otomatik retry
        - Pagination desteği
        - Token tabanlı kimlik doğrulama
    
    Kullanım:
        client = GitHubClient(token="ghp_xxxx")
        repo_data = client.fetch_repository("owner", "repo")
    """
    
    def __init__(
        self,
        token: Optional[str] = None,
        config: Optional[GitHubConfig] = None
    ):
        """
        GitHubClient oluşturur.
        
        Args:
            token: GitHub Personal Access Token (opsiyonel, rate limit için önerilir)
            config: API yapılandırması
        """
        self.token = token
        self.config = config or GitHubConfig()
        self.session = requests.Session()
        self._setup_session()
        
        # Rate limit bilgisi
        self.rate_limit_remaining = None
        self.rate_limit_reset = None
    
    def _setup_session(self) -> None:
        """Session'ı yapılandırır."""
        self.session.headers.update({
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "GitHub-Quality-Analyzer/1.0"
        })
        
        if self.token:
            self.session.headers["Authorization"] = f"token {self.token}"
    
    def _update_rate_limit(self, response: requests.Response) -> None:
        """Rate limit bilgisini günceller."""
        self.rate_limit_remaining = int(response.headers.get("X-RateLimit-Remaining", 0))
        reset_timestamp = int(response.headers.get("X-RateLimit-Reset", 0))
        self.rate_limit_reset = datetime.fromtimestamp(reset_timestamp) if reset_timestamp else None
    
    def _handle_rate_limit(self) -> None:
        """Rate limit durumunda bekler."""
        if self.rate_limit_remaining is not None and self.rate_limit_remaining < 5:
            if self.rate_limit_reset:
                wait_time = (self.rate_limit_reset - datetime.now()).total_seconds()
                if wait_time > 0:
                    print(f"⏳ Rate limit yaklaşıyor, {wait_time:.0f} saniye bekleniyor...")
                    time.sleep(min(wait_time + 1, 60))  # Max 60 saniye bekle
    
    def _request(
        self,
        endpoint: str,
        params: Optional[dict] = None,
        method: str = "GET"
    ) -> tuple[Optional[dict | list], Optional[str]]:
        """
        GitHub API'ye istek yapar.
        
        Args:
            endpoint: API endpoint (örn: /repos/owner/repo)
            params: Query parametreleri
            method: HTTP method
            
        Returns:
            (data, error) tuple'ı
        """
        url = f"{self.config.base_url}{endpoint}"
        
        for attempt in range(self.config.max_retries):
            try:
                self._handle_rate_limit()
                
                response = self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    timeout=self.config.timeout
                )
                
                self._update_rate_limit(response)
                
                if response.status_code == 200:
                    return response.json(), None
                elif response.status_code == 404:
                    return None, "Repository bulunamadı"
                elif response.status_code == 403:
                    if "rate limit" in response.text.lower():
                        return None, "Rate limit aşıldı. Lütfen bir GitHub token kullanın."
                    return None, "Erişim reddedildi"
                elif response.status_code == 401:
                    return None, "Geçersiz token"
                else:
                    return None, f"API hatası: {response.status_code}"
                    
            except requests.Timeout:
                if attempt < self.config.max_retries - 1:
                    time.sleep(self.config.retry_delay * (attempt + 1))
                    continue
                return None, "İstek zaman aşımına uğradı"
            except requests.RequestException as e:
                return None, f"Bağlantı hatası: {str(e)}"
        
        return None, "Maksimum deneme sayısı aşıldı"
    
    def _paginate(
        self,
        endpoint: str,
        params: Optional[dict] = None,
        max_items: int = 500
    ) -> tuple[list, Optional[str]]:
        """
        Pagination ile tüm verileri çeker.
        
        Args:
            endpoint: API endpoint
            params: Query parametreleri
            max_items: Maksimum öğe sayısı
            
        Returns:
            (items, error) tuple'ı
        """
        params = params or {}
        params["per_page"] = self.config.per_page
        
        all_items = []
        page = 1
        
        while len(all_items) < max_items:
            params["page"] = page
            data, error = self._request(endpoint, params)
            
            if error:
                return all_items, error if not all_items else None
            
            if not data or not isinstance(data, list):
                break
            
            all_items.extend(data)
            
            if len(data) < self.config.per_page:
                break
            
            page += 1
        
        return all_items[:max_items], None
    
    def get_rate_limit_info(self) -> dict[str, Any]:
        """Rate limit bilgisini döndürür."""
        data, error = self._request("/rate_limit")
        if error:
            return {"error": error}
        return data.get("rate", {}) if data else {}
    
    def fetch_repo_info(self, owner: str, repo: str) -> tuple[dict, Optional[str]]:
        """
        Repository bilgisini çeker.
        
        Returns:
            (repo_info, error)
        """
        data, error = self._request(f"/repos/{owner}/{repo}")
        return data or {}, error
    
    def fetch_contributors(
        self,
        owner: str,
        repo: str,
        max_count: int = 50
    ) -> tuple[list[dict], Optional[str]]:
        """
        Contributor listesini çeker.
        
        Her contributor için ek profil bilgisi de alınır.
        """
        contributors, error = self._paginate(
            f"/repos/{owner}/{repo}/contributors",
            max_items=max_count
        )
        
        if error and not contributors:
            return [], error
        
        # İlk 15 contributor için detaylı bilgi çek
        for contributor in contributors[:15]:
            user_url = contributor.get("url", "")
            if user_url:
                # Sadece endpoint kısmını al
                endpoint = user_url.replace(self.config.base_url, "")
                user_data, _ = self._request(endpoint)
                if user_data:
                    contributor["name"] = user_data.get("name", contributor.get("login"))
                    contributor["bio"] = user_data.get("bio", "")
                    contributor["followers"] = user_data.get("followers", 0)
                    contributor["public_repos"] = user_data.get("public_repos", 0)
                    contributor["location"] = user_data.get("location", "")
                    contributor["company"] = user_data.get("company", "")
        
        return contributors, None
    
    def fetch_commits(
        self,
        owner: str,
        repo: str,
        since: Optional[datetime] = None,
        max_count: int = 200
    ) -> tuple[list[dict], Optional[str]]:
        """
        Commit listesini çeker.
        
        Args:
            since: Bu tarihten sonraki commitler
            max_count: Maksimum commit sayısı
        """
        params = {}
        if since:
            params["since"] = since.isoformat()
        
        return self._paginate(
            f"/repos/{owner}/{repo}/commits",
            params=params,
            max_items=max_count
        )
    
    def fetch_issues(
        self,
        owner: str,
        repo: str,
        state: str = "all",
        max_count: int = 200
    ) -> tuple[list[dict], Optional[str]]:
        """
        Issue listesini çeker (PR'lar hariç).
        
        Args:
            state: "open", "closed" veya "all"
        """
        issues, error = self._paginate(
            f"/repos/{owner}/{repo}/issues",
            params={"state": state},
            max_items=max_count
        )
        
        # PR'ları filtrele (issue'larda pull_request key'i varsa PR'dır)
        issues = [i for i in issues if "pull_request" not in i]
        
        return issues, error
    
    def fetch_pull_requests(
        self,
        owner: str,
        repo: str,
        state: str = "all",
        max_count: int = 200
    ) -> tuple[list[dict], Optional[str]]:
        """Pull request listesini çeker."""
        return self._paginate(
            f"/repos/{owner}/{repo}/pulls",
            params={"state": state},
            max_items=max_count
        )
    
    def fetch_files(
        self,
        owner: str,
        repo: str,
        branch: Optional[str] = None
    ) -> tuple[list[str], Optional[str]]:
        """
        Repository dosya listesini çeker.
        
        Args:
            branch: Branch adı (varsayılan: default branch)
        """
        # Önce repo bilgisini al (default branch için)
        if not branch:
            repo_info, error = self.fetch_repo_info(owner, repo)
            if error:
                return [], error
            branch = repo_info.get("default_branch", "main")
        
        # Git tree'yi çek
        data, error = self._request(
            f"/repos/{owner}/{repo}/git/trees/{branch}",
            params={"recursive": "1"}
        )
        
        if error:
            return [], error
        
        if not data:
            return [], "Dosya ağacı alınamadı"
        
        # Sadece dosyaları al (blob'lar)
        files = [
            item.get("path", "")
            for item in data.get("tree", [])
            if item.get("type") == "blob"
        ]
        
        return files, None
    
    def fetch_languages(self, owner: str, repo: str) -> tuple[dict, Optional[str]]:
        """Repository'de kullanılan dilleri çeker."""
        data, error = self._request(f"/repos/{owner}/{repo}/languages")
        return data or {}, error
    
    def fetch_repository(self, owner: str, repo: str) -> RepositoryData:
        """
        Tüm repository verilerini çeker.
        
        Args:
            owner: Repository sahibi
            repo: Repository adı
            
        Returns:
            RepositoryData objesi
        """
        result = RepositoryData()
        
        # Repo bilgisi
        result.repo_info, error = self.fetch_repo_info(owner, repo)
        if error:
            result.error = error
            return result
        
        # Contributors
        result.contributors, _ = self.fetch_contributors(owner, repo)
        
        # Son 90 günün commit'leri
        since = datetime.now() - timedelta(days=90)
        result.commits, _ = self.fetch_commits(owner, repo, since=since)
        
        # Issues
        result.issues, _ = self.fetch_issues(owner, repo)
        
        # Pull Requests
        result.pull_requests, _ = self.fetch_pull_requests(owner, repo)
        
        # Dosyalar
        result.files, _ = self.fetch_files(owner, repo)
        
        # Diller
        result.languages, _ = self.fetch_languages(owner, repo)
        
        return result


def parse_github_url(url: str) -> tuple[Optional[str], Optional[str]]:
    """
    GitHub URL'sinden owner ve repo adını çıkarır.
    
    Args:
        url: GitHub URL'si (örn: https://github.com/owner/repo)
        
    Returns:
        (owner, repo) tuple'ı veya (None, None)
    """
    # URL pattern'leri
    patterns = [
        r"github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$",
        r"github\.com/([^/]+)/([^/]+)",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1), match.group(2).rstrip('/')
    
    return None, None


def analyze_repository(
    repo_url: str,
    client: Optional[GitHubClient] = None,
    token: Optional[str] = None
) -> dict[str, Any]:
    """
    Repository'yi analiz eder ve tüm metrikleri hesaplar.
    
    Bu fonksiyon, metrics.py, trends.py ve scoring.py modüllerini
    kullanarak kapsamlı bir analiz yapar.
    
    Args:
        repo_url: GitHub repository URL'si
        client: GitHubClient instance (opsiyonel)
        token: GitHub token (client yoksa kullanılır)
        
    Returns:
        {
            "success": bool,
            "error": str | None,
            "repository": repo bilgileri,
            "contributors": contributor listesi,
            "metrics": {
                "commit_frequency": {...},
                "issue_resolution": {...},
                "pr_rejection": {...},
                "test_ratio": {...}
            },
            "trends": {
                "commit_trend": {...},
                "issue_trend": {...}
            },
            "overall": {
                "score": 0-100,
                "grade": "A" - "F",
                "breakdown": {...}
            }
        }
    """
    # URL'yi parse et
    owner, repo = parse_github_url(repo_url)
    if not owner or not repo:
        return {
            "success": False,
            "error": "Geçersiz GitHub URL'si. Format: https://github.com/owner/repo"
        }
    
    # Client oluştur
    if not client:
        client = GitHubClient(token=token)
    
    # Verileri çek
    print(f"📥 Veriler çekiliyor: {owner}/{repo}")
    data = client.fetch_repository(owner, repo)
    
    if not data.is_valid:
        return {
            "success": False,
            "error": data.error or "Veri çekilemedi"
        }
    
    # Metrikleri hesapla
    print("📊 Metrikler hesaplanıyor...")
    
    from .metrics import (
        compute_commit_frequency,
        compute_issue_resolution,
        compute_pr_rejection,
        compute_test_ratio,
        compute_overall_score
    )
    from .trends import compute_commit_trend, compute_issue_trend
    
    # Metrics
    commit_freq = compute_commit_frequency(data.commits)
    issue_res = compute_issue_resolution(data.issues)
    pr_rej = compute_pr_rejection(data.pull_requests)
    test_ratio = compute_test_ratio(data.files)
    
    metrics = {
        "commit_frequency": commit_freq,
        "issue_resolution": issue_res,
        "pr_rejection": pr_rej,
        "test_ratio": test_ratio
    }
    
    # Trends
    commit_trend = compute_commit_trend(data.commits)
    issue_trend = compute_issue_trend(data.issues)
    
    trends = {
        "commit_trend": commit_trend,
        "issue_trend": issue_trend
    }
    
    # Overall score
    overall = compute_overall_score(metrics)
    
    # Repository bilgileri
    repo_info = {
        "name": data.repo_info.get("name", repo),
        "full_name": data.repo_info.get("full_name", f"{owner}/{repo}"),
        "description": data.repo_info.get("description", ""),
        "url": data.repo_info.get("html_url", repo_url),
        "stars": data.repo_info.get("stargazers_count", 0),
        "forks": data.repo_info.get("forks_count", 0),
        "watchers": data.repo_info.get("watchers_count", 0),
        "open_issues": data.repo_info.get("open_issues_count", 0),
        "language": data.repo_info.get("language", "Unknown"),
        "created_at": data.repo_info.get("created_at", ""),
        "updated_at": data.repo_info.get("updated_at", ""),
        "default_branch": data.repo_info.get("default_branch", "main")
    }
    
    # Sonucu döndür
    return {
        "success": True,
        "error": None,
        "repository": repo_info,
        "contributors": data.contributors,
        "languages": data.languages,
        "stats": {
            "total_commits": len(data.commits),
            "total_issues": len(data.issues),
            "total_prs": len(data.pull_requests),
            "total_files": len(data.files)
        },
        "metrics": metrics,
        "trends": trends,
        "overall": overall
    }


def get_analysis_summary(analysis: dict[str, Any]) -> str:
    """
    Analiz sonuçlarının özet metnini oluşturur.
    
    Args:
        analysis: analyze_repository() çıktısı
        
    Returns:
        Markdown formatında özet metin
    """
    if not analysis.get("success"):
        return f"❌ Analiz başarısız: {analysis.get('error', 'Bilinmeyen hata')}"
    
    repo = analysis.get("repository", {})
    overall = analysis.get("overall", {})
    metrics = analysis.get("metrics", {})
    stats = analysis.get("stats", {})
    
    summary = f"""
# 📊 {repo.get('full_name', 'Repository')} Analiz Raporu

## Genel Bakış
- **Kalite Skoru:** {overall.get('overall_score', 0)}/100
- **Not:** {overall.get('grade', 'N/A')}
- **Dil:** {repo.get('language', 'N/A')}
- **⭐ Stars:** {repo.get('stars', 0):,}
- **🍴 Forks:** {repo.get('forks', 0):,}

## İstatistikler
- 📝 **Commits (90 gün):** {stats.get('total_commits', 0)}
- 🐛 **Issues:** {stats.get('total_issues', 0)}
- 🔀 **Pull Requests:** {stats.get('total_prs', 0)}
- 📁 **Dosya Sayısı:** {stats.get('total_files', 0)}

## Metrik Detayları

| Metrik | Skor | Detay |
|--------|------|-------|
| Commit Sıklığı | {metrics.get('commit_frequency', {}).get('score', 0):.0f}/100 | {metrics.get('commit_frequency', {}).get('raw', 0):.2f} commit/gün |
| Issue Çözümü | {metrics.get('issue_resolution', {}).get('score', 0):.0f}/100 | Ort. {metrics.get('issue_resolution', {}).get('raw', 0):.1f} gün |
| PR Kalitesi | {metrics.get('pr_rejection', {}).get('score', 0):.0f}/100 | %{metrics.get('pr_rejection', {}).get('raw', 0)*100:.1f} red oranı |
| Test Coverage | {metrics.get('test_ratio', {}).get('score', 0):.0f}/100 | %{metrics.get('test_ratio', {}).get('raw', 0)*100:.1f} test dosyası |

---
*Rapor oluşturulma: {datetime.now().strftime('%Y-%m-%d %H:%M')}*
"""
    
    return summary


# CLI desteği
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Kullanım: python -m analytics.utils <github_repo_url> [token]")
        print("Örnek: python -m analytics.utils https://github.com/facebook/react")
        sys.exit(1)
    
    url = sys.argv[1]
    token = sys.argv[2] if len(sys.argv) > 2 else None
    
    print(f"\n🔍 Analiz başlatılıyor: {url}\n")
    
    result = analyze_repository(url, token=token)
    
    if result["success"]:
        print(get_analysis_summary(result))
    else:
        print(f"❌ Hata: {result['error']}")

