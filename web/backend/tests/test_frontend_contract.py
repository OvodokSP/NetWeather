import re
import unittest
from pathlib import Path


class FrontendContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.html = (cls.root / "frontend" / "index.html").read_text(encoding="utf-8")
        cls.js = (cls.root / "frontend" / "assets" / "dashboard.js").read_text(encoding="utf-8")
        cls.css = (cls.root / "frontend" / "assets" / "dashboard.css").read_text(encoding="utf-8")

    def test_every_js_id_exists_in_html(self):
        referenced = set(re.findall(r'q\("#([A-Za-z0-9_-]+)"\)', self.js))
        declared = set(re.findall(r'id="([A-Za-z0-9_-]+)"', self.html))
        missing = sorted(referenced - declared)
        self.assertEqual(missing, [], "JS references missing DOM ids: %s" % missing)

    def test_navigation_views_exist(self):
        views = set(re.findall(r'data-view="([A-Za-z0-9_-]+)"', self.html))
        sections = set(re.findall(r'id="view-([A-Za-z0-9_-]+)"', self.html))
        self.assertTrue(views.issubset(sections))
        self.assertEqual(sections, {"overview","resources","alerts","diagnostics","history","settings"})

    def test_dashboard_core_sections_exist(self):
        required = (
            "globalSearch","topSystemStatus","kpiGlobal","kpiRu","kpiPersonal","kpiIncidents",
            "streamChart","eventFeed","resourceCards","faultMap","overviewResourceTable",
            "faultPath","faultConclusion","faultResourceSelect"
        )
        for item in required:
            self.assertIn(f'id="{item}"', self.html)

    def test_actions_and_dialogs_exist(self):
        for item in (
            "resourceDialog","detailDialog","tokenDialog","checkAll","diagTrace",
            "diagTraceDomestic","diagCheck","openAddResource","overviewAddResource",
            "faultTraceVps","faultTraceRu"
        ):
            self.assertIn(f'id="{item}"', self.html)

    def test_no_runtime_cdn_dependency(self):
        lower = self.html.lower()
        self.assertNotIn("cdn.jsdelivr", lower)
        self.assertNotIn("fonts.googleapis", lower)
        self.assertIn('/assets/dashboard.js', self.html)
        self.assertIn('/assets/dashboard.css', self.html)

    def test_no_inline_fake_metrics(self):
        self.assertNotRegex(self.html, r'>\s*9[0-9](?:\.\d+)?%\s*<')
        self.assertIn('id="kpiGlobal">—</strong>', self.html)
        self.assertIn('id="kpiRu">—</strong>', self.html)


if __name__ == "__main__":
    unittest.main()
