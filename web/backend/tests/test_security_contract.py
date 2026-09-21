import unittest
from pathlib import Path


class SecurityContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.dockerfile = (cls.root / "Dockerfile").read_text(encoding="utf-8")
        cls.compose = (cls.root / "docker-compose.yml").read_text(encoding="utf-8")
        cls.main = (cls.root / "backend" / "app" / "main.py").read_text(encoding="utf-8")
        repo_root = cls.root.parent
        cls.workflow = (repo_root / ".github" / "workflows" / "deploy-web.yml").read_text(encoding="utf-8")
        cls.release_workflow = (repo_root / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
        cls.readme = (repo_root / "README.md").read_text(encoding="utf-8")
        cls.helper = (cls.root / "deploy" / "security" / "netweather-deploy-helper").read_text(encoding="utf-8")
        cls.gate = (cls.root / "deploy" / "security" / "netweather-ssh-gate").read_text(encoding="utf-8")
        cls.guard = (cls.root / "deploy" / "security" / "netweather-egress-guard").read_text(encoding="utf-8")
        cls.vpn_guard = (cls.root / "deploy" / "security" / "netweather-vpn-invariants").read_text(encoding="utf-8")

    def test_image_runs_as_non_root(self):
        self.assertIn("USER 10001:10001", self.dockerfile)
        self.assertNotIn("USER root", self.dockerfile)

    def test_compose_mirrors_locked_runtime(self):
        required = (
            'user: "10001:10001"',
            "read_only: true",
            "cap_drop:",
            "- ALL",
            "no-new-privileges:true",
            "pids_limit: 256",
            '127.0.0.1:${NETWEATHER_BIND_PORT:-18081}:8000',
            "netweather-isolated:",
            "ipv4_address: 172.30.250.2",
        )
        for token in required:
            self.assertIn(token, self.compose)
        self.assertNotIn("privileged: true", self.compose)
        self.assertNotIn("/var/run/docker.sock", self.compose)

    def test_production_deploy_is_gated_and_off_host_built(self):
        self.assertIn("if: vars.NETWEATHER_DEPLOY_ENABLED == 'true'", self.workflow)
        self.assertIn("Build production image off-host", self.workflow)
        self.assertIn('docker save "netweather-web:$GITHUB_SHA"', self.workflow)
        self.assertIn("Stream image into forced-command deploy gate", self.workflow)
        self.assertNotIn("scp ", self.workflow)
        self.assertNotIn("docker compose up", self.workflow)
        self.assertNotIn("bash -s", self.workflow)

    def test_android_preview_is_installable_traceable_and_clearly_labeled(self):
        required = (
            "testDebugUnitTest assembleDebug",
            "NetWeather-0.4.1-alpha-debug.apk",
            "sha256sum",
            "android-v0.4.1-alpha-preview.1",
            "docs/ANDROID_PREVIEW.md",
            "--prerelease",
        )
        for token in required:
            self.assertIn(token, self.release_workflow)
        self.assertNotIn("assembleRelease", self.release_workflow)
        self.assertIn(
            "releases/tag/android-v0.4.1-alpha-preview.1",
            self.readme,
        )

    def test_runtime_has_no_host_bind_mounts_or_privilege(self):
        required = (
            "--read-only",
            "--cap-drop ALL",
            "--security-opt no-new-privileges=true",
            "--user 10001:10001",
            "--network",
            "netweather-isolated",
            "--ip",
            "172.30.250.2",
            "--publish 127.0.0.1:18081:8000",
            "--env NETWEATHER_ALLOW_OPEN_ACCESS=false",
            "--env ALLOW_PRIVATE_TARGETS=false",
            "owner authentication secret is not configured",
        )
        for token in required:
            self.assertIn(token, self.helper)
        self.assertNotIn("--privileged", self.helper)
        self.assertNotIn("/var/run/docker.sock", self.helper)
        self.assertNotIn("type=bind", self.helper)

    def test_deploy_helper_keeps_temp_files_out_of_shared_tmp(self):
        self.assertIn('HEALTH_JSON="${STATE}/health-${SHA}.json"', self.helper)
        self.assertIn('LOAD_LOG="${STATE}/docker-load-${SHA}.txt"', self.helper)
        self.assertNotIn("/tmp/netweather-health.json", self.helper)
        self.assertNotIn("/tmp/netweather-docker-load.txt", self.helper)

    def test_deploy_ssh_is_forced_command_only(self):
        self.assertIn("SSH_ORIGINAL_COMMAND", self.gate)
        self.assertIn("^deploy", self.gate)
        self.assertIn("netweather-deploy-helper", self.gate)
        self.assertIn('[[ "$#" -eq 1 ]]', self.helper)

    def test_kernel_guard_blocks_host_and_private_networks(self):
        self.assertIn("chain input", self.guard)
        self.assertIn("ct state established,related", self.guard)
        self.assertIn("chain forward", self.guard)
        for subnet in ("10.0.0.0/8", "100.64.0.0/10", "169.254.0.0/16", "172.16.0.0/12", "192.168.0.0/16"):
            self.assertIn(subnet, self.guard)

    def test_deploy_is_blocked_and_rolled_back_on_vpn_regression(self):
        for token in (
            'VPN_GUARD="/usr/local/sbin/netweather-vpn-invariants"',
            "=== VPN PRE-DEPLOY INVARIANTS ===",
            "=== VPN POST-DEPLOY INVARIANTS ===",
            "=== VPN INVARIANTS AFTER NETWEATHER ROLLBACK ===",
        ):
            self.assertIn(token, self.helper)
        for token in (
            "verify_tls_ip",
            "VPN_XRAY_CONTAINER",
            "VPN_AWG_CONTAINER",
            "VPN_AWG_REQUIRE_REDIRECT",
            "VPN_INVARIANTS=PASS",
        ):
            self.assertIn(token, self.vpn_guard)

    def test_no_wildcard_cors_and_spa_path_is_contained(self):
        self.assertNotIn('allow_origins=["*"]', self.main)
        self.assertNotIn("CORSMiddleware", self.main)
        self.assertIn("candidate.relative_to(root)", self.main)
        self.assertIn('raise RuntimeError("Owner authentication secret is required")', self.main)

    def test_hardware_specific_probe_runtime_is_absent(self):
        self.assertFalse(any((self.root / "deploy" / "keenetic").glob("*")))
        self.assertNotIn("/api/agent", self.main)
        self.assertNotIn("NETWEATHER_AGENT_TOKEN", self.main)


if __name__ == "__main__":
    unittest.main()
