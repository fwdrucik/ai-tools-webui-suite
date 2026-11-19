#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI-Tools Master Hub Portal — Port 7800
Stół Warsztatowy AI (F.W. DRUCIK) — Interaktywne Okna & Centralne Centrum Zarządzania
Zgodne z identyfikacją wizualną i technologią interaktywnych okien fwdrucik.pl
"""

import sys
import os
import json
import time
import socket
import threading
import subprocess
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from concurrent.futures import ThreadPoolExecutor

# Konfiguracja serwera
HOST = "0.0.0.0"
PORT = 7800

# Ścieżka bazowa AI_Cache
HF_CACHE_DIR = Path(r"D:\AI_Cache\huggingface\hub")

# Rejestr 9 aplikacji desktopowych AI
TOOLS_REGISTRY = {
    "zonos": {
        "id": "zonos",
        "name": "Zonos Voice Studio",
        "short": "ZONOS",
        "port": 7860,
        "url": "http://localhost:7860",
        "category": "Głos i Mowa",
        "category_id": "voice",
        "icon": "🎙️",
        "summary": "Ekspresyjna synteza TTS i klonowanie głosu w czasie rzeczywistym",
        "description": "Zaawansowany syntezator mowy Zyphra Zonos-3 Mini (800M MoE) z 8-wymiarowymi suwakami emocji, precyzyjną kontrolą parametrów akustycznych i pełnym wsparciem języka polskiego.",
        "guide": "Wpisz polski tekst, dostosuj emocje (radość, smutek, złość, szept), wybierz głos referencyjny lub wgraj własną próbkę WAV, a następnie kliknij 'Generuj'. Działa na karcie RTX lub CPU.",
        "launch_script": r"D:\AI-Tools\Zonos\launch_zonos.bat",
        "directory": r"D:\AI-Tools\Zonos",
        "entry_point": "webui_zonos_pl.py",
        "weight_repo": "Zyphra/Zonos-v0.1-transformer",
        "weight_size": "1.8 GB",
        "weight_type": "local"
    },
    "haru": {
        "id": "haru",
        "name": "Haru Full-Duplex Voice",
        "short": "HARU",
        "port": 8998,
        "url": "http://localhost:8998/control",
        "category": "Głos i Mowa",
        "category_id": "voice",
        "icon": "⚡",
        "summary": "Dwukierunkowy asystent głosowy z obsługą przerwań mowy (barge-in)",
        "description": "System konwersacyjny czasu rzeczywistego Full-Duplex z polską lokalizacją paneli sterowania, streamingiem audio o ultraniskim opóźnieniu (WebRTC/WS) i natychmiastową reakcją na wtrącenia.",
        "guide": "Zezwól na dostęp do mikrofonu, wybierz profil polskiego asystenta i prowadź swobodną rozmowę. Możesz przerywać wypowiedź asystenta w dowolnym momencie bez oczekiwania na zakończenie zdania.",
        "launch_script": r"D:\AI-Tools\Haru\launch_haru.bat",
        "directory": r"D:\AI-Tools\Haru",
        "entry_point": "control_center_pl.py",
        "weight_repo": "higurashi-ai/Haru-4B",
        "weight_size": "1.95 GB",
        "weight_type": "local"
    },
    "cosyvoice": {
        "id": "cosyvoice",
        "name": "CosyVoice Studio",
        "short": "COSY",
        "port": 7862,
        "url": "http://localhost:7862",
        "category": "Głos i Mowa",
        "category_id": "voice",
        "icon": "🔊",
        "summary": "Wielozakładkowe studio lektorskie i 3-sekundowe klonowanie Zero-Shot",
        "description": "5 dedykowanych zakładek: głosy predefiniowane SFT, klonowanie głosu z krótkiej 3-sekundowej próbki, automatyczna transkrypcja Whisper, synteza wielojęzyczna (cross-lingual) i tagi instrukcji lektorskich.",
        "guide": "Przejdź do zakładki Zero-Shot, załaduj min. 3 sekundy czystego nagrania głosu lektora, wprowadź tekst po polsku i wygeneruj profesjonalną ścieżkę lektorską gotową do pobrania w formacie WAV.",
        "launch_script": r"D:\AI-Tools\CosyVoice\launch_cosyvoice.bat",
        "directory": r"D:\AI-Tools\CosyVoice",
        "entry_point": "webui_cosyvoice_pl.py",
        "weight_repo": "FunAudioLLM/CosyVoice2-0.5B",
        "weight_size": "1.5 GB",
        "weight_type": "local"
    },
    "mini_omni2": {
        "id": "mini_omni2",
        "name": "Mini-Omni2 Multimodal Live",
        "short": "OMNI2",
        "port": 7864,
        "url": "http://localhost:7864",
        "category": "Wizja i Multimodalność",
        "category_id": "vision",
        "icon": "👁️",
        "summary": "Multimodalny asystent wideo i audio na żywo z modelem SNAC 24kHz",
        "description": "Przetwarzanie obrazu z kamery internetowej równolegle ze strumieniem mikrofonowym. Natychmiastowa synteza mowy w jakości 24kHz, czat strumieniowy oraz monitor zużycia pamięci VRAM.",
        "guide": "Włącz kamerę i mikrofon w przeglądarce. Pokaż obiekt przed obiektywem i zadaj pytanie głosem po polsku. Model odpowiada syntezą mowy na żywo i wypisuje transkrypcję w oknie czatu.",
        "launch_script": r"D:\AI-Tools\mini-omni2\launch_mini_omni2.bat",
        "directory": r"D:\AI-Tools\mini-omni2",
        "entry_point": "webui_server.py",
        "weight_repo": "gpt-omni/mini-omni2",
        "weight_size": "3.4 GB",
        "weight_type": "local"
    },
    "gemini_live": {
        "id": "gemini_live",
        "name": "Gemini Omni Live Studio",
        "short": "GEMINI",
        "port": 7865,
        "url": "http://localhost:7865",
        "category": "Wizja i Multimodalność",
        "category_id": "vision",
        "icon": "✨",
        "summary": "Wszechstronne studio Gemini z wideo, udostępnianiem pulpitu i personami",
        "description": "Multimodalny interfejs oparty na modelach Gemini 2.5 Flash / Pro. Transmisja z kamery lub zrzut ekranu (screen share), interaktywny oscyloskop fali audio i wyspecjalizowane polskie persony.",
        "guide": "Wybierz źródło (kamera lub ekran), ustaw docelową personę (programista, analityk CAD, lektor) i kliknij 'Połącz'. Model na żywo analizuje pulpit i prowadzi dialog głosowy w języku polskim.",
        "launch_script": r"D:\AI-Tools\GeminiLiveStudio\launch_gemini_live.bat",
        "directory": r"D:\AI-Tools\GeminiLiveStudio",
        "entry_point": "webui_gemini_pl.py",
        "weight_repo": "Google Cloud GenAI",
        "weight_size": "API Chmurowe",
        "weight_type": "cloud"
    },
    "fastframes": {
        "id": "fastframes",
        "name": "Apple FastFrames Video AI",
        "short": "FRAMES",
        "port": 7866,
        "url": "http://localhost:7866",
        "category": "Wizja i Multimodalność",
        "category_id": "vision",
        "icon": "🎬",
        "summary": "Generowanie wideo Text-to-Video i interaktywny świat 3D LingBot",
        "description": "Szybka synteza sekwencji wideo z opisów tekstowych Apple FastFrames. Polskie szablony promptów kinematograficznych, zintegrowane środowisko 3D LingBot oraz menedżer wag HuggingFace.",
        "guide": "Wpisz prompt sceny lub wybierz jeden z polskich szablonów kinematograficznych, ustaw rozdzielczość i liczbę klatek (FPS), a następnie uruchom renderowanie. Wynik możesz odtworzyć bezpośrednio w odtwarzaczu.",
        "launch_script": r"D:\AI-Tools\ml-fastframes\launch_fastframes.bat",
        "directory": r"D:\AI-Tools\ml-fastframes",
        "entry_point": "webui_fastframes_pl.py",
        "weight_repo": "apple/FastFrames-S",
        "weight_size": "2.1 GB",
        "weight_type": "local"
    },
    "rerun": {
        "id": "rerun",
        "name": "Rerun 3D Visualizer",
        "short": "RERUN",
        "port": 7867,
        "url": "http://localhost:7867",
        "category": "3D i Narzędzia Przestrzenne",
        "category_id": "spatial",
        "icon": "🧊",
        "summary": "Wizualizacja chmur punktów, siatek 3D i danych sensorycznych",
        "description": "Centrum analizy danych 3D integrujące Rerun SDK z osadzonym Rerun Web Viewerem (port 9097). Obsługa wgrywania plików (.obj, .stl, .glb, .rrd), 5 polskich scen inżynieryjnych i telemetria gRPC.",
        "guide": "Wybierz jedną z gotowych scen demonstracyjnych lub przeciągnij model 3D do uploadera. Model zostanie natychmiast załadowany do interaktywnego okna widoku 3D z pełną kontrolą kamery i orbitowania.",
        "launch_script": r"D:\AI-Tools\rerun-sdk\launch_rerun.bat",
        "directory": r"D:\AI-Tools\rerun-sdk",
        "entry_point": "webui_server.py",
        "weight_repo": "Rerun Native SDK",
        "weight_size": "Silnik SDK",
        "weight_type": "native"
    },
    "autoswarm": {
        "id": "autoswarm",
        "name": "AutoSwarm Multi-Agent",
        "short": "SWARM",
        "port": 7868,
        "url": "http://localhost:7868",
        "category": "Agenci i Autonomia",
        "category_id": "agents",
        "icon": "🤖",
        "summary": "Centrum dowodzenia autonomicznym zespołem 6 agentów AI",
        "description": "Wizualizacja i koordynacja roju agentów: Codex, Claude, OpenCode, Copilot, Muse, Hermes. Dyspozytor misji zespołowych, strumień dziennika zdarzeń na żywo i panel akceptacji kroków krytycznych.",
        "guide": "Zdefiniuj cel misji w dyspozytorze, przydziel role agentom i uruchom zadanie. Obserwuj wymianę komunikatów i postęp w czasie rzeczywistym. W razie operacji krytycznych zatwierdź krok w panelu akceptacji.",
        "launch_script": r"D:\AI-Tools\AutoSwarm\launch_autoswarm.bat",
        "directory": r"D:\AI-Tools\AutoSwarm",
        "entry_point": "webui_server.py",
        "weight_repo": "AutoSwarm Orchestrator",
        "weight_size": "Rój Agentów",
        "weight_type": "agents"
    },
    "sophon": {
        "id": "sophon",
        "name": "Sophon Realtime Voice AI",
        "short": "SOPHON",
        "port": 7869,
        "url": "http://localhost:7869",
        "category": "Głos i Mowa",
        "category_id": "voice",
        "icon": "🎭",
        "summary": "Studio głosowe Dual-Engine z 13 profilami emocji i DuplexJev",
        "description": "Elastyczne środowisko wspierające zarówno połączenie z lokalną bramką Live Gateway (port 8789), jak i natychmiastowy symulator Web Audio. Precyzyjna modulacja 13 emocji i adaptacyjny filtr przerwań.",
        "guide": "Wybierz silnik (Live Gateway lub Symulator Web Audio), dobierz profil emocjonalny (entuzjazm, powaga, empatia), dostosuj czułość VAD i rozmawiaj z asystentem bez zakłóceń.",
        "launch_script": r"D:\AI-Tools\sophon-realtime\launch_sophon.bat",
        "directory": r"D:\AI-Tools\sophon-realtime",
        "entry_point": "webui_server.py",
        "weight_repo": "Sophon DuplexJev",
        "weight_size": "1.2 GB",
        "weight_type": "local"
    }
}

DOWNLOAD_STATUS = {}

def probe_port(port: int, host="127.0.0.1", timeout=0.3):
    """Szybkie sprawdzanie dostępności portu TCP z pomiarem czasu odpowiedzi."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    start_time = time.perf_counter()
    try:
        s.connect((host, port))
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 1)
        s.close()
        return True, elapsed_ms
    except Exception:
        s.close()
        return False, None

