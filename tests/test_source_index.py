import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from apk_audit.contracts import Rule
from apk_audit.source_index import SourceIndex


class SourceIndexTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "workspace"
        self.root.mkdir()
        self.cache = self.base / "cache"

    def write(self, relative, text):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def build(self, digest="fixture"):
        return SourceIndex.build(self.root, digest, self.cache)

    def rule(self, area="language"):
        return Rule(id="ADS_" + area.upper(), title="Check", mode="agent", area=area)

    def test_placement_in_obfuscated_file_beats_unrelated_screen_name(self):
        self.write("sources/a/b.java", 'class b {\n public void a() {\n  load("native_language_click");\n }\n}\n')
        self.write("sources/demo/LanguageActivity.java", 'class LanguageActivity { String splash = "inter_splash"; }')
        bundle = self.build().bundle(self.rule(), {}, {"code_references": {
            "native_language_click": [{"file": "sources/a/b.java", "line": 3}]}})
        self.assertEqual(bundle["snippets"][0]["file"], "sources/a/b.java")
        self.assertTrue(any('load("native_language_click")' in line["text"]
                            for line in bundle["snippets"][0]["lines"]))
        self.assertTrue(bundle["heuristic"])
        self.assertIn("workspace", bundle["search_guidance"])

    def test_manifest_application_and_config_references_are_preserved(self):
        self.write("resources/AndroidManifest.xml", '<manifest><application name="demo.App"/></manifest>')
        self.write("sources/demo/App.java", 'class App { public void onCreate() { a(); } }')
        self.write("sources/z/c.java", 'class c { String a = "ad_config_debug.json"; }')
        facts = {"manifest": {"file": "resources/AndroidManifest.xml",
                              "application_file": "sources/demo/App.java"}}
        bundle = self.build().bundle(self.rule("init"), facts, {"config_references": {
            "ad_config_debug.json": [{"file": "sources/z/c.java", "line": 1}]}})
        files = {snippet["file"] for snippet in bundle["snippets"]}
        self.assertEqual(files, {"resources/AndroidManifest.xml", "sources/demo/App.java", "sources/z/c.java"})

    def test_lexical_methods_and_strings_supply_locations_without_inventory(self):
        self.write("sources/x/y.java", 'class y {\n public void registerActivityLifecycleCallbacks() {\n  String a = "FirebaseRemoteConfig";\n }\n}\n')
        index = self.build()
        bundle = index.bundle(self.rule("remote_config"), {}, {})
        self.assertEqual(bundle["snippets"][0]["file"], "sources/x/y.java")
        self.assertGreater(index.stats["methods_indexed"], 0)
        self.assertGreater(index.stats["strings_indexed"], 0)
        snippet = bundle["snippets"][0]
        self.assertEqual(snippet["start"], snippet["lines"][0]["line"])
        self.assertEqual(snippet["lines"][0]["line"], 1)

    def test_json_budget_counts_unicode_escaping_and_marks_omitted_evidence(self):
        for number in range(20):
            self.write(f"sources/a/C{number}.java", 'class C {\n' +
                       ' String a = "native_language_' + '漢\\\"' * 500 + '";\n}\n')
        index = self.build()
        for limit in (700, 1200, 2200, 20000):
            with self.subTest(limit=limit):
                bundle = index.bundle(self.rule(), {}, {}, max_chars=limit)
                self.assertLessEqual(len(json.dumps(bundle, ensure_ascii=False)), limit)
                self.assertTrue(bundle["truncated"])
                self.assertGreater(bundle["coverage"]["files_indexed"], 0)
                self.assertGreater(bundle["coverage"]["candidate_files"], 0)
        with self.assertRaises(ValueError):
            index.bundle(self.rule(), {}, {}, max_chars=1)

    def test_warm_cache_reuses_scan_and_tracks_current_workspace_root(self):
        self.write("sources/a/b.java", 'class b { String a = "native_language"; }')
        cold = self.build()
        self.assertFalse(cold.cache_hit)
        moved = self.base / "moved"
        shutil.move(self.root, moved)
        with patch.object(SourceIndex, "_scan", side_effect=AssertionError("must reuse index")):
            warm = SourceIndex.build(moved, "fixture", self.cache)
        self.assertTrue(warm.cache_hit)
        self.assertEqual(cold.stats["files_indexed"], warm.stats["files_indexed"])
        self.assertIn("native_language", str(warm.bundle(self.rule(), {}, {})["snippets"]))

    def test_corrupt_cache_and_policy_change_require_rebuild(self):
        self.write("sources/a/b.java", 'class b { String a = "native_language"; }')
        self.build()
        caches = list(self.cache.rglob("*.json"))
        self.assertEqual(len(caches), 1)
        caches[0].write_text('{"files": "broken"}')
        self.assertFalse(self.build().cache_hit)
        self.assertTrue(self.build().cache_hit)
        with patch("apk_audit.source_index.INDEX_POLICY", "different-policy"):
            changed = self.build()
        self.assertFalse(changed.cache_hit)
        self.assertEqual(len(list(self.cache.rglob("*.json"))), 2)
        self.assertFalse(self.build("changed-hash").cache_hit)

    def test_symlink_escape_and_inventory_path_injection_are_ignored(self):
        outside = self.base / "secret.java"
        outside.write_text('class Secret { String a = "native_language_SECRET"; }')
        self.write("sources/a/b.java", 'class b { String a = "native_language"; }')
        (self.root / "sources/out.java").symlink_to(outside)
        (self.root / "escape").symlink_to(self.base, target_is_directory=True)
        index = self.build()
        bundle = index.bundle(self.rule(), {"manifest": {"application_file": "../secret.java"}},
                              {"code_references": {"native_language": [
                                  {"file": "../secret.java", "line": 1},
                                  {"file": str(outside), "line": 1},
                                  {"file": "sources/out.java", "line": 1}]}})
        self.assertEqual(index.stats["files_indexed"], 1)
        self.assertNotIn("SECRET", json.dumps(bundle))
        self.assertEqual([snippet["file"] for snippet in bundle["snippets"]], ["sources/a/b.java"])

    def test_source_changed_to_external_symlink_after_index_is_not_read(self):
        path = self.write("sources/a/b.java", 'class b { String a = "native_language"; }')
        index = self.build()
        outside = self.base / "secret.java"
        outside.write_text('class Secret { String a = "native_language_SECRET"; }')
        path.unlink()
        path.symlink_to(outside)
        bundle = index.bundle(self.rule(), {}, {})
        self.assertEqual(bundle["snippets"], [])
        self.assertTrue(bundle["truncated"])

    def test_large_source_is_streamed_and_snippet_does_not_include_whole_library(self):
        self.write("sources/a/Large.java", "// padding\n" * 12000 +
                   'class a { void a() { load("native_language"); } }\n' + "// padding\n" * 12000)
        index = self.build()
        bundle = index.bundle(self.rule(), {}, {})
        self.assertEqual(bundle["coverage"]["files_indexed"], 1)
        self.assertTrue(any(line["line"] == 12001 for snippet in bundle["snippets"] for line in snippet["lines"]))
        self.assertLess(sum(len(s["lines"]) for s in bundle["snippets"]), 100)
        self.assertTrue(bundle["truncated"])

    def test_cache_with_escaping_path_is_rebuilt_without_reading_external_source(self):
        self.write("sources/a/b.java", 'class b { String a = "native_language"; }')
        self.build()
        cache = next(self.cache.glob("*.json"))
        data = json.loads(cache.read_text())
        data["files"][0]["file"] = "../secret.java"
        cache.write_text(json.dumps(data))
        index = self.build()
        self.assertFalse(index.cache_hit)
        self.assertEqual(index.bundle(self.rule(), {}, {})["snippets"][0]["file"], "sources/a/b.java")

    def test_missing_or_non_boolean_cached_truncation_is_rebuilt(self):
        self.write("sources/a/b.java", 'class b { String a = "native_language"; }')
        self.build()
        cache = next(self.cache.glob("*.json"))
        original = cache.read_text()
        for value in ("missing", None, 0, 1, "false", [], {}):
            with self.subTest(truncated=value):
                data = json.loads(original)
                if value == "missing":
                    del data["files"][0]["truncated"]
                else:
                    data["files"][0]["truncated"] = value
                cache.write_text(json.dumps(data))
                rebuilt = self.build()
                self.assertFalse(rebuilt.cache_hit)
                bundle = rebuilt.bundle(self.rule(), {}, {})
                self.assertEqual(bundle["snippets"][0]["file"], "sources/a/b.java")
                self.assertIs(type(bundle["snippets"][0]["truncated"]), bool)
                self.assertTrue(self.build().cache_hit)

    def test_missing_or_invalid_cached_statistics_are_rebuilt(self):
        self.write("sources/a/b.java", 'class b { String a = "native_language"; }')
        self.build()
        cache = next(self.cache.glob("*.json"))
        original = cache.read_text()
        for field in json.loads(original)["stats"]:
            for value in ("missing", None, True, -1, 1.5, "1", [], {}):
                with self.subTest(field=field, value=value):
                    data = json.loads(original)
                    if value == "missing":
                        del data["stats"][field]
                    else:
                        data["stats"][field] = value
                    cache.write_text(json.dumps(data))
                    rebuilt = self.build()
                    self.assertFalse(rebuilt.cache_hit)
                    self.assertEqual(rebuilt.bundle(self.rule(), {}, {})["coverage"]["files_indexed"], 1)

    def test_no_hit_is_not_reported_as_workspace_coverage(self):
        self.write("sources/demo/Unrelated.java", 'class Unrelated { int counter = 1; }')
        bundle = self.build().bundle(self.rule("remote_config"), {}, {})
        self.assertEqual(bundle["coverage"]["files_indexed"], 1)
        self.assertEqual(bundle["coverage"]["candidate_files"], 0)
        self.assertEqual(bundle["snippets"], [])
        self.assertTrue(bundle["heuristic"])

    def test_noisy_sdk_vocabulary_does_not_expand_cache(self):
        for number in range(120):
            noise = '\n'.join(f' public void unrelated{number}x{item}() {{ String q = "opaque{number}x{item}"; }}'
                              for item in range(140))
            self.write(f"sources/vendor/sdk/C{number}.java", "class C {\n" + noise + "\n}")
        self.write("sources/x/y.java", 'class y { void a() { load("native_language"); } }')
        index = self.build()
        cache_size = sum(path.stat().st_size for path in self.cache.glob("*.json"))
        self.assertLess(cache_size, 100000)
        self.assertEqual(index.stats["files_indexed"], 121)
        bundle = index.bundle(self.rule(), {}, {})
        self.assertEqual(bundle["snippets"][0]["file"], "sources/x/y.java")
        self.assertTrue(bundle["coverage"]["index_filtered"])
        self.assertIn("vocabulary", bundle["limitations"])

    def test_relevant_symbol_storage_is_bounded_and_custom_placements_remain_searchable(self):
        declarations = '\n'.join(f' public void loadNative{number}() {{ String q = "native_rare_slot_{number}"; }}'
                                 for number in range(100))
        self.write("sources/x/y.java", "class y {\n" + declarations + "\n}")
        index = self.build()
        self.assertLessEqual(index.stats["methods_indexed"], 16)
        self.assertLessEqual(index.stats["strings_indexed"], 16)
        custom_rule = Rule(id="CUSTOM", title="Custom", mode="agent", area="custom", question="native_rare_slot_99")
        bundle = index.bundle(custom_rule, {}, {})
        self.assertTrue(any("native_rare_slot_99" in line["text"] for snippet in bundle["snippets"] for line in snippet["lines"]))

    def test_inventory_can_locate_arbitrary_keys_outside_limited_vocabulary(self):
        self.write("sources/x/y.java", 'class y { String q = "opaque_partner_key"; }')
        bundle = self.build().bundle(self.rule("config"), {}, {"code_references": {
            "opaque_partner_key": [{"file": "sources/x/y.java", "line": 1}]}})
        self.assertEqual(bundle["snippets"][0]["file"], "sources/x/y.java")

    def test_warm_cache_rejects_parent_symlink_to_external_source(self):
        self.write("sources/x/y.java", 'class y { String q = "native_language"; }')
        self.build()
        shutil.move(self.root / "sources/x", self.base / "external")
        (self.root / "sources/x").symlink_to(self.base / "external", target_is_directory=True)
        rebuilt = self.build()
        self.assertFalse(rebuilt.cache_hit)
        self.assertEqual(rebuilt.bundle(self.rule(), {}, {})["snippets"], [])

    def test_hardcoded_ad_ids_and_custom_firebase_events_remain_lexical_leads(self):
        self.write("sources/x/a.java", 'class a { String q = "ca-app-pub-1234567890123456/1234567890"; }')
        self.write("sources/x/b.java", 'class b { String q = "partner_custom_scr_view"; }')
        index = self.build()
        config = index.bundle(self.rule("config"), {}, {})
        self.assertIn("sources/x/a.java", {s["file"] for s in config["snippets"]})
        event = Rule(id="EVENT", title="Event", mode="agent", area="general", question="partner_custom_scr_view")
        event_bundle = index.bundle(event, {}, {})
        self.assertIn("sources/x/b.java", {s["file"] for s in event_bundle["snippets"]})
        self.assertEqual(event_bundle["coverage"]["vocabulary_policy"], index.policy)


if __name__ == "__main__":
    unittest.main()
