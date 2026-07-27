import inspect
import unittest
from unittest.mock import Mock, patch

from app.ai.config import AIProviderConfig
from app.generation.article_generation_plan import ArticleGenerationPlan
from app.generation.generated_article import (
    GeneratedArticle,
    GeneratedIntroduction,
)

from app.master_generator import (
    _answer_from_result,
    _methodology_instructions,
    generate_article_content,
    generate_master,
)


class MasterGeneratorTests(unittest.TestCase):
    def test_preserves_exact_question(self):
        section = {
            "number": 3,
            "question": "¿Qué aprendemos de este ejemplo?",
            "paragraph_numbers": [5, 6],
            "scripture_references": ["Juan 3:16"],
        }
        result = {
            "answer": "Aprendemos a actuar con amor.",
            "source_notes": ["Párrafos 5 y 6"],
        }
        answer = _answer_from_result(section, result)
        self.assertEqual(answer.question, section["question"])
        self.assertEqual(answer.paragraph_numbers, [5, 6])

    def test_methodology_forbids_speculation(self):
        instructions = _methodology_instructions(
            {"principles": ["No se permite especulación."]}
        )
        self.assertIn("No se permite especulación", instructions)


    @patch("app.master_generator.GenerateArticleContentUseCase")
    @patch("app.master_generator.create_article_content_service")
    def test_generates_article_content_through_composition_and_use_case(
        self,
        create_service,
        use_case_type,
    ):
        plan = ArticleGenerationPlan(
            title="Título",
            introduction="Introducción",
        )
        config = AIProviderConfig(
            model="modelo-prueba",
            timeout_seconds=30,
        )
        service = Mock(name="article_content_service")
        generated = GeneratedArticle(
            title="Título generado",
            introduction=GeneratedIntroduction(),
        )
        use_case = use_case_type.return_value
        use_case.execute.return_value = generated
        create_service.return_value = service

        result = generate_article_content(
            plan,
            "fake",
            config,
        )

        create_service.assert_called_once_with(
            "fake",
            config,
        )
        use_case_type.assert_called_once_with(service)
        use_case.execute.assert_called_once_with(plan)
        self.assertIs(result, generated)

    def test_new_entry_point_does_not_import_openai_sdk(self):
        source = inspect.getsource(generate_article_content)

        self.assertNotIn("OpenAI(", source)
        self.assertNotIn("from openai", source)
        self.assertNotIn("import openai", source)
        self.assertNotIn("openai_client", source)
        self.assertNotIn("openai_api_key", source)

    def test_legacy_generate_master_entry_point_remains_available(self):
        self.assertTrue(callable(generate_master))


if __name__ == "__main__":
    unittest.main()
