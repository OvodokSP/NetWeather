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
            "globalSearch","topSystemStatus","kpiGlobal","kpiResources","kpiLatency","kpiRu","kpiPersonal","kpiIncidents",
            "streamChart","eventFeed","resourceCards","faultMap","overviewResourceTable",
            "faultPath","faultConclusion","faultResourceSelect","mapRegion","mapZoomIn","mapZoomOut",
            "overviewFreshness","overviewResourceSummary","eventSummary",
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
            "resourceDialog","detailDialog","diagTrace","diagTraceDomestic",
            "diagCheck","openAddResource","overviewAddResource","groupDialog","openAddGroup","groupForm",
            "sidebarAddResource","manageGroups","checkAllResources","enableNotifications",
            "ackAllIncidents","resourceIdentityPreview","resourceTargetHint",
            "resourceCatalogForm","catalogSearch","resourceCatalogGroups","customResourceTarget",
            "customResourceName","customResourceGroup","customCatalogMatch","addCatalogResources","resourceEditDialog",
            "customizeOverview","dashboardPreferencesDialog","dashboardPreferencesForm","pinnedResourceGroups",
            "pinnedResourceCount","dashboardPanelChoices","resetDashboardPreferences",
            "confirmDialog","confirmTitle","confirmMessage","confirmHint","confirmCancel","confirmAccept",
        ):
            self.assertIn(f'id="{item}"', self.html)

    def test_interaction_contract(self):
        for token in (
            "function openDialog(", "function closeDialog(", "function setupDialogs(",
            "function setBusy(", "function withBusy(", "function confirmAction(",
            "function handleSearchKeydown(", "aria-busy", "dataset.locked",
        ):
            self.assertIn(token, self.js)
        self.assertNotRegex(self.js, r'\bconfirm\(')
        self.assertIn(':focus-visible', self.css)
        self.assertIn('prefers-reduced-motion:reduce', self.css)
        self.assertIn('.btn.is-busy', self.css)
        self.assertIn('role="status" aria-live="polite"', self.html)
        self.assertIn('aria-controls="searchResults"', self.html)

    def test_public_add_mode_has_owner_session_controls(self):
        for obsolete in ("tokenDialog","tokenForm","tokenInput","openToken2","clearToken"):
            self.assertNotIn(f'id="{obsolete}"', self.html)
            self.assertNotIn(obsolete, self.js)
        for item in ("ownerLoginDialog", "ownerLoginForm", "ownerPassword", "ownerAuthAction", "ownerModeTitle"):
            self.assertIn(f'id="{item}"', self.html)
        self.assertIn("function applyOwnerMode(", self.js)
        self.assertIn("function submitOwnerLogin(", self.js)
        self.assertIn("viewer-mode", self.css)
        self.assertNotIn('class="btn tiny primary owner-only" id="overviewAddResource"', self.html)
        self.assertNotIn('class="page-actions owner-only"', self.html)

    def test_ranked_catalog_picker_contract(self):
        for token in (
            "function openResourceCatalog(", "function renderCatalog(", "function inspectCustomResource(",
            "/api/resource-catalog", "/api/resource-catalog/match?target=", "/api/resource-catalog/add",
        ):
            self.assertIn(token, self.js)
        self.assertIn(".resource-catalog-groups{", self.css)
        self.assertRegex(
            self.css,
            r"\.resource-catalog-groups\{[^}]*display:flex;[^}]*flex-direction:column",
        )
        self.assertRegex(self.css, r"\.catalog-group\{[^}]*flex:0 0 auto")
        self.assertIn(".catalog-resource-row{", self.css)
        self.assertRegex(
            self.css,
            r"\.catalog-resource-row\{[^}]*grid-template-columns:18px 28px minmax\(0,1fr\) auto",
        )
        self.assertNotIn("grid-template-columns:18px 0 28px", self.css)
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
        self.assertNotIn('/favicon.ico', self.js)
        self.assertNotIn('onerror="this.remove()', self.js)

    def test_navigation_hides_unavailable_capabilities(self):
        self.assertIn("function applyCapabilityNavigation(", self.js)
        self.assertIn("capability-hidden", self.js)
        self.assertIn(".capability-hidden", self.css)
        self.assertIn('data-view="map"', self.html)
        self.assertIn('id="diagTraceDomestic"', self.html)

    def test_stale_core_and_live_map_contract(self):
        for token in (
            "core-offline", "lastSuccessAt", "function probeInRegion(",
            "function appendProbePoint(", "mapPagePoints", "mapPageEmpty",
        ):
            self.assertTrue(token in self.js or token in self.html or token in self.css)
        self.assertNotIn('toast("Фильтр карты:', self.js)

    def test_availability_axis_matches_reference_bands(self):
        self.assertIn("var ticks=[100,99,98,95,90]", self.js)
        self.assertIn("function availabilityY(", self.js)

    def test_overview_resources_are_problem_first_and_bounded(self):
        self.assertIn(".compact-table{", self.css)
        self.assertIn("overflow-y:visible", self.css)
        self.assertIn("function resourceAttentionRank(", self.js)
        self.assertIn('S.overviewResourceMode==="ISSUES"', self.js)
        self.assertIn("var visible=matching.slice(0,8)", self.js)
        self.assertIn("data-overview-resource-mode", self.html)

    def test_dashboard_preferences_and_capability_gating(self):
        for token in (
            "DASHBOARD_PREFS_KEY", "function dashboardCapabilities(", "function visiblePinnedResourceIds(",
            "function applyDashboardPreferences(", "function renderDashboardPreferencesModal(",
            "data-dashboard-panel", "data-pin-resource", "pinned_resource_ids",
        ):
            self.assertTrue(token in self.js or token in self.html)
        self.assertIn(".dashboard-hidden", self.css)
        self.assertIn(".overview-row.single-panel", self.css)
        self.assertIn("fault_domain:resources.length>0&&(hasDomestic||hasPersonal)", self.js)

    def test_font_sizes_never_drop_below_ten_pixels(self):
        values = [float(v) for v in re.findall(r'font-size:\s*(\d+(?:\.\d+)?)px', self.css)]
        shorthand = [float(v) for v in re.findall(r'font:\s*(\d+(?:\.\d+)?)px', self.css)]
        too_small = sorted(v for v in values + shorthand if v < 10)
        self.assertEqual(too_small, [], "Font sizes below 10px: %s" % too_small)

    def test_reference_typography_tokens_are_global(self):
        self.assertIn('--nw-font:"Inter","Segoe UI",Roboto,Arial,sans-serif', self.css)
        self.assertIn("--nw-fs-2xs:10px", self.css)
        self.assertIn("html,body,button,input,select,textarea{font-family:var(--nw-font)}", self.css)

    def test_overview_scrolls_for_readable_operational_detail(self):
        self.assertIn("html,body{margin:0;width:100%;height:100%;overflow:hidden", self.css)
        self.assertIn(".overview-view{height:auto;overflow:visible}", self.css)
        self.assertIn("grid-template-rows:none", self.css)
        self.assertIn("padding-bottom:34px", self.css)
        self.assertIn('q(".overview-grid").style.removeProperty("grid-template-rows")', self.js)
        self.assertNotIn("grid.style.gridTemplateRows=", self.js)

    def test_responsive_viewport_and_touch_contract(self):
        self.assertIn(
            'content="width=device-width,initial-scale=1,maximum-scale=5"',
            self.html,
        )
        for token in (
            "@media(max-width:1050px)",
            "@media(max-width:640px)",
            "@media(pointer:coarse)",
            "@supports (height:100dvh)",
            "overflow-x:clip",
            "--mobile-nav-h:56px",
            "min-height:44px",
        ):
            self.assertIn(token, self.css)
        self.assertIn(
            ".kpi-grid,.overview-row-chart,.overview-row-middle,.overview-row-bottom,.resource-cards{grid-template-columns:minmax(0,1fr)!important}",
            self.css,
        )

    def test_dual_charts_share_ranges_refresh_and_fixed_layout(self):
        self.assertNotIn("expandChart", self.html + self.js)
        self.assertNotIn("chart-expanded", self.css + self.js)
        self.assertIn('api("/api/realtime?minutes="+S.streamMinutes+"&scope=DOMESTIC")', self.js)
        self.assertIn('setInterval(function(){if(!S.loading)loadAll(true)},5000)', self.js)
        self.assertIn(".overview-row-dual>.streams-panel,.overview-row-dual>.domestic-stream-panel{display:grid;grid-template-rows:56px minmax(0,1fr) 38px}", self.css)

    def test_bulk_check_button_calls_owner_endpoint(self):
        self.assertIn('id="checkAllResources"', self.html)
        self.assertIn('api("/api/check-all",{method:"POST"},true)', self.js)

    def test_browser_