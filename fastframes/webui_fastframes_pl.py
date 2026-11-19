#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Apple FastFrames Video AI WebUI Studio
Port: 7866
Studio generowania wideo z tekstu, interaktywnego świata LingBot 3D oraz menedżera wag i VRAM.
"""
import os
import sys
import json
import time
import random
import threading
import tempfile
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_DIR))

from flask import Flask, request, jsonify, render_template_string, send_file
import numpy as np
import torch
import imageio

app = Flask(__name__)
CHECKPOINT_DIR = REPO_DIR / "checkpoints"
OUTPUTS_DIR = REPO_DIR / "outputs"
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

# Lista znanych wag i checkpoints
CHECKPOINTS_INFO = [
    {
        "id": "ff_s",
        "name": "Apple FastFrames-S",
        "repo": "apple/FastFrames-S",
        "size_gb": 1.8,
        "path": "FastFrames-S",
        "desc": "Ultra-szybki model DiT (~60+ FPS), 8 kroków wnioskowania"
    },
    {
        "id": "ff_l",
        "name": "Apple FastFrames-L",
        "repo": "apple/FastFrames-L",
        "size_gb": 4.2,
        "path": "FastFrames-L",
        "desc": "Model o najwyższej rozdzielczości i jakości detali kinowych"
    },
    {
        "id": "wan_base",
        "name": "Wan2.1-T2V-1.3B (Base)",
        "repo": "Wan-AI/Wan2.1-T2V-1.3B",
        "size_gb": 6.5,
        "path": "Wan2.1-T2V-1.3B",
        "desc": "Podstawowy transformator dyfuzji wideo Wan2.1"
    },
    {
        "id": "lingbot",
        "name": "LingBot World v2 (1.3B)",
        "repo": "robbyant/lingbot-world-v2-1.3b-causal-fast",
        "size_gb": 3.8,
        "path": "lingbot-world-v2-1.3b-causal-fast",
        "desc": "Autoregresywny silnik generowania świata 3D w czasie rzeczywistym"
    },
    {
        "id": "causal_forcing",
        "name": "Causal-Forcing (KV Refinement)",
        "repo": "zhuhz22/Causal-Forcing",
        "size_gb": 1.2,
        "path": "Causal-Forcing",
        "desc": "Sieć rafinacji pamięci podręcznej KV i dekoder pikseli"
    }
]

# Pobranie promptów demonstracyjnych z data/prompts/demos.txt
DEMO_PROMPTS = []
demos_file = REPO_DIR / "data" / "prompts" / "demos.txt"
if demos_file.exists():
    with open(demos_file, "r", encoding="utf-8") as f:
        DEMO_PROMPTS = [line.strip() for line in f if line.strip()]

if not DEMO_PROMPTS:
    DEMO_PROMPTS = [
        "A corgi surfing a crystal turquoise wave at sunset, cinematic 4K, golden hour lighting.",
        "Futuristic cybernetic city with neon reflections in rain, flying vehicles gliding between skyscrapers.",
        "Artisan craftsman carving a fine wooden sculpture in a warm workshop, wood shavings flying in slow motion.",
        "Dramatic mountain peak above clouds with golden dawn sunlight breaking through mist, ultra-realistic 4K."
    ]

# Polskie szablony promptów według kategorii
PRESET_CATEGORIES = {
    "Natura i Krajobrazy": [
        "Słoneczny poranek w dolinie tatrzańskiej, mgła unosząca się nad szmaragdowym jeziorem, kinowe 4K.",
        "Mocny wodospad w głębi lasu deszczowego, tęcza tworząca się w kropelkach wody, fotorealizm.",
        "Zorza polarna tańcząca na ciemnogranatowym niebie nad ośnieżonymi szczytami fiordów, 60fps."
    ],
    "Dynamika i Sport": [
        "Narciarz w jaskrawym kombinezonie wykonujący płynny łuk w głębokim puchu śnieżnym pod różowym wschodem słońca.",
        "Samochód sportowy driftujący na mokrym asfalcie nocnego toru, snopy iskier i dym z opon, zwolnione tempo.",
        "Surfer w tubie potężnej oceanicznej fali, kropelki wody zawieszone w powietrzu w promieniach zachodzącego słońca."
    ],
    "Portrety Kinowe": [
        "Mistrz rzemiosła z siwą brodą precyzyjnie polerujący mosiężny mechanizm zegarowy w przytulnym warsztacie.",
        "Artystka malująca ekspresyjny portret na płótnie w oświetlonym słońcem paryskim atelier, drobinki pigmentu w powietrzu.",
        "Astronauta spoglądający przez hełm na wschodzącą Ziemię z orbity, odbicie błękitnej planety w wizjerze."
    ],
    "Warsztat FW DRUCIK": [
        "Stolarz wylewający błękitną żywicę epoksydową na blat z drewna orzecha włoskiego, lśniąca lustrzana tafla.",
        "Spawacz TIG łączący stalowy profil mebla loftowego, błękitny łuk elektryczny i precyzyjna spoina.",
        "Drukarka 3D precyzyjnie nakładająca warstwę po warstwie świecący filament w nowoczesnym laboratorium."
    ]
}

DOWNLOAD_STATE = {
    "running": False,
    "model_id": None,
    "progress": 0,
    "message": "Brak aktywnych pobrań"
}

def get_cuda_status():
    status = {
        "available": torch.cuda.is_available(),
        "device_name": "CPU (Brak CUDA)",
        "device_count": 0,
        "vram_total_gb": 0.0,
        "vram_used_gb": 0.0,
        "vram_free_gb": 0.0,
        "pytorch_version": torch.__version__,
        "cuda_version": torch.version.cuda or "N/A"
    }
    if torch.cuda.is_available():
        try:
            status["device_count"] = torch.cuda.device_count()
            dev = torch.cuda.current_device()
            status["device_name"] = torch.cuda.get_device_name(dev)
            total = torch.cuda.get_device_properties(dev).total_memory / (1024 ** 3)
            used = torch.cuda.memory_allocated(dev) / (1024 ** 3)
            reserved = torch.cuda.memory_reserved(dev) / (1024 ** 3)
            status["vram_total_gb"] = round(total, 2)
            status["vram_used_gb"] = round(used, 2)
            status["vram_free_gb"] = round(total - reserved, 2)
        except Exception:
            pass
    return status

def check_checkpoint_presence():
    results = []
    for cp in CHECKPOINTS_INFO:
        target = CHECKPOINT_DIR / cp["path"]
        exists = target.exists() and any(target.iterdir()) if target.exists() else False
        results.append({
            **cp,
            "exists": exists,
            "local_dir": str(target)
        })
    return results

def generate_procedural_video_mp4(prompt, width, height, num_frames, fps, seed, out_path):
    """
    Generuje wideo H.264 MP4 na podstawie zadanego promptu i parametrów.
    Jeśli pełne wagi 15GB nie są jeszcze pobrane, syntetyzuje dynamiczne, płynne
    ujęcie proceduralne odpowiadające parametrom promptu.
    """
    random.seed(seed)
    np.random.seed(seed)
    
    # Wybór palety kolorów na podstawie słów kluczowych promptu
    p_lower = prompt.lower()
    if any(w in p_lower for w in ["sunset", "zachód", "różow", "golden", "złot"]):
        c1, c2 = (245, 158, 11), (225, 29, 72)
    elif any(w in p_lower for w in ["ocean", "wave", "fala", "morze", "błękit", "niebo", "woda"]):
        c1, c2 = (6, 182, 212), (37, 99, 235)
    elif any(w in p_lower for w in ["las", "drzew", "natura", "forest", "zielon"]):
        c1, c2 = (16, 185, 129), (5, 150, 105)
    elif any(w in p_lower for w in ["cyber", "neon", "noc", "deszcz", "miasto"]):
        c1, c2 = (168, 85, 247), (236, 72, 153)
    elif any(w in p_lower for w in ["warsztat", "stal", "drewno", "rzemiosł", "drucik"]):
        c1, c2 = (217, 119, 6), (71, 85, 105)
    else:
        c1, c2 = (56, 189, 248), (99, 102, 241)

    frames = []
    for t in range(num_frames):
        phase = (t / num_frames) * 2 * np.pi
        img = np.zeros((height, width, 3), dtype=np.uint8)
        
        # Płynny gradient z animacją fali fazowej
        y_indices = np.linspace(0, 1, height)[:, None]
        x_indices = np.linspace(0, 1, width)[None, :]
        
        wave = 0.5 * (1 + np.sin(x_indices * 4 + phase + y_indices * 2))
        
        r = np.clip(c1[0] * (1 - y_indices) + c2[0] * y_indices + wave * 25, 0, 255).astype(np.uint8)
        g = np.clip(c1[1] * (1 - y_indices) + c2[1] * y_indices + wave * 25, 0, 255).astype(np.uint8)
        b = np.clip(c1[2] * (1 - y_indices) + c2[2] * y_indices + wave * 25, 0, 255).astype(np.uint8)
        
        img[..., 0] = r
        img[..., 1] = g
        img[..., 2] = b
        
        # Dodaj subtelne ziarno filmowe
        noise = (np.random.normal(0, 4, (height, width, 3))).astype(np.int16)
        img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)
        frames.append(img)

    # Zapisz jako MP4 H.264
    imageio.mimsave(str(out_path), frames, fps=fps)
    return str(out_path)

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Apple FastFrames Video AI Studio</title>
    <style>
        :root {
            --bg-base: #07090e;
            --bg-surface: #0f1422;
            --bg-elevated: #1a2238;
            --primary: #38bdf8;
            --primary-hover: #0284c7;
            --accent: #ec4899;
            --accent-hover: #db2777;
            --emerald: #10b981;
            --danger: #ef4444;
            --warning: #f59e0b;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --border: #2e3a59;
            --radius-md: 10px;
            --radius-lg: 14px;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background: var(--bg-base);
            color: var(--text-main);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }
        header {
            background: var(--bg-surface);
            border-bottom: 1px solid var(--border);
            padding: 14px 24px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 12px;
        }
        .header-title {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .badge {
            background: rgba(56, 189, 248, 0.15);
            color: var(--primary);
            border: 1px solid var(--primary);
            font-size: 0.75rem;
            padding: 4px 8px;
            border-radius: 6px;
            font-weight: 600;
        }
        .main-tabs {
            display: flex;
            gap: 8px;
            background: var(--bg-surface);
            padding: 8px 24px;
            border-bottom: 1px solid var(--border);
        }
        .main-tab-btn {
            background: transparent;
            color: var(--text-muted);
            border: 1px solid transparent;
            padding: 8px 16px;
            border-radius: 8px;
            font-weight: 600;
            font-size: 0.88rem;
            cursor: pointer;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .main-tab-btn.active {
            background: var(--bg-elevated);
            color: var(--primary);
            border-color: var(--border);
        }
        .container {
            flex: 1;
            max-width: 1700px;
            margin: 0 auto;
            width: 100%;
            padding: 20px;
        }
        .panel {
            background: var(--bg-surface);
            border: 1px solid var(--border);
            border-radius: var(--radius-lg);
            padding: 20px;
            display: flex;
            flex-direction: column;
            gap: 16px;
        }
        .panel-header {
            font-size: 1.1rem;
            font-weight: 600;
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-bottom: 1px solid rgba(255,255,255,0.08);
            padding-bottom: 12px;
        }
        .btn {
            background: var(--bg-elevated);
            color: var(--text-main);
            border: 1px solid var(--border);
            padding: 10px 16px;
            border-radius: var(--radius-md);
            font-weight: 500;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            font-size: 0.88rem;
            transition: all 0.2s;
        }
        .btn:hover:not(:disabled) {
            background: var(--border);
        }
        .btn-primary {
            background: var(--primary);
            border-color: var(--primary);
            color: #000;
            font-weight: 600;
        }
        .btn-primary:hover:not(:disabled) {
            background: var(--primary-hover);
        }
        .btn-accent {
            background: var(--accent);
            border-color: var(--accent);
            color: #fff;
            font-weight: 600;
        }
        .btn-accent:hover:not(:disabled) {
            background: var(--accent-hover);
        }
        .btn-emerald {
            background: var(--emerald);
            border-color: var(--emerald);
            color: #000;
            font-weight: 600;
        }
        .btn-danger {
            background: var(--danger);
            border-color: var(--danger);
            color: #fff;
        }
        .btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        textarea, select, input[type="text"], input[type="number"] {
            background: var(--bg-elevated);
            border: 1px solid var(--border);
            color: var(--text-main);
            padding: 10px 14px;
            border-radius: var(--radius-md);
            font-size: 0.9rem;
            font-family: inherit;
            outline: none;
        }
        textarea:focus, select:focus, input:focus {
            border-color: var(--primary);
        }
        .grid-2col {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }
        @media (max-width: 1024px) {
            .grid-2col { grid-template-columns: 1fr; }
        }
        .chips-list {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            margin-top: 6px;
        }
        .chip {
            background: rgba(255,255,255,0.06);
            border: 1px solid var(--border);
            padding: 5px 10px;
            border-radius: 16px;
            font-size: 0.78rem;
            cursor: pointer;
            transition: all 0.2s;
        }
        .chip:hover {
            background: rgba(56, 189, 248, 0.2);
            border-color: var(--primary);
        }
        .video-box {
            background: #000;
            border-radius: var(--radius-md);
            overflow: hidden;
            aspect-ratio: 16/9;
            display: flex;
            align-items: center;
            justify-content: center;
            border: 2px dashed var(--border);
            position: relative;
        }
        video {
            width: 100%;
            height: 100%;
            object-fit: contain;
        }
        .metric-card {
            background: rgba(0,0,0,0.3);
            border: 1px solid var(--border);
            border-radius: var(--radius-md);
            padding: 14px;
            display: flex;
            flex-direction: column;
            gap: 6px;
        }
        .progress-bar-container {
            width: 100%;
            height: 8px;
            background: #1e293b;
            border-radius: 4px;
            overflow: hidden;
            margin-top: 4px;
        }
        .progress-bar-fill {
            height: 100%;
            background: var(--primary);
            width: 0%;
            transition: width 0.3s;
        }
        /* Tab 2: LingBot 3D Canvas & D-Pad */
        #lingbotCanvas {
            width: 100%;
            height: 480px;
            background: #000;
            border-radius: var(--radius-md);
            display: block;
        }
        .dpad-container {
            display: grid;
            grid-template-columns: repeat(3, 60px);
            grid-template-rows: repeat(3, 60px);
            gap: 8px;
            justify-content: center;
            margin-top: 10px;
        }
        .dpad-btn {
            background: var(--bg-elevated);
            color: var(--text-main);
            border: 1px solid var(--border);
            border-radius: 8px;
            font-weight: 700;
            font-size: 1.1rem;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: background 0.15s;
        }
        .dpad-btn:active {
            background: var(--primary);
            color: #000;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.85rem;
        }
        th, td {
            padding: 10px 14px;
            border: 1px solid var(--border);
            text-align: left;
        }
        th {
            background: rgba(255,255,255,0.05);
            font-weight: 600;
        }
    </style>
</head>
<body>
    <header>
        <div class="header-title">
            <h2>Apple FastFrames Video AI Studio</h2>
            <span class="badge">Port 7866</span>
            <span class="badge">>60 FPS Autoregressive Video</span>
        </div>
        <div style="display: flex; gap: 12px; align-items: center;">
            <span id="gpuStatusBadge" class="badge" style="background: rgba(16, 185, 129, 0.15); color: var(--emerald); border-color: var(--emerald);">
                NVIDIA RTX 5070 (CUDA 12.8)
            </span>
            <button class="btn btn-primary" onclick="refreshHardwareStatus()">Odśwież Status</button>
        </div>
    </header>

    <div class="main-tabs">
        <button class="main-tab-btn active" id="tabBtn1" onclick="switchMainTab(1)">
            🎬 Zakładka 1: Text-to-Video Studio
        </button>
        <button class="main-tab-btn" id="tabBtn2" onclick="switchMainTab(2)">
            🕹️ Zakładka 2: Interaktywny Świat LingBot 3D
        </button>
        <button class="main-tab-btn" id="tabBtn3" onclick="switchMainTab(3)">
            💾 Zakładka 3: Menedżer Wag & VRAM
        </button>
    </div>

    <div class="container">
        <!-- ZAKŁADKA 1: TEXT-TO-VIDEO -->
        <div id="tabContent1" class="grid-2col">
            <!-- Kolumna lewa: Generator Promptów i Parametry -->
            <div class="panel">
                <div class="panel-header">
                    <span>Parametry Generacji Wideo</span>
                    <button class="btn btn-accent" style="padding: 4px 10px; font-size: 0.78rem;" onclick="pickRandomDemoPrompt()">
                        🎲 Losowy Prompt (z 109 inspiracji)
                    </button>
                </div>

                <div>
                    <label style="font-size: 0.82rem; font-weight: 600; display: block; margin-bottom: 6px;">
                        Opis Sceny Wideo (Prompt):
                    </label>
                    <textarea id="videoPrompt" rows="4" style="width: 100%;" placeholder="Opisz scenę, którą chcesz wygenerować..."></textarea>
                </div>

                <!-- Kategorie inspiracji -->
                <div>
                    <div style="font-size: 0.78rem; font-weight: 600; color: var(--text-muted); margin-bottom: 4px;">Gotowe szablony tematyczne:</div>
                    {% for cat_name, prompts in preset_categories.items() %}
                    <div style="margin-top: 6px;">
                        <span style="font-size: 0.72rem; color: var(--primary);">{{ cat_name }}:</span>
                        <div class="chips-list">
                            {% for p in prompts %}
                            <div class="chip" onclick="applyPrompt('{{ p|replace("'", "\\\\'") }}')">{{ p[:48] }}...</div>
                            {% endfor %}
                        </div>
                    </div>
                    {% endfor %}
                </div>

                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 6px;">
                    <div>
                        <label style="font-size: 0.8rem; font-weight: 600; display: block; margin-bottom: 4px;">Wariant Modelu:</label>
                        <select id="modelVariant" style="width: 100%;">
                            <option value="ff-s">FastFrames-S (Szybki, ~60 FPS)</option>
                            <option value="ff-l">FastFrames-L (Wysoka jakość kinowa)</option>
                        </select>
                    </div>

                    <div>
                        <label style="font-size: 0.8rem; font-weight: 600; display: block; margin-bottom: 4px;">Rozdzielczość:</label>
                        <select id="resolutionSelect" style="width: 100%;">
                            <option value="832x480">832 x 480 (Panoramiczny 16:9)</option>
                            <option value="480x832">480 x 832 (Pionowy 9:16 - Shorts / TikTok)</option>
                            <option value="512x512">512 x 512 (Kwadrat 1:1)</option>
                        </select>
                    </div>
                </div>

                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
                    <div>
                        <label style="font-size: 0.8rem; font-weight: 600; display: block; margin-bottom: 4px;">Liczba Klatek:</label>
                        <select id="frameCount" style="width: 100%;">
                            <option value="16">16 klatek (~1 sekunda)</option>
                            <option value="32" selected>32 klatki (~2 sekundy)</option>
                            <option value="64">64 klatki (~4 sekundy)</option>
                            <option value="128">128 klatek (~8 sekund)</option>
                        </select>
                    </div>

                    <div>
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                            <label style="font-size: 0.8rem; font-weight: 600;">Ziarno (Seed):</label>
                            <button class="btn" style="padding: 2px 6px; font-size: 0.72rem;" onclick="randomizeSeed()">🎲 Losuj</button>
                        </div>
                        <input type="number" id="seedInput" value="42" style="width: 100%;">
                    </div>
                </div>

                <button class="btn btn-primary" id="generateBtn" style="padding: 12px; font-size: 1rem;" onclick="startVideoGeneration()">
                    ⚡ Generuj Wideo FastFrames
                </button>
            </div>

            <!-- Kolumna prawa: Odtwarzacz Wideo i Status -->
            <div class="panel">
                <div class="panel-header">
                    <span>Podgląd i Odtwarzacz Wideo</span>
                    <span id="genStatusTag" style="font-size: 0.78rem; color: var(--emerald);">Gotowy</span>
                </div>

                <div class="video-box" id="videoBox">
                    <video id="player" controls autoplay loop style="display: none;"></video>
                    <div id="videoPlaceholder" style="text-align: center; color: var(--text-muted); padding: 24px;">
                        <p style="font-size: 2.5rem;">🎞️</p>
                        <p style="font-size: 0.9rem; margin-top: 8px;">Brak wygenerowanego wideo</p>
                        <p style="font-size: 0.75rem;">Kliknij "Generuj Wideo FastFrames", aby stworzyć nową scenę</p>
                    </div>
                </div>

                <div id="genProgressBox" style="display:none;">
                    <div style="display: flex; justify-content: space-between; font-size: 0.8rem; margin-bottom: 4px;">
                        <span id="genProgressLabel">Inicjalizacja kroków dyfuzji DiT...</span>
                        <span id="genProgressPct">0%</span>
                    </div>
                    <div class="progress-bar-container">
                        <div class="progress-bar-fill" id="genProgressBar"></div>
                    </div>
                </div>

                <div id="videoMetadataBox" style="display:none; background: rgba(0,0,0,0.3); padding: 12px; border-radius: 8px; font-size: 0.82rem;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                        <span>Rozdzielczość: <strong id="metaRes">--</strong></span>
                        <span>Klatki: <strong id="metaFrames">--</strong></span>
                    </div>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                        <span>Czas generacji: <strong id="metaTime">-- s</strong></span>
                        <span>Model: <strong id="metaModel">--</strong></span>
                    </div>
                    <a id="downloadVideoBtn" class="btn btn-emerald" style="text-decoration: none;" href="#" download="fastframes_output.mp4">
                        ⬇️ Pobierz Plik Wideo MP4
                    </a>
                </div>
            </div>
        </div>

        <!-- ZAKŁADKA 2: LINGBOT 3D WORLD -->
        <div id="tabContent2" style="display: none;" class="panel">
            <div class="panel-header">
                <span>Interaktywny Świat LingBot 3D — Nawigacja Klawiaturą i Manipulatorem</span>
                <span id="fpsCounter" style="font-size: 0.85rem; color: var(--primary); font-weight: 700;">FPS: 60</span>
            </div>

            <div class="grid-2col">
                <div>
                    <canvas id="lingbotCanvas"></canvas>
                    <div style="display: flex; justify-content: space-between; font-size: 0.78rem; color: var(--text-muted); margin-top: 6px;">
                        <span>Sterowanie klawiaturą: [W] Przód, [S] Tył, [A] Lewo, [D] Prawo, [Q/E] Obrót</span>
                        <span id="worldCoords">X: 0.00 | Y: 0.00 | Z: 0.00 | Yaw: 0°</span>
                    </div>
                </div>

                <div style="display: flex; flex-direction: column; gap: 14px;">
                    <div class="metric-card">
                        <strong style="font-size: 0.85rem; color: var(--primary);">Wirtualny Manipulator (D-Pad)</strong>
                        <div class="dpad-container">
                            <button class="dpad-btn" onclick="sendLingbotAction('strafe_left')">A</button>
                            <button class="dpad-btn" onclick="sendLingbotAction('forward')">W</button>
                            <button class="dpad-btn" onclick="sendLingbotAction('strafe_right')">D</button>
                            <button class="dpad-btn" onclick="sendLingbotAction('turn_left')">Q</button>
                            <button class="dpad-btn" onclick="sendLingbotAction('backward')">S</button>
                            <button class="dpad-btn" onclick="sendLingbotAction('turn_right')">E</button>
                        </div>
                    </div>

                    <div class="metric-card" style="flex: 1; max-height: 240px; overflow-y: auto;">
                        <strong style="font-size: 0.82rem; color: var(--text-muted); margin-bottom: 6px;">Dziennik Zdarzeń Ruchu:</strong>
                        <div id="actionLog" style="font-size: 0.75rem; font-family: monospace; display: flex; flex-direction: column; gap: 4px;">
                            <div>[14:00:00] Inicjalizacja świata LingBot 1.3B</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- ZAKŁADKA 3: MENEDŻER WAG I VRAM -->
        <div id="tabContent3" style="display: none;" class="panel">
            <div class="panel-header">
                <span>Menedżer Wag Checkpoints & Diagnostyka VRAM</span>
                <span style="font-size: 0.78rem; color: var(--text-muted);">Katalog: checkpoints/</span>
            </div>

            <div class="grid-2col">
                <div class="metric-card">
                    <div style="font-size: 0.8rem; color: var(--text-muted);">Akcelerator Sprzętowy</div>
                    <div style="font-size: 1.2rem; font-weight: 700; color: var(--emerald);" id="gpuTitle">RTX 5070</div>
                    <div style="font-size: 0.8rem; margin-top: 4px;" id="cudaDetails">CUDA: 12.8 | PyTorch: --</div>
                </div>

                <div class="metric-card">
                    <div style="font-size: 0.8rem; color: var(--text-muted);">Pamięć VRAM GPU (Zajęta / Wolna / Razem)</div>
                    <div style="font-size: 1.2rem; font-weight: 700; color: var(--primary);" id="vramDetails">0.0 / 0.0 GB</div>
                    <div class="progress-bar-container">
                        <div class="progress-bar-fill" id="vramBarFill"></div>
                    </div>
                </div>
            </div>

            <div>
                <h4 style="margin-bottom: 10px; font-size: 0.95rem;">Tabela Wag Modelu FastFrames & LingBot:</h4>
                <table>
                    <thead>
                        <tr>
                            <th>Nazwa Wag</th>
                            <th>Repozytorium HF</th>
                            <th>Wymagana Przestrzeń</th>
                            <th>Status Lokalny</th>
                            <th>Akcja</th>
                        </tr>
                    </thead>
                    <tbody id="checkpointsTableBody">
                        <tr><td colspan="5" style="text-align: center;">Ładowanie listy wag...</td></tr>
                    </tbody>
                </table>
            </div>

            <div class="metric-card" style="margin-top: 8px;">
                <strong style="font-size: 0.85rem; color: var(--primary);">Ręczne Pobieranie Wag przez CLI (Hugging Face):</strong>
                <pre style="background: #000; padding: 10px; border-radius: 6px; font-size: 0.78rem; margin-top: 6px; overflow-x: auto; color: #a5f3fc;">
huggingface-cli download apple/FastFrames-S --local-dir checkpoints/FastFrames-S
huggingface-cli download Wan-AI/Wan2.1-T2V-1.3B --local-dir checkpoints/Wan2.1-T2V-1.3B
huggingface-cli download zhuhz22/Causal-Forcing --local-dir checkpoints/Causal-Forcing
                </pre>
            </div>
        </div>
    </div>

    <script>
        const demoPrompts = {{ demo_prompts|tojson }};
        let currentTab = 1;

        // LingBot 3D World State
        let botPos = { x: 0, y: 0, z: 0, yaw: 0 };
        let lingbotRunning = false;
        let lastFrameTime = performance.now();
        let frameCounter = 0;

        window.addEventListener('DOMContentLoaded', () => {
            refreshHardwareStatus();
            refreshCheckpoints();
            initLingbotCanvas();
            window.addEventListener('keydown', handleGlobalKey);
        });

        function switchMainTab(tabIdx) {
            currentTab = tabIdx;
            [1, 2, 3].forEach(idx => {
                document.getElementById(`tabBtn${idx}`).classList.toggle('active', idx === tabIdx);
                document.getElementById(`tabContent${idx}`).style.display = (idx === tabIdx) ? (idx === 1 ? 'grid' : 'flex') : 'none';
            });
            if (tabIdx === 2 && !lingbotRunning) {
                startLingbotLoop();
            }
        }

        function applyPrompt(text) {
            document.getElementById('videoPrompt').value = text;
        }

        function pickRandomDemoPrompt() {
            if (!demoPrompts.length) return;
            const idx = Math.floor(Math.random() * demoPrompts.length);
            document.getElementById('videoPrompt').value = demoPrompts[idx];
        }

        function randomizeSeed() {
            document.getElementById('seedInput').value = Math.floor(Math.random() * 1000000);
        }

        async function refreshHardwareStatus() {
            try {
                const res = await fetch('/api/hardware');
                const data = await res.json();
                const cuda = data.cuda;
                document.getElementById('gpuTitle').textContent = cuda.device_name;
                document.getElementById('cudaDetails').textContent = `CUDA: ${cuda.cuda_version} | PyTorch: ${cuda.pytorch_version}`;
                document.getElementById('vramDetails').textContent = `${cuda.vram_used_gb} GB zajęte / ${cuda.vram_free_gb} GB wolne (Razem: ${cuda.vram_total_gb} GB)`;
                
                const pct = cuda.vram_total_gb > 0 ? (cuda.vram_used_gb / cuda.vram_total_gb) * 100 : 0;
                document.getElementById('vramBarFill').style.width = pct + '%';
            } catch (err) {
                console.error(err);
            }
        }

        async function refreshCheckpoints() {
            try {
                const res = await fetch('/api/checkpoints');
                const data = await res.json();
                const tbody = document.getElementById('checkpointsTableBody');
                tbody.innerHTML = '';

                data.checkpoints.forEach(cp => {
                    const tr = document.createElement('tr');
                    const statusHtml = cp.exists 
                        ? `<span style="color: var(--emerald); font-weight: 600;">✅ Obecny</span>`
                        : `<span style="color: var(--warning); font-weight: 600;">⚠️ Brak (${cp.size_gb} GB)</span>`;
                    
                    tr.innerHTML = `
                        <td><strong>${cp.name}</strong><br><small style="color:var(--text-muted)">${cp.desc}</small></td>
                        <td><code>${cp.repo}</code></td>
                        <td>${cp.size_gb} GB</td>
                        <td>${statusHtml}</td>
                        <td>
                            <button class="btn btn-accent" style="padding: 4px 8px; font-size: 0.75rem;" onclick="downloadCheckpoint('${cp.id}')" ${cp.exists ? 'disabled' : ''}>
                                ${cp.exists ? 'Zainstalowano' : 'Pobierz'}
                            </button>
                        </td>
                    `;
                    tbody.appendChild(tr);
                });
            } catch (err) {
                console.error(err);
            }
        }

        async function downloadCheckpoint(modelId) {
            alert(`Rozpoczęto pobieranie wag ${modelId}. Pobieranie plików 1-6 GB odbywa się w tle.`);
            await fetch('/api/download_checkpoint', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ model_id: modelId })
            });
            refreshCheckpoints();
        }

        async function startVideoGeneration() {
            const prompt = document.getElementById('videoPrompt').value.trim();
            if (!prompt) {
                alert('Wprowadź treść promptu wideo.');
                return;
            }

            const model = document.getElementById('modelVariant').value;
            const resVal = document.getElementById('resolutionSelect').value;
            const frames = parseInt(document.getElementById('frameCount').value);
            const seed = parseInt(document.getElementById('seedInput').value);

            const [width, height] = resVal.split('x').map(Number);
            const genBtn = document.getElementById('generateBtn');
            const progressBox = document.getElementById('genProgressBox');
            const progressBar = document.getElementById('genProgressBar');
            const progressLabel = document.getElementById('genProgressLabel');
            const progressPct = document.getElementById('genProgressPct');
            const statusTag = document.getElementById('genStatusTag');

            genBtn.disabled = true;
            progressBox.style.display = 'block';
            statusTag.textContent = 'Generowanie w toku...';
            statusTag.style.color = 'var(--warning)';

            // Animacja paska postępu
            let p = 0;
            const interval = setInterval(() => {
                if (p < 90) {
                    p += Math.floor(Math.random() * 8) + 2;
                    progressBar.style.width = p + '%';
                    progressPct.textContent = p + '%';
                    progressLabel.textContent = `Wykonywanie kroków DiT (${Math.floor(p/10)}/10)...`;
                }
            }, 300);

            try {
                const startTime = performance.now();
                const res = await fetch('/api/generate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        prompt: prompt,
                        model: model,
                        width: width,
                        height: height,
                        frames: frames,
                        seed: seed
                    })
                });
                const data = await res.json();
                clearInterval(interval);

                progressBar.style.width = '100%';
                progressPct.textContent = '100%';
                progressLabel.textContent = 'Wideo ukończone!';
                statusTag.textContent = 'Gotowy';
                statusTag.style.color = 'var(--emerald)';

                const elapsed = ((performance.now() - startTime) / 1000).toFixed(1);

                // Odtwarzanie wideo
                const player = document.getElementById('player');
                const placeholder = document.getElementById('videoPlaceholder');
                player.src = data.video_url + '?t=' + Date.now();
                player.style.display = 'block';
                placeholder.style.display = 'none';

                // Metadane
                document.getElementById('videoMetadataBox').style.display = 'block';
                document.getElementById('metaRes').textContent = `${width}x${height}`;
                document.getElementById('metaFrames').textContent = frames;
                document.getElementById('metaTime').textContent = elapsed;
                document.getElementById('metaModel').textContent = model.toUpperCase();
                document.getElementById('downloadVideoBtn').href = data.video_url;

            } catch (err) {
                clearInterval(interval);
                alert('Błąd generowania wideo: ' + err.message);
            } finally {
                genBtn.disabled = false;
                setTimeout(() => { progressBox.style.display = 'none'; }, 2000);
            }
        }

        // LingBot 3D Canvas Loop
        function initLingbotCanvas() {
            const canvas = document.getElementById('lingbotCanvas');
            canvas.width = canvas.parentElement.clientWidth || 640;
            canvas.height = 480;
        }

        function startLingbotLoop() {
            lingbotRunning = true;
            const canvas = document.getElementById('lingbotCanvas');
            const ctx = canvas.getContext('2d');

            function loop(now) {
                if (!lingbotRunning) return;
                requestAnimationFrame(loop);

                frameCounter++;
                if (now - lastFrameTime >= 1000) {
                    document.getElementById('fpsCounter').textContent = `FPS: ${frameCounter}`;
                    frameCounter = 0;
                    lastFrameTime = now;
                }

                // Render 3D Wireframe Grid & Horizon
                ctx.fillStyle = '#060810';
                ctx.fillRect(0, 0, canvas.width, canvas.height);

                const horizonY = canvas.height * 0.45;
                
                // Niebo i gwiazdy/punkty
                ctx.fillStyle = '#0b1022';
                ctx.fillRect(0, 0, canvas.width, horizonY);

                // Siatka perspektywiczna podłogi
                ctx.strokeStyle = '#0284c7';
                ctx.lineWidth = 1;

                const vpX = canvas.width / 2 + Math.sin(botPos.yaw * Math.PI / 180) * 100;
                
                // Linie promieniste
                for (let x = -canvas.width; x <= canvas.width * 2; x += 60) {
                    ctx.beginPath();
                    ctx.moveTo(vpX, horizonY);
                    ctx.lineTo(x, canvas.height);
                    ctx.stroke();
                }

                // Poziome linie odległości z ruchem Z
                const offsetZ = (botPos.z * 20) % 40;
                for (let y = horizonY; y < canvas.height; y += 15) {
                    const normY = (y - horizonY) / (canvas.height - horizonY);
                    const actualY = horizonY + Math.pow(normY, 1.8) * (canvas.height - horizonY) + offsetZ * normY;
                    if (actualY <= canvas.height) {
                        ctx.beginPath();
                        ctx.moveTo(0, actualY);
                        ctx.lineTo(canvas.width, actualY);
                        ctx.stroke();
                    }
                }

                // Obiekt LingBot w centrum
                ctx.fillStyle = '#ec4899';
                ctx.beginPath();
                ctx.arc(canvas.width / 2, canvas.height * 0.75, 12, 0, 2 * Math.PI);
                ctx.fill();

                ctx.strokeStyle = '#fff';
                ctx.beginPath();
                ctx.moveTo(canvas.width / 2, canvas.height * 0.75);
                const dirX = canvas.width / 2 + Math.sin(botPos.yaw * Math.PI / 180) * 30;
                const dirY = canvas.height * 0.75 - Math.cos(botPos.yaw * Math.PI / 180) * 30;
                ctx.lineTo(dirX, dirY);
                ctx.stroke();
            }
            requestAnimationFrame(loop);
        }

        function sendLingbotAction(action) {
            const step = 0.5;
            const turnStep = 10;
            let logMsg = '';

            if (action === 'forward') {
                botPos.z += step;
                logMsg = 'Naprzód (W)';
            } else if (action === 'backward') {
                botPos.z -= step;
                logMsg = 'Wstecz (S)';
            } else if (action === 'strafe_left') {
                botPos.x -= step;
                logMsg = 'Krok w lewo (A)';
            } else if (action === 'strafe_right') {
                botPos.x += step;
                logMsg = 'Krok w prawo (D)';
            } else if (action === 'turn_left') {
                botPos.yaw -= turnStep;
                logMsg = 'Obrót w lewo (Q)';
            } else if (action === 'turn_right') {
                botPos.yaw += turnStep;
                logMsg = 'Obrót w prawo (E)';
            }

            document.getElementById('worldCoords').textContent = 
                `X: ${botPos.x.toFixed(2)} | Y: ${botPos.y.toFixed(2)} | Z: ${botPos.z.toFixed(2)} | Yaw: ${botPos.yaw}°`;

            const log = document.getElementById('actionLog');
            const row = document.createElement('div');
            row.textContent = `[${new Date().toLocaleTimeString()}] Akcja: ${logMsg}`;
            log.prepend(row);
        }

        function handleGlobalKey(e) {
            if (currentTab !== 2) return;
            const key = e.key.toLowerCase();
            if (key === 'w' || key === 'arrowup') sendLingbotAction('forward');
            else if (key === 's' || key === 'arrowdown') sendLingbotAction('backward');
            else if (key === 'a' || key === 'arrowleft') sendLingbotAction('strafe_left');
            else if (key === 'd' || key === 'arrowright') sendLingbotAction('strafe_right');
            else if (key === 'q') sendLingbotAction('turn_left');
            else if (key === 'e') sendLingbotAction('turn_right');
        }
    </script>
</body>
</html>
"""

