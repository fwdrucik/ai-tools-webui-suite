#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Automatyczny test weryfikacyjny dla AutoSwarm Multi-Agent WebUI (Port 7868).
"""

import sys
import time
from pathlib import Path
from fastapi.testclient import TestClient

# Dodaj ścieżkę do sys.path
APP_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(APP_DIR))

import webui_server
from webui_server import app

def test_autoswarm_webui():
    print("[TEST] Inicjalizacja TestClient dla AutoSwarm Multi-Agent...")
    with TestClient(app) as client:
        # 1. Health check
        print("[TEST 1/7] Weryfikacja endpointu /health...")
        resp = client.get("/health")
        assert resp.status_code == 200, f"Health check błąd: {resp.status_code}"
        health_data = resp.json()
        assert health_data["status"] == "ok"
        assert health_data["app"] == "AutoSwarm Multi-Agent"
        assert health_data["port"] == 7868
        print(f"  -> Wynik /health: {health_data} [OK]")

        # 2. Wykryte agenty
        print("[TEST 2/7] Weryfikacja endpointu /api/agents...")
        resp = client.get("/api/agents")
        assert resp.status_code == 200
        agents_data = resp.json()
        assert agents_data["ok"] is True
        agents_list = agents_data["data"]
        
        # Weryfikacja czy wykryto 6 głównych agentów
        providers = {a["provider"]: a for a in agents_list}
        expected_providers = ["codex", "claude-code", "opencode", "copilot", "muse", "hermes"]
        for exp in expected_providers:
            assert exp in providers, f"Brak agenta {exp} na liście wykrytych!"
            assert providers[exp]["available"] is True, f"Agent {exp} powinien być dostępny!"
            print(f"  -> Agent {providers[exp]['display_name']} (wersja: {providers[exp]['version'][:30]}...) [DOSTĘPNY - OK]")

        # 3. AutoSwarm Doctor
        print("[TEST 3/7] Weryfikacja endpointu /api/doctor...")
        resp = client.get("/api/doctor")
        assert resp.status_code == 200
        doctor_data = resp.json()
        assert doctor_data["ok"] is True
        doc_report = doctor_data["data"]
        assert doc_report["available_agents"] >= 6
        assert "autoswarm" in doc_report["home"].lower()
        print(f"  -> Raport Doctor: {doc_report['available_agents']} agentów dostępnych, Home: {doc_report['home']} [OK]")

        # 4. Interfejs HTML Landing Page
        print("[TEST 4/7] Weryfikacja strony głównej HTML /...")
        resp = client.get("/")
        assert resp.status_code == 200
        html = resp.text
        assert "AUTOSWARM MULTI-AGENT" in html
        assert "Centrum Dowodzenia Rojem" in html
        assert "Dyspozytor Misji Roju" in html
        assert "Panel Zgód (Approvals)" in html
        assert "Strumień Wykonania na Żywo" in html
        assert "Refaktoryzacja" in html
        assert "Testy TDD" in html
        print("  -> Interfejs HTML poprawnie wygenerowany z pełną polską lokalizacją [OK]")

        # 5. Lista zgód
        print("[TEST 5/7] Weryfikacja endpointu /api/approvals...")
        resp = client.get("/api/approvals")
        assert resp.status_code == 200
        approvals_data = resp.json()
        assert approvals_data["ok"] is True
        print(f"  -> Lista zgód pobrana: {len(approvals_data['data'])} oczekujących [OK]")

        # 6. Dyspozycja misji roju (/api/dispatch)
        print("[TEST 6/7] Testowanie wysyłki misji roju /api/dispatch...")
        mission_payload = {
            "lead_agent": "codex",
            "workers": ["claude-code", "opencode"],
            "cwd": "D:\\AI-Tools",
            "effort": "high",
            "delegate_approvals": True,
            "prompt": "Przeprowadź refaktoryzację modułu przetwarzania danych zgodnie z SOLID i napisz testy TDD."
        }
        resp = client.post("/api/dispatch", json=mission_payload)
        assert resp.status_code == 200, f"Błąd dispatchu: {resp.text}"
        dispatch_res = resp.json()
        assert dispatch_res["ok"] is True
        mission_id = dispatch_res["mission_id"]
        print(f"  -> Misja pomyślnie zarejestrowana: {mission_id} (Lead: {dispatch_res['lead_agent']}) [OK]")

        # 7. Weryfikacja historii misji i logów
        print("[TEST 7/7] Weryfikacja /api/missions i /api/mission/{id}/logs...")
        resp = client.get("/api/missions")
        assert resp.status_code == 200
        missions_list = resp.json()["data"]
        assert any(m["id"] == mission_id for m in missions_list), f"Misja {mission_id} nie znaleziona w historii!"

        resp = client.get(f"/api/mission/{mission_id}/logs")
        assert resp.status_code == 200
        logs = resp.json()["data"]
        print(f"  -> Pobrano logi dla misji {mission_id} (zarejestrowane zdarzenia: {len(logs)}) [OK]")

    print("\n============================================================")
    print("  WSZYSTKIE TESTY DLA AUTOSWARM MULTI-AGENT ZAKOŃCZONE SUKCESEM!")
    print("============================================================\n")

if __name__ == "__main__":
    test_autoswarm_webui()
