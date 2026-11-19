#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rerun 3D Visualizer - Zaawansowane Polskie Studio Wizualizacji Danych Multimodalnych i Przestrzennych 3D.
Port WebUI: 7867 | Port Web Viewer: 9097 | Port gRPC Server: 9877
"""

import os
import sys
import time
import math
import shutil
import subprocess
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional
from contextlib import asynccontextmanager

import numpy as np
import rerun as rr
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Ścieżki bazowe i porty
ROOT_DIR = Path(__file__).resolve().parent
UPLOADS_DIR = ROOT_DIR / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

WEBUI_PORT = 7867
WEB_VIEWER_PORT = 9097
GRPC_PORT = 9877

# Stan serwera Rerun
rerun_state = {
    "initialized": False,
    "grpc_uri": None,
    "web_viewer_active": False,
    "recording_id": "rerun_studio_session",
    "total_logged_entities": 0,
    "uploaded_files": [],
    "last_demo_loaded": None,
    "start_time": time.time(),
}

def find_rerun_executable() -> Optional[str]:
    """Wyszukuje ścieżkę do wykonywalnego pliku rerun.exe."""
    cli = shutil.which("rerun")
    if cli and os.path.exists(cli):
        return cli
    custom_paths = [
        Path(os.environ.get("APPDATA", "")) / "Python" / "Python314" / "Scripts" / "rerun.exe",
        Path(os.environ.get("USERPROFILE", "")) / ".local" / "bin" / "rerun.exe",
        Path(os.environ.get("USERPROFILE", "")) / ".cargo" / "bin" / "rerun.exe",
    ]
    for p in custom_paths:
        if p.exists():
            return str(p)
    return None

def init_rerun_session():
    """Inicjalizuje strumień Rerun, serwer gRPC i Web Viewer."""
    try:
        rr.init("Rerun_3D_Studio", spawn=False)
        rr.log("/", rr.ViewCoordinates.RIGHT_HAND_Z_UP, static=True)
        
        # Uruchom serwer gRPC
        grpc_uri = rr.serve_grpc(grpc_port=GRPC_PORT)
        rerun_state["grpc_uri"] = grpc_uri
        
        # Uruchom Web Viewer
        rr.serve_web_viewer(web_port=WEB_VIEWER_PORT, open_browser=False, connect_to=grpc_uri)
        rerun_state["web_viewer_active"] = True
        rerun_state["initialized"] = True
        print(f"[Rerun Studio] gRPC serwer nasłuchuje na {grpc_uri}")
        print(f"[Rerun Studio] Web Viewer dostępny pod http://localhost:{WEB_VIEWER_PORT}")
        
        # Wczytaj początkową powitalną scenę (Wielowymiarowy Układ Współrzędnych z Siatką Przestrzenną)
        generate_welcome_scene()
    except Exception as e:
        print(f"[Rerun Studio] Błąd startu Rerun: {e}", file=sys.stderr)
        rerun_state["error"] = str(e)

def generate_welcome_scene():
    """Generuje wstępną, powitalną scenę z siatką przestrzenną i wektorami bazowymi."""
    try:
        rr.set_time("krok_czasowy", sequence=0)
        # Siatka podłoża
        grid_range = np.linspace(-5, 5, 21)
        lines = []
        for v in grid_range:
            lines.append([[-5.0, float(v), 0.0], [5.0, float(v), 0.0]])
            lines.append([[float(v), -5.0, 0.0], [float(v), 5.0, 0.0]])
        rr.log("studio/siatka_podloza", rr.LineStrips3D(lines, colors=[70, 85, 110, 180], radii=0.01))
        
        # Osie współrzędnych XYZ (Czerwony X, Zielony Y, Niebieski Z)
        axis_lines = [
            [[0.0, 0.0, 0.0], [2.0, 0.0, 0.0]],
            [[0.0, 0.0, 0.0], [0.0, 2.0, 0.0]],
            [[0.0, 0.0, 0.0], [0.0, 0.0, 2.0]],
        ]
        axis_colors = [
            [255, 60, 60, 255],   # X
            [60, 230, 90, 255],   # Y
            [60, 140, 255, 255],  # Z
        ]
        rr.log("studio/osie_wspolrzednych", rr.LineStrips3D(axis_lines, colors=axis_colors, radii=0.03))
        
        # Etykieta powitalna
        rr.log("studio/powitanie", rr.Points3D([[0.0, 0.0, 2.2]], labels=["Rerun 3D Studio - Gotowe do Pracy"], radii=0.08, colors=[0, 220, 255, 255]))
        rerun_state["total_logged_entities"] += 3
    except Exception as e:
        print(f"[Rerun Studio] Błąd generowania sceny powitalnej: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start usług w tle
    init_rerun_session()
    yield
    print("[Rerun Studio] Zamykanie serwera...")

app = FastAPI(
    title="Rerun 3D Visualizer WebUI",
    description="Profesjonalny interfejs webowy dla silnika Rerun 3D z polską lokalizacją",
    version="0.43.2",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------------------
# 5 POLSKICH INTERAKTYWNYCH SCEN DEMONSTRACYJNYCH
# -------------------------------------------------------------

def demo_1_point_cloud_rgb():
    """Scena 1: Kolorowa Chmura Punktów RGB (Points3D z gradientem przestrzennym)."""
    n_points = 6000
    phi = np.linspace(0, 8 * np.pi, n_points)
    theta = np.linspace(0, 2 * np.pi, n_points)
    r = 2.5 + 0.8 * np.cos(3 * theta)
    
    x = r * np.sin(theta) * np.cos(phi * 0.25)
    y = r * np.cos(theta) * np.cos(phi * 0.25)
    z = 1.2 * np.sin(phi * 0.25) + 0.3 * np.sin(10 * theta)
    
    pts = np.column_stack([x, y, z])
    # Normalizacja kolorów do przestrzeni RGB [0, 255]
    norm_x = np.uint8(np.clip((x + 3.5) / 7.0 * 255, 0, 255))
    norm_y = np.uint8(np.clip((y + 3.5) / 7.0 * 255, 0, 255))
    norm_z = np.uint8(np.clip((z + 2.0) / 4.0 * 255, 0, 255))
    colors = np.column_stack([norm_x, norm_y, norm_z, np.full(n_points, 240, dtype=np.uint8)])
    radii = np.float32(0.02 + 0.025 * np.abs(np.sin(theta * 2)))
    
    rr.set_time("krok_czasowy", sequence=1)
    rr.log("sceny_demo/scena_1_chmura_rgb", rr.Points3D(
        positions=pts,
        colors=colors,
        radii=radii,
        labels=[f"Pkt #{i}" if i % 1000 == 0 else "" for i in range(n_points)]
    ))
    rerun_state["total_logged_entities"] += 1
    rerun_state["last_demo_loaded"] = "Scena 1: Kolorowa Chmura Punktów RGB"
    return {"status": "ok", "elements": n_points, "name": "Kolorowa Chmura Punktów RGB"}

def demo_2_dna_helix():
    """Scena 2: Helisa DNA 3D (Podwójna helisa z parami zasad azotowych)."""
    n_pairs = 80
    t = np.linspace(0, 6 * np.pi, n_pairs)
    radius = 1.2
    pitch = 0.25
    
    # Nić 1 i Nić 2
    x1, y1, z1 = radius * np.cos(t), radius * np.sin(t), pitch * t
    x2, y2, z2 = radius * np.cos(t + np.pi), radius * np.sin(t + np.pi), pitch * t
    
    pts1 = np.column_stack([x1, y1, z1])
    pts2 = np.column_stack([x2, y2, z2])
    
    # Kolory nici cukrowo-fosforanowych
    color_strand1 = [0, 200, 255, 255]  # Cyjan
    color_strand2 = [255, 80, 160, 255]  # Róż
    
    # Szczeble - Pary Zasad (Adenina-Tymina, Guanina-Cytozyna)
    rungs_lines = []
    rungs_colors = []
    base_pairs_labels = []
    base_pair_types = ["A-T (Adenina-Tymina)", "G-C (Guanina-Cytozyna)", "T-A (Tymina-Adenina)", "C-G (Cytozyna-Guanina)"]
    palette = [
        [255, 70, 70, 255],   # A-T: Czerwony
        [70, 230, 90, 255],   # G-C: Zielony
        [255, 200, 40, 255],  # T-A: Złoty
        [140, 90, 255, 255],  # C-G: Fioletowy
    ]
    
    for i in range(n_pairs):
        p1 = [float(x1[i]), float(y1[i]), float(z1[i])]
        p2 = [float(x2[i]), float(y2[i]), float(z2[i])]
        rungs_lines.append([p1, p2])
        pair_type_idx = i % 4
        rungs_colors.append(palette[pair_type_idx])
        base_pairs_labels.append(base_pair_types[pair_type_idx])
    
    rr.set_time("krok_czasowy", sequence=2)
    rr.log("sceny_demo/scena_2_dna/nic_wiodaca", rr.Points3D(pts1, colors=color_strand1, radii=0.07, labels=["Nić wiodąca 5'->3'"]))
    rr.log("sceny_demo/scena_2_dna/nic_matrycowa", rr.Points3D(pts2, colors=color_strand2, radii=0.07, labels=["Nić komplementarna 3'->5'"]))
    rr.log("sceny_demo/scena_2_dna/pary_zasad", rr.LineStrips3D(rungs_lines, colors=rungs_colors, radii=0.03))
    
    rerun_state["total_logged_entities"] += 3
    rerun_state["last_demo_loaded"] = "Scena 2: Helisa DNA 3D"
    return {"status": "ok", "base_pairs": n_pairs, "name": "Helisa DNA 3D"}

def demo_3_lidar_detection():
    """Scena 3: Detekcja LiDAR 3D z Bounding Boxes (Pojazdy autonomiczne, przeszkody)."""
    # 1. Symulacja skanu LiDAR drogi i otoczenia (ok. 5000 punktów)
    n_road = 3500
    rx = np.random.uniform(-10, 10, n_road)
    ry = np.random.uniform(-5, 35, n_road)
    rz = np.random.normal(0.0, 0.05, n_road)
    
    # Krawężniki i pobocze
    mask_curb = (np.abs(rx) > 6.0)
    rz[mask_curb] += 0.25
    
    road_pts = np.column_stack([rx, ry, rz])
    road_intensity = np.uint8(np.clip(180 - (ry * 3), 40, 200))
    road_colors = np.column_stack([road_intensity, road_intensity, road_intensity + 30, np.full(n_road, 200, dtype=np.uint8)])
    
    # 2. Bounding Boxes dla obiektów w ruchu drogowym
    centers = [
        [0.0, 8.5, 0.75],       # Samochód przed nami
        [-3.2, 16.0, 0.80],     # Samochód na lewym pasie
        [3.8, 12.0, 1.60],      # Ciężarówka dostawcza na prawym pasie
        [2.5, 5.0, 0.90],       # Rowerzysta przy krawędzi
        [-1.8, 4.2, 0.95],      # Pieszy na przejściu
    ]
    half_sizes = [
        [0.95, 2.25, 0.75],     # Samochód: szer 1.9m, dł 4.5m, wys 1.5m
        [0.90, 2.10, 0.75],
        [1.25, 4.20, 1.60],     # Ciężarówka: szer 2.5m, dł 8.4m, wys 3.2m
        [0.35, 0.95, 0.90],     # Rowerzysta
        [0.30, 0.35, 0.95],     # Pieszy
    ]
    labels = [
        "Samochód Osobowy [ID: 101, v: 48 km/h]",
        "Samochód Osobowy [ID: 102, v: 54 km/h]",
        "Ciężarówka Dostawcza [ID: 103, v: 42 km/h]",
        "Rowerzysta [ID: 201, v: 18 km/h]",
        "Pieszy [ID: 301, v: 4 km/h - Uwaga!]",
    ]
    box_colors = [
        [0, 255, 128, 255],    # Zielony
        [0, 255, 128, 255],    # Zielony
        [160, 80, 255, 255],   # Fiolet
        [0, 220, 255, 255],    # Cyjan
        [255, 60, 60, 255],    # Czerwony ostrzegawczy
    ]
    
    rr.set_time("krok_czasowy", sequence=3)
    rr.log("sceny_demo/scena_3_lidar/chmura_otoczenia", rr.Points3D(road_pts, colors=road_colors, radii=0.03))
    rr.log("sceny_demo/scena_3_lidar/wykryte_obiekty_3d", rr.Boxes3D(
        centers=centers,
        half_sizes=half_sizes,
        labels=labels,
        colors=box_colors,
        fill_mode="MajorWireframe"
    ))
    
    rerun_state["total_logged_entities"] += 2
    rerun_state["last_demo_loaded"] = "Scena 3: Detekcja LiDAR 3D z Bounding Boxes"
    return {"status": "ok", "points": n_road, "boxes": len(centers), "name": "Detekcja LiDAR 3D"}

def demo_4_geometric_mesh():
    """Scena 4: Siatka Geometryczna 3D (Torus 3D z siatką trójkątów, normalnymi i kolorami wierzchołków)."""
    R_major = 2.4
    r_minor = 0.9
    n_u = 36
    n_v = 24
    
    u_vals = np.linspace(0, 2 * np.pi, n_u, endpoint=False)
    v_vals = np.linspace(0, 2 * np.pi, n_v, endpoint=False)
    U, V = np.meshgrid(u_vals, v_vals)
    
    X = (R_major + r_minor * np.cos(V)) * np.cos(U)
    Y = (R_major + r_minor * np.cos(V)) * np.sin(U)
    Z = r_minor * np.sin(V)
    
    verts = np.column_stack([X.ravel(), Y.ravel(), Z.ravel()])
    
    # Wektory normalne wierzchołków
    Nx = np.cos(V) * np.cos(U)
    Ny = np.cos(V) * np.sin(U)
    Nz = np.sin(V)
    normals = np.column_stack([Nx.ravel(), Ny.ravel(), Nz.ravel()])
    
    # Kolory wierzchołków w oparciu o pozycję
    col_r = np.uint8(np.clip((Nx.ravel() + 1.0) * 0.5 * 255, 0, 255))
    col_g = np.uint8(np.clip((Ny.ravel() + 1.0) * 0.5 * 255, 0, 255))
    col_b = np.uint8(np.clip((Nz.ravel() + 1.0) * 0.5 * 255, 0, 255))
    vertex_colors = np.column_stack([col_r, col_g, col_b, np.full(len(verts), 255, dtype=np.uint8)])
    
    # Indeksy trójkątów siatki
    triangles = []
    for j in range(n_v):
        for i in range(n_u):
            i_next = (i + 1) % n_u
            j_next = (j + 1) % n_v
            
            p1 = j * n_u + i
            p2 = j_next * n_u + i
            p3 = j_next * n_u + i_next
            p4 = j * n_u + i_next
            
            triangles.append([p1, p2, p3])
            triangles.append([p1, p3, p4])
            
    rr.set_time("krok_czasowy", sequence=4)
    rr.log("sceny_demo/scena_4_siatka/torus_3d", rr.Mesh3D(
        vertex_positions=verts,
        triangle_indices=triangles,
        vertex_normals=normals,
        vertex_colors=vertex_colors
    ))
    
    rerun_state["total_logged_entities"] += 1
    rerun_state["last_demo_loaded"] = "Scena 4: Siatka Geometryczna 3D"
    return {"status": "ok", "vertices": len(verts), "triangles": len(triangles), "name": "Siatka Geometryczna 3D"}

def demo_5_sensor_telemetry():
    """Scena 5: Przebiegi Czasowe i Sensoryka (Wielokanałowa telemetria przemysłowa)."""
    n_steps = 150
    time_points = np.linspace(0, 15.0, n_steps)
    
    for step, t in enumerate(time_points):
        rr.set_time("czas_sekundy", duration=float(t))
        rr.set_time("krok_symulacji", sequence=step)
        
        # 1. Temperatura uzwojenia silnika elektrycznego [°C]
        temp_silnika = 45.0 + 35.0 * (1.0 - math.exp(-t / 4.0)) + np.random.normal(0, 0.4)
        rr.log("sceny_demo/scena_5_sensoryka/temperatura_uzwojenia_c", rr.Scalars(temp_silnika))
        
        # 2. Prędkość obrotowa wrzeciona [RPM]
        rpm = 3000.0 * (1.0 - math.exp(-t / 1.5)) + 120.0 * math.sin(t * 3.0) + np.random.normal(0, 15.0)
        rr.log("sceny_demo/scena_5_sensoryka/obroty_wrzeciona_rpm", rr.Scalars(rpm))
        
        # 3. Wibracje osi Z [mm/s] (Peak-to-Peak)
        vib_z = 1.2 + 0.8 * math.sin(t * 8.0) * math.cos(t * 2.0) + np.random.normal(0, 0.1)
        rr.log("sceny_demo/scena_5_sensoryka/wibracje_z_mms", rr.Scalars(vib_z))
        
        # 4. Ciśnienie w układzie chłodzenia [bar]
        cisnienie_bar = 5.5 - 0.6 * (1.0 - math.exp(-t / 6.0)) + np.random.normal(0, 0.05)
        rr.log("sceny_demo/scena_5_sensoryka/cisnienie_chlodziwa_bar", rr.Scalars(cisnienie_bar))
        
        # 5. Pobór prądu falownika [A]
        prad_a = 18.0 + (rpm / 3000.0) * 32.0 + np.random.normal(0, 0.7)
        rr.log("sceny_demo/scena_5_sensoryka/prad_fazowy_a", rr.Scalars(prad_a))
        
    rerun_state["total_logged_entities"] += 5
    rerun_state["last_demo_loaded"] = "Scena 5: Przebiegi Czasowe i Sensoryka"
    return {"status": "ok", "steps": n_steps, "channels": 5, "name": "Przebiegi Czasowe i Sensoryka"}

# -------------------------------------------------------------
# ENDPOINTY API
# -------------------------------------------------------------

@app.get("/health")
def health_check():
    """Wymagany kontraktem endpoint kontrolny."""
    return {"status": "ok", "app": "Rerun 3D Visualizer", "port": WEBUI_PORT}

@app.get("/api/status")
def get_status():
    """Zwraca bieżący stan silnika Rerun, portów i pamięci."""
    rerun_cli = find_rerun_executable()
    return {
        "status": "ok",
        "app": "Rerun 3D Visualizer",
        "version": "0.43.2",
        "webui_port": WEBUI_PORT,
        "web_viewer_port": WEB_VIEWER_PORT,
        "grpc_port": GRPC_PORT,
        "grpc_uri": rerun_state.get("grpc_uri"),
        "web_viewer_active": rerun_state.get("web_viewer_active", False),
        "total_logged_entities": rerun_state.get("total_logged_entities", 0),
        "uploaded_files": rerun_state.get("uploaded_files", []),
        "last_demo_loaded": rerun_state.get("last_demo_loaded"),
        "rerun_cli_path": rerun_cli,
        "rerun_cli_available": bool(rerun_cli),
        "uptime_seconds": int(time.time() - rerun_state["start_time"]),
    }

@app.post("/api/demos/{demo_id}")
def trigger_demo(demo_id: int):
    """Uruchamia generowanie i logowanie wybranej demonstracji 3D."""
    if demo_id == 1:
        res = demo_1_point_cloud_rgb()
    elif demo_id == 2:
        res = demo_2_dna_helix()
    elif demo_id == 3:
        res = demo_3_lidar_detection()
    elif demo_id == 4:
        res = demo_4_geometric_mesh()
    elif demo_id == 5:
        res = demo_5_sensor_telemetry()
    else:
        raise HTTPException(status_code=400, detail=f"Nieznany numer demonstracji: {demo_id} (Dozwolone: 1..5)")
    return res

@app.post("/api/upload-model")
async def upload_model(file: UploadFile = File(...)):
    """Przyjmuje plik modelu 3D (.obj, .stl, .ply, .glb, .gltf, .rrd) i ładuje go do Rerun."""
    ext = Path(file.filename).suffix.lower()
    allowed_extensions = {".obj", ".stl", ".ply", ".glb", ".gltf", ".rrd"}
    if ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail=f"Nieobsługiwany format: {ext}. Dozwolone: {', '.join(allowed_extensions)}")
    
    target_path = UPLOADS_DIR / file.filename
    with open(target_path, "wb") as f:
        content = await file.read()
        f.write(content)
        
    entity_path = f"wgrane_modele/{Path(file.filename).stem}"
    
    try:
        # Próba wczytania przez Importer Rerun
        rr.set_time("krok_czasowy", sequence=int(time.time()) % 10000)
        try:
            rr.log_file_from_path(str(target_path), entity_path_prefix=entity_path)
        except Exception:
            rr.log(entity_path, rr.Asset3D(path=str(target_path)))
            
        rerun_state["total_logged_entities"] += 1
        rerun_state["uploaded_files"].append({
            "filename": file.filename,
            "size_bytes": len(content),
            "entity_path": entity_path,
            "uploaded_at": time.strftime("%H:%M:%S")
        })
        return {
            "status": "ok",
            "message": f"Plik {file.filename} został pomyślnie załadowany do wizualizacji!",
            "entity_path": entity_path,
            "size_bytes": len(content)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Błąd podczas wczytywania modelu do Rerun: {e}")

@app.post("/api/viewer/launch-native")
def launch_native_viewer():
    """Uruchamia natywny Rerun Viewer na pulpicie z akceleracją sprzętową GPU."""
    cli = find_rerun_executable()
    if not cli:
        raise HTTPException(status_code=500, detail="Nie odnaleziono pliku rerun.exe w systemie!")
    
    try:
        server_target = f"rerun+http://127.0.0.1:{GRPC_PORT}/proxy"
        # Spawnowanie procesu natywnego w tle
        subprocess.Popen(
            [cli, server_target],
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS if os.name == "nt" else 0,
            close_fds=True
        )
        return {
            "status": "ok",
            "message": "Natywny Rerun Viewer został pomyślnie uruchomiony na pulpicie!",
            "connected_to": server_target
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Błąd uruchamiania natywnego Viewera: {e}")

@app.post("/api/viewer/restart")
def restart_viewer():
    """Restartuje sesję Rerun w przypadku zawieszenia gniazda."""
    init_rerun_session()
    return {"status": "ok", "message": "Zresetowano sesję gRPC i Web Viewera Rerun."}

# -------------------------------------------------------------
# INTERFEJS UŻYTKOWNIKA (HTML5 + TAILWIND CSS + POLISH LOCALIZATION)
# -------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def index_html():
    return f"""<!DOCTYPE html>
