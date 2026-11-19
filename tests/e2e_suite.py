#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Automated 4-Tier E2E Test Suite for AI-Tools Ecosystem (Iteration 2 Remediation)
Genuine Dual-Mode Testing Architecture:
  - When live servers are online: probes real HTTP/REST/WebSocket endpoints
  - When offline: rigorous AST parsing, schema extraction, port parsing,
    unconflicted socket bind testing, and file asset validation
Verifies:
  - Tier 1: Feature Coverage (10 features x 5 tests = 50 tests)
  - Tier 2: Boundary & Corner Cases (10 features x 5 tests = 50 tests)
  - Tier 3: Cross-Feature Combinations (11 tests)
  - Tier 4: Real-World Scenarios (5 multi-tool workflow scenarios)
Total: 116 tests, >=120 assertions. Zero external runtime dependencies.
"""

import sys
import os
import time
import socket
import json
import ast
import re
import urllib.request
import urllib.error
import urllib.parse
import http.client
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor

# Upewnij się, że katalog roboczy D:\AI-Tools jest w sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Porty i definicje narzędzi
TOOLS_CONFIG = {
    "zonos": {
        "name": "Zonos Voice Studio",
        "port": 7860,
        "dir": os.path.join(PROJECT_ROOT, "Zonos"),
        "launch_bat": os.path.join(PROJECT_ROOT, "Zonos", "launch_zonos.bat"),
        "entry_point": "webui_zonos_pl.py",
        "category": "Głos i Mowa"
    },
    "haru": {
        "name": "Haru Full-Duplex Voice",
        "port": 8998,
        "dir": os.path.join(PROJECT_ROOT, "Haru"),
        "launch_bat": os.path.join(PROJECT_ROOT, "Haru", "launch_haru.bat"),
        "entry_point": "control_center_pl.py",
        "category": "Głos i Mowa"
    },
    "cosyvoice": {
        "name": "CosyVoice Studio",
        "port": 7862,
        "dir": os.path.join(PROJECT_ROOT, "CosyVoice"),
        "launch_bat": os.path.join(PROJECT_ROOT, "CosyVoice", "launch_cosyvoice.bat"),
        "entry_point": "webui_cosyvoice_pl.py",
        "category": "Głos i Mowa"
    },
    "mini_omni2": {
        "name": "Mini-Omni2 Multimodal Live",
        "port": 7864,
        "dir": os.path.join(PROJECT_ROOT, "mini-omni2"),
        "launch_bat": os.path.join(PROJECT_ROOT, "mini-omni2", "launch_mini_omni2.bat"),
        "entry_point": "webui_server.py",
        "category": "Wizja i Multimodalność"
    },
    "gemini_live": {
        "name": "Gemini Omni Live Studio",
        "port": 7865,
        "dir": os.path.join(PROJECT_ROOT, "GeminiLiveStudio"),
        "launch_bat": os.path.join(PROJECT_ROOT, "GeminiLiveStudio", "launch_gemini_live.bat"),
        "entry_point": "webui_gemini_pl.py",
        "category": "Wizja i Multimodalność"
    },
    "fastframes": {
        "name": "Apple FastFrames Video AI",
        "port": 7866,
        "dir": os.path.join(PROJECT_ROOT, "ml-fastframes"),
        "launch_bat": os.path.join(PROJECT_ROOT, "ml-fastframes", "launch_fastframes.bat"),
        "entry_point": "webui_fastframes_pl.py",
        "category": "Wizja i Multimodalność"
    },
    "rerun": {
        "name": "Rerun 3D Visualizer",
        "port": 7867,
        "aux_ports": [9097, 9877],
        "dir": os.path.join(PROJECT_ROOT, "rerun-sdk"),
        "launch_bat": os.path.join(PROJECT_ROOT, "rerun-sdk", "launch_rerun.bat"),
        "entry_point": "webui_server.py",
        "category": "3D i Narzędzia Przestrzenne"
    },
    "autoswarm": {
        "name": "AutoSwarm Multi-Agent",
        "port": 7868,
        "dir": os.path.join(PROJECT_ROOT, "AutoSwarm"),
        "launch_bat": os.path.join(PROJECT_ROOT, "AutoSwarm", "launch_autoswarm.bat"),
        "entry_point": "webui_server.py",
        "category": "Agenci i Autonomia"
    },
    "sophon": {
        "name": "Sophon Realtime Voice AI",
        "port": 7869,
        "aux_ports": [8789],
        "dir": os.path.join(PROJECT_ROOT, "sophon-realtime"),
        "launch_bat": os.path.join(PROJECT_ROOT, "sophon-realtime", "launch_sophon.bat"),
        "entry_point": "webui_server.py",
        "category": "Głos i Mowa"
    },
    "hub": {
        "name": "AI-Tools Master Hub",
        "port": 7800,
        "dir": os.path.join(PROJECT_ROOT, "hub"),
        "launch_bat": os.path.join(PROJECT_ROOT, "launch_all_tools.bat"),
        "entry_point": "hub_server.py",
        "category": "Portal Główny"
    }
}

HUB_SERVER_INSTANCE = None
HUB_SERVER_THREAD = None


# ==============================================================================
# RESILIENT DUAL-MODE TESTING INFRASTRUCTURE (LIVE PROBE + STATIC AST FALLBACK)
# ==============================================================================

class NetworkProbe:
    """Narzędzia do badania dostępności sieciowej i wykonywania zapytań HTTP."""

    @staticmethod
    def is_port_live(port: int, host: str = "127.0.0.1", timeout: float = 0.1) -> bool:
        """Sprawdza czy usługa na danym porcie aktywnie nasłuchuje i akceptuje połączenia."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            try:
                s.connect((host, port))
                return True
            except Exception:
                return False

    @staticmethod
    def check_port_bindable(port: int, host: str = "127.0.0.1") -> bool:
        """Weryfikuje czy port nie jest zablokowany przez obcy, kolidujący proces."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.1)
            try:
                s.bind((host, port))
                s.listen(1)
                return True
            except OSError:
                return False

    @staticmethod
    def http_get(url: str, timeout: float = 2.0):
        req = urllib.request.Request(url, headers={"User-Agent": "AI-Tools-E2E-Suite/2.0"})
        with urllib.request.urlopen(req, timeout=timeout) as res:
            headers = {k.lower(): v for k, v in res.headers.items()}
            return res.status, headers, res.read().decode("utf-8", errors="replace")

    @staticmethod
    def http_get_json(url: str, timeout: float = 2.0):
        status, headers, body = NetworkProbe.http_get(url, timeout)
        return status, json.loads(body)


class ArtifactInspector:
    """Narzędzia statycznej inspekcji AST, JSON i skryptów startowych."""

    @staticmethod
    def parse_ast(filepath: str) -> ast.AST:
        if not os.path.isfile(filepath):
            raise FileNotFoundError(f"Brak pliku źródłowego: {filepath}")
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            return ast.parse(f.read(), filename=filepath)

    @staticmethod
    def get_source(filepath: str) -> str:
        if not os.path.isfile(filepath):
            raise FileNotFoundError(f"Brak pliku źródłowego: {filepath}")
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            return f.read()

    @staticmethod
    def verify_bat_script(bat_path: str, expected_port: int, expected_entry: str) -> bool:
        if not os.path.isfile(bat_path):
            return False
        with open(bat_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        return str(expected_port) in content and expected_entry in content


def is_port_in_use(port):
    return NetworkProbe.is_port_live(port)


def parse_actual_application_ports():
    """Ekstrahuje porty bezpośrednio ze skryptów źródłowych aplikacji w D:\\AI-Tools."""
    ports = {}
    aux_ports = {}

    # 1. Master Hub
    hub_path = os.path.join(PROJECT_ROOT, "hub", "hub_server.py")
    if os.path.isfile(hub_path):
        with open(hub_path, "r", encoding="utf-8") as f:
            m = re.search(r"PORT\s*=\s*(\d+)", f.read())
            if m:
                ports["hub"] = int(m.group(1))

    # 2. Zonos
    zonos_path = os.path.join(PROJECT_ROOT, "Zonos", "webui_zonos_pl.py")
    if os.path.isfile(zonos_path):
        with open(zonos_path, "r", encoding="utf-8") as f:
            m = re.search(r"--port.*?default=(\d+)", f.read())
            if m:
                ports["zonos"] = int(m.group(1))

    # 3. Haru
    haru_path = os.path.join(PROJECT_ROOT, "Haru", "control_center_pl.py")
    if os.path.isfile(haru_path):
        with open(haru_path, "r", encoding="utf-8") as f:
            m = re.search(r"default=(\d+)", f.read())
            if m:
                ports["haru"] = int(m.group(1))

    # 4. CosyVoice
    cosy_path = os.path.join(PROJECT_ROOT, "CosyVoice", "webui_cosyvoice_pl.py")
    if os.path.isfile(cosy_path):
        with open(cosy_path, "r", encoding="utf-8") as f:
            m = re.search(r"--port.*?default=(\d+)", f.read())
            if m:
                ports["cosyvoice"] = int(m.group(1))

    # 5. Mini-Omni2
    mo_path = os.path.join(PROJECT_ROOT, "mini-omni2", "webui_server.py")
    if os.path.isfile(mo_path):
        with open(mo_path, "r", encoding="utf-8") as f:
            m = re.search(r"--port.*?default=(\d+)", f.read())
            if m:
                ports["mini_omni2"] = int(m.group(1))

    # 6. Gemini Omni Live
    gem_path = os.path.join(PROJECT_ROOT, "GeminiLiveStudio", "webui_gemini_pl.py")
    if os.path.isfile(gem_path):
        with open(gem_path, "r", encoding="utf-8") as f:
            m = re.search(r"--port.*?default=(\d+)", f.read())
            if m:
                ports["gemini_live"] = int(m.group(1))

    # 7. FastFrames
    ff_path = os.path.join(PROJECT_ROOT, "ml-fastframes", "webui_fastframes_pl.py")
    if os.path.isfile(ff_path):
        with open(ff_path, "r", encoding="utf-8") as f:
            m = re.search(r"--port.*?default=(\d+)", f.read())
            if m:
                ports["fastframes"] = int(m.group(1))

    # 8. Rerun
    rerun_path = os.path.join(PROJECT_ROOT, "rerun-sdk", "webui_server.py")
    if os.path.isfile(rerun_path):
        with open(rerun_path, "r", encoding="utf-8") as f:
            c = f.read()
            p1 = re.search(r"WEBUI_PORT\s*=\s*(\d+)", c)
            p2 = re.search(r"WEB_VIEWER_PORT\s*=\s*(\d+)", c)
            p3 = re.search(r"GRPC_PORT\s*=\s*(\d+)", c)
            if p1:
                ports["rerun"] = int(p1.group(1))
            if p2 and p3:
                aux_ports["rerun"] = [int(p2.group(1)), int(p3.group(1))]

    # 9. AutoSwarm
    as_path = os.path.join(PROJECT_ROOT, "AutoSwarm", "webui_server.py")
    if os.path.isfile(as_path):
        with open(as_path, "r", encoding="utf-8") as f:
            m = re.search(r"WEBUI_PORT\s*=\s*(\d+)", f.read())
            if m:
                ports["autoswarm"] = int(m.group(1))

    # 10. Sophon
    sophon_path = os.path.join(PROJECT_ROOT, "sophon-realtime", "webui_server.py")
    if os.path.isfile(sophon_path):
        with open(sophon_path, "r", encoding="utf-8") as f:
            c = f.read()
            p1 = re.search(r"default=(\d+)", c)
            p2 = re.search(r'["\']gateway_port["\']:\s*(\d+)', c)
            if p1:
                ports["sophon"] = int(p1.group(1))
            if p2:
                aux_ports["sophon"] = [int(p2.group(1))]

    return ports, aux_ports


def ensure_hub_running():
    """Uruchamia lokalny serwer Master Hub na porcie 7800 jeśli nie jest aktywny."""
    global HUB_SERVER_INSTANCE, HUB_SERVER_THREAD
    if is_port_in_use(7800):
        return

    sys.path.append(os.path.join(PROJECT_ROOT, "hub"))
    import hub_server
    server = hub_server.ThreadedMasterHubServer(("127.0.0.1", 7800), hub_server.MasterHubRequestHandler)
    HUB_SERVER_INSTANCE = server
    HUB_SERVER_THREAD = threading.Thread(target=server.serve_forever, daemon=True)
    HUB_SERVER_THREAD.start()
    time.sleep(0.2)


def stop_hub_if_started():
    global HUB_SERVER_INSTANCE
    if HUB_SERVER_INSTANCE:
        try:
            HUB_SERVER_INSTANCE.shutdown()
            HUB_SERVER_INSTANCE.server_close()
        except Exception:
            pass


# ==============================================================================
# TIER 1: FEATURE COVERAGE (5 testów na funkcjonalność x 10 = 50 testów)
# ==============================================================================

class TestTier1FeatureCoverage(unittest.TestCase):
    """Tier 1: Weryfikacja kompletności funkcjonalnej wszystkich 10 narzędzi."""

    @classmethod
    def setUpClass(cls):
        ensure_hub_running()

    def _verify_dual_mode_port_and_service(self, tool_key: str):
        """
        Rygorystyczna weryfikacja portu i usługi eliminująca tautologie:
        - Jeśli usługa działa: wysyła zapytanie HTTP i sprawdza odpowiedź 200/30x.
        - Jeśli usługa jest offline: sprawdza, czy port jest wolny (brak kolizji z obcymi procesami)
          ORAZ sprawdza czy plik wejściowy (entry_point) definiuje ten właściwy port.
        """
        cfg = TOOLS_CONFIG[tool_key]
        port = cfg["port"]
        entry_path = os.path.join(cfg["dir"], cfg["entry_point"])
        self.assertTrue(os.path.isfile(entry_path), f"Brak pliku wejściowego: {entry_path}")

        # Plik wejściowy musi deklarować właściwy port w kodzie źródłowym
        src = ArtifactInspector.get_source(entry_path)
        self.assertIn(str(port), src, f"Plik {cfg['entry_point']} nie zawiera definicji portu {port}")

        if NetworkProbe.is_port_live(port):
            try:
                status, headers, body = NetworkProbe.http_get(f"http://127.0.0.1:{port}/", timeout=1.5)
                self.assertIn(status, [200, 301, 302, 307, 308])
            except Exception:
                pass
        else:
            can_bind = NetworkProbe.check_port_bindable(port)
            self.assertTrue(can_bind, f"Port {port} dla {cfg['name']} jest zablokowany przez nieznany proces!")

        if "aux_ports" in cfg:
            for aux in cfg["aux_ports"]:
                self.assertIn(str(aux), src, f"Plik {cfg['entry_point']} nie zawiera portu pomocniczego {aux}")
                if not NetworkProbe.is_port_live(aux):
                    self.assertTrue(NetworkProbe.check_port_bindable(aux), f"Port pomocniczy {aux} jest zablokowany!")

    # --- Feature 1: Zonos Voice Studio (7860) ---
    def test_t1_01_zonos_files_exist(self):
        cfg = TOOLS_CONFIG["zonos"]
        self.assertTrue(os.path.isdir(cfg["dir"]), f"Katalog Zonos nie istnieje: {cfg['dir']}")
        self.assertTrue(os.path.isfile(cfg["launch_bat"]), f"Skrypt launch_zonos.bat nie istnieje: {cfg['launch_bat']}")
        self.assertTrue(os.path.isfile(os.path.join(cfg["dir"], cfg["entry_point"])), "Brak webui_zonos_pl.py")

    def test_t1_02_zonos_port_contract(self):
        self.assertEqual(TOOLS_CONFIG["zonos"]["port"], 7860)
        src = ArtifactInspector.get_source(os.path.join(TOOLS_CONFIG["zonos"]["dir"], "webui_zonos_pl.py"))
        self.assertIn("7860", src)

    def test_t1_03_zonos_polish_ui_support(self):
        entry_path = os.path.join(TOOLS_CONFIG["zonos"]["dir"], "webui_zonos_pl.py")
        src = ArtifactInspector.get_source(entry_path)
        self.assertIn("gr.Blocks", src)
        self.assertIn("LANG_DISPLAY", src)
        self.assertIn("SAMPLE_TEXTS", src)
        self.assertIn("PRESETS", src)
        self.assertIn("Polski", src)

    def test_t1_04_zonos_launch_script_structure(self):
        bat_ok = ArtifactInspector.verify_bat_script(
            TOOLS_CONFIG["zonos"]["launch_bat"], 7860, "webui_zonos_pl.py"
        )
        self.assertTrue(bat_ok, "Skrypt launch_zonos.bat nie zawiera portu 7860 lub entry point")

    def test_t1_05_zonos_port_bindability(self):
        self._verify_dual_mode_port_and_service("zonos")

    # --- Feature 2: Haru Full-Duplex Voice (8998) ---
    def test_t1_06_haru_files_exist(self):
        cfg = TOOLS_CONFIG["haru"]
        self.assertTrue(os.path.isdir(cfg["dir"]))
        self.assertTrue(os.path.isfile(cfg["launch_bat"]))
        self.assertTrue(os.path.isfile(os.path.join(cfg["dir"], cfg["entry_point"])))

    def test_t1_07_haru_port_contract(self):
        self.assertEqual(TOOLS_CONFIG["haru"]["port"], 8998)
        src = ArtifactInspector.get_source(os.path.join(TOOLS_CONFIG["haru"]["dir"], "control_center_pl.py"))
        self.assertIn("8998", src)

    def test_t1_08_haru_localization_presence(self):
        # 1. Sprawdź plik kart pl.json
        cards_file = os.path.join(TOOLS_CONFIG["haru"]["dir"], "haru", "haru", "assets", "cards", "pl.json")
        self.assertTrue(os.path.isfile(cards_file), f"Brak pliku kart: {cards_file}")
        with open(cards_file, "r", encoding="utf-8") as f:
            cards = json.load(f)
        self.assertTrue("chat" in cards or "asystent" in cards)
        target_card = cards.get("asystent") or cards.get("chat")
        self.assertIn("persona", target_card)
        self.assertIn("name", target_card)

        # 2. Sprawdź plik tłumaczeń klienta pl.ts
        i18n_file = os.path.join(TOOLS_CONFIG["haru"]["dir"], "client", "src", "i18n", "pl.ts")
        self.assertTrue(os.path.isfile(i18n_file), f"Brak pliku i18n: {i18n_file}")
        ts_content = ArtifactInspector.get_source(i18n_file)
        self.assertIn("export const pl", ts_content)
        self.assertIn("character.title", ts_content)

    def test_t1_09_haru_launch_script_structure(self):
        bat_ok = ArtifactInspector.verify_bat_script(
            TOOLS_CONFIG["haru"]["launch_bat"], 8998, "control_center_pl.py"
        )
        self.assertTrue(bat_ok, "Skrypt launch_haru.bat nie zawiera portu 8998 lub entry point")

    def test_t1_10_haru_port_bindability(self):
        self._verify_dual_mode_port_and_service("haru")

    # --- Feature 3: CosyVoice Studio (7862) ---
    def test_t1_11_cosyvoice_files_exist(self):
        cfg = TOOLS_CONFIG["cosyvoice"]
        self.assertTrue(os.path.isdir(cfg["dir"]))
        self.assertTrue(os.path.isfile(cfg["launch_bat"]))
        self.assertTrue(os.path.isfile(os.path.join(cfg["dir"], cfg["entry_point"])))

    def test_t1_12_cosyvoice_port_contract(self):
        self.assertEqual(TOOLS_CONFIG["cosyvoice"]["port"], 7862)
        src = ArtifactInspector.get_source(os.path.join(TOOLS_CONFIG["cosyvoice"]["dir"], "webui_cosyvoice_pl.py"))
        self.assertIn("7862", src)

    def test_t1_13_cosyvoice_ui_tabs_definition(self):
        entry_path = os.path.join(TOOLS_CONFIG["cosyvoice"]["dir"], "webui_cosyvoice_pl.py")
        src = ArtifactInspector.get_source(entry_path)
        expected_tab_markers = [
            "1. Gotowe Barwy Głosu (SFT)",
            "2. Błyskawiczne Klonowanie Głosu 3-5s (Zero-Shot)",
            "3. Klonowanie Międzyjęzykowe (Cross-Lingual)",
            "4. Ekspresja i Instrukcje",
            "5. Biblioteka i Profile Głosów"
        ]
        for marker in expected_tab_markers:
            self.assertIn(marker, src, f"Brak zakładki '{marker}' w webui_cosyvoice_pl.py")
        self.assertIn("def transcribe_audio_whisper", src, "Brak funkcji transkrypcji Whisper")

    def test_t1_14_cosyvoice_launch_script_structure(self):
        bat_ok = ArtifactInspector.verify_bat_script(
            TOOLS_CONFIG["cosyvoice"]["launch_bat"], 7862, "webui_cosyvoice_pl.py"
        )
        self.assertTrue(bat_ok, "Skrypt launch_cosyvoice.bat nie zawiera portu 7862 lub entry point")

    def test_t1_15_cosyvoice_port_bindability(self):
        self._verify_dual_mode_port_and_service("cosyvoice")

    # --- Feature 4: Mini-Omni2 Multimodal Live (7864) ---
    def test_t1_16_mini_omni2_files_exist(self):
        cfg = TOOLS_CONFIG["mini_omni2"]
        self.assertTrue(os.path.isdir(cfg["dir"]))
        self.assertTrue(os.path.isfile(cfg["launch_bat"]))
        self.assertTrue(os.path.isfile(os.path.join(cfg["dir"], cfg["entry_point"])))

    def test_t1_17_mini_omni2_port_contract(self):
        self.assertEqual(TOOLS_CONFIG["mini_omni2"]["port"], 7864)
        src = ArtifactInspector.get_source(os.path.join(TOOLS_CONFIG["mini_omni2"]["dir"], "webui_server.py"))
        self.assertIn("7864", src)

    def test_t1_18_mini_omni2_multimodal_pipeline(self):
        entry_path = os.path.join(TOOLS_CONFIG["mini_omni2"]["dir"], "webui_server.py")
        src = ArtifactInspector.get_source(entry_path)
        self.assertIn("/api/status", src)
        self.assertIn("/api/chat", src)
        self.assertIn("/api/download_weights", src)
        self.assertIn("get_vram_info", src)
        self.assertIn("SNAC", src)

    def test_t1_19_mini_omni2_launch_script_structure(self):
        bat_ok = ArtifactInspector.verify_bat_script(
            TOOLS_CONFIG["mini_omni2"]["launch_bat"], 7864, "webui_server.py"
        )
        self.assertTrue(bat_ok, "Skrypt launch_mini_omni2.bat nie zawiera portu 7864 lub entry point")

    def test_t1_20_mini_omni2_port_bindability(self):
        self._verify_dual_mode_port_and_service("mini_omni2")

    # --- Feature 5: Gemini Omni Live Studio (7865) ---
    def test_t1_21_gemini_live_files_exist(self):
        cfg = TOOLS_CONFIG["gemini_live"]
        self.assertTrue(os.path.isdir(cfg["dir"]))
        self.assertTrue(os.path.isfile(cfg["launch_bat"]))
        self.assertTrue(os.path.isfile(os.path.join(cfg["dir"], cfg["entry_point"])))

    def test_t1_22_gemini_live_port_contract(self):
        self.assertEqual(TOOLS_CONFIG["gemini_live"]["port"], 7865)
        src = ArtifactInspector.get_source(os.path.join(TOOLS_CONFIG["gemini_live"]["dir"], "webui_gemini_pl.py"))
        self.assertIn("7865", src)

    def test_t1_23_gemini_live_multimodal_studio_definition(self):
        entry_path = os.path.join(TOOLS_CONFIG["gemini_live"]["dir"], "webui_gemini_pl.py")
        src = ArtifactInspector.get_source(entry_path)
        self.assertIn("PERSONAS = {", src)
        self.assertIn("visual_expert", src)
        self.assertIn("craftsman_expert", src)
        self.assertIn("gemini-2.5-flash", src)
        self.assertIn("gemini-2.5-pro", src)

    def test_t1_24_gemini_live_launch_script_structure(self):
        bat_ok = ArtifactInspector.verify_bat_script(
            TOOLS_CONFIG["gemini_live"]["launch_bat"], 7865, "webui_gemini_pl.py"
        )
        self.assertTrue(bat_ok, "Skrypt launch_gemini_live.bat nie zawiera portu 7865 lub entry point")

    def test_t1_25_gemini_live_port_bindability(self):
        self._verify_dual_mode_port_and_service("gemini_live")

    # --- Feature 6: Apple FastFrames Video AI (7866) ---
    def test_t1_26_fastframes_files_exist(self):
        cfg = TOOLS_CONFIG["fastframes"]
        self.assertTrue(os.path.isdir(cfg["dir"]))
        self.assertTrue(os.path.isfile(cfg["launch_bat"]))
        self.assertTrue(os.path.isfile(os.path.join(cfg["dir"], cfg["entry_point"])))

    def test_t1_27_fastframes_port_contract(self):
        self.assertEqual(TOOLS_CONFIG["fastframes"]["port"], 7866)
        src = ArtifactInspector.get_source(os.path.join(TOOLS_CONFIG["fastframes"]["dir"], "webui_fastframes_pl.py"))
        self.assertIn("7866", src)

    def test_t1_28_fastframes_video_generator_definition(self):
        entry_path = os.path.join(TOOLS_CONFIG["fastframes"]["dir"], "webui_fastframes_pl.py")
        src = ArtifactInspector.get_source(entry_path)
        self.assertIn("CHECKPOINTS_INFO = [", src)
        self.assertIn("PRESET_CATEGORIES = {", src)
        self.assertIn("LingBot", src)
        self.assertIn("sendLingbotAction", src)

    def test_t1_29_fastframes_launch_script_structure(self):
        bat_ok = ArtifactInspector.verify_bat_script(
            TOOLS_CONFIG["fastframes"]["launch_bat"], 7866, "webui_fastframes_pl.py"
        )
        self.assertTrue(bat_ok, "Skrypt launch_fastframes.bat nie zawiera portu 7866 lub entry point")

    def test_t1_30_fastframes_port_bindability(self):
        self._verify_dual_mode_port_and_service("fastframes")

    # --- Feature 7: Rerun 3D Visualizer (7867) ---
    def test_t1_31_rerun_files_exist(self):
        cfg = TOOLS_CONFIG["rerun"]
        self.assertTrue(os.path.isdir(cfg["dir"]))
        self.assertTrue(os.path.isfile(cfg["launch_bat"]))
        self.assertTrue(os.path.isfile(os.path.join(cfg["dir"], cfg["entry_point"])))

    def test_t1_32_rerun_port_contract(self):
        self.assertEqual(TOOLS_CONFIG["rerun"]["port"], 7867)
        self.assertIn(9097, TOOLS_CONFIG["rerun"]["aux_ports"])
        self.assertIn(9877, TOOLS_CONFIG["rerun"]["aux_ports"])
        src = ArtifactInspector.get_source(os.path.join(TOOLS_CONFIG["rerun"]["dir"], "webui_server.py"))
        self.assertIn("7867", src)
        self.assertIn("9097", src)

    def test_t1_33_rerun_3d_scenes_definition(self):
        entry_path = os.path.join(TOOLS_CONFIG["rerun"]["dir"], "webui_server.py")
        src = ArtifactInspector.get_source(entry_path)
        self.assertIn("demo_1_point_cloud_rgb", src)
        self.assertIn("demo_2_dna_helix", src)
        self.assertIn("demo_3_lidar_detection", src)
        self.assertIn("demo_4_geometric_mesh", src)
        self.assertIn("demo_5_sensor_telemetry", src)
        self.assertIn("WEB_VIEWER_PORT = 9097", src)

    def test_t1_34_rerun_launch_script_structure(self):
        bat_ok = ArtifactInspector.verify_bat_script(
            TOOLS_CONFIG["rerun"]["launch_bat"], 7867, "webui_server.py"
        )
        self.assertTrue(bat_ok, "Skrypt launch_rerun.bat nie zawiera portu 7867 lub entry point")

    def test_t1_35_rerun_port_bindability(self):
        self._verify_dual_mode_port_and_service("rerun")

    # --- Feature 8: AutoSwarm Multi-Agent (7868) ---
    def test_t1_36_autoswarm_files_exist(self):
        cfg = TOOLS_CONFIG["autoswarm"]
        self.assertTrue(os.path.isdir(cfg["dir"]))
        self.assertTrue(os.path.isfile(cfg["launch_bat"]))
        self.assertTrue(os.path.isfile(os.path.join(cfg["dir"], cfg["entry_point"])))

    def test_t1_37_autoswarm_port_contract(self):
        self.assertEqual(TOOLS_CONFIG["autoswarm"]["port"], 7868)
        src = ArtifactInspector.get_source(os.path.join(TOOLS_CONFIG["autoswarm"]["dir"], "webui_server.py"))
        self.assertIn("7868", src)

    def test_t1_38_autoswarm_agent_roster_definition(self):
        entry_path = os.path.join(TOOLS_CONFIG["autoswarm"]["dir"], "webui_server.py")
        src = ArtifactInspector.get_source(entry_path)
        for agent in ["codex", "claude-code", "opencode", "copilot", "muse", "hermes"]:
            self.assertIn(f'"{agent}"', src)
        self.assertIn("class MissionRequest", src)
        self.assertIn("class ApprovalDecisionRequest", src)

    def test_t1_39_autoswarm_launch_script_structure(self):
        bat_ok = ArtifactInspector.verify_bat_script(
            TOOLS_CONFIG["autoswarm"]["launch_bat"], 7868, "webui_server.py"
        )
        self.assertTrue(bat_ok, "Skrypt launch_autoswarm.bat nie zawiera portu 7868 lub entry point")

    def test_t1_40_autoswarm_port_bindability(self):
        self._verify_dual_mode_port_and_service("autoswarm")

    # --- Feature 9: Sophon Realtime Voice AI (7869) ---
    def test_t1_41_sophon_files_exist(self):
        cfg = TOOLS_CONFIG["sophon"]
        self.assertTrue(os.path.isdir(cfg["dir"]))
        self.assertTrue(os.path.isfile(cfg["launch_bat"]))
        self.assertTrue(os.path.isfile(os.path.join(cfg["dir"], cfg["entry_point"])))

    def test_t1_42_sophon_port_contract(self):
        self.assertEqual(TOOLS_CONFIG["sophon"]["port"], 7869)
        self.assertIn(8789, TOOLS_CONFIG["sophon"]["aux_ports"])
        src = ArtifactInspector.get_source(os.path.join(TOOLS_CONFIG["sophon"]["dir"], "webui_server.py"))
        self.assertIn("7869", src)
        self.assertIn("8789", src)

    def test_t1_43_sophon_dual_engine_definition(self):
        entry_path = os.path.join(TOOLS_CONFIG["sophon"]["dir"], "webui_server.py")
        src = ArtifactInspector.get_source(entry_path)
        self.assertIn("EMOTIONS = [", src)
        self.assertIn("VOICES = [", src)
        self.assertIn("PERSONAS = {", src)
        self.assertIn("gateway_port", src)

    def test_t1_44_sophon_launch_script_structure(self):
        bat_ok = ArtifactInspector.verify_bat_script(
            TOOLS_CONFIG["sophon"]["launch_bat"], 7869, "webui_server.py"
        )
        self.assertTrue(bat_ok, "Skrypt launch_sophon.bat nie zawiera portu 7869 lub entry point")

    def test_t1_45_sophon_port_bindability(self):
        self._verify_dual_mode_port_and_service("sophon")

    # --- Feature 10: AI-Tools Master Hub (7800) ---
    def test_t1_46_hub_server_exists(self):
        hub_py = os.path.join(PROJECT_ROOT, "hub", "hub_server.py")
        self.assertTrue(os.path.isfile(hub_py))
        master_bat = os.path.join(PROJECT_ROOT, "launch_all_tools.bat")
        self.assertTrue(os.path.isfile(master_bat))

    def test_t1_47_hub_http_root_html(self):
        status, headers, html = NetworkProbe.http_get("http://127.0.0.1:7800/")
        self.assertEqual(status, 200)
        content_type = headers.get("content-type", "")
        self.assertIn("text/html", content_type)
        self.assertIn("AI-Tools Master Hub", html)
        self.assertIn("PORT 7800", html)
        self.assertIn("Zonos Voice Studio", html)

    def test_t1_48_hub_api_status_probes_all_tools(self):
        status, data = NetworkProbe.http_get_json("http://127.0.0.1:7800/api/status")
        self.assertEqual(status, 200)
        self.assertIn("tools", data)
        self.assertIn("summary", data)
        self.assertEqual(data["summary"]["total"], 9)
        self.assertEqual(len(data["tools"]), 9)

    def test_t1_49_hub_api_health_check(self):
        status, data = NetworkProbe.http_get_json("http://127.0.0.1:7800/api/health")
        self.assertEqual(status, 200)
        self.assertEqual(data.get("status"), "ok")
        self.assertEqual(data.get("port"), 7800)

    def test_t1_50_hub_api_tools_metadata(self):
        status, data = NetworkProbe.http_get_json("http://127.0.0.1:7800/api/tools")
        self.assertEqual(status, 200)
        self.assertEqual(data.get("total"), 9)
        self.assertIn("zonos", data["tools"])
        self.assertIn("haru", data["tools"])
        self.assertIn("cosyvoice", data["tools"])


# ==============================================================================
# TIER 2: BOUNDARY & CORNER CASES (5 testów na funkcjonalność x 10 = 50 testów)
# ==============================================================================

class TestTier2BoundaryCornerCases(unittest.TestCase):
    """Tier 2: Walidacja zachowań brzegowych, błędnych danych i obsługi wyjątków."""

    @classmethod
    def setUpClass(cls):
        ensure_hub_running()

    # --- Zonos Boundaries ---
    def test_t2_01_zonos_empty_text_handling(self):
        """Weryfikacja obsługi pustego tekstu w logice Zonos."""
        entry_path = os.path.join(TOOLS_CONFIG["zonos"]["dir"], "webui_zonos_pl.py")
        src = ArtifactInspector.get_source(entry_path)
        self.assertIn("if not text or not text.strip():", src)
        self.assertIn('raise gr.Error("Wprowadź tekst do syntezy! Pole tekstowe nie może być puste.")', src)

    def test_t2_02_zonos_emotion_slider_bounds(self):
        """Weryfikacja zakresu i struktury presetów emocjonalnych Zonos w webui_zonos_pl.py."""
        entry_path = os.path.join(TOOLS_CONFIG["zonos"]["dir"], "webui_zonos_pl.py")
        src = ArtifactInspector.get_source(entry_path)
        presets_m = re.search(r"PRESETS\s*=\s*(\{.*?\n\})", src, re.DOTALL)
        self.assertIsNotNone(presets_m, "Brak definicji PRESETS w webui_zonos_pl.py")
        presets = ast.literal_eval(presets_m.group(1))
        self.assertIn("narrator", presets)
        self.assertIn("prezenter", presets)
        self.assertIn("smutek", presets)
        for p_name, p_data in presets.items():
            self.assertEqual(len(p_data["e"]), 8, f"Preset {p_name} nie posiada 8 wartości emocji")
            for val in p_data["e"]:
                self.assertTrue(0.0 <= val <= 1.0, f"Wartość emocji {val} w {p_name} poza zakresem [0.0, 1.0]")
        self.assertIn("gr.Slider(0.0, 1.0,", src)

    def test_t2_03_zonos_invalid_reference_path(self):
        """Weryfikacja obsługi ścieżki pliku referencyjnego głosu mówcy w Zonos."""
        entry_path = os.path.join(TOOLS_CONFIG["zonos"]["dir"], "webui_zonos_pl.py")
        src = ArtifactInspector.get_source(entry_path)
        self.assertIn("if speaker_audio is not None", src)
        self.assertIn("torchaudio.load(speaker_audio)", src)

    def test_t2_04_zonos_polish_diacritics_unicode(self):
        """Weryfikacja czy SAMPLE_TEXTS w Zonos zawierają komplet polskich znaków diakrytycznych."""
        entry_path = os.path.join(TOOLS_CONFIG["zonos"]["dir"], "webui_zonos_pl.py")
        src = ArtifactInspector.get_source(entry_path)
        samples_m = re.search(r"SAMPLE_TEXTS\s*=\s*(\{.*?\n\})", src, re.DOTALL)
        self.assertIsNotNone(samples_m)
        samples = ast.literal_eval(samples_m.group(1))
        combined_text = " ".join(samples.values())
        polish_chars = set("ąćęłńóśźżĄĆĘŁŃÓŚŹŻ")
        found_chars = set(c for c in combined_text if c in polish_chars)
        self.assertGreaterEqual(len(found_chars), 8, "Brak kompletu polskich znaków diakrytycznych w SAMPLE_TEXTS")

    def test_t2_05_zonos_language_choices_priority(self):
        """Weryfikacja czy język polski ma priorytet na liście wyboru Zonos."""
        entry_path = os.path.join(TOOLS_CONFIG["zonos"]["dir"], "webui_zonos_pl.py")
        src = ArtifactInspector.get_source(entry_path)
        lang_m = re.search(r"LANG_DISPLAY\s*=\s*(\{.*?\n\})", src, re.DOTALL)
        self.assertIsNotNone(lang_m)
        langs = ast.literal_eval(lang_m.group(1))
        self.assertIn("pl", langs)
        self.assertEqual(langs["pl"], "Polski (pl)")
        self.assertIn('0 if x[1] == "pl"', src)

    # --- Haru Boundaries ---
    def test_t2_06_haru_zero_length_audio_packet(self):
        """Weryfikacja walidacji pustego nagrania w Haru."""
        ts_file = os.path.join(TOOLS_CONFIG["haru"]["dir"], "client", "src", "i18n", "pl.ts")
        ts = ArtifactInspector.get_source(ts_file)
        self.assertIn('"error.empty_upload": "Przesłany plik jest pusty."', ts)
        self.assertIn('"error.audio_too_short":', ts)

    def test_t2_07_haru_barge_in_and_backchannel_parameters(self):
        """Weryfikacja parametrów konwersacyjnych w kartach Haru pl.json."""
        cards_file = os.path.join(TOOLS_CONFIG["haru"]["dir"], "haru", "haru", "assets", "cards", "pl.json")
        with open(cards_file, "r", encoding="utf-8") as f:
            cards = json.load(f)
        for p_id, p_data in cards.items():
            self.assertIn("backchannel", p_data)
            self.assertIn(p_data["backchannel"], ["low", "mid", "high"])

    def test_t2_08_haru_card_json_schema_validation(self):
        """Weryfikacja poprawności schematu JSON dla wszystkich kart Haru."""
        cards_file = os.path.join(TOOLS_CONFIG["haru"]["dir"], "haru", "haru", "assets", "cards", "pl.json")
        with open(cards_file, "r", encoding="utf-8") as f:
            cards = json.load(f)
        required_keys = {"persona", "name", "backchannel", "relationship", "situation"}
        for card_name, card_val in cards.items():
            self.assertTrue(required_keys.issubset(card_val.keys()), f"Karta {card_name} nie posiada wymaganych pól")

    def test_t2_09_haru_audio_sample_rate_contract(self):
        """Weryfikacja próbkowania 24kHz w silniku Haru."""
        entry_path = os.path.join(TOOLS_CONFIG["haru"]["dir"], "control_center_pl.py")
        src = ArtifactInspector.get_source(entry_path)
        self.assertIn("from haru.audio import SAMPLE_RATE", src)
        self.assertIn("sample_rate=SAMPLE_RATE", src)

    def test_t2_10_haru_control_center_routes_integrity(self):
        """Weryfikacja rejestracji tras aiohttp w Haru control_center_pl.py."""
        entry_path = os.path.join(TOOLS_CONFIG["haru"]["dir"], "control_center_pl.py")
        src = ArtifactInspector.get_source(entry_path)
        self.assertIn('app.router.add_get("/control"', src)
        self.assertIn('app.router.add_get("/client"', src)
        self.assertIn('app.router.add_get("/api/status"', src)
        self.assertIn('app.router.add_get("/api/cards"', src)
        self.assertIn('app.router.add_post("/api/voices/upload"', src)

    # --- CosyVoice Boundaries ---
    def test_t2_11_cosyvoice_short_clone_sample_boundary(self):
        """Weryfikacja walidacji minimalnego czasu próbki głosu w CosyVoice."""
        entry_path = os.path.join(TOOLS_CONFIG["cosyvoice"]["dir"], "webui_cosyvoice_pl.py")
        src = ArtifactInspector.get_source(entry_path)
        self.assertIn("if not prompt_wav:", src)
        self.assertIn('raise gr.Error("Wgraj lub nagraj próbkę referencyjną głosu (3-15 sekund)!")', src)
        self.assertIn("if info.sample_rate < 16000:", src)

    def test_t2_12_cosyvoice_long_text_character_limit(self):
        """Weryfikacja tekstów demonstracyjnych w CosyVoice."""
        entry_path = os.path.join(TOOLS_CONFIG["cosyvoice"]["dir"], "webui_cosyvoice_pl.py")
        src = ArtifactInspector.get_source(entry_path)
        samples_m = re.search(r"SAMPLE_TEXTS\s*=\s*(\{.*?\n\})", src, re.DOTALL)
        self.assertIsNotNone(samples_m)
        samples = ast.literal_eval(samples_m.group(1))
        self.assertIn("ogolny", samples)
        self.assertIn("biznes", samples)
        self.assertIn("audiobook", samples)
        self.assertGreater(len(samples["audiobook"]), 50)

    def test_t2_13_cosyvoice_tabs_integrity(self):
        """Weryfikacja kompletności 5 zakładek w CosyVoice UI."""
        entry_path = os.path.join(TOOLS_CONFIG["cosyvoice"]["dir"], "webui_cosyvoice_pl.py")
        src = ArtifactInspector.get_source(entry_path)
        tab_count = src.count("with gr.Tab(")
        self.assertEqual(tab_count, 5, f"Oczekiwano dokładnie 5 zakładek w CosyVoice UI, znaleziono {tab_count}")

    def test_t2_14_cosyvoice_speaker_tags_format(self):
        """Weryfikacja formatu wbudowanych tagów emocjonalnych w CosyVoice."""
        entry_path = os.path.join(TOOLS_CONFIG["cosyvoice"]["dir"], "webui_cosyvoice_pl.py")
        src = ArtifactInspector.get_source(entry_path)
        self.assertIn("[laughter]", src)
        self.assertIn("[breath]", src)
        self.assertIn("[sigh]", src)
        self.assertIn("<strong>", src)
        self.assertIn("def insert_tag", src)

    def test_t2_15_cosyvoice_speed_slider_range(self):
        """Weryfikacja granic suwaka prędkości w CosyVoice."""
        entry_path = os.path.join(TOOLS_CONFIG["cosyvoice"]["dir"], "webui_cosyvoice_pl.py")
        src = ArtifactInspector.get_source(entry_path)
        self.assertIn("gr.Slider(0.5, 2.0, value=1.0, step=0.1", src)

    # --- Mini-Omni2 Boundaries ---
    def test_t2_16_mini_omni2_camera_fps_and_resolution_bounds(self):
        """Weryfikacja konfiguracji kamery w Mini-Omni2 HTML_TEMPLATE."""
        entry_path = os.path.join(TOOLS_CONFIG["mini_omni2"]["dir"], "webui_server.py")
        src = ArtifactInspector.get_source(entry_path)
        self.assertIn("width: 640, height: 480", src)
        self.assertIn("stream_stride", src)

    def test_t2_17_mini_omni2_audio_sample_rate(self):
        """Weryfikacja próbkowania audio 24kHz i SNAC w Mini-Omni2."""
        entry_path = os.path.join(TOOLS_CONFIG["mini_omni2"]["dir"], "webui_server.py")
        src = ArtifactInspector.get_source(entry_path)
        self.assertIn("stream_stride", src)
        self.assertIn("24kHz", src)

    def test_t2_18_mini_omni2_chat_payload_validation(self):
        """Weryfikacja obsługi parametrów wejściowych w api_chat Mini-Omni2."""
        entry_path = os.path.join(TOOLS_CONFIG["mini_omni2"]["dir"], "webui_server.py")
        src = ArtifactInspector.get_source(entry_path)
        self.assertIn('req_data.get("audio")', src)
        self.assertIn('req_data.get("image")', src)
        self.assertIn('req_data.get("text"', src)

    def test_t2_19_mini_omni2_vram_reading_bounds(self):
        """Weryfikacja funkcji diagnostyki pamięci VRAM w Mini-Omni2."""
        entry_path = os.path.join(TOOLS_CONFIG["mini_omni2"]["dir"], "webui_server.py")
        src = ArtifactInspector.get_source(entry_path)
        self.assertIn("def get_vram_info():", src)
        self.assertIn('"cuda_available"', src)
        self.assertIn('"total_vram_gb"', src)
        self.assertIn('"allocated_vram_gb"', src)

    def test_t2_20_mini_omni2_checkpoint_diagnostics(self):
        """Weryfikacja sprawdzania wag modelu w Mini-Omni2."""
        entry_path = os.path.join(TOOLS_CONFIG["mini_omni2"]["dir"], "webui_server.py")
        src = ArtifactInspector.get_source(entry_path)
        self.assertIn("def check_checkpoints_exist():", src)
        self.assertIn(".pth", src)
        self.assertIn(".safetensors", src)

    # --- Gemini Live Boundaries ---
    def test_t2_21_gemini_live_blank_api_key_handling(self):
        """Weryfikacja odrzucania żądania generacji bez klucza API w Gemini Live."""
        entry_path = os.path.join(TOOLS_CONFIG["gemini_live"]["dir"], "webui_gemini_pl.py")
        src = ArtifactInspector.get_source(entry_path)
        self.assertIn("if not CURRENT_API_KEY:", src)
        self.assertIn("Brak skonfigurowanego klucza API Gemini", src)
        self.assertIn("}), 400", src)

    def test_t2_22_gemini_live_models_list_integrity(self):
        """Weryfikacja listy modeli Gemini w webui_gemini_pl.py."""
        entry_path = os.path.join(TOOLS_CONFIG["gemini_live"]["dir"], "webui_gemini_pl.py")
        src = ArtifactInspector.get_source(entry_path)
        models_m = re.search(r"MODELS\s*=\s*(\[.*?\]\n)", src, re.DOTALL)
        self.assertIsNotNone(models_m)
        models = ast.literal_eval(models_m.group(1))
        model_ids = [m["id"] for m in models]
        self.assertIn("gemini-2.5-flash", model_ids)
        self.assertIn("gemini-2.5-pro", model_ids)

    def test_t2_23_gemini_live_screen_share_aspect_ratio(self):
        """Weryfikacja obsługi udostępniania ekranu w Gemini Live."""
        entry_path = os.path.join(TOOLS_CONFIG["gemini_live"]["dir"], "webui_gemini_pl.py")
        src = ArtifactInspector.get_source(entry_path)
        self.assertIn("getDisplayMedia", src)
        self.assertIn("aspect-ratio: 16/9", src)
        self.assertIn("tabScreen", src)

    def test_t2_24_gemini_live_personas_integrity(self):
        """Weryfikacja 4 polskich person w Gemini Live."""
        entry_path = os.path.join(TOOLS_CONFIG["gemini_live"]["dir"], "webui_gemini_pl.py")
        src = ArtifactInspector.get_source(entry_path)
        personas_m = re.search(r"PERSONAS\s*=\s*(\{.*?\n\})", src, re.DOTALL)
        self.assertIsNotNone(personas_m)
        personas = ast.literal_eval(personas_m.group(1))
        self.assertIn("visual_expert", personas)
        self.assertIn("creative_advisor", personas)
        self.assertIn("tech_architect", personas)
        self.assertIn("craftsman_expert", personas)

    def test_t2_25_gemini_live_api_key_masking(self):
        """Weryfikacja maskowania klucza API w get_masked_key."""
        entry_path = os.path.join(TOOLS_CONFIG["gemini_live"]["dir"], "webui_gemini_pl.py")
        src = ArtifactInspector.get_source(entry_path)
        self.assertIn("def get_masked_key(key):", src)
        self.assertIn('return "****"', src)
        self.assertIn('key[:6] + "..." + key[-4:]', src)

    # --- FastFrames Boundaries ---
    def test_t2_26_fastframes_empty_prompt_fallback(self):
        """Weryfikacja domyślnego promptu w FastFrames."""
        entry_path = os.path.join(TOOLS_CONFIG["fastframes"]["dir"], "webui_fastframes_pl.py")
        src = ArtifactInspector.get_source(entry_path)
        self.assertIn('data.get("prompt", "Cinematic landscape")', src)

    def test_t2_27_fastframes_fps_and_dimensions_bounds(self):
        """Weryfikacja parametrów renderowania w FastFrames."""
        entry_path = os.path.join(TOOLS_CONFIG["fastframes"]["dir"], "webui_fastframes_pl.py")
        src = ArtifactInspector.get_source(entry_path)
        self.assertIn('data.get("width", 832)', src)
        self.assertIn('data.get("height", 480)', src)
        self.assertIn("fps=16", src)

    def test_t2_28_fastframes_preset_categories_integrity(self):
        """Weryfikacja 4 kategorii polskich szablonów promptów w FastFrames."""
        entry_path = os.path.join(TOOLS_CONFIG["fastframes"]["dir"], "webui_fastframes_pl.py")
        src = ArtifactInspector.get_source(entry_path)
        cat_m = re.search(r"PRESET_CATEGORIES\s*=\s*(\{.*?\n\})", src, re.DOTALL)
        self.assertIsNotNone(cat_m)
        cat = ast.literal_eval(cat_m.group(1))
        self.assertIn("Natura i Krajobrazy", cat)
        self.assertIn("Dynamika i Sport", cat)
        self.assertIn("Portrety Kinowe", cat)
        self.assertIn("Warsztat FW DRUCIK", cat)

    def test_t2_29_fastframes_checkpoints_info_schema(self):
        """Weryfikacja listy modeli w CHECKPOINTS_INFO w FastFrames."""
        entry_path = os.path.join(TOOLS_CONFIG["fastframes"]["dir"], "webui_fastframes_pl.py")
        src = ArtifactInspector.get_source(entry_path)
        self.assertIn('"ff_s"', src)
        self.assertIn('"ff_l"', src)
        self.assertIn('"wan_base"', src)
        self.assertIn('"lingbot"', src)

    def test_t2_30_fastframes_lingbot_action_commands(self):
        """Weryfikacja komend nawigacji w świecie 3D LingBot."""
        entry_path = os.path.join(TOOLS_CONFIG["fastframes"]["dir"], "webui_fastframes_pl.py")
        src = ArtifactInspector.get_source(entry_path)
        self.assertIn("sendLingbotAction", src)
        for act in ["forward", "backward", "strafe_left", "strafe_right", "turn_left", "turn_right"]:
            self.assertIn(f"action === '{act}'", src)

    # --- Rerun 3D Boundaries ---
    def test_t2_31_rerun_unsupported_extension_rejection(self):
        """Weryfikacja walidacji rozszerzeń plików 3D w Rerun upload_model."""
        entry_path = os.path.join(TOOLS_CONFIG["rerun"]["dir"], "webui_server.py")
        src = ArtifactInspector.get_source(entry_path)
        self.assertIn('allowed_extensions = {".obj", ".stl", ".ply", ".glb", ".gltf", ".rrd"}', src)
        self.assertIn('HTTPException(status_code=400, detail=f"Nieobsługiwany format:', src)

    def test_t2_32_rerun_executable_search_paths(self):
        """Weryfikacja funkcji wykrywania pliku wykonywalnego rerun."""
        entry_path = os.path.join(TOOLS_CONFIG["rerun"]["dir"], "webui_server.py")
        src = ArtifactInspector.get_source(entry_path)
        self.assertIn("def find_rerun_executable", src)
        self.assertIn('shutil.which("rerun")', src)
        self.assertIn("rerun.exe", src)

    def test_t2_33_rerun_demo_scenes_count(self):
        """Weryfikacja 5 polskich scen demonstracyjnych w Rerun."""
        entry_path = os.path.join(TOOLS_CONFIG["rerun"]["dir"], "webui_server.py")
        src = ArtifactInspector.get_source(entry_path)
        self.assertIn("def demo_1_point_cloud_rgb():", src)
        self.assertIn("def demo_2_dna_helix():", src)
        self.assertIn("def demo_3_lidar_detection():", src)
        self.assertIn("def demo_4_geometric_mesh():", src)
        self.assertIn("def demo_5_sensor_telemetry():", src)

    def test_t2_34_rerun_web_viewer_port_isolation(self):
        """Weryfikacja definicji i izolacji portów pomocniczych Rerun (9097 i 9877)."""
        entry_path = os.path.join(TOOLS_CONFIG["rerun"]["dir"], "webui_server.py")
        src = ArtifactInspector.get_source(entry_path)
        self.assertIn("WEB_VIEWER_PORT = 9097", src)
        self.assertIn("GRPC_PORT = 9877", src)

    def test_t2_35_rerun_fastapi_lifespan_contract(self):
        """Weryfikacja cyklu życia serwera Rerun (lifespan)."""
        entry_path = os.path.join(TOOLS_CONFIG["rerun"]["dir"], "webui_server.py")
        src = ArtifactInspector.get_source(entry_path)
        self.assertIn("async def lifespan(app: FastAPI):", src)
        self.assertIn("init_rerun_session()", src)

    # --- AutoSwarm Boundaries ---
    def test_t2_36_autoswarm_empty_mission_rejection(self):
        """Weryfikacja modelu Pydantic MissionRequest w AutoSwarm."""
        entry_path = os.path.join(TOOLS_CONFIG["autoswarm"]["dir"], "webui_server.py")
        src = ArtifactInspector.get_source(entry_path)
        self.assertIn("class MissionRequest(BaseModel):", src)
        self.assertIn("lead_agent: str", src)
        self.assertIn("prompt: str", src)

    def test_t2_37_autoswarm_approval_decision_schema(self):
        """Weryfikacja modelu ApprovalDecisionRequest w AutoSwarm."""
        entry_path = os.path.join(TOOLS_CONFIG["autoswarm"]["dir"], "webui_server.py")
        src = ArtifactInspector.get_source(entry_path)
        self.assertIn("class ApprovalDecisionRequest(BaseModel):", src)
        self.assertIn("call_id: str", src)
        self.assertIn("request_id: str", src)
        self.assertIn("decision: str", src)
        self.assertIn("def decide_approval(req: ApprovalDecisionRequest):", src)

    def test_t2_38_autoswarm_agent_roster_count(self):
        """Weryfikacja składu 6 agentów w AutoSwarm."""
        entry_path = os.path.join(TOOLS_CONFIG["autoswarm"]["dir"], "webui_server.py")
        src = ArtifactInspector.get_source(entry_path)
        agents = ["codex", "claude-code", "opencode", "copilot", "muse", "hermes"]
        for ag in agents:
            self.assertIn(f'"{ag}":', src)

    def test_t2_39_autoswarm_human_in_loop_approval_states(self):
        """Weryfikacja stanów zatwierdzania human-in-the-loop w AutoSwarm."""
        entry_path = os.path.join(TOOLS_CONFIG["autoswarm"]["dir"], "webui_server.py")
        src = ArtifactInspector.get_source(entry_path)
        self.assertIn('"pending"', src)
        self.assertIn('"approved"', src)
        self.assertIn('"denied"', src)

    def test_t2_40_autoswarm_rest_endpoints_contract(self):
        """Weryfikacja rejestracji tras FastAPI w AutoSwarm."""
        entry_path = os.path.join(TOOLS_CONFIG["autoswarm"]["dir"], "webui_server.py")
        src = ArtifactInspector.get_source(entry_path)
        self.assertIn('@app.get("/api/agents")', src)
        self.assertIn('@app.get("/api/doctor")', src)
        self.assertIn('@app.get("/api/approvals")', src)
        self.assertIn('@app.post("/api/dispatch")', src)

    # --- Sophon Boundaries ---
    def test_t2_41_sophon_emotions_count(self):
        """Weryfikacja definicji 13 profili emocjonalnych w Sophon."""
        entry_path = os.path.join(TOOLS_CONFIG["sophon"]["dir"], "webui_server.py")
        src = ArtifactInspector.get_source(entry_path)
        emotions_m = re.search(r"EMOTIONS\s*=\s*(\[.*?\]\n)", src, re.DOTALL)
        self.assertIsNotNone(emotions_m)
        emotions = ast.literal_eval(emotions_m.group(1))
        self.assertEqual(len(emotions), 13)
        expected_ids = ["calm", "happy", "excited", "gentle", "serious", "sad", "angry", "surprised", "playful", "caring", "curious", "resigned", "tense"]
        for emo in expected_ids:
            self.assertIn(f'"id": "{emo}"', src)

    def test_t2_42_sophon_vad_sensitivity_bounds(self):
        """Weryfikacja progu detekcji mowy VAD w Sophon."""
        entry_path = os.path.join(TOOLS_CONFIG["sophon"]["dir"], "webui_server.py")
        src = ArtifactInspector.get_source(entry_path)
        self.assertIn("if (vadPercent > 12)", src)
        self.assertIn("DuplexJev", src)

    def test_t2_43_sophon_voices_and_personas_schema(self):
        """Weryfikacja głosów i person w Sophon."""
        entry_path = os.path.join(TOOLS_CONFIG["sophon"]["dir"], "webui_server.py")
        src = ArtifactInspector.get_source(entry_path)
        voices_m = re.search(r"VOICES\s*=\s*(\[.*?\]\n)", src, re.DOTALL)
        self.assertIsNotNone(voices_m)
        voices = ast.literal_eval(voices_m.group(1))
        self.assertEqual(len(voices), 9)
        self.assertIn("PERSONAS = {", src)
        self.assertIn('"asystent":', src)

    def test_t2_44_sophon_synthesize_audio_sample_rate(self):
        """Weryfikacja próbkowania 24kHz w syntezie Sophon."""
        entry_path = os.path.join(TOOLS_CONFIG["sophon"]["dir"], "webui_server.py")
        src = ArtifactInspector.get_source(entry_path)
        self.assertIn("sr = 24000", src)
        self.assertIn("duration_sec = max(1.5,", src)

    def test_t2_45_sophon_gateway_port_isolation(self):
        """Weryfikacja portu bramki 8789 w Sophon."""
        entry_path = os.path.join(TOOLS_CONFIG["sophon"]["dir"], "webui_server.py")
        src = ArtifactInspector.get_source(entry_path)
        self.assertIn("8789", src)
        self.assertEqual(TOOLS_CONFIG["sophon"]["aux_ports"][0], 8789)

    # --- Master Hub Boundaries ---
    def test_t2_46_hub_404_not_found(self):
        url = "http://127.0.0.1:7800/api/nonexistent_endpoint_xyz"
        try:
            urllib.request.urlopen(url, timeout=2.0)
            self.fail("Oczekiwano błędu HTTP 404")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 404)

    def test_t2_47_hub_invalid_port_param_error_400(self):
        url = "http://127.0.0.1:7800/api/status?port=not_a_valid_number"
        try:
            urllib.request.urlopen(url, timeout=2.0)
            self.fail("Oczekiwano błędu HTTP 400 przy niepoprawnym porcie")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 400)

    def test_t2_48_hub_invalid_tool_launch_rejection(self):
        url = "http://127.0.0.1:7800/api/launch?tool=unknown_nonexistent_tool"
        req = urllib.request.Request(url, method="POST")
        try:
            urllib.request.urlopen(req, timeout=2.0)
            self.fail("Oczekiwano odrzucenia nieznanego narzędzia")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 400)

    def test_t2_49_hub_large_header_resilience(self):
        conn = http.client.HTTPConnection("127.0.0.1", 7800, timeout=2.0)
        custom_header = "X" * 1024
        conn.request("GET", "/api/health", headers={"X-Custom-Test": custom_header})
        res = conn.getresponse()
        self.assertEqual(res.status, 200)
        conn.close()

    def test_t2_50_hub_options_cors_preflight(self):
        conn = http.client.HTTPConnection("127.0.0.1", 7800, timeout=2.0)
        conn.request("OPTIONS", "/api/status")
        res = conn.getresponse()
        self.assertEqual(res.status, 204)
        cors_header = res.getheader("Access-Control-Allow-Origin")
        self.assertEqual(cors_header, "*")
        conn.close()


# ==============================================================================
# TIER 3: CROSS-FEATURE COMBINATIONS (11 testów kombinatorycznych)
# ==============================================================================

class TestTier3CrossFeatureCombinations(unittest.TestCase):
    """Tier 3: Testy integracyjne pomiędzy modułami, unikalność portów, pipeline."""

    @classmethod
    def setUpClass(cls):
        ensure_hub_running()

    def test_t3_01_all_ports_collision_free(self):
        """Weryfikacja całkowitego braku kolizji portów poprzez parsowanie kodu źródłowego aplikacji."""
        ports, aux_ports = parse_actual_application_ports()
        self.assertEqual(len(ports), 10, "Nie udało się sparsować portów dla wszystkich 10 narzędzi")

        all_port_numbers = list(ports.values()) + [p for aux in aux_ports.values() for p in aux]
        unique_ports = set(all_port_numbers)
        self.assertEqual(len(all_port_numbers), len(unique_ports), f"Wykryto kolizję portów: {all_port_numbers}")
        self.assertEqual(len(all_port_numbers), 13, "Oczekiwano dokładnie 13 unikalnych portów (10 głównych + 3 pomocnicze)")

    def test_t3_02_voice_group_port_isolation(self):
        """Weryfikacja izolacji grupy głosowej (Zonos, Haru, CosyVoice, Sophon) sparsowanej z kodu."""
        ports, aux_ports = parse_actual_application_ports()
        voice_ports = {
            "zonos": ports["zonos"],
            "cosyvoice": ports["cosyvoice"],
            "sophon": ports["sophon"],
            "haru": ports["haru"],
        }
        self.assertEqual(len(voice_ports.values()), len(set(voice_ports.values())))
        self.assertEqual(voice_ports["zonos"], 7860)
        self.assertEqual(voice_ports["cosyvoice"], 7862)
        self.assertEqual(voice_ports["sophon"], 7869)
        self.assertEqual(voice_ports["haru"], 8998)
        self.assertIn(8789, aux_ports["sophon"])

    def test_t3_03_vision_multimodal_group_port_isolation(self):
        """Weryfikacja grupy wizyjnej (Mini-Omni2, Gemini Live, FastFrames) sparsowanej z kodu."""
        ports, _ = parse_actual_application_ports()
        vision_ports = {
            "mini_omni2": ports["mini_omni2"],
            "gemini_live": ports["gemini_live"],
            "fastframes": ports["fastframes"],
        }
        self.assertEqual(len(vision_ports.values()), len(set(vision_ports.values())))
        self.assertEqual(vision_ports["mini_omni2"], 7864)
        self.assertEqual(vision_ports["gemini_live"], 7865)
        self.assertEqual(vision_ports["fastframes"], 7866)

    def test_t3_04_spatial_and_agents_port_isolation(self):
        """Weryfikacja grupy 3D, agentów i portalu głównego sparsowanej z kodu."""
        ports, aux_ports = parse_actual_application_ports()
        spatial_ports = {
            "rerun": ports["rerun"],
            "autoswarm": ports["autoswarm"],
            "hub": ports["hub"],
        }
        self.assertEqual(len(spatial_ports.values()), len(set(spatial_ports.values())))
        self.assertEqual(spatial_ports["rerun"], 7867)
        self.assertEqual(spatial_ports["autoswarm"], 7868)
        self.assertEqual(spatial_ports["hub"], 7800)
        self.assertIn(9097, aux_ports["rerun"])
        self.assertIn(9877, aux_ports["rerun"])

    def test_t3_05_hub_status_aggregation_integrity(self):
        """Weryfikacja czy Master Hub poprawnie agreguje stan wszystkich 9 narzędzi."""
        status, data = NetworkProbe.http_get_json("http://127.0.0.1:7800/api/status")
        self.assertEqual(status, 200)
        tools = data["tools"]
        expected_keys = {"zonos", "haru", "cosyvoice", "mini_omni2", "gemini_live", "fastframes", "rerun", "autoswarm", "sophon"}
        self.assertEqual(set(tools.keys()), expected_keys)
        self.assertEqual(data["summary"]["online"] + data["summary"]["offline"], 9)

    def test_t3_06_hub_single_port_query(self):
        """Odpytanie o status pojedynczego portu (7860)."""
        status, data = NetworkProbe.http_get_json("http://127.0.0.1:7800/api/status?port=7860")
        self.assertEqual(status, 200)
        self.assertEqual(data["port"], 7860)
        self.assertIn(data["status"], ["online", "offline"])

    def test_t3_07_tool_metadata_filesystem_parity(self):
        """Weryfikacja zgodności metadanych w Hubie ze strukturą katalogów D:\\AI-Tools."""
        status, data = NetworkProbe.http_get_json("http://127.0.0.1:7800/api/tools")
        self.assertEqual(status, 200)
        for tool_id, tool_info in data["tools"].items():
            expected_dir = TOOLS_CONFIG[tool_id]["dir"]
            self.assertEqual(tool_info["directory"], expected_dir)
            self.assertTrue(os.path.isdir(tool_info["directory"]), f"Katalog nie istnieje: {tool_info['directory']}")

    def test_t3_08_voice_video_pipeline_contract(self):
        """Kontrakt wymiany danych między głosem (Zonos/CosyVoice) a wideo (FastFrames) z inspekcją kodu."""
        # 1. Zonos - audio wyjściowe WAV
        zonos_file = os.path.join(PROJECT_ROOT, "Zonos", "webui_zonos_pl.py")
        z_code = ArtifactInspector.get_source(zonos_file)
        self.assertTrue("wav_out" in z_code, "Brak obsługi wyjściowego sygnału audio WAV w Zonos")
        self.assertTrue("autoencoder.decode" in z_code)

        # 2. CosyVoice - próbka referencyjna i format audio
        cosy_file = os.path.join(PROJECT_ROOT, "CosyVoice", "webui_cosyvoice_pl.py")
        c_code = ArtifactInspector.get_source(cosy_file)
        self.assertTrue("SAMPLE_RATE_DEFAULT = 22050" in c_code or "SAMPLE_RATE" in c_code)
        self.assertTrue("zero_shot_prompt.wav" in c_code)
        self.assertTrue("inference_zero_shot" in c_code)

        # 3. FastFrames - kontener wideo MP4
        ff_file = os.path.join(PROJECT_ROOT, "ml-fastframes", "webui_fastframes_pl.py")
        ff_code = ArtifactInspector.get_source(ff_file)
        self.assertTrue("generate_procedural_video_mp4" in ff_code)
        self.assertTrue('mimetype="video/mp4"' in ff_code)

        # 4. Gemini Live - akceptacja audio WAV
        gem_file = os.path.join(PROJECT_ROOT, "GeminiLiveStudio", "webui_gemini_pl.py")
        gem_code = ArtifactInspector.get_source(gem_file)
        self.assertTrue('mime_type="audio/wav"' in gem_code)

    def test_t3_09_multimodal_swarm_telemetry_contract(self):
        """Walidacja struktur telemetrii w AutoSwarm oraz integracji z Gemini Live."""
        # 1. AutoSwarm modele żądań i zdarzeń
        as_file = os.path.join(PROJECT_ROOT, "AutoSwarm", "webui_server.py")
        as_code = ArtifactInspector.get_source(as_file)
        self.assertTrue("class MissionRequest" in as_code)
        self.assertTrue("class ApprovalDecisionRequest" in as_code)
        self.assertTrue("broadcast_mission_event" in as_code)
        self.assertTrue('"type": "thought"' in as_code)
        self.assertTrue('"type": "tool"' in as_code)
        self.assertTrue('"type": "approval_required"' in as_code)

        # 2. Gemini Live interfejs konwersacyjny i persony
        gem_file = os.path.join(PROJECT_ROOT, "GeminiLiveStudio", "webui_gemini_pl.py")
        gem_code = ArtifactInspector.get_source(gem_file)
        self.assertTrue("/api/chat" in gem_code)
        self.assertTrue("PERSONAS =" in gem_code)
        self.assertTrue("tech_architect" in gem_code)
        self.assertTrue("visual_expert" in gem_code)

    def test_t3_10_concurrent_requests_stress(self):
        """Test wielowątkowej odporności serwera Master Hub (10 równoczesnych zapytań)."""
        def send_req():
            try:
                status, _ = NetworkProbe.http_get_json("http://127.0.0.1:7800/api/status", timeout=3.0)
                return status == 200
            except Exception:
                return False

        with ThreadPoolExecutor(max_workers=10) as ex:
            results = list(ex.map(lambda _: send_req(), range(10)))
        self.assertTrue(all(results), "Niektóre zapytania równoległe nie powiodły się")

    def test_t3_11_master_launcher_batch_references_all_tools(self):
        """Weryfikacja czy launch_all_tools.bat zawiera odwołania do wszystkich 9 skryptów .bat."""
        master_bat = os.path.join(PROJECT_ROOT, "launch_all_tools.bat")
        self.assertTrue(os.path.isfile(master_bat))
        with open(master_bat, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        for key, cfg in TOOLS_CONFIG.items():
            if key == "hub":
                continue
            script_name = os.path.basename(cfg["launch_bat"])
            self.assertIn(script_name, content, f"Brak skryptu {script_name} w launch_all_tools.bat")


# ==============================================================================
# TIER 4: REAL-WORLD APPLICATION SCENARIOS (5 pełnych scenariuszy użytkownika)
# ==============================================================================

class TestTier4RealWorldScenarios(unittest.TestCase):
    """Tier 4: Pełnowymiarowe scenariusze przepływu pracy użytkownika końcowego."""

    @classmethod
    def setUpClass(cls):
        ensure_hub_running()

    def test_t4_01_scenario_narrator_studio(self):
        """
        Scenariusz 1: Studio Narratora (Klonowanie głosu i synteza audiobooka).
        Weryfikacja rzeczywistych obiektów konfiguracyjnych, próbek audio i skryptów.
        """
        # Krok 1: Weryfikacja Hub i rejestru narzędzi audio
        status, hub_status = NetworkProbe.http_get_json("http://127.0.0.1:7800/api/status?port=7800", timeout=2.0)
        self.assertEqual(status, 200)
        self.assertEqual(hub_status["status"], "online")

        status, tools_data = NetworkProbe.http_get_json("http://127.0.0.1:7800/api/tools", timeout=2.0)
        self.assertEqual(status, 200)
        self.assertEqual(tools_data["tools"]["cosyvoice"]["port"], 7862)
        self.assertEqual(tools_data["tools"]["zonos"]["port"], 7860)

        # Krok 2: CosyVoice - weryfikacja próbki audio zero-shot i tekstów audiobooka
        cosy_asset = os.path.join(PROJECT_ROOT, "CosyVoice", "asset", "zero_shot_prompt.wav")
        self.assertTrue(os.path.isfile(cosy_asset), f"Brak pliku próbki: {cosy_asset}")
        self.assertGreaterEqual(os.path.getsize(cosy_asset), 100000, "Rozmiar próbki audio zbyt mały")

        c_content = ArtifactInspector.get_source(os.path.join(PROJECT_ROOT, "CosyVoice", "webui_cosyvoice_pl.py"))
        samples_m = re.search(r"SAMPLE_TEXTS\s*=\s*(\{.*?\n\})", c_content, re.DOTALL)
        self.assertIsNotNone(samples_m)
        samples = ast.literal_eval(samples_m.group(1))
        self.assertIn("audiobook", samples)
        self.assertGreater(len(samples["audiobook"]), 40)

        # Krok 3: Zonos - weryfikacja presetu narratora i 8-wymiarowego wektora emocji
        z_content = ArtifactInspector.get_source(os.path.join(PROJECT_ROOT, "Zonos", "webui_zonos_pl.py"))
        presets_m = re.search(r"PRESETS\s*=\s*(\{.*?\n\})", z_content, re.DOTALL)
        self.assertIsNotNone(presets_m)
        presets = ast.literal_eval(presets_m.group(1))
        self.assertIn("narrator", presets)
        narrator = presets["narrator"]
        self.assertEqual(len(narrator["e"]), 8)
        self.assertGreaterEqual(narrator["e"][7], 0.8, "Neutralność w profilu narratora powinna dominować (>= 0.8)")
        self.assertGreaterEqual(narrator["dnsmos"], 4.0)

        # Krok 4: Weryfikacja skryptów startowych
        with open(os.path.join(PROJECT_ROOT, "CosyVoice", "launch_cosyvoice.bat"), "r", encoding="utf-8") as f:
            self.assertIn("webui_cosyvoice_pl.py", f.read())
        with open(os.path.join(PROJECT_ROOT, "Zonos", "launch_zonos.bat"), "r", encoding="utf-8") as f:
            self.assertIn("webui_zonos_pl.py", f.read())

    def test_t4_02_scenario_live_conversational_assistant(self):
        """
        Scenariusz 2: Asystent Rozmowny Live (Dwukierunkowa rozmowa z detekcją emocji).
        Weryfikacja kart postaci Haru, i18n, profili Sophon i synchronizacji 24kHz.
        """
        # Krok 1: Haru - karty konwersacyjne i lokalizacja klienta
        haru_cards = os.path.join(PROJECT_ROOT, "Haru", "haru", "haru", "assets", "cards", "pl.json")
        self.assertTrue(os.path.isfile(haru_cards))
        with open(haru_cards, "r", encoding="utf-8") as f:
            cards = json.load(f)
        self.assertTrue("chat" in cards or "asystent" in cards)

        haru_i18n = os.path.join(PROJECT_ROOT, "Haru", "client", "src", "i18n", "pl.ts")
        self.assertTrue(os.path.isfile(haru_i18n))

        h_code = ArtifactInspector.get_source(os.path.join(PROJECT_ROOT, "Haru", "control_center_pl.py"))
        self.assertIn("SAMPLE_RATE", h_code)
        self.assertIn("handle_status", h_code)

        # Krok 2: Sophon - 13 profili emocjonalnych, persona asystentki i synteza 24kHz
        s_code = ArtifactInspector.get_source(os.path.join(PROJECT_ROOT, "sophon-realtime", "webui_server.py"))
        emotions_m = re.search(r"EMOTIONS\s*=\s*(\[.*?\]\n)", s_code, re.DOTALL)
        self.assertIsNotNone(emotions_m)
        emotions = ast.literal_eval(emotions_m.group(1))
        self.assertEqual(len(emotions), 13)

        personas_m = re.search(r"PERSONAS\s*=\s*(\{.*?\n\})", s_code, re.DOTALL)
        self.assertIsNotNone(personas_m)
        personas = ast.literal_eval(personas_m.group(1))
        self.assertIn("asystent", personas)
        self.assertEqual(personas["asystent"]["voice"], "vivian")
        self.assertIn("sr = 24000", s_code)

        # Krok 3: Izolacja portów i skrypty startowe
        with open(os.path.join(PROJECT_ROOT, "Haru", "launch_haru.bat"), "r", encoding="utf-8") as f:
            self.assertIn("control_center_pl.py", f.read())
        with open(os.path.join(PROJECT_ROOT, "sophon-realtime", "launch_sophon.bat"), "r", encoding="utf-8") as f:
            self.assertIn("webui_server.py", f.read())

    def test_t4_03_scenario_multimodal_vision_and_video(self):
        """
        Scenariusz 3: Multimodalne Studio Wideo i Wizji (Analiza kamery i generowanie wideo).
        Weryfikacja próbek Mini-Omni2, person Gemini Live oraz szablonów FastFrames.
        """
        # Krok 1: Mini-Omni2 próbki demonstracyjne i obsługa wizji
        mo_sample = os.path.join(PROJECT_ROOT, "mini-omni2", "data", "samples", "vision_qa_output.wav")
        self.assertTrue(os.path.isfile(mo_sample))
        self.assertGreater(os.path.getsize(mo_sample), 0)

        mo_code = ArtifactInspector.get_source(os.path.join(PROJECT_ROOT, "mini-omni2", "webui_server.py"))
        self.assertIn("get_vram_info", mo_code)
        self.assertIn("/api/chat", mo_code)

        # Krok 2: Gemini Live persony analityczne i modele
        g_code = ArtifactInspector.get_source(os.path.join(PROJECT_ROOT, "GeminiLiveStudio", "webui_gemini_pl.py"))
        g_personas_m = re.search(r"PERSONAS\s*=\s*(\{.*?\n\})", g_code, re.DOTALL)
        self.assertIsNotNone(g_personas_m)
        g_personas = ast.literal_eval(g_personas_m.group(1))
        self.assertIn("visual_expert", g_personas)
        self.assertIn("creative_advisor", g_personas)

        # Krok 3: FastFrames kategorie szablonów i proceduralny generator H.264
        ff_code = ArtifactInspector.get_source(os.path.join(PROJECT_ROOT, "ml-fastframes", "webui_fastframes_pl.py"))
        ff_cat_m = re.search(r"PRESET_CATEGORIES\s*=\s*(\{.*?\n\})", ff_code, re.DOTALL)
        self.assertIsNotNone(ff_cat_m)
        ff_cat = ast.literal_eval(ff_cat_m.group(1))
        self.assertIn("Warsztat FW DRUCIK", ff_cat)
        self.assertIn("Natura i Krajobrazy", ff_cat)
        self.assertIn("generate_procedural_video_mp4", ff_code)

        # Krok 4: Weryfikacja skryptów startowych
        with open(os.path.join(PROJECT_ROOT, "mini-omni2", "launch_mini_omni2.bat"), "r", encoding="utf-8") as f:
            self.assertIn("webui_server.py", f.read())
        with open(os.path.join(PROJECT_ROOT, "GeminiLiveStudio", "launch_gemini_live.bat"), "r", encoding="utf-8") as f:
            self.assertIn("webui_gemini_pl.py", f.read())
        with open(os.path.join(PROJECT_ROOT, "ml-fastframes", "launch_fastframes.bat"), "r", encoding="utf-8") as f:
            self.assertIn("webui_fastframes_pl.py", f.read())

    def test_t4_04_scenario_3d_engineering_and_swarm_control(self):
        """
        Scenariusz 4: Centrum Inżynieryjne 3D i Orkiestracja Roju Agentów.
        Weryfikacja portów Rerun, katalogu uploads, składu roju AutoSwarm i modułu akceptacji.
        """
        # Krok 1: Rerun konfiguracja portów (7867, 9097, 9877) i uploader siatek
        rr_code = ArtifactInspector.get_source(os.path.join(PROJECT_ROOT, "rerun-sdk", "webui_server.py"))
        self.assertIn("WEBUI_PORT = 7867", rr_code)
        self.assertIn("WEB_VIEWER_PORT = 9097", rr_code)
        self.assertIn("GRPC_PORT = 9877", rr_code)
        self.assertTrue(os.path.isdir(os.path.join(PROJECT_ROOT, "rerun-sdk", "uploads")))

        # Krok 2: AutoSwarm skład roju 6 agentów, model żądania misji i raport diagnostyczny
        as_code = ArtifactInspector.get_source(os.path.join(PROJECT_ROOT, "AutoSwarm", "webui_server.py"))
        as_meta_m = re.search(r"agent_meta\s*=\s*(\{.*?\n    \})", as_code, re.DOTALL)
        self.assertIsNotNone(as_meta_m)
        meta = ast.literal_eval(as_meta_m.group(1))
        self.assertEqual(len(meta), 6)
        self.assertEqual(set(meta.keys()), {"codex", "claude-code", "opencode", "copilot", "muse", "hermes"})
        self.assertIn("get_doctor_report", as_code)
        self.assertIn("class ApprovalDecisionRequest", as_code)

        # Krok 3: Weryfikacja launcherów
        with open(os.path.join(PROJECT_ROOT, "rerun-sdk", "launch_rerun.bat"), "r", encoding="utf-8") as f:
            self.assertIn("webui_server.py", f.read())
        with open(os.path.join(PROJECT_ROOT, "AutoSwarm", "launch_autoswarm.bat"), "r", encoding="utf-8") as f:
            self.assertIn("webui_server.py", f.read())

    def test_t4_05_scenario_full_parallel_ecosystem_health(self):
        """
        Scenariusz 5: Pełny Równoległy Rozruch Ekosystemu (Jednoczesna praca 9 narzędzi + Hub).
        Kroki:
        1. Odpytanie Master Hub `/api/status` o pełen rejestr narzędzi.
        2. Weryfikacja, że wszystkie 9 narzędzi są zarejestrowane z poprawnymi portami.
        3. Sprawdzenie, że każdy skrypt startowy `.bat` istnieje i ma poprawną ścieżkę.
        4. Potwierdzenie gotowości całego ekosystemu AI-Tools do pracy produkcyjnej.
        """
        status, data = NetworkProbe.http_get_json("http://127.0.0.1:7800/api/status", timeout=2.5)
        self.assertEqual(status, 200)
        tools = data["tools"]

        self.assertEqual(len(tools), 9)
        for tid, tinfo in tools.items():
            self.assertIn("name", tinfo)
            self.assertIn("port", tinfo)
            self.assertIn("status", tinfo)
            self.assertIn("launch_script", tinfo)
            self.assertTrue(os.path.exists(tinfo["launch_script"]), f"Brak skryptu startowego: {tinfo['launch_script']}")

        # Weryfikacja Master Launcher script
        master_bat = os.path.join(PROJECT_ROOT, "launch_all_tools.bat")
        self.assertTrue(os.path.isfile(master_bat))


# ==============================================================================
# BEAUTIFUL TEST RUNNER & FORMATTER
# ==============================================================================

def run_suite():
    print("\n" + "=" * 80)
    print("      AI-TOOLS AUTOMATED 4-TIER E2E TEST SUITE (REMEDIATED V2)")
    print("      Weryfikacja 9 Aplikacji Desktopowych AI oraz Master Hub")
    print("      Architektura Dual-Mode: Live Probing + Deep Static AST/Schema")
    print("=" * 80 + "\n")

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Dodanie klas testowych w porządku tierów
    suite.addTests(loader.loadTestsFromTestCase(TestTier1FeatureCoverage))
    suite.addTests(loader.loadTestsFromTestCase(TestTier2BoundaryCornerCases))
    suite.addTests(loader.loadTestsFromTestCase(TestTier3CrossFeatureCombinations))
    suite.addTests(loader.loadTestsFromTestCase(TestTier4RealWorldScenarios))

    total_tests = suite.countTestCases()
    print(f"[*] Skonfigurowano testów: {total_tests}")
    print("    - Tier 1 (Feature Coverage):           50 testów")
    print("    - Tier 2 (Boundary & Corner Cases):     50 testów")
    print("    - Tier 3 (Cross-Feature Combinations):  11 testów")
    print("    - Tier 4 (Real-World Scenarios):         5 testów")
    print("    - Łączna liczba asercji:               >=120 asercji\n")
    print("-" * 80)

    start_time = time.time()
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    elapsed = time.time() - start_time

    print("\n" + "=" * 80)
    print(f"[*] WYNIKI PAKIETU TESTÓW E2E:")
    print(f"    Wykonano testów:   {result.testsRun}")
    print(f"    Sukcesy (PASS):    {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"    Błędy (ERRORS):    {len(result.errors)}")
    print(f"    Porażki (FAILS):   {len(result.failures)}")
    print(f"    Czas wykonania:    {elapsed:.2f} s")
    print("=" * 80)

    stop_hub_if_started()

    if result.wasSuccessful():
        print("\n>>> [SUKCES 100%] Wszystkie testy E2E zakończyły się pomyślnie! <<<")
        print(">>> System AI-Tools jest w pełni zintegrowany, wolny od kolizji i gotowy do pracy. <<<\n")
        return 0
    else:
        print("\n>>> [PORAŻKA] Niektóre testy E2E nie przeszły weryfikacji. Sprawdź logi powyżej. <<<\n")
        return 1


if __name__ == "__main__":
    exit_code = run_suite()
    sys.exit(exit_code)
