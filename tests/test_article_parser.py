import unittest

from app.parsers.article_parser import parse_article


class ArticleParserTests(unittest.TestCase):
    def test_structures_questions_and_paragraphs(self):
        sample = {
            "title": "Cómo fortalecer nuestra fe",
            "text": """
Cómo fortalecer nuestra fe
TEXTO TEMÁTICO
1 La fe nos ayuda a mantenernos firmes. Lea Heb. 11:1.
1. ¿Por qué necesitamos fortalecer la fe?
2 También debemos orar con frecuencia. Vea Rom. 12:10.
2. ¿Qué nos ayudará a mantenernos firmes?
APRENDAMOS DE LOS EJEMPLOS
3 La confianza se fortalece con la práctica.
3. ¿Cómo podemos seguir fortaleciendo la fe?
CONCLUSIÓN
4 Jehová valora nuestros esfuerzos sinceros.
4. ¿Qué conclusión podemos sacar?
""",
        }
        article = parse_article(sample)
        self.assertEqual(article.title, "Cómo fortalecer nuestra fe")
        self.assertEqual(len(article.sections), 4)
        self.assertEqual(article.sections[0].paragraph_numbers, [1])
        self.assertIn("Hebreos 11:1", article.sections[0].scripture_references)


if __name__ == "__main__":
    unittest.main()
