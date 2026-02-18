"""
Analytics Paketi

GitHub repository kalite analizi için metrik hesaplama modülleri.
"""

from .metrics import (
    compute_commit_frequency,
    compute_issue_resolution,
    compute_pr_rejection,
    compute_test_ratio,
    compute_overall_score,
)

from .scoring import (
    calculate_weighted_score,
    get_grade,
    get_grade_description,
    adjust_weights,
    calculate_improvement_potential,
    DEFAULT_WEIGHTS,
    GRADE_THRESHOLDS,
)

from .trends import (
    compute_commit_trend,
    compute_issue_trend,
    compute_weekly_summary,
)

from .visualization import (
    create_contributor_effort_chart,
    create_effort_pie_chart,
    create_commit_heatmap,
    create_test_coverage_gauge,
    create_trend_line_chart,
    create_quality_radar_chart,
    create_weekly_comparison_chart,
    export_charts_to_html,
)

from .utils import (
    GitHubClient,
    GitHubConfig,
    RepositoryData,
    analyze_repository,
    parse_github_url,
    get_analysis_summary,
)

from .llm import (
    LLMClient,
    LLMConfig,
    LLMResponse,
    generate_quality_report,
    generate_metric_explanation,
    generate_improvement_suggestions,
)

__all__ = [
    # Metrics
    "compute_commit_frequency",
    "compute_issue_resolution",
    "compute_pr_rejection",
    "compute_test_ratio",
    "compute_overall_score",
    # Scoring
    "calculate_weighted_score",
    "get_grade",
    "get_grade_description",
    "adjust_weights",
    "calculate_improvement_potential",
    "DEFAULT_WEIGHTS",
    "GRADE_THRESHOLDS",
    # Trends
    "compute_commit_trend",
    "compute_issue_trend",
    "compute_weekly_summary",
    # Visualization
    "create_contributor_effort_chart",
    "create_effort_pie_chart",
    "create_commit_heatmap",
    "create_test_coverage_gauge",
    "create_trend_line_chart",
    "create_quality_radar_chart",
    "create_weekly_comparison_chart",
    "export_charts_to_html",
    # Utils (GitHub API)
    "GitHubClient",
    "GitHubConfig",
    "RepositoryData",
    "analyze_repository",
    "parse_github_url",
    "get_analysis_summary",
    # LLM
    "LLMClient",
    "LLMConfig",
    "LLMResponse",
    "generate_quality_report",
    "generate_metric_explanation",
    "generate_improvement_suggestions",
]

__version__ = "1.0.0"

