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
        cls.helper = (cls.root / "deploy" / "security" / "netweather-deploy-helper").read_text(encoding="utf-8")
        cls.gate = (cls.root / "deploy" / "security" / "netweather-ssh-gate").read_text(encoding="utf-8")
        cls.guard = (cls.root / "deploy" / "security" / "netweather-egress-guard").read_text(encoding="utf-8")

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
            "--env ALLOW_PRIVATE_TARGETS=false",
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

    def test_no_wildcard_cors_and_spa_path_is_contained(self):
        self.assertNotIn('allow_origins=["*"]', self.main)
        self.assertNotIn("CORSMiddleware", self.main)
        self.assertIn("candidate.relative_to(root)", self.main)


if __name__ == "__main__":
    unittest.main()
