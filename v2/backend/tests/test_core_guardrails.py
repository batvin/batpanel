import ast
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
SOURCE = (ROOT / "app" / "main.py").read_text(encoding="utf-8")
COMPOSE = (ROOT.parent / "docker-compose.yml").read_text(encoding="utf-8")


class CoreGuardrailTests(unittest.TestCase):
    def test_backend_is_valid_python(self):
        ast.parse(SOURCE)

    def test_wireguard_is_removed(self):
        self.assertNotIn("wireguard", SOURCE.lower())

    def test_live_provisioning_is_not_claimed(self):
        self.assertIn('"live_provisioning": False', SOURCE)
        self.assertIn('"mode": "engine-agent-not-installed"', SOURCE)

    def test_all_supported_engines_are_marked_pending(self):
        for protocol in ("vless", "vmess", "trojan", "openvpn"):
            self.assertIn(f'"id": "{protocol}"', SOURCE)
        self.assertIn('"status": "engine_pending"', SOURCE)

    def test_customer_creation_fails_closed_until_agent_exists(self):
        tree = ast.parse(SOURCE)
        target = next(
            node for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == "create_customer"
        )
        first = target.body[0]
        self.assertIsInstance(first, ast.Raise)
        self.assertIn("503", ast.unparse(first))

    def test_panel_port_is_loopback_only(self):
        self.assertIn('127.0.0.1:${PANEL_PORT:-8000}:8000', COMPOSE)


if __name__ == "__main__":
    unittest.main()
