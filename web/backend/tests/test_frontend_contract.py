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

    def test_dom_ids_are_unique(self):
        ids = re.findall(r'id="([A-Za-z0-9_-]+)"', self.html)
        duplicates = sorted({item for item in ids if ids.count(item) > 1})
        self.assertEqual(duplicates, [], "Duplicate DOM ids: %s" % duplicates)

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
            "ackAllIncidents","resourceIdentityPreview","resourceTargetHint",
            "resourceCatalogForm","catalogSearch","resourceCatalogGroups","customResourceTarget",
            "customResourceName","customResourceGroup","customCatalogMatch","addCatalogResources","resourceEditDialog",
        ):
            self.assertIn(f'id="{item}"', self.html)

    def test_ranked_catalog_picker_contract(self):
        for token in (
            "function openResourceCatalog(", "function renderCatalog(", "function inspectCustomResource(",
            "/api/resource-catalog", "/api/resource-catalog/match?target=", "/api/resource-catalog/add",
        ):
            self.assertIn(token, self.js)
        self.assertIn(".resource-catalog-groups{", self.css)
        self.assertIn(".catalog-resource-row{", self.css)
        self.assertIn(".custom-resource-block{", self.css)
        self.assertIn("Добавить выбранные", self.html)

    def test_resource_identity_and_incident_read_handlers_exist(self):
        self.assertIn("function targetMeta(", self.js)
        self.assertIn("syncResourceIdentity", self.js)
        self.assertIn("/api/target-meta?target=", self.js)
        self.assertIn("hydrateResourceIcons", self.js)
        self.assertIn("/api/incidents/ack-all", self.js)
        self.assertIn("data-ack", self.js)
        self.assertIn("resource-logo-img", self.css)

    def test_availability_axis_matches_reference_bands(self):
        self.assertIn("var ticks=[100,99,98,95,90]", self.js)
        self.assertIn("function availabilityY(", self.js)

    def test_overview_resource_window_scrolls(self):
        self.assertIn(".compact-table{", self.css)
        self.assertIn("overflow-y:auto", self.css)
        self.assertIn("var visible=rows;", self.js)
        self.assertNotIn("var visible=rows.slice(0,6)", self.js)

    def test_reference_typography_tokens_are_global(self):
        self.assertIn('--nw-font:"Inter","Segoe UI",Roboto,Arial,sans-serif', self.css)
        self.assertIn("html,body,button,input,select,textarea{font-family:var(--nw-font)}", self.css)

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
