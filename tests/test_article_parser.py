import unittest

from app.parsers.article_parser import parse_article


class ArticleParserTests(unittest.TestCase):
    def test_detects_box_and_keeps_it_out_of_article_structure(self):
        sample = {
            "title": "Respetemos las decisiones de los demás",
            "text": """
Respetemos las decisiones de los demás
TEMA
Cómo respetar las decisiones ajenas.
PRIMER PUNTO
1 Este párrafo recomienda pensar con cuidado. Vea también el recuadro “Si una decisión le parece mal”.
1. ¿Qué debemos hacer antes de juzgar una decisión?
Si una decisión le parece mal
Hágase las siguientes preguntas.
˙ ¿Viola algún mandato bíblico?
˙ ¿Estoy imaginándome lo peor?
LA ATALAYA
SEGUNDO PUNTO
2 Debemos respetar el derecho de los demás a decidir.
2. ¿Qué derecho debemos respetar?
""",
        }

        article = parse_article(sample)
        data = article.to_dict()

        self.assertEqual(len(article.boxes), 1)
        self.assertEqual(article.boxes[0].title, "Si una decisión le parece mal")
        self.assertEqual(article.boxes[0].linked_paragraph, 1)
        self.assertEqual(
            article.boxes[0].content,
            [
                "Hágase las siguientes preguntas.",
                "¿Viola algún mandato bíblico?",
                "¿Estoy imaginándome lo peor?",
            ],
        )
        self.assertEqual(article.boxes[0].type, "reflection")
        self.assertEqual(data["boxes"][0]["linked_paragraph"], 1)

        paragraph_numbers = {
            paragraph.number
            for section in article.sections
            for paragraph in section.paragraphs
        }
        self.assertEqual(paragraph_numbers, {1, 2})
        self.assertEqual(len(article.sections), 2)
        self.assertNotIn(
            "Si una decisión le parece mal",
            [section.subtitle for section in article.sections],
        )

    def test_detects_subtitles_summaries_and_review_questions(self):
        sample = {
            "title": "CUIDEMOS NUESTRA AMISTAD CON JEHOVÁ",
            "text": """
CUIDEMOS NUESTRA AMISTAD CON JEHOVÁ
“Manténganse cerca de Jehová” (SANT. 4:8).
1-7 DE JULIO DE 2026
CANCIÓN 10
Jehová es nuestro refugio
TEMA
Cómo proteger nuestra amistad con Jehová.
Esta es la introducción del artículo.
1 La introducción presenta el tema principal.
1. ¿Qué presenta la introducción?
MANTÉN UN BUEN PROGRAMA DE ACTIVIDADES ESPIRITUALES
2 Debemos estudiar y orar todos los días.
2. ¿Qué actividades debemos mantener?
PROTEGE TU CAPACIDAD DE PENSAR
3 Debemos cuidar nuestra manera de pensar.
3. ¿Qué debemos proteger?
REPASO
1. ¿Qué programa debemos mantener?
2. ¿Cómo protegemos nuestra capacidad de pensar?
3. ¿Qué aprendimos de Jehová?
CANCIÓN 20
Sigamos adelante
""",
        }

        article = parse_article(sample)
        data = article.to_dict()

        self.assertEqual(article.title, "CUIDEMOS NUESTRA AMISTAD CON JEHOVÁ")
        self.assertNotIn(article.title, article.detected_headings)
        self.assertNotIn("CANCIÓN 10", article.detected_headings)
        self.assertFalse(hasattr(article, "section_summary"))

        self.assertEqual(article.sections[0].subtitle, "")
        self.assertIsNone(article.sections[0].section_summary)
        self.assertEqual(
            article.sections[1].subtitle,
            "MANTÉN UN BUEN PROGRAMA DE ACTIVIDADES ESPIRITUALES",
        )
        self.assertEqual(
            article.sections[1].questions,
            ["¿Qué actividades debemos mantener?"],
        )
        self.assertEqual(article.sections[1].paragraph_numbers, [2])
        self.assertEqual(
            article.sections[2].subtitle,
            "PROTEGE TU CAPACIDAD DE PENSAR",
        )
        self.assertIsNone(article.sections[2].section_summary)
        self.assertEqual(
            article.review_questions,
            [
                "¿Qué programa debemos mantener?",
                "¿Cómo protegemos nuestra capacidad de pensar?",
                "¿Qué aprendimos de Jehová?",
            ],
        )
        self.assertEqual(data["sections"][1]["section_summary"], None)
        self.assertEqual(data["review_questions"], article.review_questions)

    def test_recovers_initial_paragraph_when_number_one_is_missing(self):
        sample = {
            "title": "Artículo de prueba",
            "text": """
ENCABEZADO UNO
ENCABEZADO DOS
ENCABEZADO TRES
ENCABEZADO CUATRO
ENCABEZADO CINCO
ENCABEZADO SEIS
El primer párrafo comienza directamente con su contenido narrativo.
Continúa en otra línea antes de que aparezca el siguiente número.
2 El segundo párrafo sí conserva su número visible.
1, 2. ¿Qué enseñan los primeros dos párrafos?
""",
        }

        article = parse_article(sample)

        self.assertEqual(article.sections[0].paragraph_numbers, [1, 2])
        self.assertEqual(
            article.sections[0].paragraphs[0].text,
            (
                "El primer párrafo comienza directamente con su contenido "
                "narrativo. Continúa en otra línea antes de que aparezca el "
                "siguiente número."
            ),
        )

    def test_separates_consecutive_numbered_questions(self):
        sample = {
            "title": "Artículo de prueba",
            "text": """
1 Primer párrafo.
2 Segundo párrafo.
3 Tercer párrafo.
1. ¿Qué aprendemos del primer párrafo?
2. ¿Qué aprendemos del segundo párrafo?
3. ¿Qué aprendemos del tercer párrafo?
ENCABEZADO UNO
ENCABEZADO DOS
ENCABEZADO TRES
ENCABEZADO CUATRO
""",
        }

        article = parse_article(sample)

        self.assertEqual(len(article.sections), 3)
        self.assertEqual(
            [section.paragraph_numbers for section in article.sections],
            [[1], [2], [3]],
        )

    def test_recognizes_question_mark_on_following_line(self):
        sample = {
            "title": "Artículo de prueba",
            "text": """
ENCABEZADO UNO
ENCABEZADO DOS
ENCABEZADO TRES
ENCABEZADO CUATRO
ENCABEZADO CINCO
ENCABEZADO SEIS
ENCABEZADO SIETE
19 Este párrafo ayuda a prepararnos.
19. Antes de empezar los estudios adicionales,
¿qué podemos hacer para estar preparados?
""",
        }

        article = parse_article(sample)

        self.assertEqual(len(article.sections), 1)
        self.assertEqual(
            article.sections[0].question,
            (
                "Antes de empezar los estudios adicionales, "
                "¿qué podemos hacer para estar preparados?"
            ),
        )
        self.assertEqual(article.sections[0].paragraph_numbers, [19])

    def test_keeps_combined_question_as_one_section(self):
        sample = {
            "title": "Artículo de prueba",
            "text": """
1 Primer párrafo.
2 Segundo párrafo.
1, 2. a) ¿Qué aprendemos del primer párrafo?
b) ¿Qué aprendemos del segundo párrafo?
ENCABEZADO UNO
ENCABEZADO DOS
ENCABEZADO TRES
ENCABEZADO CUATRO
ENCABEZADO CINCO
ENCABEZADO SEIS
""",
        }

        article = parse_article(sample)

        self.assertEqual(len(article.sections), 1)
        self.assertEqual(article.sections[0].paragraph_numbers, [1, 2])
        self.assertEqual(
            article.sections[0].question,
            (
                "a) ¿Qué aprendemos del primer párrafo? "
                "b) ¿Qué aprendemos del segundo párrafo?"
            ),
        )

    def test_does_not_treat_body_question_without_number_as_study_question(self):
        sample = {
            "title": "Artículo de prueba",
            "text": """
ENCABEZADO UNO
ENCABEZADO DOS
ENCABEZADO TRES
ENCABEZADO CUATRO
ENCABEZADO CINCO
1 Este párrafo contiene una reflexión.
¿Cómo podemos poner en práctica este consejo?
2 Este es el segundo párrafo.
1. ¿Qué contiene el primer párrafo?
2. ¿Qué contiene el segundo párrafo?
""",
        }

        article = parse_article(sample)

        self.assertEqual(len(article.sections), 2)
        self.assertEqual(
            [section.paragraph_numbers for section in article.sections],
            [[1], [2]],
        )

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

    def test_does_not_treat_date_heading_as_paragraph(self):
        sample = {
            "title": "Cuida tu espiritualidad mientras cursas estudios adicionales",
            "text": """
=== PÁGINA 1 ===
27 DE JULIO-2 DE AGOSTO DE 2026
CANCIÓN 56 Vive la verdad
Cuida tu espiritualidad mientras cursas estudios adicionales
“Sigamos andando correctamente por ese mismo camino” (FILIP. 3:16).
TEMA
Cuatro principios bíblicos que protegerán tu amistad con Jehová.
1. ¿De qué tendrás que asegurarte?
Respuesta
1 Debes mantener una estrecha relación con Jehová.
SEGUNDO PRINCIPIO
2. ¿Qué más debes hacer?
Respuesta
2 Mantén un buen programa de actividades espirituales.
""",
        }

        article = parse_article(sample)

        self.assertEqual(len(article.sections), 2)
        self.assertEqual(article.sections[0].paragraph_numbers, [1])
        self.assertEqual(article.sections[1].paragraph_numbers, [2])
        self.assertEqual(article.unassigned_paragraphs, [])
        self.assertEqual(article.conclusion, "")
        self.assertNotIn(
            "Quedaron 1 párrafos sin asignar a una pregunta.",
            article.parser_warnings,
        )


if __name__ == "__main__":
    unittest.main()
