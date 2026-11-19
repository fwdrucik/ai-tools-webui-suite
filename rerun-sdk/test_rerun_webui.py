#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Automatyczny test weryfikacyjny dla Rerun 3D Visualizer WebUI (Port 7867).
"""

import sys
import io
from pathlib import Path
from fastapi.testclient import TestClient

# Dodaj ścieżkę do sys.path
SDK_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SDK_DIR))

import webui_server
from webui_server import app

def test_rerun_webui():
    print("[TEST] Inicjalizacja TestClient dla Rerun 3D Studio...")
    with TestClient(app) as client:
        # 1. Health check
        print("[TEST 1/7] Weryfikacja endpointu /health...")
        resp = client.get("/health")
        assert resp.status_code == 200, f"Health check nieudany: {resp.status_code}"
        health_data = resp.json()
        assert health_data["status"] == "ok"
        assert health_data["app"] == "Rerun 3D Visualizer"
        assert health_data["port"] == 7867
        print(f"  -> Wynik: {health_data} [OK]")

        # 2. Status API
        print("[TEST 2/7] Weryfikacja endpointu /api/status...")
        resp = client.get("/api/status")
        assert resp.status_code == 200
        status_data = resp.json()
        assert status_data["version"] == "0.43.2"
        assert status_data["webui_port"] == 7867
        assert status_data["web_viewer_port"] == 9097
        assert status_data["grpc_port"] == 9877
        print(f"  -> Stan silnika: {status_data['status']}, encje: {status_data['total_logged_entities']} [OK]")

        # 3. HTML Landing Page
        print("[TEST 3/7] Weryfikacja strony głównej HTML /...")
        resp = client.get("/")
        assert resp.status_code == 200
        html = resp.text
        assert "RERUN 3D VISUALIZER" in html
        assert "http://localhost:9097" in html
        assert "Kolorowa Chmura Punktów RGB" in html
        assert "Helisa DNA 3D" in html
        assert "Detekcja LiDAR 3D z Bounding Boxes" in html
        assert "Siatka Geometryczna 3D" in html
        assert "Przebiegi Czasowe i Sensoryka" in html
        print("  -> Interfejs HTML poprawnie wygenerowany z pełną polską lokalizacją [OK]")

        # 4. Wszystkie 5 Scen Demonstracyjnych
        for demo_id in range(1, 6):
            print(f"[TEST 4/7 - Scena {demo_id}] Testowanie generowania sceny demonstracyjnej #{demo_id}...")
            resp = client.post(f"/api/demos/{demo_id}")
            assert resp.status_code == 200, f"Błąd sceny {demo_id}: {resp.text}"
            demo_res = resp.json()
            assert demo_res["status"] == "ok"
            print(f"  -> Scena #{demo_id} załadowana pomyślnie: {demo_res} [OK]")

        # 5. Błędny ID demonstracji
        print("[TEST 5/7] Weryfikacja obsługi błędów dla nieistniejącej sceny /api/demos/99...")
        resp = client.post("/api/demos/99")
        assert resp.status_code == 400
        print("  -> Poprawna obsługa błędu 400 dla nieznanego ID [OK]")

        # 6. Upload pliku 3D (.obj)
        print("[TEST 6/7] Testowanie uploadu modelu 3D /api/upload-model...")
        sample_obj = b"v 0.0 0.0 0.0\nv 1.0 0.0 0.0\nv 0.0 1.0 0.0\nf 1 2 3\n"
        files = {"file": ("test_trojkat.obj", io.BytesIO(sample_obj), "text/plain")}
        resp = client.post("/api/upload-model", files=files)
        assert resp.status_code == 200, f"Błąd uploadu: {resp.text}"
        upload_res = resp.json()
        assert upload_res["status"] == "ok"
        print(f"  -> Model 3D pomyślnie załadowany i zalogowany do Rerun: {upload_res} [OK]")

        # 7. Wyszukiwanie natywnego rerun.exe
        print("[TEST 7/7] Weryfikacja dostępności natywnego rerun.exe...")
        exe_path = webui_server.find_rerun_executable()
        assert exe_path is not None, "Nie znaleziono rerun.exe!"
        print(f"  -> Odnaleziono rerun.exe: {exe_path} [OK]")

    print("\n============================================================")
    print("  WSZYSTKIE TESTY DLA RERUN 3D VISUALIZER ZAKOŃCZONE SUKCESEM!")
    print("============================================================\n")

if __name__ == "__main__":
    test_rerun_webui()