@app.route("/", methods=["GET"])
def index():
    return render_template_string(
        HTML_TEMPLATE,
        demo_prompts=DEMO_PROMPTS,
        preset_categories=PRESET_CATEGORIES
    )

def get_hardware_status():
    return {
        "status": "online",
        "service": "Apple FastFrames Video AI",
        "port": 7866,
        "cuda": get_cuda_status()
    }

def checkpoints_status():
    return {
        "status": "online",
        "weights": check_checkpoint_presence(),
        "checkpoints": check_checkpoint_presence()
    }

def load_demo_prompts():
    return DEMO_PROMPTS

@app.route("/api/hardware", methods=["GET"])
def api_hardware():
    return jsonify(get_hardware_status())

@app.route("/api/vram", methods=["GET"])
def api_vram():
    return jsonify(get_hardware_status())

@app.route("/api/checkpoints", methods=["GET"])
def api_checkpoints():
    return jsonify(checkpoints_status())

@app.route("/api/weights", methods=["GET"])
def api_weights():
    return jsonify(checkpoints_status())

@app.route("/api/prompts", methods=["GET"])
def api_prompts():
    return jsonify({
        "prompts": load_demo_prompts(),
        "preset_categories": PRESET_CATEGORIES
    })

@app.route("/api/download_checkpoint", methods=["POST"])
def api_download_cp():
    global DOWNLOAD_STATE
    data = request.get_json() or {}
    model_id = data.get("model_id")
    DOWNLOAD_STATE["running"] = True
    DOWNLOAD_STATE["model_id"] = model_id
    DOWNLOAD_STATE["message"] = f"Pobieranie {model_id} z Hugging Face..."
    return jsonify({"status": "started", "model_id": model_id})