<html lang="pl">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Rerun 3D Studio — Interaktywny Wizualizator Danych Przestrzennych</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  <style>
    body {{
      background-color: #0b0f19;
      color: #e2e8f0;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    }}
    .glow-cyan {{
      box-shadow: 0 0 15px rgba(6, 182, 212, 0.35);
    }}
    .glow-emerald {{
      box-shadow: 0 0 15px rgba(16, 185, 129, 0.35);
    }}
    .viewer-frame {{
      background: #020617;
      border: 1px solid #1e293b;
      height: calc(100vh - 90px);
    }}
    ::-webkit-scrollbar {{
      width: 6px;
      height: 6px;
    }}
    ::-webkit-scrollbar-track {{
      background: #0f172a;
    }}
    ::-webkit-scrollbar-thumb {{
      background: #334155;
      border-radius: 3px;
    }}
    ::-webkit-scrollbar-thumb:hover {{
      background: #475569;
    }}
  </style>
</head>
<body class="min-h-screen flex flex-col overflow-hidden">

  <!-- GÓRNY PASEK NAWIGACYJNY I STATUS -->
  <header class="h-16 bg-slate-900 border-b border-slate-800 px-6 flex items-center justify-between z-20">
    <div class="flex items-center space-x-4">
      <div class="w-10 h-10 rounded-lg bg-gradient-to-tr from-cyan-600 to-blue-500 flex items-center justify-center text-white font-black text-xl shadow-lg glow-cyan">
        <i class="fa-solid fa-cube"></i>
      </div>
      <div>
        <h1 class="text-lg font-bold tracking-tight text-white flex items-center gap-2">
          RERUN 3D VISUALIZER
          <span class="text-xs px-2 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-800">v0.43.2 WebAssembly</span>
        </h1>
        <p class="text-xs text-slate-400">Polskie Profesjonalne Studio Danych Przestrzennych, Chmur Punktów i Telemetrii</p>
      </div>
    </div>

    <!-- WSKAŹNIKI STANU PORTÓW -->
    <div class="flex items-center space-x-3 text-xs">
      <div class="flex items-center space-x-1.5 px-3 py-1.5 rounded-full bg-slate-800/80 border border-slate-700">
        <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
        <span class="text-slate-300">Web Viewer:</span>
        <span class="text-emerald-400 font-mono font-semibold">:{WEB_VIEWER_PORT}</span>
      </div>
      <div class="flex items-center space-x-1.5 px-3 py-1.5 rounded-full bg-slate-800/80 border border-slate-700">
        <span class="w-2 h-2 rounded-full bg-cyan-400"></span>
        <span class="text-slate-300">gRPC Server:</span>
        <span class="text-cyan-400 font-mono font-semibold">:{GRPC_PORT}</span>
      </div>
      <div class="flex items-center space-x-1.5 px-3 py-1.5 rounded-full bg-slate-800/80 border border-slate-700">
        <span class="w-2 h-2 rounded-full bg-indigo-400"></span>
        <span class="text-slate-300">WebUI:</span>
        <span class="text-indigo-400 font-mono font-semibold">:{WEBUI_PORT}</span>
      </div>

      <!-- AKCJE SZYBKIE -->
      <a href="http://localhost:{WEB_VIEWER_PORT}/?url=rerun+http://127.0.0.1:{GRPC_PORT}/proxy" target="_blank"
         class="px-3 py-1.5 rounded bg-cyan-600/20 hover:bg-cyan-600/30 text-cyan-300 border border-cyan-700/50 flex items-center gap-1.5 transition">
        <i class="fa-solid fa-arrow-up-right-from-square text-xs"></i>
        <span>Nowa Karta</span>
      </a>
      <button onclick="refreshIframe()" class="p-2 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition" title="Odśwież Podgląd 3D">
        <i class="fa-solid fa-arrows-rotate"></i>
      </button>
      <button onclick="openDocsModal()" class="px-3 py-1.5 rounded bg-amber-600/20 hover:bg-amber-600/30 text-amber-300 border border-amber-700/50 flex items-center gap-1.5 transition">
        <i class="fa-solid fa-book-open"></i>
        <span>Baza Wiedzy</span>
      </button>
    </div>
  </header>

  <!-- GŁÓWNA STRUKTURA DZIELONA (SPLIT VIEW) -->
  <div class="flex-1 flex overflow-hidden">
    
    <!-- LEWY PANEL STEROWANIA (SIDEBAR) -->
    <aside class="w-96 bg-slate-900/90 border-r border-slate-800 flex flex-col overflow-y-auto p-4 space-y-4">
      
      <!-- KARTA 1: 1-KLIK NATIVE DESKTOP LAUNCHER -->
      <div class="p-3.5 rounded-xl bg-gradient-to-br from-slate-800 to-slate-800/60 border border-slate-700">
        <div class="flex items-center justify-between mb-2">
          <span class="text-xs font-semibold text-cyan-400 uppercase tracking-wider flex items-center gap-1.5">
            <i class="fa-solid fa-bolt"></i> Natywny Desktop
          </span>
          <span class="text-[10px] bg-cyan-950 text-cyan-300 px-1.5 py-0.5 rounded border border-cyan-800">GPU Vulkan/GL</span>
        </div>
        <p class="text-xs text-slate-300 mb-3 leading-relaxed">
          Uruchom pełnoekranową natywną aplikację Rerun z pełną wydajnością Twojej karty graficznej RTX.
        </p>
        <button id="btnNativeLaunch" onclick="launchNativeViewer()"
                class="w-full py-2.5 px-3 rounded-lg bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white font-semibold text-xs flex items-center justify-center gap-2 shadow-md transition active:scale-[0.98]">
          <i class="fa-solid fa-display"></i>
          <span>Uruchom Natywny Rerun Viewer</span>
        </button>
        <div id="nativeLaunchFeedback" class="mt-2 text-[11px] text-center hidden"></div>
      </div>

      <!-- KARTA 2: WGRYWANIE WŁASNYCH MODELI 3D -->
      <div class="p-3.5 rounded-xl bg-slate-800/70 border border-slate-700">
        <div class="flex items-center justify-between mb-2">
          <span class="text-xs font-semibold text-emerald-400 uppercase tracking-wider flex items-center gap-1.5">
            <i class="fa-solid fa-cloud-arrow-up"></i> Import Modeli 3D
          </span>
          <span class="text-[10px] text-slate-400 font-mono">.obj .stl .ply .glb .rrd</span>
        </div>
        
        <div id="dropZone" ondragover="handleDragOver(event)" ondragleave="handleDragLeave(event)" ondrop="handleFileDrop(event)"
             onclick="document.getElementById('fileInput').click()"
             class="border-2 border-dashed border-slate-600 hover:border-emerald-500 rounded-lg p-4 text-center cursor-pointer transition bg-slate-900/50 hover:bg-slate-900/80">
          <input type="file" id="fileInput" class="hidden" accept=".obj,.stl,.ply,.glb,.gltf,.rrd" onchange="handleFileSelect(event)">
          <i class="fa-solid fa-file-arrow-up text-2xl text-slate-400 mb-2"></i>
          <p class="text-xs text-slate-200 font-medium">Przeciągnij plik lub kliknij tutaj</p>
          <p class="text-[10px] text-slate-400 mt-0.5">Obsługuje siatki, chmury punktów oraz archiwa nagrań Rerun</p>
        </div>
        <div id="uploadStatus" class="mt-2 text-[11px] hidden"></div>
      </div>

      <!-- KARTA 3: 5 POLSKICH INTERAKTYWNYCH SCEN DEMO -->
      <div class="p-3.5 rounded-xl bg-slate-800/70 border border-slate-700 flex-1">
        <div class="flex items-center justify-between mb-2.5">
          <span class="text-xs font-semibold text-purple-400 uppercase tracking-wider flex items-center gap-1.5">
            <i class="fa-solid fa-wand-magic-sparkles"></i> Sceny Demonstracyjne
          </span>
          <span class="text-[10px] bg-purple-950 text-purple-300 px-1.5 py-0.5 rounded border border-purple-800">5 Scen PL</span>
        </div>
        <p class="text-xs text-slate-300 mb-3">Kliknij przycisk, aby w czasie rzeczywistym przesłać do Viewera algorytmiczną scenę 3D:</p>

        <div class="space-y-2">
          <!-- DEMO 1 -->
          <button onclick="triggerDemo(1)"
                  class="w-full text-left p-2.5 rounded-lg bg-slate-900/80 hover:bg-slate-700/80 border border-slate-700/80 hover:border-cyan-500/50 transition group flex items-start gap-2.5">
            <div class="w-7 h-7 rounded bg-cyan-950/80 border border-cyan-800 text-cyan-400 flex items-center justify-center text-xs flex-shrink-0 mt-0.5 group-hover:bg-cyan-600 group-hover:text-white transition">
              1
            </div>
            <div>
              <div class="text-xs font-semibold text-slate-200 group-hover:text-cyan-300 transition">Kolorowa Chmura Punktów RGB</div>
              <div class="text-[11px] text-slate-400">6000 punktów z gradientem w przestrzeni 3D (`Points3D`)</div>
            </div>
          </button>

          <!-- DEMO 2 -->
          <button onclick="triggerDemo(2)"
                  class="w-full text-left p-2.5 rounded-lg bg-slate-900/80 hover:bg-slate-700/80 border border-slate-700/80 hover:border-pink-500/50 transition group flex items-start gap-2.5">
            <div class="w-7 h-7 rounded bg-pink-950/80 border border-pink-800 text-pink-400 flex items-center justify-center text-xs flex-shrink-0 mt-0.5 group-hover:bg-pink-600 group-hover:text-white transition">
              2
            </div>
            <div>
              <div class="text-xs font-semibold text-slate-200 group-hover:text-pink-300 transition">Helisa DNA 3D</div>
              <div class="text-[11px] text-slate-400">Podwójna helisa, pary zasad A-T, G-C (`Points3D` + nici)</div>
            </div>
          </button>

          <!-- DEMO 3 -->
          <button onclick="triggerDemo(3)"
                  class="w-full text-left p-2.5 rounded-lg bg-slate-900/80 hover:bg-slate-700/80 border border-slate-700/80 hover:border-emerald-500/50 transition group flex items-start gap-2.5">
            <div class="w-7 h-7 rounded bg-emerald-950/80 border border-emerald-800 text-emerald-400 flex items-center justify-center text-xs flex-shrink-0 mt-0.5 group-hover:bg-emerald-600 group-hover:text-white transition">
              3
            </div>
            <div>
              <div class="text-xs font-semibold text-slate-200 group-hover:text-emerald-300 transition">Detekcja LiDAR 3D z Bounding Boxes</div>
              <div class="text-[11px] text-slate-400">Skan drogi, pojazdy, pieszy, rowerzysta (`Boxes3D`)</div>
            </div>
          </button>

          <!-- DEMO 4 -->
          <button onclick="triggerDemo(4)"
                  class="w-full text-left p-2.5 rounded-lg bg-slate-900/80 hover:bg-slate-700/80 border border-slate-700/80 hover:border-blue-500/50 transition group flex items-start gap-2.5">
            <div class="w-7 h-7 rounded bg-blue-950/80 border border-blue-800 text-blue-400 flex items-center justify-center text-xs flex-shrink-0 mt-0.5 group-hover:bg-blue-600 group-hover:text-white transition">
              4
            </div>
            <div>
              <div class="text-xs font-semibold text-slate-200 group-hover:text-blue-300 transition">Siatka Geometryczna 3D</div>
              <div class="text-[11px] text-slate-400">Torus 3D z normalnymi i kolorami wierzchołków (`Mesh3D`)</div>
            </div>
          </button>

          <!-- DEMO 5 -->
          <button onclick="triggerDemo(5)"
                  class="w-full text-left p-2.5 rounded-lg bg-slate-900/80 hover:bg-slate-700/80 border border-slate-700/80 hover:border-amber-500/50 transition group flex items-start gap-2.5">
            <div class="w-7 h-7 rounded bg-amber-950/80 border border-amber-800 text-amber-400 flex items-center justify-center text-xs flex-shrink-0 mt-0.5 group-hover:bg-amber-600 group-hover:text-white transition">
              5
            </div>
            <div>
              <div class="text-xs font-semibold text-slate-200 group-hover:text-amber-300 transition">Przebiegi Czasowe i Sensoryka</div>
              <div class="text-[11px] text-slate-400">150 kroków czasowych: RPM, temperatura, wibracje (`Scalars`)</div>
            </div>
          </button>
        </div>
        <div id="demoStatus" class="mt-3 text-[11px] text-center hidden"></div>
      </div>

    </aside>

    <!-- PRAWY PANEL: WBUDOWANY WEB VIEWER RERUN W IFRAME -->
    <main class="flex-1 flex flex-col bg-slate-950 relative">
      <iframe id="rerunIframe"
              src="http://localhost:{WEB_VIEWER_PORT}/?url=rerun+http://127.0.0.1:{GRPC_PORT}/proxy"
              class="w-full flex-1 border-0"
              allow="accelerometer; camera; encrypted-media; gyroscope; microphone"
              loading="lazy">
      </iframe>

      <!-- DOLNY PASEK POMOCY NAWIGACYJNEJ -->
      <footer class="h-9 bg-slate-900 border-t border-slate-800 px-4 flex items-center justify-between text-[11px] text-slate-400">
        <div class="flex items-center space-x-4">
          <span><i class="fa-solid fa-computer-mouse text-cyan-400 mr-1"></i> <strong>LPM:</strong> Obrót widoku 3D</span>
          <span><i class="fa-solid fa-arrows-up-down-left-right text-cyan-400 mr-1"></i> <strong>PPM:</strong> Przesuwanie kamery (Pan)</span>
          <span><i class="fa-solid fa-arrows-up-down text-cyan-400 mr-1"></i> <strong>Kółko myszy:</strong> Przybliżanie / Oddalanie</span>
        </div>
        <div class="flex items-center space-x-3">
          <span id="activeRecordingLabel">Układ: Prawoskrętny Z-Up</span>
          <button onclick="restartViewerSession()" class="text-slate-400 hover:text-red-400 transition" title="Zresetuj sesję">
            <i class="fa-solid fa-power-off"></i> Restart Sesji
          </button>
        </div>
      </footer>
    </main>
  </div>

  <!-- MODAL BAZY WIEDZY I DOKUMENTACJI W JĘZYKU POLSKIM -->
  <div id="docsModal" class="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4 hidden">
    <div class="bg-slate-900 border border-slate-700 rounded-2xl max-w-3xl w-full max-h-[85vh] flex flex-col shadow-2xl overflow-hidden">
      <div class="px-6 py-4 bg-slate-800 border-b border-slate-700 flex items-center justify-between">
        <h3 class="text-base font-bold text-white flex items-center gap-2">
          <i class="fa-solid fa-graduation-cap text-cyan-400"></i>
          Podręcznik Architektury Rerun 3D i Dobre Praktyki
        </h3>
        <button onclick="closeDocsModal()" class="text-slate-400 hover:text-white transition">
          <i class="fa-solid fa-xmark text-lg"></i>
        </button>
      </div>

      <div class="p-6 overflow-y-auto space-y-5 text-xs text-slate-300 leading-relaxed">
        
        <div class="p-4 rounded-xl bg-slate-800/60 border border-slate-700">
          <h4 class="text-sm font-semibold text-cyan-400 mb-1.5 flex items-center gap-2">
            <i class="fa-solid fa-compass"></i> 1. Układ Współrzędnych Z-Up (Right-Handed)
          </h4>
          <p>
            Rerun domyślnie wspiera konfigurowalny układ współrzędnych. W naszym studiu na stałe włączony jest prawoskrętny układ <strong>Z-Up</strong>:
            Oś <strong>X</strong> (Czerwona) skierowana w prawo, Oś <strong>Y</strong> (Zielona) skierowana w przód, a Oś <strong>Z</strong> (Niebieska) skierowana ku górze.
            Zapobiega to przekłamaniom orientacji siatek z CAD, robotyki czy skanów geodezyjnych.
          </p>
        </div>

        <div class="p-4 rounded-xl bg-slate-800/60 border border-slate-700">
          <h4 class="text-sm font-semibold text-emerald-400 mb-1.5 flex items-center gap-2">
            <i class="fa-solid fa-sitemap"></i> 2. Hierarchia Encji (Entity Paths)
          </h4>
          <p>
            Wszystkie dane w Rerun organizowane są w drzewo encji oddzielone ukośnikami, np. <code>robot/ramie_1/chwytak</code> lub <code>telemetria/silnik/temperatura</code>.
            Każda encja może posiadać własne transformacje przestrzenne <code>Transform3D</code>, co pozwala tworzyć zaawansowane układy kinematyczne (Forward Kinematics).
          </p>
        </div>

        <div class="p-4 rounded-xl bg-slate-800/60 border border-slate-700">
          <h4 class="text-sm font-semibold text-purple-400 mb-1.5 flex items-center gap-2">
            <i class="fa-solid fa-timeline"></i> 3. Osie Czasu (Timelines) i Recording Streams
          </h4>
          <p>
            Rerun pozwala logować dane w wielu niezależnych osiach czasu, np. <code>krok_symulacji</code> (sekwencyjny indeks całkowity) oraz <code>czas_sekundy</code> (czas rzeczywisty).
            Możesz swobodnie przewijać czas na dolnym suwaku Viewera, analizując historię ruchu pojazdów lub anomalie w sensorach.
          </p>
        </div>

        <div class="p-4 rounded-xl bg-slate-800/60 border border-slate-700">
          <h4 class="text-sm font-semibold text-amber-400 mb-1.5 flex items-center gap-2">
            <i class="fa-solid fa-terminal"></i> 4. Uruchamianie z Linii Poleceń (CLI)
          </h4>
          <p class="mb-2">Możesz bezpośrednio przesyłać własne nagrania do działającego studia za pomocą CLI:</p>
          <pre class="bg-slate-950 p-2.5 rounded font-mono text-[11px] text-cyan-300 overflow-x-auto">
# Dołączenie do działającego serwera gRPC w studiu:
rerun rerun+http://127.0.0.1:{GRPC_PORT}/proxy

# Logowanie pliku 3D bez interfejsu graficznego:
rerun moj_model.obj --connect
          </pre>
        </div>

      </div>

      <div class="px-6 py-3 bg-slate-800 border-t border-slate-700 flex justify-end">
        <button onclick="closeDocsModal()" class="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg text-xs font-medium transition">
          Rozumiem, zamknij
        </button>
      </div>
    </div>
  </div>

  <!-- SKRYPTY OBSŁUGI ZDARZEŃ -->
  <script>
    function refreshIframe() {{
      const iframe = document.getElementById('rerunIframe');
      iframe.src = iframe.src;
    }}

    function openDocsModal() {{
      document.getElementById('docsModal').classList.remove('hidden');
    }}

    function closeDocsModal() {{
      document.getElementById('docsModal').classList.add('hidden');
    }}

    async function launchNativeViewer() {{
      const btn = document.getElementById('btnNativeLaunch');
      const fb = document.getElementById('nativeLaunchFeedback');
      btn.disabled = true;
      btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Uruchamianie...';
      fb.classList.remove('hidden', 'text-red-400', 'text-emerald-400');
      fb.textContent = 'Łączenie z procesem rerun.exe...';

      try {{
        const resp = await fetch('/api/viewer/launch-native', {{ method: 'POST' }});
        const data = await resp.json();
        if (resp.ok) {{
          fb.classList.add('text-emerald-400');
          fb.textContent = 'Natywny Rerun uruchomiony na pulpicie!';
        }} else {{
          fb.classList.add('text-red-400');
          fb.textContent = data.detail || 'Błąd startu natywnego viewera.';
        }}
      }} catch (err) {{
        fb.classList.add('text-red-400');
        fb.textContent = 'Błąd sieciowy: ' + err.message;
      }} finally {{
        btn.disabled = false;
        btn.innerHTML = '<i class="fa-solid fa-display"></i> <span>Uruchom Natywny Rerun Viewer</span>';
      }}
    }}

    async function triggerDemo(demoId) {{
      const fb = document.getElementById('demoStatus');
      fb.classList.remove('hidden', 'text-red-400', 'text-emerald-400');
      fb.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-1"></i> Generowanie sceny #' + demoId + '...';

      try {{
        const resp = await fetch('/api/demos/' + demoId, {{ method: 'POST' }});
        const data = await resp.json();
        if (resp.ok) {{
          fb.classList.add('text-emerald-400');
          fb.innerHTML = '<i class="fa-solid fa-check mr-1"></i> Załadowano: ' + data.name;
        }} else {{
          fb.classList.add('text-red-400');
          fb.textContent = data.detail || 'Błąd ładowania sceny.';
        }}
      }} catch (err) {{
        fb.classList.add('text-red-400');
        fb.textContent = 'Błąd sieci: ' + err.message;
      }}
    }}

    function handleDragOver(e) {{
      e.preventDefault();
      document.getElementById('dropZone').classList.add('border-emerald-500', 'bg-slate-900');
    }}

    function handleDragLeave(e) {{
      e.preventDefault();
      document.getElementById('dropZone').classList.remove('border-emerald-500', 'bg-slate-900');
    }}

    function handleFileDrop(e) {{
      e.preventDefault();
      handleDragLeave(e);
      if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {{
        uploadFile(e.dataTransfer.files[0]);
      }}
    }}

    function handleFileSelect(e) {{
      if (e.target.files && e.target.files.length > 0) {{
        uploadFile(e.target.files[0]);
      }}
    }}

    async function uploadFile(file) {{
      const fb = document.getElementById('uploadStatus');
      fb.classList.remove('hidden', 'text-red-400', 'text-emerald-400');
      fb.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-1"></i> Przesyłanie: ' + file.name + '...';

      const formData = new FormData();
      formData.append('file', file);

      try {{
        const resp = await fetch('/api/upload-model', {{
          method: 'POST',
          body: formData
        }});
        const data = await resp.json();
        if (resp.ok) {{
          fb.classList.add('text-emerald-400');
          fb.innerHTML = '<i class="fa-solid fa-check mr-1"></i> Wgrano: ' + file.name;
        }} else {{
          fb.classList.add('text-red-400');
          fb.textContent = data.detail || 'Błąd uploadu.';
        }}
      }} catch (err) {{
        fb.classList.add('text-red-400');
        fb.textContent = 'Błąd: ' + err.message;
      }}
    }}

    async function restartViewerSession() {{
      if (!confirm('Czy na pewno chcesz zresetować sesję serwera Rerun?')) return;
      try {{
        await fetch('/api/viewer/restart', {{ method: 'POST' }});
        alert('Sesja zresetowana!');
        refreshIframe();
      }} catch (e) {{
        alert('Błąd restartu: ' + e.message);
      }}
    }}
  </script>
</body>
</html>
"""

def main():
    print(f"============================================================")
    print(f"  Rerun 3D Multimodal Visualizer Studio (v0.43.2)")
    print(f"  Główny interfejs WebUI: http://localhost:{WEBUI_PORT}")
    print(f"  Wbudowany Web Viewer:  http://localhost:{WEB_VIEWER_PORT}")
    print(f"  Serwer gRPC:           http://localhost:{GRPC_PORT}")
    print(f"============================================================")
    uvicorn.run(app, host="0.0.0.0", port=WEBUI_PORT)

if __name__ == "__main__":
    main()
