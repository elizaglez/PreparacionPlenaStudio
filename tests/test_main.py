import unittest
from unittest.mock import Mock, patch

import main
from app.config import ROOT_DIR


class MainTests(unittest.TestCase):
    def test_loads_project_env_before_building_main_window(self):
        events = []
        application = Mock()
        application.exec.return_value = 0
        window = Mock()

        def load_environment(path):
            events.append(("load_dotenv", path))

        def create_application(arguments):
            events.append(("QApplication", arguments))
            return application

        def create_window():
            events.append(("MainWindow", None))
            return window

        with (
            patch.object(
                main,
                "load_dotenv",
                side_effect=load_environment,
            ) as load_dotenv,
            patch.object(
                main,
                "QApplication",
                side_effect=create_application,
            ),
            patch.object(
                main,
                "MainWindow",
                side_effect=create_window,
            ),
            patch.object(main.sys, "argv", ["preparacion-plena"]),
        ):
            result = main.main()

        self.assertEqual(
            events,
            [
                ("load_dotenv", ROOT_DIR / ".env"),
                ("QApplication", ["preparacion-plena"]),
                ("MainWindow", None),
            ],
        )
        load_dotenv.assert_called_once_with(ROOT_DIR / ".env")
        application.setApplicationName.assert_called_once_with(
            "Preparación Plena Studio"
        )
        application.setOrganizationName.assert_called_once_with(
            "Preparación Plena"
        )
        application.setStyleSheet.assert_called_once_with(
            main.APP_STYLESHEET
        )
        window.show.assert_called_once_with()
        application.exec.assert_called_once_with()
        self.assertEqual(result, 0)


if __name__ == "__main__":
    unittest.main()
