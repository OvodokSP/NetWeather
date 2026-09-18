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
        self.assertEqual(
            sections,
            {"overview","resources","groups","alerts","map","probes","diagnostics","history","notifications","integrations","settings"},
        )

    def test_reference_overview_sections_exist(self):
        required = (
            "globalSearch","topSystemStatus","kpiGlobal","kpiRu","kpiPersonal","kpiIncidents",
            "streamChart","eventFeed","resourceCards","faultMap","overviewResourceTable",
            "faultPath","faultConclusion","faultResourceSelect","mapRegion","mapZoomIn","mapZoomOut",
        )
        for item in required:
            self.assertIn(f'id="{item}"', self.html)

    def test_reference_navigation_items_exist(self):
        for label in (
            "Обзор","Мониторинг","Инциденты","Карта сбоев","Точки наблюдения",
            "Отчёты","Уведомления","Интеграции","Настройки",
        ):
            self.assertIn(label, self.html)

    def test_actions_and_dialogs_exist(self):
        for item in (
            "resourceDialog","detailDialog","tokenDialog","diagTrace","diagTraceDomestic",
            "diagCheck","openAddResource","overviewAddResource","groupDialog","openAddGroup","groupForm",
            "sidebarAddResource","manageGroups","expandChart","enableNotifications",
        ):
            self.assertIn(f'id="{item}"', self.html)

    def test_overview_is_desktop_no_scroll(self):
        self.assertIn("html,body{margin:0;width:100%;height:100%;overflow:hidden", self.css)
        self.assertIn(".overview-view{height:100%;overflow:hidden}", self.css)
        self.assertIn(".overview-grid{height:100%;display:grid", self.css)

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
