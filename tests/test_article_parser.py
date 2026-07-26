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

    def test_parses_question_before_real_paragraph_and_page_break(self):
        sample = {
            "title": "Cómo proteger nuestra amistad con Jehová",
            "text": """
=== PÁGINA 1 ===
Cómo proteger nuestra amistad con Jehová
PRIMER PRINCIPIO
1. ¿Qué debemos hacer para mantenernos
espiritualmente fuertes?
Respuesta

=== PÁGINA 2 ===
1 Debemos reservar tiempo para estudiar la Biblia y orar todos los días.
2. ¿Por qué debemos escoger bien nuestras amistades?
Respuesta
2 Las buenas amistades nos ayudan a tomar decisiones sabias.
3 Este párrafo no tiene una pregunta asociada en esta muestra.
""",
        }

        article = parse_article(sample)

        self.assertEqual(len(article.sections), 2)
        self.assertEqual(
            article.sections[0].question,
            "¿Qué debemos hacer para mantenernos espiritualmente fuertes?",
        )
        self.assertEqual(article.sections[0].paragraph_numbers, [1])
        self.assertEqual(
            article.sections[0].paragraphs[0].text,
            "Debemos reservar tiempo para estudiar la Biblia y orar todos los días.",
        )
        self.assertNotIn("Respuesta", article.sections[0].paragraphs[0].text)
        self.assertNotIn("PÁGINA", article.sections[0].paragraphs[0].text)

        unassigned_numbers = {
            paragraph.number for paragraph in article.unassigned_paragraphs
        }
        self.assertNotIn(1, unassigned_numbers)
        self.assertNotIn(2, unassigned_numbers)
        self.assertIn(3, unassigned_numbers)

    def test_preserves_all_parts_of_compound_question(self):
        sample = {
            "title": "Cómo mantenernos espiritualmente fuertes",
            "text": """
Cómo mantenernos espiritualmente fuertes
TEMA DEL ARTÍCULO
1, 2. a) Si seguimos estudiando, ¿de qué tendremos que asegurarnos?
b) ¿Qué significa seguir andando por el camino correcto?
c) ¿Qué ayuda adicional podemos buscar?
Respuesta
1 Tenemos que asegurarnos de mantener una amistad estrecha con Jehová.
2 Seguir por el camino correcto significa continuar sirviendo fielmente.
OTRA SECCIÓN
3 Este párrafo pertenece a otra parte del artículo.
""",
        }

        article = parse_article(sample)

        self.assertEqual(len(article.sections), 1)
        self.assertEqual(
            article.sections[0].question,
            (
                "a) Si seguimos estudiando, ¿de qué tendremos que asegurarnos? "
                "b) ¿Qué significa seguir andando por el camino correcto? "
                "c) ¿Qué ayuda adicional podemos buscar?"
            ),
        )
        self.assertEqual(article.sections[0].paragraph_numbers, [1, 2])
        self.assertEqual(
            [paragraph.text for paragraph in article.sections[0].paragraphs],
            [
                "Tenemos que asegurarnos de mantener una amistad estrecha con Jehová.",
                "Seguir por el camino correcto significa continuar sirviendo fielmente.",
            ],
        )

        unassigned_numbers = {
            paragraph.number for paragraph in article.unassigned_paragraphs
        }
        self.assertNotIn(1, unassigned_numbers)
        self.assertNotIn(2, unassigned_numbers)
        self.assertIn(3, unassigned_numbers)


if __name__ == "__main__":
    unittest.main()
