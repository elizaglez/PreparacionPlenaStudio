import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.models import Project, ProjectSources
from app.pages.new_project_page import NewProjectPage


class NewProjectPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def setUp(self):
        self.page = NewProjectPage()
        self.page.name.setText("Proyecto funcional")
        self.page.pdf.set_value("C:/fuentes/articulo.pdf")
        self.page.audio.set_value("C:/fuentes/audio.mp3")
        self.page.bible.set_value("C:/fuentes/citas.txt")
        self.page.destination.set_value("C:/proyectos")

    def tearDown(self):
        self.page.close()

    def test_successful_creation_emits_same_project_instance(self):
        project = Project(
            name="Proyecto funcional",
            root="C:/proyectos/Proyecto funcional",
            status="nuevo",
            created_at="2026-07-28T10:00:00-06:00",
            updated_at="2026-07-28T10:00:00-06:00",
            sources=ProjectSources(
                pdf="fuente/articulo.pdf",
                audio="fuente/audio.mp3",
                bible="fuente/citas.txt",
            ),
            outputs={
                "article": "trabajo/articulo.json",
            },
        )
        received = []
        self.page.project_created.connect(received.append)

        with (
            patch(
                "app.pages.new_project_page.create_project",
                return_value=project,
            ) as create_project,
            patch(
                "app.pages.new_project_page.QMessageBox.information",
            ) as information,
        ):
            self.page.create()

        create_project.assert_called_once_with(
            "Proyecto funcional",
            "C:/proyectos",
            "C:/fuentes/articulo.pdf",
            "C:/fuentes/audio.mp3",
            "C:/fuentes/citas.txt",
        )
        information.assert_called_once_with(
            self.page,
            "Proyecto creado",
            project.root,
        )

        self.assertEqual(len(received), 1)
        self.assertIs(received[0], project)
        self.assertIsInstance(received[0], Project)
        self.assertNotEqual(received[0], {})
        self.assertEqual(received[0].name, "Proyecto funcional")
        self.assertEqual(
            received[0].sources.pdf,
            "fuente/articulo.pdf",
        )
        self.assertEqual(
            received[0].outputs["article"],
            "trabajo/articulo.json",
        )

        self.assertEqual(self.page.name.text(), "")
        self.assertEqual(self.page.pdf.value(), "")
        self.assertEqual(self.page.audio.value(), "")
        self.assertEqual(self.page.bible.value(), "")
        self.assertEqual(self.page.destination.value(), "C:/proyectos")
        self.assertTrue(self.page.create_button.isEnabled())


if __name__ == "__main__":
    unittest.main()
