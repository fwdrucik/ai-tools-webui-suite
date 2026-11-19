#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI-Tools Master Hub Portal — Port 7800
Centralny Panel Zarządzania i Monitorowania 9 Narzędzi Desktopowych AI
"""

import sys
import os
import json
import time
import socket
import threading
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from concurrent.futures import ThreadPoolExecutor

# Konfiguracja serwera
HOST = "0.0.0.0"
PORT = 7800

# Rejestr 9 aplikacji desktopowych AI
TOOLS_REGISTRY = {
    "zonos": {
        "id": "zonos",
        "name": "Zonos Voice Studio",
        "port": 7860,
        "url": "http://localhost:7860",
        "category": "Głos i Mowa",
        "category_id": "voice",
        "summary": "Ekspresyjna synteza TTS i klonowanie głosu w czasie rzeczywistym",
        "description": "Zaawansowany syntezator mowy Zyphra Zonos-3 Mini (800M MoE) z 8-wymiarowymi suwakami emocji, precyzyjną kontrolą parametrów akustycznych i pełnym wsparciem języka polskiego.",
        "guide": "Wpisz polski tekst, dostosuj emocje (radość, smutek, złość, szept), wybierz głos referencyjny lub wgraj własną próbkę WAV, a następnie kliknij 'Generuj'. Działa na karcie RTX lub CPU.",
        "launch_script": r"D:\AI-Tools\Zonos\launch_zonos.bat",
        "directory": r"D:\AI-Tools\Zonos",
        "entry_point": "webui_zonos_pl.py"
    },
    "haru": {
        "id": "haru",
        "name": "Haru Full-Duplex Voice",
        "port": 8998,
        "url": "http://localhost:8998",
        "category": "Głos i Mowa",
        "category_id": "voice",
        "summary": "Dwukierunkowy asystent głosowy z obsługą przerwań mowy (barge-in)",
        "description": "System konwersacyjny czasu rzeczywistego Full-Duplex z polską lokalizacją paneli sterowania, streamingiem audio o ultraniskim opóźnieniu (WebRTC/WS) i natychmiastową reakcją na wtrącenia.",
        "guide": "Zezwól na dostęp do mikrofonu, wybierz profil polskiego asystenta i prowadź swobodną rozmowę. Możesz przerywać wypowiedź asystenta w dowolnym momencie bez oczekiwania na zakończenie zdania.",
        "launch_script": r"D:\AI-Tools\Haru\launch_haru.bat",
        "directory": r"D:\AI-Tools\Haru",
        "entry_point": "control_center_pl.py"
    },
    "cosyvoice": {
        "id": "cosyvoice",
        "name": "CosyVoice Studio",
        "port": 7862,
        "url": "http://localhost:7862",
        "category": "Głos i Mowa",
        "category_id": "voice",
        "summary": "Wielozakładkowe studio lektorskie i 3-sekundowe klonowanie Zero-Shot",
        "description": "5 dedykowanych zakładek: głosy predefiniowane SFT, klonowanie głosu z krótkiej 3-sekundowej próbki, automatyczna transkrypcja Whisper, synteza wielojęzyczna (cross-lingual) i tagi instrukcji lektorskich.",
        "guide": "Przejdź do zakładki Zero-Shot, załaduj min. 3 sekundy czystego nagrania głosu lektora, wprowadź tekst po polsku i wygeneruj profesjonalną ścieżkę lektorską gotową do pobrania w formacie WAV.",
        "launch_script": r"D:\AI-Tools\CosyVoice\launch_cosyvoice.bat",
        "directory": r"D:\AI-Tools\CosyVoice",
        "entry_point": "webui_cosyvoice_pl.py"
    },
    "mini_omni2": {
        "id": "mini_omni2",
        "name": "Mini-Omni2 Multimodal Live",
        "port": 7864,
        "url": "http://localhost:7864",
        "category": "Wizja i Multimodalność",
        "category_id": "vision",
        "summary": "Multimodalny asystent wideo i audio na żywo z modelem SNAC 24kHz",
        "description": "Przetwarzanie obrazu z kamery internetowej równolegle ze strumieniem mikrofonowym. Natychmiastowa synteza mowy w jakości 24kHz, czat strumieniowy oraz monitor zużycia pamięci VRAM.",
        "guide": "Włącz kamerę i mikrofon w przeglądarce. Pokaż obiekt przed obiektywem i zadaj pytanie głosem po polsku. Model odpowiada syntezą mowy na żywo i wypisuje transkrypcję w oknie czatu.",
        "launch_script": r"D:\AI-Tools\mini-omni2\launch_mini_omni2.bat",
        "directory": r"D:\AI-Tools\mini-omni2",
        "entry_point": "webui_server.py"
    },
    "gemini_live": {
        "id": "gemini_live",
        "name": "Gemini Omni Live Studio",
        "port": 7865,
        "url": "http://localhost:7865",
        "category": "Wizja i Multimodalność",
        "category_id": "vision",
        "summary": "Wszechstronne studio Gemini z wideo, udostępnianiem pulpitu i personami",
        "description": "Multimodalny interfejs oparty na modelach Gemini 2.5 Flash / Pro. Transmisja z kamery lub zrzut ekranu (screen share), interaktywny oscyloskop fali audio i wyspecjalizowane polskie persony.",
        "guide": "Wybierz źródło (kamera lub ekran), ustaw docelową personę (programista, analityk CAD, lektor) i kliknij 'Połącz'. Model na żywo analizuje pulpit i prowadzi dialog głosowy w języku polskim.",
        "launch_script": r"D:\AI-Tools\GeminiLiveStudio\launch_gemini_live.bat",
        "directory": r"D:\AI-Tools\GeminiLiveStudio",
        "entry_point": "webui_gemini_pl.py"
    },
    "fastframes": {
        "id": "fastframes",
        "name": "Apple FastFrames Video AI",
        "port": 7866,
        "url": "http://localhost:7866",
        "category": "Wizja i Multimodalność",
        "category_id": "vision",
        "summary": "Generowanie wideo Text-to-Video i interaktywny świat 3D LingBot",
        "description": "Szybka synteza sekwencji wideo z opisów tekstowych Apple FastFrames. Polskie szablony promptów kinematograficznych, zintegrowane środowisko 3D LingBot oraz menedżer wag HuggingFace.",
        "guide": "Wpisz prompt sceny lub wybierz jeden z polskich szablonów kinematograficznych, ustaw rozdzielczość i liczbę klatek (FPS), a następnie uruchom renderowanie. Wynik możesz odtworzyć bezpośrednio w odtwarzaczu.",
        "launch_script": r"D:\AI-Tools\ml-fastframes\launch_fastframes.bat",
        "directory": r"D:\AI-Tools\ml-fastframes",
        "entry_point": "webui_fastframes_pl.py"
    },
    "rerun": {
        "id": "rerun",
        "name": "Rerun 3D Visualizer",
        "port": 7867,
        "url": "http://localhost:7867",
        "category": "3D i Narzędzia Przestrzenne",
        "category_id": "spatial",
        "summary": "Wizualizacja chmur punktów, siatek 3D i danych sensorycznych",
        "description": "Centrum analizy danych 3D integrujące Rerun SDK z osadzonym Rerun Web Viewerem (port 9097). Obsługa wgrywania plików (.obj, .stl, .glb, .rrd), 5 polskich scen inżynieryjnych i telemetria gRPC.",
        "guide": "Wybierz jedną z gotowych scen demonstracyjnych lub przeciągnij model 3D do uploadera. Model zostanie natychmiast załadowany do interaktywnego okna widoku 3D z pełną kontrolą kamery i orbitowania.",
        "launch_script": r"D:\AI-Tools\rerun-sdk\launch_rerun.bat",
        "directory": r"D:\AI-Tools\rerun-sdk",
        "entry_point": "webui_server.py"
    },
    "autoswarm": {
        "id": "autoswarm",
        "name": "AutoSwarm Multi-Agent",
        "port": 7868,
        "url": "http://localhost:7868",
        "category": "Agenci i Autonomia",
        "category_id": "agents",
        "summary": "Centrum dowodzenia autonomicznym zespołem 6 agentów AI",
        "description": "Wizualizacja i koordynacja roju agentów: Codex, Claude, OpenCode, Copilot, Muse, Hermes. Dyspozytor misji zespołowych, strumień dziennika zdarzeń na żywo i panel akceptacji kroków krytycznych.",
        "guide": "Zdefiniuj cel misji w dyspozytorze, przydziel role agentom i uruchom zadanie. Obserwuj wymianę komunikatów i postęp w czasie rzeczywistym. W razie operacji krytycznych zatwierdź krok w panelu akceptacji.",
        "launch_script": r"D:\AI-Tools\AutoSwarm\launch_autoswarm.bat",
        "directory": r"D:\AI-Tools\AutoSwarm",
        "entry_point": "webui_server.py"
    },
    "sophon": {
        "id": "sophon",
        "name": "Sophon Realtime Voice AI",
        "port": 7869,
        "url": "http://localhost:7869",
        "category": "Głos i Mowa",
        "category_id": "voice",
        "summary": "Studio głosowe Dual-Engine z 13 profilami emocji i DuplexJev",
        "description": "Elastyczne środowisko wspierające zarówno połączenie z lokalną bramką Live Gateway (port 8789), jak i natychmiastowy symulator Web Audio. Precyzyjna modulacja 13 emocji i adaptacyjny filtr przerwań.",
        "guide": "Wybierz silnik (Live Gateway lub Symulator Web Audio), dobierz profil emocjonalny (entuzjazm, powaga, empatia), dostosuj czułość VAD i rozmawiaj z asystentem bez zakłóceń.",
        "launch_script": r"D:\AI-Tools\sophon-realtime\launch_sophon.bat",
        "directory": r"D:\AI-Tools\sophon-realtime",
        "entry_point": "webui_server.py"
    }
}


def probe_port(port, timeout=0.25):
    """Szybkie sprawdzenie czy dany port TCP odpowiada na localhost."""
    start = time.perf_counter()
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect(("127.0.0.1", port))
        s.close()
        elapsed_ms = round((time.perf_counter() - start) * 1000, 1)
        return True, elapsed_ms
    except Exception:
        return False, None


def get_all_tools_status():
    """Wielowątkowe równoległe sondowanie wszystkich 9 narzędzi."""
    results = {}
    online_count = 0
    offline_count = 0

    def check_tool(tool_id, tool_data):
        nonlocal online_count, offline_count
        port = tool_data["port"]
        is_online, resp_time = probe_port(port)
        if is_online:
            online_count += 1
            status_text = "online"
        else:
            offline_count += 1
            status_text = "offline"

        results[tool_id] = {
            **tool_data,
            "status": status_text,
            "response_time_ms": resp_time,
            "last_checked": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [
            executor.submit(check_tool, tool_id, tool_data)
            for tool_id, tool_data in TOOLS_REGISTRY.items()
        ]
        for f in futures:
            f.result()

    return {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "hub_port": PORT,
        "summary": {
            "total": len(TOOLS_REGISTRY),
            "online": online_count,
            "offline": offline_count
        },
        "tools": results
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
        # Na Windows uruchamiamy w nowej konsoli
        if sys.platform == "win32":
            subprocess.Popen(
                ["cmd.exe", "/c", script_path],
                cwd=work_dir,
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
        else:
            subprocess.Popen([script_path], cwd=work_dir)
        return True, f"Pomyślnie uruchomiono skrypt dla {tool['name']}"
    except Exception as e:
        return False, f"Błąd uruchamiania skryptu: {str(e)}"


def generate_initial_cards_html():
    cards = []
    for tool_id, tool in TOOLS_REGISTRY.items():
        cards.append(f"""
            <div class="tool-card" id="card-{tool_id}">
                <div>
                    <div class="card-header">
                        <span class="category-tag">{tool['category']}</span>
                        <span class="port-badge">PORT {tool['port']}</span>
                    </div>
                    <h3 class="tool-title">{tool['name']}</h3>
                    <div class="status-indicator status-offline" id="status-{tool_id}">
                        <span class="dot dot-red"></span>
                        <span>Sprawdzanie stanu...</span>
                    </div>
                    <p class="tool-desc">{tool['description']}</p>
                    <button class="guide-toggle" id="guide-btn-{tool_id}" onclick="toggleGuide('{tool_id}')">
                        &#9662; Pokaż instrukcję i przewodnik PL
                    </button>
                    <div class="guide-box" id="guide-{tool_id}">
                        <strong>Przewodnik obsługi:</strong><br>{tool['guide']}<br><br>
                        <strong>Plik główny:</strong> <code>{tool['entry_point']}</code><br>
                        <strong>Katalog roboczy:</strong> <code>{tool['directory']}</code>
                    </div>
                </div>
                <div class="card-actions">
                    <a href="{tool['url']}" target="_blank" class="btn btn-outline btn-sm">Otwórz WebUI &#8599;</a>
                    <button onclick="launchTool('{tool_id}')" class="btn btn-sm">Uruchom .bat &#9889;</button>
                </div>
            </div>
        """)
    return "\n".join(cards)


def generate_initial_table_html():
    rows = []
    for tool_id, tool in TOOLS_REGISTRY.items():
        script_name = os.path.basename(tool['launch_script'])
        rows.append(f"""
            <tr id="tr-{tool_id}">
                <td><strong>{tool['name']}</strong></td>
                <td>{tool['category']}</td>
                <td><span class="port-badge">{tool['port']}</span></td>
                <td><a href="{tool['url']}" target="_blank" style="color: var(--accent-blue); text-decoration: none;">{tool['url']}</a></td>
                <td style="font-family: monospace; font-size: 0.75rem; color: var(--text-muted);">{script_name}</td>
                <td><span class="status-offline" id="tbl-status-{tool_id}">&bull; Oczekiwanie...</span></td>
            </tr>
        """)
    return "\n".join(rows)


# Szablon HTML interfejsu Master Hub
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI-Tools Master Hub — Port 7800</title>
    <style>
        :root {
            --bg-base: #090d16;
            --bg-card: #131b2e;
            --bg-card-hover: #19233c;
            --border: #233152;
            --border-hover: #3b82f6;
            --text-main: #f1f5f9;
            --text-muted: #94a3b8;
            --accent-blue: #3b82f6;
            --accent-cyan: #06b6d4;
            --accent-green: #10b981;
            --accent-red: #ef4444;
            --accent-amber: #f59e0b;
            --font-stack: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            background-color: var(--bg-base);
            color: var(--text-main);
            font-family: var(--font-stack);
            line-height: 1.5;
            min-height: 100vh;
            padding: 0;
            margin: 0;
        }

        header {
            background: linear-gradient(180deg, #101728 0%, #0d1220 100%);
            border-bottom: 1px solid var(--border);
            padding: 24px 32px;
            position: sticky;
            top: 0;
            z-index: 50;
        }

        .header-content {
            max-width: 1400px;
            margin: 0 auto;
            display: flex;
            flex-wrap: wrap;
            justify-content: space-between;
            align-items: center;
            gap: 20px;
        }

        .logo-area h1 {
            font-size: 1.5rem;
            font-weight: 700;
            color: #ffffff;
            letter-spacing: -0.02em;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .logo-badge {
            background: rgba(59, 130, 246, 0.15);
            color: var(--accent-blue);
            font-size: 0.75rem;
            padding: 4px 8px;
            border-radius: 6px;
            border: 1px solid rgba(59, 130, 246, 0.3);
            text-transform: uppercase;
            font-weight: 600;
        }

        .logo-area p {
            color: var(--text-muted);
            font-size: 0.875rem;
            margin-top: 4px;
        }

        .stats-bar {
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
            align-items: center;
        }

        .stat-pill {
            background: var(--bg-card);
            border: 1px solid var(--border);
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 0.8125rem;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .stat-pill strong {
            color: #ffffff;
        }

        .dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            display: inline-block;
        }

        .dot-green { background-color: var(--accent-green); box-shadow: 0 0 8px var(--accent-green); }
        .dot-red { background-color: var(--accent-red); box-shadow: 0 0 8px var(--accent-red); }
        .dot-blue { background-color: var(--accent-blue); }

        .btn {
            background-color: var(--accent-blue);
            color: #ffffff;
            border: none;
            padding: 8px 16px;
            border-radius: 6px;
            font-size: 0.8125rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }

        .btn:hover {
            filter: brightness(1.15);
            transform: translateY(-1px);
        }

        .btn-outline {
            background-color: transparent;
            border: 1px solid var(--border);
            color: var(--text-main);
        }

        .btn-outline:hover {
            background-color: var(--bg-card-hover);
            border-color: var(--border-hover);
        }

        .btn-sm {
            padding: 6px 12px;
            font-size: 0.75rem;
        }

        main {
            max-width: 1400px;
            margin: 0 auto;
            padding: 32px;
        }

        .controls-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 16px;
            margin-bottom: 24px;
        }

        .filters {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }

        .filter-btn {
            background: var(--bg-card);
            border: 1px solid var(--border);
            color: var(--text-muted);
            padding: 6px 14px;
            border-radius: 6px;
            font-size: 0.8125rem;
            cursor: pointer;
            transition: all 0.15s ease;
        }

        .filter-btn:hover, .filter-btn.active {
            background: rgba(59, 130, 246, 0.15);
            color: #ffffff;
            border-color: var(--accent-blue);
        }

        .search-input {
            background: var(--bg-card);
            border: 1px solid var(--border);
            color: #ffffff;
            padding: 8px 14px;
            border-radius: 6px;
            font-size: 0.8125rem;
            width: 260px;
            outline: none;
            transition: border-color 0.15s ease;
        }

        .search-input:focus {
            border-color: var(--accent-blue);
        }

        .tools-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
            gap: 24px;
            margin-bottom: 40px;
        }

        .tool-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 20px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            transition: all 0.2s ease;
            position: relative;
        }

        .tool-card:hover {
            border-color: var(--border-hover);
            background: var(--bg-card-hover);
            transform: translateY(-2px);
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.4);
        }

        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 12px;
        }

        .category-tag {
            font-size: 0.7rem;
            font-weight: 600;
            text-transform: uppercase;
            padding: 3px 8px;
            border-radius: 4px;
            background: rgba(255, 255, 255, 0.05);
            color: var(--accent-cyan);
            border: 1px solid rgba(6, 182, 212, 0.2);
        }

        .port-badge {
            font-family: monospace;
            font-size: 0.75rem;
            font-weight: 700;
            background: #0b111e;
            padding: 3px 8px;
            border-radius: 4px;
            border: 1px solid var(--border);
            color: var(--accent-amber);
        }

        .tool-title {
            font-size: 1.15rem;
            font-weight: 700;
            color: #ffffff;
            margin-bottom: 4px;
        }

        .status-indicator {
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 0.75rem;
            font-weight: 600;
            margin-bottom: 12px;
        }

        .status-online { color: var(--accent-green); }
        .status-offline { color: var(--accent-red); }

        .tool-desc {
            font-size: 0.85rem;
            color: var(--text-muted);
            margin-bottom: 16px;
            flex-grow: 1;
        }

        .guide-box {
            background: #0c1220;
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 10px 12px;
            margin-bottom: 16px;
            font-size: 0.78rem;
            color: #cbd5e1;
            display: none;
        }

        .guide-box.visible {
            display: block;
        }

        .guide-toggle {
            font-size: 0.75rem;
            color: var(--accent-blue);
            background: none;
            border: none;
            cursor: pointer;
            padding: 0;
            margin-bottom: 14px;
            display: inline-flex;
            align-items: center;
            gap: 4px;
            font-weight: 500;
        }

        .guide-toggle:hover {
            text-decoration: underline;
        }

        .card-actions {
            display: flex;
            gap: 8px;
            padding-top: 14px;
            border-top: 1px solid rgba(255, 255, 255, 0.05);
        }

        .card-actions .btn {
            flex: 1;
            justify-content: center;
        }

        .info-section {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 24px;
            margin-top: 32px;
        }

        .info-section h2 {
            font-size: 1.15rem;
            font-weight: 700;
            margin-bottom: 16px;
            color: #ffffff;
        }

        .ports-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.8125rem;
        }

        .ports-table th {
            text-align: left;
            padding: 10px 12px;
            background: #0d1424;
            color: var(--text-muted);
            border-bottom: 1px solid var(--border);
            font-weight: 600;
        }

        .ports-table td {
            padding: 10px 12px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }

        .ports-table tr:hover td {
            background: rgba(255, 255, 255, 0.02);
        }

        .toast {
            position: fixed;
            bottom: 24px;
            right: 24px;
            background: #1e293b;
            color: #ffffff;
            padding: 12px 20px;
            border-radius: 8px;
            border: 1px solid var(--border);
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.5);
            font-size: 0.875rem;
            z-index: 100;
            opacity: 0;
            transform: translateY(20px);
            transition: all 0.3s ease;
            pointer-events: none;
        }

        .toast.show {
            opacity: 1;
            transform: translateY(0);
        }

        footer {
            border-top: 1px solid var(--border);
            padding: 24px 32px;
            text-align: center;
            font-size: 0.75rem;
            color: var(--text-muted);
            margin-top: 40px;
        }
    </style>
</head>
<body>
    <header>
        <div class="header-content">
            <div class="logo-area">
                <h1>
                    <span>AI-Tools Master Hub</span>
                    <span class="logo-badge">PORT 7800</span>
                </h1>
                <p>Centralny Portal Zarządzania Ekosystemem 9 Aplikacji Desktopowych AI z Polskim WebUI</p>
            </div>
            <div class="stats-bar">
                <div class="stat-pill">
                    <span class="dot dot-blue"></span>
                    <span>Wszystkich: <strong>9</strong></span>
                </div>
                <div class="stat-pill">
                    <span class="dot dot-green"></span>
                    <span>Aktywne: <strong id="stat-online">0</strong></span>
                </div>
                <div class="stat-pill">
                    <span class="dot dot-red"></span>
                    <span>Nieaktywne: <strong id="stat-offline">9</strong></span>
                </div>
                <button class="btn btn-outline btn-sm" onclick="fetchStatus()">
                    <span>Odśwież stan</span>
                </button>
                <button class="btn btn-sm" onclick="launchAll()">
                    <span>Uruchom Wszystkie (.bat)</span>
                </button>
            </div>
        </div>
    </header>

    <main>
        <div class="controls-row">
            <div class="filters">
                <button class="filter-btn active" data-filter="all" onclick="filterCategory('all', this)">Wszystkie (9)</button>
                <button class="filter-btn" data-filter="voice" onclick="filterCategory('voice', this)">Głos i Mowa (4)</button>
                <button class="filter-btn" data-filter="vision" onclick="filterCategory('vision', this)">Wizja i Multimodalność (3)</button>
                <button class="filter-btn" data-filter="spatial" onclick="filterCategory('spatial', this)">3D i Narzędzia (1)</button>
                <button class="filter-btn" data-filter="agents" onclick="filterCategory('agents', this)">Agenci i Autonomia (1)</button>
            </div>
            <input type="text" class="search-input" id="search-box" placeholder="Filtruj narzędzia lub porty..." oninput="handleSearch()">
        </div>

        <div class="tools-grid" id="tools-container">
            {{INITIAL_CARDS}}
        </div>

        <div class="info-section">
            <h2>Architektura Ekosystemu i Rejestr Portów</h2>
            <table class="ports-table">
                <thead>
                    <tr>
                        <th>Narzędzie AI</th>
                        <th>Kategoria</th>
                        <th>Port HTTP</th>
                        <th>Adres URL</th>
                        <th>Skrypt Startowy</th>
                        <th>Stan Portu</th>
                    </tr>
                </thead>
                <tbody id="ports-table-body">
                    {{INITIAL_ROWS}}
                </tbody>
            </table>
        </div>
    </main>

    <div class="toast" id="toast-msg"></div>

    <footer>
        <p>AI-Tools Master Hub Portal &bull; D:\\AI-Tools &bull; Zgodność ze standardem UTF-8 i izolacją portów &bull; 2026</p>
    </footer>

    <script>
        let currentFilter = 'all';
        let currentSearch = '';
        let cachedData = null;

        function showToast(text) {
            const toast = document.getElementById('toast-msg');
            toast.textContent = text;
            toast.classList.add('show');
            setTimeout(() => {
                toast.classList.remove('show');
            }, 3500);
        }

        async function fetchStatus() {
            try {
                const res = await fetch('/api/status');
                if (!res.ok) throw new Error('Błąd odpowiedzi serwera');
                const data = await res.json();
                cachedData = data;
                renderDashboard(data);
            } catch (err) {
                console.error('Błąd pobierania statusu:', err);
            }
        }

        function filterCategory(cat, btn) {
            currentFilter = cat;
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            if (cachedData) renderDashboard(cachedData);
        }

        function handleSearch() {
            currentSearch = document.getElementById('search-box').value.toLowerCase().trim();
            if (cachedData) renderDashboard(cachedData);
        }

        function toggleGuide(id) {
            const el = document.getElementById('guide-' + id);
            const btn = document.getElementById('guide-btn-' + id);
            if (el.classList.contains('visible')) {
                el.classList.remove('visible');
                btn.innerHTML = '&#9662; Pokaż instrukcję i przewodnik PL';
            } else {
                el.classList.add('visible');
                btn.innerHTML = '&#9652; Ukryj instrukcję';
            }
        }

        async function launchTool(id) {
            showToast('Uruchamianie skryptu dla ' + id + '...');
            try {
                const res = await fetch('/api/launch?tool=' + encodeURIComponent(id), { method: 'POST' });
                const json = await res.json();
                showToast(json.message || 'Wysłano polecenie uruchomienia');
                setTimeout(fetchStatus, 2000);
            } catch (err) {
                showToast('Błąd uruchamiania narzędzia: ' + err.message);
            }
        }

        async function launchAll() {
            showToast('Uruchamianie wszystkich 9 narzędzi...');
            try {
                const res = await fetch('/api/launch_all', { method: 'POST' });
                const json = await res.json();
                showToast(json.message || 'Wysłano polecenie uruchomienia wszystkich narzędzi');
                setTimeout(fetchStatus, 3000);
            } catch (err) {
                showToast('Błąd uruchamiania: ' + err.message);
            }
        }

        function renderDashboard(data) {
            document.getElementById('stat-online').textContent = data.summary.online;
            document.getElementById('stat-offline').textContent = data.summary.offline;

            const container = document.getElementById('tools-container');
            const tableBody = document.getElementById('ports-table-body');
            container.innerHTML = '';
            tableBody.innerHTML = '';

            const tools = Object.values(data.tools);

            tools.forEach(tool => {
                const matchCat = (currentFilter === 'all') || (tool.category_id === currentFilter);
                const matchSearch = !currentSearch ||
                    tool.name.toLowerCase().includes(currentSearch) ||
                    tool.summary.toLowerCase().includes(currentSearch) ||
                    String(tool.port).includes(currentSearch);

                const row = document.createElement('tr');
                const isOnline = tool.status === 'online';
                row.innerHTML = `
                    <td><strong>${tool.name}</strong></td>
                    <td>${tool.category}</td>
                    <td><span class="port-badge">${tool.port}</span></td>
                    <td><a href="${tool.url}" target="_blank" style="color: var(--accent-blue); text-decoration: none;">${tool.url}</a></td>
                    <td style="font-family: monospace; font-size: 0.75rem; color: var(--text-muted);">${tool.launch_script.split('\\\\').pop()}</td>
                    <td><span class="${isOnline ? 'status-online' : 'status-offline'}">&bull; ${isOnline ? 'Aktywny (' + tool.response_time_ms + ' ms)' : 'Nieaktywny'}</span></td>
                `;
                tableBody.appendChild(row);

                if (!matchCat || !matchSearch) return;

                const card = document.createElement('div');
                card.className = 'tool-card';
                card.innerHTML = `
                    <div>
                        <div class="card-header">
                            <span class="category-tag">${tool.category}</span>
                            <span class="port-badge">PORT ${tool.port}</span>
                        </div>
                        <h3 class="tool-title">${tool.name}</h3>
                        <div class="status-indicator ${isOnline ? 'status-online' : 'status-offline'}">
                            <span class="dot ${isOnline ? 'dot-green' : 'dot-red'}"></span>
                            <span>${isOnline ? 'Aktywny (Online) — ' + tool.response_time_ms + ' ms' : 'Nieaktywny (Offline)'}</span>
                        </div>
                        <p class="tool-desc">${tool.description}</p>
                        <button class="guide-toggle" id="guide-btn-${tool.id}" onclick="toggleGuide('${tool.id}')">
                            &#9662; Pokaż instrukcję i przewodnik PL
                        </button>
                        <div class="guide-box" id="guide-${tool.id}">
                            <strong>Przewodnik obsługi:</strong><br>${tool.guide}<br><br>
                            <strong>Plik główny:</strong> <code>${tool.entry_point}</code><br>
                            <strong>Katalog roboczy:</strong> <code>${tool.directory}</code>
                        </div>
                    </div>
                    <div class="card-actions">
                        <a href="${tool.url}" target="_blank" class="btn btn-outline btn-sm">Otwórz WebUI &#8599;</a>
                        <button onclick="launchTool('${tool.id}')" class="btn btn-sm">Uruchom .bat &#9889;</button>
                    </div>
                `;
                container.appendChild(card);
            });
        }

        fetchStatus();
        setInterval(fetchStatus, 4000);
    </script>
</body>
</html>
"""

