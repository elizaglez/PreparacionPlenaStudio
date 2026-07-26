from app.generation.article_generation_plan import (
    ArticleGenerationPlan,
    ArticleGenerationPlanError,
    GenerationSection,
    QuestionSource,
    build_article_generation_plan,
)
from app.generation.article_content_generator import ArticleContentGenerator
from app.generation.content_generation_request import (
    BoxGenerationRequest,
    ContentGenerationRequest,
    QuestionGenerationRequest,
    SectionGenerationRequest,
    build_content_generation_request,
)
from app.generation.generated_article import (
    GeneratedArticle,
    GeneratedBox,
    GeneratedIntroduction,
    GeneratedQuestion,
    GeneratedSection,
)


_LEGACY_EXPORTS = {
    "MasterGenerationError",
    "PIPELINE_STAGES",
    "_answer_from_result",
    "_generate_one",
}


def __getattr__(name: str):
    """Load the legacy generation pipeline only when explicitly requested."""
    if name not in _LEGACY_EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    from app.generation import master_answer_generator

    return getattr(master_answer_generator, name)

__all__ = [
    "ArticleGenerationPlan",
    "ArticleGenerationPlanError",
    "ArticleContentGenerator",
    "BoxGenerationRequest",
    "ContentGenerationRequest",
    "GenerationSection",
    "GeneratedArticle",
    "GeneratedBox",
    "GeneratedIntroduction",
    "GeneratedQuestion",
    "GeneratedSection",
    "QuestionGenerationRequest",
    "QuestionSource",
    "SectionGenerationRequest",
    "build_article_generation_plan",
    "build_content_generation_request",
]