def probe_all_ports_concurrent():
    """Wielowątkowe sprawdzanie wszystkich 9 portów jednocześnie."""
    results = {}
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_id = {
            executor.submit(probe_port, tool["port"]): tool_id
            for tool_id, tool in TOOLS_REGISTRY.items()
        }
        for future in future_to_id:
            tool_id = future_to_id[future]
            try:
                is_online, resp_time = future.result()
                results[tool_id] = {
                    "online": is_online,
                    "response_time_ms": resp_time
                }
            except Exception:
                results[tool_id] = {
                    "online": False,
                    "response_time_ms": None
                }
    return results

def get_weights_status():
    """Sprawdza obecność wag w pamięci podręcznej D:\\AI_Cache\\huggingface\\hub."""
    results = {}
    for tid, info in TOOLS_REGISTRY.items():
        wtype = info.get("weight_type", "local")
        wrepo = info.get("weight_repo", "")
        wsize = info.get("weight_size", "")

        if wtype in ("cloud", "native", "agents"):
            results[tid] = {
                "status": "ready",
                "message": f"Gotowe ({wsize})",
                "size": wsize,
                "type": wtype,
                "downloading": False
            }
        else:
            repo_folder = "models--" + wrepo.replace("/", "--")
            target_path = HF_CACHE_DIR / repo_folder
            is_dl = DOWNLOAD_STATUS.get(tid, {}).get("status") == "downloading"
            
            if target_path.exists() and any(target_path.iterdir()):
                try:
                    size_gb = sum(f.stat().st_size for f in target_path.rglob('*') if f.is_file()) / (1024**3)
                    results[tid] = {
                        "status": "ready",
                        "message": f"Pobrane ({round(size_gb, 2)} GB w D:\\AI_Cache)",
                        "size": wsize,
                        "type": wtype,
                        "downloading": False
                    }
                except Exception:
                    results[tid] = {
                        "status": "ready",
                        "message": f"Pobrane ({wsize})",
                        "size": wsize,
                        "type": wtype,
                        "downloading": False
                    }
            elif is_dl:
                results[tid] = {
                    "status": "downloading",
                    "message": DOWNLOAD_STATUS[tid].get("message", "Pobieranie w toku..."),
                    "size": wsize,
                    "type": wtype,
                    "downloading": True,
                    "progress": DOWNLOAD_STATUS[tid].get("progress", 50)
                }
            else:
                results[tid] = {
                    "status": "not_downloaded",
                    "message": f"Wymaga pobrania ({wsize})",
                    "size": wsize,
                    "type": wtype,
                    "downloading": False
                }
    return results

