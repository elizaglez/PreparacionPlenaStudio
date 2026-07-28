import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.pages.settings_page import SettingsPage
from app.security.secret_loader import SecretLoader


class SettingsPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def setUp(self):
        self.settings = {
            "default_projects_folder": "projects",
            "theme": "dark",
            "language": "es",
            "openai_model": "gpt-5-mini",
        }

    def create_page(self, root: Path):
        save_settings = Mock()
        patches = [
            patch(
                "app.pages.settings_page.ROOT_DIR",
                root,
            ),
            patch(
                "app.pages.settings_page.load_settings",
                return_value=dict(self.settings),
            ),
            patch(
                "app.pages.settings_page.load_methodology",
                return_value={},
            ),
            patch(
                "app.pages.settings_page.save_settings",
                save_settings,
            ),
            patch(
                "app.pages.settings_page.QMessageBox.information",
            ),
        ]
        active = [item.start() for item in patches]
        self.addCleanup(
            lambda: [item.stop() for item in reversed(patches)]
        )
        page = SettingsPage()
        self.addCleanup(page.close)
        return page, save_settings, active[-1]

    def test_saved_api_key_is_available_without_restarting(self):
        secret = "clave-nueva-de-prueba"

        with (
            tempfile.TemporaryDirectory() as temporary,
            patch.dict(os.environ, {}, clear=False),
        ):
            os.environ.pop("OPENAI_API_KEY", None)
            root = Path(temporary)
            page, save_settings, information = self.create_page(root)
            page.api_key.setText(f"  {secret}  ")

            page.save()

            self.assertEqual(
                SecretLoader().get_secret("OPENAI_API_KEY"),
                secret,
            )
            self.assertEqual(
                (root / ".env").read_text(encoding="utf-8"),
                f"OPENAI_API_KEY={secret}\n",
            )
            self.assertEqual(page.api_key.text(), "")
            save_settings.assert_called_once()
            information.assert_called_once()

    def test_replaces_existing_key_without_duplicating_it(self):
        old_secret = "clave-anterior"
        new_secret = "clave-actualizada"

        with (
            tempfile.TemporaryDirectory() as temporary,
            patch.dict(
                os.environ,
                {"OPENAI_API_KEY": old_secret},
                clear=False,
            ),
        ):
            root = Path(temporary)
            (root / ".env").write_text(
                (
                    "OTRA_VARIABLE=valor\n"
                    f"OPENAI_API_KEY={old_secret}\n"
                ),
                encoding="utf-8",
            )
            page, _, _ = self.create_page(root)
            page.api_key.setText(new_secret)

            page.save()

            env_text = (root / ".env").read_text(encoding="utf-8")
            self.assertEqual(
                env_text,
                (
                    "OTRA_VARIABLE=valor\n"
                    f"OPENAI_API_KEY={new_secret}\n"
                ),
            )
            self.assertEqual(
                env_text.count("OPENAI_API_KEY="),
                1,
            )
            self.assertEqual(
                os.environ["OPENAI_API_KEY"],
                new_secret,
            )

    def test_blank_key_does_not_change_file_or_environment(self):
        existing_secret = "clave-existente"

        with (
            tempfile.TemporaryDirectory() as temporary,
            patch.dict(
                os.environ,
                {"OPENAI_API_KEY": existing_secret},
                clear=False,
            ),
        ):
            root = Path(temporary)
            env_path = root / ".env"
            original = f"OPENAI_API_KEY={existing_secret}\n"
            env_path.write_text(original, encoding="utf-8")
            page, save_settings, _ = self.create_page(root)
            page.api_key.setText("   ")

            page.save()

            self.assertEqual(
                env_path.read_text(encoding="utf-8"),
                original,
            )
            self.assertEqual(
                os.environ["OPENAI_API_KEY"],
                existing_secret,
            )
            save_settings.assert_called_once()


if __name__ == "__main__":
    unittest.main()