def get_html_page():
    return HTML_TEMPLATE.replace("{{INITIAL_CARDS}}", generate_initial_cards_html()).replace("{{INITIAL_ROWS}}", generate_initial_table_html())



class MasterHubRequestHandler(BaseHTTPRequestHandler):
    """Obsługa żądań HTTP dla Master Hub Portal na porcie 7800."""

    def log_message(self, format, *args):
        # Ciche logowanie lub standardowe
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
            # Jeśli podano port, sprawdź tylko ten port
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

            # Sprawdzenie wszystkich narzędzi
            data = get_all_tools_status()
            self.send_json(data)
            return

        elif path == "/api/health":
            self.send_json({
                "status": "ok",
                "service": "AI-Tools Master Hub Portal",
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

        # Odczyt ciała żądania jeśli obecne
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

        else:
            self.send_json({"error": "Nieobsługiwany punkt końcowy POST", "path": path}, 404)


class ThreadedMasterHubServer(HTTPServer):
    """Wielowątkowy serwer HTTP umożliwiający jednoczesną obsługę wielu klientów."""
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
        finally:
            self.shutdown_request(request)


def run_hub_server(host=HOST, port=PORT):
    server_address = (host, port)
    httpd = ThreadedMasterHubServer(server_address, MasterHubRequestHandler)
    print(f"============================================================")
    print(f"  AI-Tools Master Hub Portal — Uruchomiono na porcie {port}")
    print(f"  Adres lokalny: http://localhost:{port}")
    print(f"  Interfejs sieciowy: http://{host}:{port}")
    print(f"  Wielowątkowe monitorowanie 9 narzędzi AI aktywne")
    print(f"============================================================")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nZatrzymywanie serwera Master Hub...")
    finally:
        httpd.server_close()
        print("Serwer Master Hub zatrzymany.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="AI-Tools Master Hub Server")
    parser.add_argument("--host", default=HOST, help="Adres nasłuchiwania (domyślnie 0.0.0.0)")
    parser.add_argument("--port", type=int, default=PORT, help="Port serwera (domyślnie 7800)")
    args = parser.parse_args()

    run_hub_server(host=args.host, port=args.port)