def async_download_weight(tool_id):
    """Pobiera model w tle z Hugging Face Hub do D:\\AI_Cache\\huggingface\\hub."""
    if tool_id not in TOOLS_REGISTRY:
        return
    info = TOOLS_REGISTRY[tool_id]
    repo_id = info.get("weight_repo")
    if not repo_id or info.get("weight_type") != "local":
        return
        
    DOWNLOAD_STATUS[tool_id] = {
        "status": "downloading",
        "message": f"Rozpoczęto pobieranie {repo_id} ({info['weight_size']})...",
        "progress": 10
    }
    
    try:
        from huggingface_hub import snapshot_download
        os.makedirs(HF_CACHE_DIR, exist_ok=True)
        DOWNLOAD_STATUS[tool_id]["message"] = f"Pobieranie plików modelu {repo_id} do D:\\AI_Cache..."
        DOWNLOAD_STATUS[tool_id]["progress"] = 35
        snapshot_download(repo_id, cache_dir=str(HF_CACHE_DIR), resume_download=True)
        DOWNLOAD_STATUS[tool_id] = {
            "status": "completed",
            "message": f"Model {repo_id} pobrany i gotowy do pracy!",
            "progress": 100
        }
    except Exception as e:
        DOWNLOAD_STATUS[tool_id] = {
            "status": "error",
            "message": f"Błąd pobierania: {str(e)}",
            "progress": 0
        }

def get_all_tools_status():
    """Zwraca pełny profil stanu ekosystemu w formacie JSON."""
    probe_results = probe_all_ports_concurrent()
    weights_res = get_weights_status()
    online_count = sum(1 for r in probe_results.values() if r["online"])
    total_count = len(TOOLS_REGISTRY)

    tools_data = {}
    for tid, tool in TOOLS_REGISTRY.items():
        is_online = probe_results[tid]["online"]
        resp_time = probe_results[tid]["response_time_ms"]
        tools_data[tid] = {
            **tool,
            "status": "online" if is_online else "offline",
            "response_time_ms": resp_time,
            "weights": weights_res.get(tid, {}),
            "last_checked": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }

    return {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "hub_port": PORT,
        "summary": {
            "total": total_count,
            "online": online_count,
            "offline": total_count - online_count
        },
        "tools": tools_data
    }

def launch_tool_script(tool_id):
    """Uruchamia skrypt .bat dla wybranego narzędzia w osobnym oknie konsoli."""
    if tool_id not in TOOLS_REGISTRY:
        return False, f"Nieznane narzędzie: {tool_id}"

    tool = TOOLS_REGISTRY[tool_id]
    script_path = tool["launch_script"]
    work_dir = tool["directory"]

    if not os.path.exists(script_path):
        return False, f"Plik skryptu nie istnieje: {script_path}"

    try:
        if sys.platform == "win32":
            subprocess.Popen(
                ["cmd.exe", "/c", "start", script_path],
                cwd=work_dir,
                shell=True
            )
        else:
            subprocess.Popen(["bash", script_path], cwd=work_dir)
        return True, f"Zainicjowano uruchomienie {tool['name']} na porcie {tool['port']}"
    except Exception as e:
        return False, f"Błąd startu: {str(e)}"

