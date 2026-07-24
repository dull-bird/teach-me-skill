#!/usr/bin/env python3
"""Tests for import provenance (origin) tracking.

Imported knowledge must stay distinguishable from knowledge Teach Me
accumulates natively: notes, concept state, and knowledge-tree nodes all
carry the `origin` block, and provenance is first-wins.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
TEACH_ME_SCRIPT = REPO_ROOT / "skills" / "teach-me" / "scripts" / "teach_me.py"


class ImportProvenanceTests(unittest.TestCase):
    def run_teach_me(self, env: dict[str, str], *args: str, input_data: str | None = None) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(TEACH_ME_SCRIPT), *args],
            capture_output=True,
            text=True,
            env=env,
            input=input_data,
            timeout=30,
        )

    def make_env(self, tmp: str, lang: str = "zh") -> tuple[dict[str, str], Path]:
        home = Path(tmp) / "teach_me_home"
        home.mkdir()
        vault = home / "vault"
        vault.mkdir()
        (vault / ".teach-me").mkdir(parents=True)

        config = {
            "version": 2,
            "current_user": "default",
            "users": {
                "default": {
                    "name": "Default User",
                    "github": None,
                    "vault_path": str(vault),
                    "language": lang,
                    "max_notes_per_phase": 3,
                    "git_sync": {"enabled": False, "remote": "", "branch": "main", "auto_sync": False},
                    "initialized": True,
                }
            },
        }
        (home / "config.json").write_text(json.dumps(config))
        env = os.environ.copy()
        env["TEACH_ME_HOME"] = str(home)
        return env, vault

    def make_obsidian_vault(self, tmp: str) -> Path:
        vault = Path(tmp) / "deeporbit_vault"
        (vault / "40_Wiki").mkdir(parents=True)
        (vault / "99_System" / "Templates").mkdir(parents=True)
        (vault / "40_Wiki" / "Event Sourcing.md").write_text(
            "---\nauthor: ai\n---\n# Event Sourcing\n\nState as an append-only log of events.",
            encoding="utf-8",
        )
        (vault / "99_System" / "Templates" / "Noise.md").write_text(
            "# System noise\n\nShould never be imported.", encoding="utf-8"
        )
        return vault

    def read_state(self, vault: Path) -> dict:
        return json.loads((vault / ".teach-me" / "learning-state.json").read_text())

    def test_import_output_carries_origin_block(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env, _ = self.make_env(tmp)
            source = self.make_obsidian_vault(tmp)
            result = self.run_teach_me(
                env, "import", "--source", "obsidian", "--path", str(source),
                "--project", "DeepOrbit Vault", "--json",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            output = json.loads(result.stdout)
            origin = output.get("origin")
            self.assertIsNotNone(origin)
            self.assertEqual(origin["kind"], "import")
            self.assertEqual(origin["source_type"], "obsidian")
            self.assertEqual(origin["source_path"], str(source))
            self.assertEqual(origin["vault_name"], "DeepOrbit Vault")
            self.assertTrue(origin["import_id"].startswith("import-"))
            # The prompt must instruct the agent to pass origin through.
            self.assertIn('"origin"', output["prompt_for_ai"])
            self.assertIn(origin["import_id"], output["prompt_for_ai"])
            # Per-note metadata is exposed for item-level provenance.
            meta = output.get("note_meta")
            self.assertEqual(len(meta), 1)
            self.assertEqual(meta[0]["path"], "40_Wiki/Event Sourcing.md")
            self.assertTrue(meta[0].get("updated"))
            self.assertIn("SOURCE NOTES", output["prompt_for_ai"])

    def test_obsidian_import_skips_deeporbit_system_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env, _ = self.make_env(tmp)
            source = self.make_obsidian_vault(tmp)
            result = self.run_teach_me(
                env, "import", "--source", "obsidian", "--path", str(source),
                "--project", "DeepOrbit Vault", "--json",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            output = json.loads(result.stdout)
            self.assertEqual(output.get("note_count"), 1)
            skipped = output.get("skipped_paths", [])
            self.assertTrue(any("99_System" in path for path in skipped))

    def test_capture_with_origin_marks_note_and_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env, vault = self.make_env(tmp)
            origin = {
                "kind": "import",
                "source_type": "obsidian",
                "source_path": "/home/user/MyVault",
                "vault_name": "MyVault",
                "import_id": "import-20260724-120000",
            }
            item_origin = {
                "source_note": "40_Wiki/Event Sourcing.md",
                "source_created": "2026-06-01",
                "source_updated": "2026-07-20",
            }
            payload = {
                "project": {"name": "MyVault", "path": "/home/user/MyVault"},
                "phase": "external import",
                "origin": origin,
                "items": [
                    {
                        "type": "concept",
                        "title": "event sourcing",
                        "one_line": "State as an append-only log of events.",
                        "mastery": "seen",
                        "origin": item_origin,
                    }
                ],
            }
            result = self.run_teach_me(env, "capture", input_data=json.dumps(payload))
            self.assertEqual(result.returncode, 0, result.stderr)

            note = vault / "02_Concepts" / "event-sourcing.md"
            text = note.read_text(encoding="utf-8")
            # Dedicated external-vault frontmatter block.
            self.assertIn("external: true", text)
            self.assertIn("origin: import", text)
            self.assertIn("external_vault: MyVault", text)
            self.assertIn('external_vault_path: "/home/user/MyVault"', text)
            self.assertIn('source_path: "40_Wiki/Event Sourcing.md"', text)
            self.assertIn("source_created: 2026-06-01", text)
            self.assertIn("source_updated: 2026-07-20", text)
            self.assertIn("import_id: import-20260724-120000", text)
            self.assertIn("**Origin:** imported from MyVault", text)
            # Still a teach-me note, so re-import filters keep working.
            self.assertIn("type: teach-me/concept", text)

            state = self.read_state(vault)
            concept_origin = state["concepts"]["event sourcing"].get("origin")
            self.assertIsNotNone(concept_origin)
            self.assertEqual(concept_origin["import_id"], "import-20260724-120000")
            self.assertEqual(concept_origin["source_note"], "40_Wiki/Event Sourcing.md")
            tree_origin = state["knowledge_tree"]["event sourcing"].get("origin")
            self.assertEqual(tree_origin["vault_name"], "MyVault")

    def test_origin_is_first_wins(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env, vault = self.make_env(tmp)
            origin = {"kind": "import", "source_type": "obsidian", "vault_name": "MyVault",
                      "import_id": "import-20260724-120000"}
            first = {"origin": origin, "items": [{"title": "cqrs", "one_line": "Split reads and writes."}]}
            second = {"items": [{"title": "cqrs", "one_line": "Learned natively later."}]}
            result = self.run_teach_me(env, "capture", input_data=json.dumps(first))
            self.assertEqual(result.returncode, 0, result.stderr)
            result = self.run_teach_me(env, "capture", input_data=json.dumps(second))
            self.assertEqual(result.returncode, 0, result.stderr)

            state = self.read_state(vault)
            self.assertEqual(state["concepts"]["cqrs"]["origin"]["import_id"], "import-20260724-120000")
            self.assertEqual(state["knowledge_tree"]["cqrs"]["origin"]["vault_name"], "MyVault")

    def test_capture_without_origin_has_no_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env, vault = self.make_env(tmp)
            payload = {"items": [{"title": "idempotency", "one_line": "Safe to retry."}]}
            result = self.run_teach_me(env, "capture", input_data=json.dumps(payload))
            self.assertEqual(result.returncode, 0, result.stderr)
            note = (vault / "02_Concepts" / "idempotency.md").read_text(encoding="utf-8")
            self.assertNotIn("origin:", note)
            self.assertNotIn("external:", note)
            state = self.read_state(vault)
            self.assertNotIn("origin", state["concepts"]["idempotency"])

    def test_assess_with_origin_marks_tree_node(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env, vault = self.make_env(tmp)
            origin = {"kind": "import", "source_type": "obsidian", "vault_name": "ResearchVault",
                      "import_id": "import-20260724-130000"}
            payload = {
                "origin": origin,
                "nodes": [{"title": "backpressure", "mastery": "seen", "confidence": 0.5}],
            }
            result = self.run_teach_me(env, "assess", input_data=json.dumps(payload))
            self.assertEqual(result.returncode, 0, result.stderr)
            state = self.read_state(vault)
            node_origin = state["knowledge_tree"]["backpressure"].get("origin")
            self.assertIsNotNone(node_origin)
            self.assertEqual(node_origin["vault_name"], "ResearchVault")

    def test_import_fills_dedicated_obsidian_vault_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env, _ = self.make_env(tmp)
            source = self.make_obsidian_vault(tmp)
            result = self.run_teach_me(
                env, "import", "--source", "obsidian", "--path", str(source),
                "--project", "DeepOrbit Vault", "--json",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            status = self.run_teach_me(env, "status")
            data = json.loads(status.stdout)
            resolved = str(source.resolve())
            self.assertEqual(data["obsidian_vault_path"], resolved)
            self.assertEqual(data["linked_vaults"][0]["path"], resolved)

    def test_configure_obsidian_vault_overrides(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env, _ = self.make_env(tmp)
            other = Path(tmp) / "other_vault"
            other.mkdir()
            result = self.run_teach_me(env, "configure", "--obsidian-vault", str(other))
            self.assertEqual(result.returncode, 0, result.stderr)
            status = json.loads(self.run_teach_me(env, "status").stdout)
            self.assertEqual(status["obsidian_vault_path"], str(other.resolve()))


if __name__ == "__main__":
    unittest.main()