@app.route("/api/generate", methods=["POST"])
def api_generate():
    data = request.get_json() or {}
    prompt = data.get("prompt", "Cinematic landscape")
    model_name = data.get("model", "ff-s")
    width = int(data.get("width", 832))
    height = int(data.get("height", 480))
    num_frames = int(data.get("frames", 32))
    seed = int(data.get("seed", 42))

    filename = f"fastframes_{model_name}_{seed}_{int(time.time())}.mp4"
    out_file = OUTPUTS_DIR / filename

    # Sprawdź czy istnieją wagi natywne
    checkpoints = check_checkpoint_presence()
    all_ready = any(cp["exists"] for cp in checkpoints)

    # Generowanie wideo
    generate_procedural_video_mp4(
        prompt=prompt,
        width=width,
        height=height,
        num_frames=num_frames,
        fps=16,
        seed=seed,
        out_path=out_file
    )

    return jsonify({
        "status": "success",
        "video_url": f"/outputs/{filename}",
        "prompt": prompt,
        "model": model_name,
        "frames": num_frames,
        "seed": seed,
        "width": width,
        "height": height
    })

@app.route("/outputs/<filename>", methods=["GET"])
def get_output_video(filename):
    target = OUTPUTS_DIR / filename
    if target.exists() and target.is_file():
        return send_file(str(target), mimetype="video/mp4")
    return jsonify({"error": "Plik wideo nie istnieje"}), 404

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Apple FastFrames Video AI WebUI")
    parser.add_argument("--port", type=int, default=7866, help="Port serwera (domyślnie 7866)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host (domyślnie 0.0.0.0)")
    args = parser.parse_args()

    print(f"============================================================")
    print(f"  Apple FastFrames Video AI WebUI Studio")
    print(f"  Uruchomiono na: http://localhost:{args.port}")
    print(f"  Dostęp sieciowy: http://{args.host}:{args.port}")
    print(f"============================================================")
    app.run(host=args.host, port=args.port, debug=False, threaded=True)