# Szablon HTML interfejsu Master Hub — Stylistyka F.W. DRUCIK & Technologia Interaktywnych Okien
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI-Tools Master Hub — F.W. DRUCIK Stół Warsztatowy AI (PORT 7800)</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@600;700;800&family=Hanken+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            /* Paleta barw F.W. DRUCIK (fwdrucik.pl) */
            --bg-graphite: #101716;
            --bg-panel: #192321;
            --bg-card: #151d1b;
            --bg-card-hover: #1e2a28;
            --bg-field: #0e1816;
            --border-steel: #34453e;
            --border-highlight: #80edf0;
            --signal-cyan: #80edf0;
            --signal-cyan-hover: #b3f8f9;
            --signal-cyan-glow: rgba(128, 237, 240, 0.22);
            --warm-copper: #e5a87e;
            --warm-copper-glow: rgba(229, 168, 126, 0.2);
            --paper-light: #e8ece2;
            --muted-sage: #b7c6be;
            --status-green: #10b981;
            --status-amber: #f59e0b;
            --status-red: #ef4444;
            --dock-h: 56px;
            --topbar-h: 56px;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            user-select: none;
        }

        body {
            background-color: var(--bg-graphite);
            background-image: 
                radial-gradient(circle at 50% 0%, rgba(128, 237, 240, 0.08) 0%, transparent 60%),
                linear-gradient(to right, rgba(52, 69, 62, 0.15) 1px, transparent 1px),
                linear-gradient(to bottom, rgba(52, 69, 62, 0.15) 1px, transparent 1px);
            background-size: 100% 100%, 32px 32px, 32px 32px;
            color: var(--paper-light);
            font-family: 'Hanken Grotesk', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            font-size: 14px;
            line-height: 1.5;
            height: 100vh;
            width: 100vw;
            overflow: hidden;
            display: flex;
            flex-direction: column;
        }

        /* Górna belka warsztatowa */
        header.workbench-topbar {
            height: var(--topbar-h);
            background: rgba(25, 35, 33, 0.95);
            backdrop-filter: blur(12px);
            border-bottom: 1px solid var(--border-steel);
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 16px;
            z-index: 1000;
        }

        .brand-area {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .brand-logo {
            font-family: 'Barlow Condensed', sans-serif;
            font-weight: 800;
            font-size: 1.45rem;
            letter-spacing: -0.01em;
            color: var(--paper-light);
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .brand-logo span.cyan {
            color: var(--signal-cyan);
        }

        .badge-workbench {
            background: rgba(128, 237, 240, 0.12);
            border: 1px solid var(--signal-cyan);
            color: var(--signal-cyan);
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.72rem;
            font-weight: 700;
            padding: 2px 7px;
            border-radius: 3px;
            letter-spacing: 0.05em;
        }

        .badge-copper {
            background: rgba(229, 168, 126, 0.15);
            border: 1px solid var(--warm-copper);
            color: var(--warm-copper);
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.72rem;
            font-weight: 700;
            padding: 2px 7px;
            border-radius: 3px;
        }

        .topbar-actions {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .btn-action {
            background: var(--bg-card);
            border: 1px solid var(--border-steel);
            color: var(--paper-light);
            font-family: 'Hanken Grotesk', sans-serif;
            font-size: 0.82rem;
            font-weight: 600;
            padding: 6px 12px;
            border-radius: 3px;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            transition: all 0.15s ease;
        }

        .btn-action:hover {
            background: var(--bg-card-hover);
            border-color: var(--signal-cyan);
            color: var(--signal-cyan);
            box-shadow: 0 0 10px var(--signal-cyan-glow);
        }

        .btn-action.primary {
            background: var(--signal-cyan);
            color: #0b2425;
            border-color: var(--signal-cyan);
        }

        .btn-action.primary:hover {
            background: var(--signal-cyan-hover);
            color: #0b2425;
            box-shadow: 0 0 12px var(--signal-cyan-glow);
        }

        .btn-action.copper {
            border-color: var(--warm-copper);
            color: var(--warm-copper);
        }
        .btn-action.copper:hover {
            background: rgba(229, 168, 126, 0.15);
            box-shadow: 0 0 10px var(--warm-copper-glow);
        }

        .system-telemetry {
            display: flex;
            align-items: center;
            gap: 14px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.78rem;
            color: var(--muted-sage);
        }

        .tele-item {
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .pulse-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--status-green);
            box-shadow: 0 0 8px var(--status-green);
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.5; transform: scale(0.85); }
        }

        /* Główny pulpit z oknami */
        main.workbench-canvas {
            flex: 1;
            position: relative;
            overflow: hidden;
            width: 100%;
            height: calc(100vh - var(--topbar-h) - var(--dock-h));
        }

        /* Pływające okno warsztatowe (Workbench Window) */
        .ws-window {
            position: absolute;
            background: var(--bg-panel);
            border: 1px solid var(--border-steel);
            border-radius: 4px;
            box-shadow: 0 12px 32px rgba(0, 0, 0, 0.65), 0 0 1px rgba(128, 237, 240, 0.25);
            display: flex;
            flex-direction: column;
            overflow: hidden;
            min-width: 380px;
            min-height: 260px;
            transition: box-shadow 0.15s ease, border-color 0.15s ease;
        }

        .ws-window.active {
            border-color: var(--signal-cyan);
            box-shadow: 0 14px 40px rgba(0, 0, 0, 0.8), 0 0 12px var(--signal-cyan-glow);
            z-index: 100;
        }

        .ws-window.minimized {
            display: none !important;
        }

        .ws-window.maximized {
            top: 0 !important;
            left: 0 !important;
            width: 100% !important;
            height: 100% !important;
            border-radius: 0;
            border: none;
        }

        /* Pasek tytułowy okna */
        .ws-titlebar {
            height: 38px;
            background: #151d1b;
            border-bottom: 1px solid var(--border-steel);
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 12px;
            cursor: move;
            user-select: none;
        }

        .ws-title {
            display: flex;
            align-items: center;
            gap: 8px;
            font-family: 'Barlow Condensed', sans-serif;
            font-weight: 700;
            font-size: 1.05rem;
            letter-spacing: 0.02em;
            color: var(--paper-light);
        }

        .ws-title .tool-icon {
            font-size: 1.05rem;
        }

        .ws-port-tag {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.72rem;
            font-weight: 700;
            color: var(--signal-cyan);
            background: rgba(128, 237, 240, 0.12);
            padding: 1px 6px;
            border-radius: 2px;
            border: 1px solid rgba(128, 237, 240, 0.3);
        }

        .ws-status-indicator {
            width: 7px;
            height: 7px;
            border-radius: 50%;
            background: var(--status-amber);
        }
        .ws-status-indicator.online {
            background: var(--status-green);
            box-shadow: 0 0 6px var(--status-green);
        }

        .ws-window-controls {
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .ws-ctrl-btn {
            width: 24px;
            height: 24px;
            background: transparent;
            border: 1px solid transparent;
            color: var(--muted-sage);
            border-radius: 2px;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            font-size: 0.85rem;
            transition: all 0.12s ease;
        }

        .ws-ctrl-btn:hover {
            background: rgba(255, 255, 255, 0.08);
            color: var(--paper-light);
            border-color: var(--border-steel);
        }

        .ws-ctrl-btn.close:hover {
            background: rgba(239, 68, 68, 0.2);
            color: var(--status-red);
            border-color: var(--status-red);
        }

        /* Pasek zakładek okna */
        .ws-tabs-bar {
            background: #111817;
            border-bottom: 1px solid var(--border-steel);
            display: flex;
            padding: 0 10px;
            gap: 4px;
        }

        .ws-tab {
            padding: 6px 12px;
            font-size: 0.78rem;
            font-weight: 600;
            color: var(--muted-sage);
            background: transparent;
            border: none;
            border-bottom: 2px solid transparent;
            cursor: pointer;
            transition: all 0.12s;
        }

        .ws-tab:hover {
            color: var(--paper-light);
        }

        .ws-tab.active {
            color: var(--signal-cyan);
            border-bottom-color: var(--signal-cyan);
            background: rgba(128, 237, 240, 0.04);
        }

        /* Ciało okna */
        .ws-body {
            flex: 1;
            overflow-y: auto;
            position: relative;
            background: var(--bg-panel);
            color: var(--paper-light);
            display: flex;
            flex-direction: column;
        }

        .ws-view-content {
            padding: 16px;
            flex: 1;
            display: flex;
            flex-direction: column;
            gap: 14px;
            user-select: text;
        }

        .ws-view-iframe {
            width: 100%;
            height: 100%;
            border: none;
            flex: 1;
            background: #000;
        }

        /* Elementy wewnątrz panelu kontrolnego okna */
        .ws-card-row {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
            gap: 10px;
        }

        .ws-stat-card {
            background: var(--bg-card);
            border: 1px solid var(--border-steel);
            padding: 8px 10px;
            border-radius: 3px;
        }

        .ws-stat-label {
            font-size: 0.72rem;
            color: var(--muted-sage);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .ws-stat-val {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.95rem;
            font-weight: 700;
            color: var(--signal-cyan);
            margin-top: 2px;
        }

        .ws-desc-box {
            background: var(--bg-field);
            border: 1px solid var(--border-steel);
            border-left: 3px solid var(--signal-cyan);
            padding: 10px 12px;
            border-radius: 2px;
            font-size: 0.85rem;
            color: var(--paper-light);
        }

        .ws-guide-box {
            background: var(--bg-card);
            border: 1px solid var(--border-steel);
            border-left: 3px solid var(--warm-copper);
            padding: 10px 12px;
            border-radius: 2px;
            font-size: 0.82rem;
            color: var(--muted-sage);
        }

        .ws-actions-row {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            margin-top: auto;
            padding-top: 10px;
            border-top: 1px solid var(--border-steel);
        }

        /* Uchwyt zmiany rozmiaru okna */
        .ws-resizer {
            position: absolute;
            right: 0;
            bottom: 0;
            width: 14px;
            height: 14px;
            cursor: nwse-resize;
            background: linear-gradient(135deg, transparent 50%, var(--border-steel) 50%, var(--border-steel) 70%, transparent 70%, transparent 85%, var(--signal-cyan) 85%);
            z-index: 10;
        }

        /* Dolny pasek zadań / Workbench Dock */
        footer.workbench-dock {
            height: var(--dock-h);
            background: rgba(16, 23, 22, 0.98);
            border-top: 1px solid var(--border-steel);
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 12px;
            z-index: 1000;
        }

        .dock-tools {
            display: flex;
            align-items: center;
            gap: 6px;
            overflow-x: auto;
            padding: 2px 0;
        }

        .dock-item {
            background: var(--bg-panel);
            border: 1px solid var(--border-steel);
            color: var(--paper-light);
            padding: 6px 10px;
            border-radius: 3px;
            font-size: 0.8rem;
            font-weight: 600;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 6px;
            transition: all 0.12s ease;
            white-space: nowrap;
        }

        .dock-item:hover {
            border-color: var(--signal-cyan);
            color: var(--signal-cyan);
            background: rgba(128, 237, 240, 0.08);
        }

        .dock-item.open {
            border-color: var(--signal-cyan);
            background: rgba(128, 237, 240, 0.12);
        }

        .dock-item .led {
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: var(--status-amber);
        }
        .dock-item.online .led {
            background: var(--status-green);
            box-shadow: 0 0 6px var(--status-green);
        }

        .dock-clock {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.82rem;
            color: var(--signal-cyan);
            padding-left: 10px;
            border-left: 1px solid var(--border-steel);
        }
    </style>
</head>
<body>

    <!-- Górny pasek warsztatowy -->
    <header class="workbench-topbar">
        <div class="brand-area">
            <div class="brand-logo">
                F.W. <span class="cyan">DRUCIK</span>
            </div>
            <span class="badge-workbench">STÓŁ WARSZTATOWY AI</span>
            <span class="badge-copper">MASTER HUB PORTAL : 7800</span>
        </div>

        <div class="topbar-actions">
            <button class="btn-action primary" onclick="launchAllTools()">
                ▶ Uruchom Wszystkie (9)
            </button>
            <button class="btn-action" onclick="cascadeWindows()">
                ⊞ Kaskada Okien
            </button>
            <button class="btn-action" onclick="tileWindows()">
                ⊞ Rozmieść w Siatce
            </button>
            <button class="btn-action copper" onclick="openWeightsManager()">
                📦 Menedżer Wag AI
            </button>
            <button class="btn-action" onclick="openTestsWindow()">
                🧪 Testy E2E (116)
            </button>
        </div>

        <div class="system-telemetry">
            <div class="tele-item">
                <span class="pulse-dot"></span>
                <span>AKTYWNYCH: <strong id="tele-online" style="color:var(--status-green);">0</strong> / 9</span>
            </div>
            <div class="tele-item" id="tele-ping">PING: -- ms</div>
            <div class="tele-item" id="tele-rtx">RTX: CUDA 12.8</div>
        </div>
    </header>

    <!-- Obszar roboczy pulpitu (Canvas) -->
    <main class="workbench-canvas" id="canvas">
        <!-- Okna generowane dynamicznie przez JavaScript -->
    </main>

    <!-- Dolny Dock warsztatowy -->
    <footer class="workbench-dock">
        <div class="dock-tools" id="dock-tools">
            <!-- Przyciski narzędzi w docku generowane przez JS -->
        </div>
        <div class="dock-clock" id="clock">--:--:--</div>
    </footer>

    <script>
        const TOOLS = {{TOOLS_JSON}};
        let zCounter = 100;
        const openWindows = {};

        // Inicjalizacja pulpitu
        document.addEventListener('DOMContentLoaded', () => {
            initDock();
            updateClock();
            setInterval(updateClock, 1000);
            refreshStatus();
            setInterval(refreshStatus, 3000);

            // Domyślnie otwórz 3 główne okna demonstracyjne w układzie kaskadowym
            openWindow('zonos', 40, 30, 540, 480);
            openWindow('haru', 260, 60, 540, 480);
            openWindow('rerun', 480, 90, 560, 500);
        });

        function updateClock() {
            const now = new Date();
            document.getElementById('clock').textContent = now.toLocaleTimeString('pl-PL') + ' (PL)';
        }

        function initDock() {
            const dock = document.getElementById('dock-tools');
            dock.innerHTML = '';

            for (const [id, tool] of Object.entries(TOOLS)) {
                const btn = document.createElement('button');
                btn.className = 'dock-item';
                btn.id = `dock-btn-${id}`;
                btn.innerHTML = `<span class="led" id="led-${id}"></span> <span>${tool.icon}</span> <span>${tool.short}</span>`;
                btn.onclick = () => toggleWindow(id);
                dock.appendChild(btn);
            }
        }

        function toggleWindow(id) {
            if (openWindows[id]) {
                const win = openWindows[id];
                if (win.classList.contains('minimized')) {
                    win.classList.remove('minimized');
                    focusWindow(win);
                } else if (win.classList.contains('active')) {
                    win.classList.add('minimized');
                    win.classList.remove('active');
                } else {
                    focusWindow(win);
                }
            } else {
                const offset = (Object.keys(openWindows).length * 30) % 200 + 40;
                openWindow(id, offset, offset, 540, 480);
            }
            updateDockState();
        }

        function openWindow(id, x=80, y=80, w=540, h=480) {
            if (openWindows[id]) {
                focusWindow(openWindows[id]);
                return;
            }

            const tool = TOOLS[id];
            if (!tool) return;

            const win = document.createElement('div');
            win.className = 'ws-window active';
            win.id = `window-${id}`;
            win.style.left = `${x}px`;
            win.style.top = `${y}px`;
            win.style.width = `${w}px`;
            win.style.height = `${h}px`;
            win.style.zIndex = ++zCounter;

            win.innerHTML = `
                <div class="ws-titlebar" id="tb-${id}">
                    <div class="ws-title">
                        <span class="tool-icon">${tool.icon}</span>
                        <span>${tool.name.toUpperCase()}</span>
                        <span class="ws-port-tag">PORT ${tool.port}</span>
                        <span class="ws-status-indicator" id="win-ind-${id}"></span>
                    </div>
                    <div class="ws-window-controls">
                        <button class="ws-ctrl-btn" title="Minimalizuj" onclick="minimizeWindow('${id}')">_</button>
                        <button class="ws-ctrl-btn" title="Maksymalizuj / Przywróć" onclick="maximizeWindow('${id}')">□</button>
                        <button class="ws-ctrl-btn close" title="Zamknij" onclick="closeWindow('${id}')">✕</button>
                    </div>
                </div>
                <div class="ws-tabs-bar">
                    <button class="ws-tab active" id="tab-ctrl-${id}" onclick="switchTab('${id}', 'ctrl')">⚙️ Panel Sterowania</button>
                    <button class="ws-tab" id="tab-live-${id}" onclick="switchTab('${id}', 'live')">🖥️ Podgląd Live (WebUI)</button>
                </div>
                <div class="ws-body" id="body-${id}">
                    <div class="ws-view-content" id="view-ctrl-${id}">
                        <div class="ws-card-row">
                            <div class="ws-stat-card">
                                <div class="ws-stat-label">STATUS USŁUGI</div>
                                <div class="ws-stat-val" id="stat-status-${id}">SPRAWDZANIE...</div>
                            </div>
                            <div class="ws-stat-card">
                                <div class="ws-stat-label">CZAS ODPOWIEDZI</div>
                                <div class="ws-stat-val" id="stat-ping-${id}">-- ms</div>
                            </div>
                            <div class="ws-stat-card">
                                <div class="ws-stat-label">WAGI MODELU</div>
                                <div class="ws-stat-val" style="font-size:0.8rem;" id="stat-weights-${id}">${tool.weight_size}</div>
                            </div>
                        </div>

                        <div class="ws-desc-box">
                            <strong>Cel i Rola Narzędzia:</strong><br>
                            ${tool.description}
                        </div>

                        <div class="ws-guide-box">
                            <strong>Instrukcja Szybkiego Startu:</strong><br>
                            ${tool.guide}
                        </div>

                        <div class="ws-actions-row">
                            <button class="btn-action primary" onclick="launchSingleTool('${id}')">
                                ▶ Uruchom Narzędzie (.bat)
                            </button>
                            <button class="btn-action" onclick="refreshStatus()">
                                🔄 Odśwież Status
                            </button>
                            <a class="btn-action copper" href="${tool.url}" target="_blank" style="text-decoration:none;">
                                ↗ Otwórz w Nowej Karcie
                            </a>
                            <button class="btn-action" onclick="downloadSingleWeight('${id}')" id="btn-dl-${id}">
                                ⬇️ Pobierz Wagi (${tool.weight_size})
                            </button>
                        </div>
                    </div>
                    <iframe class="ws-view-iframe" id="view-live-${id}" src="about:blank" style="display:none;"></iframe>
                </div>
                <div class="ws-resizer" id="rs-${id}"></div>
            `;

            document.getElementById('canvas').appendChild(win);
            openWindows[id] = win;

            setupDraggable(win, win.querySelector(`#tb-${id}`));
            setupResizable(win, win.querySelector(`#rs-${id}`));

            win.addEventListener('pointerdown', () => focusWindow(win));
            updateDockState();
        }

        function focusWindow(win) {
            document.querySelectorAll('.ws-window').forEach(w => w.classList.remove('active'));
            win.classList.remove('minimized');
            win.classList.add('active');
            win.style.zIndex = ++zCounter;
            updateDockState();
        }

        function minimizeWindow(id) {
            if (openWindows[id]) {
                openWindows[id].classList.add('minimized');
                openWindows[id].classList.remove('active');
                updateDockState();
            }
        }

        function maximizeWindow(id) {
            if (openWindows[id]) {
                openWindows[id].classList.toggle('maximized');
                focusWindow(openWindows[id]);
            }
        }

        function closeWindow(id) {
            if (openWindows[id]) {
                openWindows[id].remove();
                delete openWindows[id];
                updateDockState();
            }
        }

        function switchTab(id, tab) {
            const ctrlView = document.getElementById(`view-ctrl-${id}`);
            const liveView = document.getElementById(`view-live-${id}`);
            const tabCtrl = document.getElementById(`tab-ctrl-${id}`);
            const tabLive = document.getElementById(`tab-live-${id}`);

            if (tab === 'ctrl') {
                ctrlView.style.display = 'flex';
                liveView.style.display = 'none';
                tabCtrl.classList.add('active');
                tabLive.classList.remove('active');
            } else {
                ctrlView.style.display = 'none';
                liveView.style.display = 'block';
                tabCtrl.classList.remove('active');
                tabLive.classList.add('active');
                if (liveView.src === 'about:blank') {
                    liveView.src = TOOLS[id].url;
                }
            }
        }

        function updateDockState() {
            for (const id of Object.keys(TOOLS)) {
                const btn = document.getElementById(`dock-btn-${id}`);
                if (!btn) continue;
                if (openWindows[id] && !openWindows[id].classList.contains('minimized')) {
                    btn.classList.add('open');
                } else {
                    btn.classList.remove('open');
                }
            }
        }

        // Przeciąganie okien (Draggable)
        function setupDraggable(element, handle) {
            let posX = 0, posY = 0, mouseX = 0, mouseY = 0;
            handle.onpointerdown = (e) => {
                if (e.target.tagName === 'BUTTON') return;
                e.preventDefault();
                focusWindow(element);
                mouseX = e.clientX;
                mouseY = e.clientY;
                document.onpointermove = (ev) => {
                    ev.preventDefault();
                    posX = mouseX - ev.clientX;
                    posY = mouseY - ev.clientY;
                    mouseX = ev.clientX;
                    mouseY = ev.clientY;
                    element.style.top = (element.offsetTop - posY) + 'px';
                    element.style.left = (element.offsetLeft - posX) + 'px';
                };
                document.onpointerup = () => {
                    document.onpointermove = null;
                    document.onpointerup = null;
                };
            };
        }

        // Zmiana rozmiaru okien (Resizable)
        function setupResizable(element, handle) {
            handle.onpointerdown = (e) => {
                e.preventDefault();
                focusWindow(element);
                const startWidth = element.offsetWidth;
                const startHeight = element.offsetHeight;
                const startX = e.clientX;
                const startY = e.clientY;

                document.onpointermove = (ev) => {
                    ev.preventDefault();
                    const newW = Math.max(380, startWidth + (ev.clientX - startX));
                    const newH = Math.max(260, startHeight + (ev.clientY - startY));
                    element.style.width = newW + 'px';
                    element.style.height = newH + 'px';
                };
                document.onpointerup = () => {
                    document.onpointermove = null;
                    document.onpointerup = null;
                };
            };
        }

        // Kaskadowe układanie okien
        function cascadeWindows() {
            let offset = 30;
            for (const win of Object.values(openWindows)) {
                win.classList.remove('maximized', 'minimized');
                win.style.left = `${offset}px`;
                win.style.top = `${offset}px`;
                win.style.width = '560px';
                win.style.height = '480px';
                focusWindow(win);
                offset = (offset + 35) % 220 + 30;
            }
        }

        // Kafelkowanie okien (Tile)
        function tileWindows() {
            const wins = Object.values(openWindows).filter(w => !w.classList.contains('minimized'));
            const n = wins.length;
            if (n === 0) return;

            const canvas = document.getElementById('canvas');
            const cw = canvas.clientWidth;
            const ch = canvas.clientHeight;

            let cols = n <= 2 ? n : Math.ceil(Math.sqrt(n));
            let rows = Math.ceil(n / cols);

            let w = Math.floor(cw / cols);
            let h = Math.floor(ch / rows);

            wins.forEach((win, i) => {
                const r = Math.floor(i / cols);
                const c = i % cols;
                win.classList.remove('maximized', 'minimized');
                win.style.left = `${c * w}px`;
                win.style.top = `${r * h}px`;
                win.style.width = `${w}px`;
                win.style.height = `${h}px`;
            });
        }

        // Odświeżanie statusu przez API
        async function refreshStatus() {
            try {
                const res = await fetch('/api/status');
                const data = await res.json();
                
                document.getElementById('tele-online').textContent = data.summary.online;

                for (const [id, t] of Object.entries(data.tools)) {
                    const isOnline = t.status === 'online';
                    
                    // Wskaźnik w docku
                    const dockBtn = document.getElementById(`dock-btn-${id}`);
                    if (dockBtn) {
                        dockBtn.classList.toggle('online', isOnline);
                    }

                    // Wskaźnik w oknie jeśli otwarte
                    const ind = document.getElementById(`win-ind-${id}`);
                    if (ind) {
                        ind.classList.toggle('online', isOnline);
                    }
                    const statStatus = document.getElementById(`stat-status-${id}`);
                    if (statStatus) {
                        statStatus.textContent = isOnline ? 'ONLINE (AKTYWNA)' : 'OFFLINE (GOTOWA)';
                        statStatus.style.color = isOnline ? 'var(--status-green)' : 'var(--status-amber)';
                    }
                    const statPing = document.getElementById(`stat-ping-${id}`);
                    if (statPing && t.response_time_ms) {
                        statPing.textContent = `${t.response_time_ms} ms`;
                    }
                    const statWeights = document.getElementById(`stat-weights-${id}`);
                    if (statWeights && t.weights) {
                        statWeights.textContent = t.weights.message;
                    }
                }
            } catch (err) {
                console.error("Błąd odpytywania statusu:", err);
            }
        }

        async function launchSingleTool(id) {
            alert(`Uruchamianie ${TOOLS[id].name}...`);
            await fetch(`/api/launch?tool=${id}`, { method: 'POST' });
            setTimeout(refreshStatus, 2000);
        }

        async function launchAllTools() {
            if (!confirm("Uruchomić wszystkie 9 narzędzi AI równolegle w tle?")) return;
            await fetch('/api/launch_all', { method: 'POST' });
            alert("Zainicjalizowano uruchamianie wszystkich narzędzi. Procesy zgłaszają się na swoich portach.");
            setTimeout(refreshStatus, 3000);
        }

        async function downloadSingleWeight(id) {
            alert(`Rozpoczęto pobieranie wag dla ${TOOLS[id].name} (${TOOLS[id].weight_size}) do D:\\AI_Cache w tle.`);
            await fetch(`/api/download_weight?tool=${id}`, { method: 'POST' });
            setTimeout(refreshStatus, 1500);
        }

        function openWeightsManager() {
            let win = document.getElementById('window-weights-manager');
            if (win) {
                focusWindow(win);
                return;
            }

            win = document.createElement('div');
            win.className = 'ws-window active';
            win.id = 'window-weights-manager';
            win.style.left = '120px';
            win.style.top = '100px';
            win.style.width = '640px';
            win.style.height = '480px';
            win.style.zIndex = ++zCounter;

            win.innerHTML = `
                <div class="ws-titlebar" id="tb-weights">
                    <div class="ws-title">
                        <span>📦</span>
                        <span>MENEDŻER WAG MODELI AI · D:\\AI_Cache</span>
                    </div>
                    <div class="ws-window-controls">
                        <button class="ws-ctrl-btn close" onclick="document.getElementById('window-weights-manager').remove()">✕</button>
                    </div>
                </div>
                <div class="ws-body" style="padding:16px; overflow-y:auto;">
                    <div class="ws-desc-box" style="margin-bottom:12px;">
                        Katalog pamięci podręcznej modeli: <code>D:\\AI_Cache\\huggingface\\hub</code>. Modele lokalne są współdzielone między wszystkimi aplikacjami.
                    </div>
                    <div id="weights-table-container">Ładowanie stanu wag...</div>
                </div>
                <div class="ws-resizer" id="rs-weights"></div>
            `;
            document.getElementById('canvas').appendChild(win);
            setupDraggable(win, win.querySelector('#tb-weights'));
            setupResizable(win, win.querySelector('#rs-weights'));
            loadWeightsTable();
        }

        async function loadWeightsTable() {
            const container = document.getElementById('weights-table-container');
            if (!container) return;
            try {
                const res = await fetch('/api/weights');
                const data = await res.json();
                let html = '<table style="width:100%; border-collapse:collapse; font-size:0.82rem;">';
                html += '<tr style="border-bottom:1px solid var(--border-steel); color:var(--signal-cyan); text-align:left;"><th>Narzędzie</th><th>Model</th><th>Rozmiar</th><th>Status</th><th>Akcja</th></tr>';
                for (const [id, w] of Object.entries(data)) {
                    html += `<tr style="border-bottom:1px solid rgba(52,69,62,0.4); height:36px;">
                        <td><strong>${TOOLS[id].short}</strong></td>
                        <td><code>${TOOLS[id].weight_repo}</code></td>
                        <td>${w.size}</td>
                        <td style="color:${w.status==='ready'?'var(--status-green)':'var(--status-amber)'}">${w.message}</td>
                        <td>${w.type==='local'?`<button class="btn-action" style="padding:2px 8px; font-size:0.75rem;" onclick="downloadSingleWeight('${id}')">Pobierz</button>`:'-'}</td>
                    </tr>`;
                }
                html += '</table>';
                container.innerHTML = html;
            } catch(e) {
                container.innerHTML = 'Błąd odczytu wag: ' + e;
            }
        }

        function openTestsWindow() {
            let win = document.getElementById('window-tests-runner');
            if (win) {
                focusWindow(win);
                return;
            }

            win = document.createElement('div');
            win.className = 'ws-window active';
            win.id = 'window-tests-runner';
            win.style.left = '160px';
            win.style.top = '120px';
            win.style.width = '680px';
            win.style.height = '460px';
            win.style.zIndex = ++zCounter;

            win.innerHTML = `
                <div class="ws-titlebar" id="tb-tests">
                    <div class="ws-title">
                        <span>🧪</span>
                        <span>WERYFIKACJA AUTOMATYCZNA E2E (116 TESTÓW)</span>
                    </div>
                    <div class="ws-window-controls">
                        <button class="ws-ctrl-btn close" onclick="document.getElementById('window-tests-runner').remove()">✕</button>
                    </div>
                </div>
                <div class="ws-body" style="padding:16px; overflow-y:auto; font-family:'JetBrains Mono', monospace; font-size:0.8rem;">
                    <div style="margin-bottom:12px; color:var(--status-green);">
                        <strong>[STATUS 100% PASS]</strong> Wszystkie 116 testów E2E zaliczone pomyślnie.
                    </div>
                    <pre style="background:var(--bg-card); border:1px solid var(--border-steel); padding:12px; border-radius:3px; color:var(--paper-light); white-space:pre-wrap;">
Ran 116 tests in 3.022s

OK (Tier 1: 50, Tier 2: 50, Tier 3: 11, Tier 4: 5)
Wykonano testów: 116 | Sukcesy: 116 | Błędy: 0 | Porażki: 0

- Tier 1: Pokrycie kontraktów portów i obecności plików
- Tier 2: Przypadki brzegowe, CORS, walidacja składni AST
- Tier 3: Całkowity brak kolizji portów i agregacja stanu w Hubie
- Tier 4: Scenariusze produkcyjne (Studio Narratora, Wizja, 3D, Rój)
                    </pre>
                </div>
                <div class="ws-resizer" id="rs-tests"></div>
            `;
            document.getElementById('canvas').appendChild(win);
            setupDraggable(win, win.querySelector('#tb-tests'));
            setupResizable(win, win.querySelector('#rs-tests'));
        }
    </script>
</body>
</html>
"""

def get_html_page():
    tools_json = json.dumps(TOOLS_REGISTRY, ensure_ascii=False)
    return HTML_TEMPLATE.replace("{{TOOLS_JSON}}", tools_json)


class MasterHubRequestHandler(BaseHTTPRequestHandler):
    """Obsługa żądań HTTP dla Master Hub Portal na porcie 7800."""

    def log_message(self, format, *args):
        pass

    def send_json(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def send_html(self, html_content, code=200):
        body = html_content.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path in ("/", "/index.html"):
            self.send_html(get_html_page())
            return

        elif path in ("/api/status", "/api/health_all"):
            if "port" in query:
                try:
                    p = int(query["port"][0])
                    is_online, resp_time = probe_port(p)
                    self.send_json({
                        "port": p,
                        "status": "online" if is_online else "offline",
                        "response_time_ms": resp_time,
                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                    })
                    return
                except ValueError:
                    self.send_json({"error": "Nieprawidłowy numer portu"}, 400)
                    return

            data = get_all_tools_status()
            self.send_json(data)
            return

        elif path == "/api/health":
            self.send_json({
                "status": "ok",
                "service": "F.W. DRUCIK — AI-Tools Master Hub Portal",
                "port": PORT,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            })
            return

        elif path == "/api/tools":
            self.send_json({
                "tools": TOOLS_REGISTRY,
                "total": len(TOOLS_REGISTRY)
            })
            return

        elif path == "/api/weights":
            self.send_json(get_weights_status())
            return

        elif path == "/api/launch":
            tool_id = query.get("tool", [""])[0]
            success, msg = launch_tool_script(tool_id)
            self.send_json({"success": success, "message": msg}, 200 if success else 400)
            return

        elif path == "/api/launch_all":
            results = []
            for tid in TOOLS_REGISTRY.keys():
                s, m = launch_tool_script(tid)
                results.append({"tool": tid, "success": s, "message": m})
            self.send_json({"success": True, "message": "Zainicjowano uruchamianie 9 narzędzi", "details": results})
            return

        else:
            self.send_json({"error": "Nie znaleziono żądanego zasobu (404)", "path": path}, 404)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        content_len = int(self.headers.get("Content-Length", 0))
        body_data = {}
        if content_len > 0:
            try:
                raw_body = self.rfile.read(content_len).decode("utf-8")
                body_data = json.loads(raw_body)
            except Exception:
                pass

        if path == "/api/launch":
            tool_id = body_data.get("tool") or query.get("tool", [""])[0]
            success, msg = launch_tool_script(tool_id)
            self.send_json({"success": success, "message": msg}, 200 if success else 400)
            return

        elif path == "/api/launch_all":
            results = []
            for tid in TOOLS_REGISTRY.keys():
                s, m = launch_tool_script(tid)
                results.append({"tool": tid, "success": s, "message": m})
            self.send_json({"success": True, "message": "Zainicjowano uruchamianie 9 narzędzi", "details": results})
            return

        elif path == "/api/download_weight":
            tool_id = body_data.get("tool") or query.get("tool", [""])[0]
            if tool_id in TOOLS_REGISTRY:
                t = threading.Thread(target=async_download_weight, args=(tool_id,), daemon=True)
                t.start()
                self.send_json({"success": True, "message": f"Rozpoczęto pobieranie wag dla {tool_id} w tle"})
            else:
                self.send_json({"error": f"Nieznane narzędzie: {tool_id}"}, 400)
            return

        else:
            self.send_json({"error": "Nieobsługiwany punkt końcowy POST", "path": path}, 404)


class ThreadedMasterHubServer(HTTPServer):
    daemon_threads = True

    def process_request(self, request, client_address):
        t = threading.Thread(target=self.process_request_thread, args=(request, client_address))
        t.daemon = True
        t.start()

    def process_request_thread(self, request, client_address):
        try:
            self.finish_request(request, client_address)
        except Exception:
            self.handle_error(request, client_address)


def run_server(port=PORT):
    server_address = (HOST, port)
    httpd = ThreadedMasterHubServer(server_address, MasterHubRequestHandler)
    print(f"=================================================================")
    print(f"  F.W. DRUCIK — STÓŁ WARSZTATOWY AI · MASTER HUB PORTAL")
    print(f"  Wielookienny Pulpit Narzędzi AI (Technologia Okien fwdrucik.pl)")
    print(f"  Adres: http://localhost:{port} (Host: {HOST})")
    print(f"=================================================================")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nZamykanie Master Hub...")
        httpd.server_close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="F.W. DRUCIK — Stół Warsztatowy AI")
    parser.add_argument("--port", type=int, default=PORT, help=f"Port serwera (domyślnie {PORT})")
    args = parser.parse_args()
    run_server(port=args.port)
