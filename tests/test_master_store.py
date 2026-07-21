import json
import tempfile
import unittest
from pathlib import Path

from app.editor.master_store import MasterStore


class MasterStoreTests(unittest.TestCase):
    def make_store(self):
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        work = root / "trabajo"
        work.mkdir(parents=True)
        (work / "master.json").write_text(
            json.dumps(
                {
                    "title": "MASTER",
                    "answers": [
                        {
                            "number": 1,
                            "question": "¿Qué aprendemos?",
                            "answer": "Respuesta inicial",
                        }
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        return temporary, MasterStore(root)

    def test_load_adds_pending_status(self):
        temporary, store = self.make_store()
        try:
            self.assertEqual(
                store.load()["answers"][0]["status"],
                "pending",
            )
        finally:
            temporary.cleanup()

    def test_update_answer_marks_edited(self):
        temporary, store = self.make_store()
        try:
            updated = store.update_answer(
                1,
                {"answer": "Respuesta editada"},
            )
            self.assertEqual(updated["answer"], "Respuesta editada")
            self.assertEqual(updated["status"], "edited")
        finally:
            temporary.cleanup()

    def test_progress_counts_approved(self):
        temporary, store = self.make_store()
        try:
            store.set_status(1, "approved")
            progress = store.progress()
            self.assertEqual(progress["approved"], 1)
            self.assertEqual(progress["total"], 1)
        finally:
            temporary.cleanup()


if __name__ == "__main__":
    unittest.main()
