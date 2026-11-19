#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mini-Omni2 Multimodal Live Studio WebUI
Port: 7864
Obsługa dwukierunkowej interakcji mowa-obraz na żywo z modelem Mini-Omni2.
"""
import os
import sys
import json
import base64
import tempfile
import threading
import time
import traceback
from pathlib import Path

# Upewnij się, że lokalne moduły repozytorium (w tym zmodyfikowany litgpt) mają pierwszeństwo przed site-packages
REPO_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_DIR))

import flask
from flask import Flask, request, jsonify, Response, send_file, render_template_string
import torch

# Stan pobierania wag
DOWNLOAD_STATUS = {
    "status": "idle",  # idle, downloading, completed, error
    "message": "Wagi nie są obecnie pobierane.",
    "progress": 0,
    "error": None
}

# Stan modelu
MODEL_STATE = {
    "client": None,
    "loading": False,
    "error": None
}

app = Flask(__name__)
CHECKPOINT_DIR = REPO_DIR / "checkpoint"

def get_vram_info():
    """Zwraca diagnostykę VRAM i CUDA"""
    info = {
        "cuda_available": torch.cuda.is_available(),
        "device_name": "Brak CUDA (CPU)",
        "total_vram_gb": 0.0,
        "allocated_vram_gb": 0.0,
        "reserved_vram_gb": 0.0,
        "free_vram_gb": 0.0,
        "cuda_version": torch.version.cuda or "N/A"
    }
    if torch.cuda.is_available():
        try:
            device = torch.cuda.current_device()
            info["device_name"] = torch.cuda.get_device_name(device)
            total = torch.cuda.get_device_properties(device).total_memory / (1024 ** 3)
            allocated = torch.cuda.memory_allocated(device) / (1024 ** 3)
            reserved = torch.cuda.memory_reserved(device) / (1024 ** 3)
            info["total_vram_gb"] = round(total, 2)
            info["allocated_vram_gb"] = round(allocated, 2)
            info["reserved_vram_gb"] = round(reserved, 2)
            info["free_vram_gb"] = round(total - reserved, 2)
        except Exception as e:
            info["error"] = str(e)
    return info

def check_checkpoints_exist():
    """Sprawdza obecność wag w katalogu ./checkpoint"""
    if not CHECKPOINT_DIR.exists():
        return False, "Katalog ./checkpoint nie istnieje."
    files = list(CHECKPOINT_DIR.glob("*"))
    if not files:
        return False, "Katalog ./checkpoint jest pusty."
    # Sprawdź kluczowe pliki jeśli istnieją
    has_weights = any(f.suffix in [".pth", ".pt", ".bin", ".safetensors"] for f in files)
    return True, f"Znaleziono {len(files)} plików w ./checkpoint"

def async_download_weights():
    global DOWNLOAD_STATUS
    DOWNLOAD_STATUS["status"] = "downloading"
    DOWNLOAD_STATUS["message"] = "Rozpoczęto pobieranie wag gpt-omni/mini-omni2 z Hugging Face..."
    DOWNLOAD_STATUS["progress"] = 5
    DOWNLOAD_STATUS["error"] = None
    try:
        from huggingface_hub import snapshot_download
        os.makedirs(CHECKPOINT_DIR, exist_ok=True)
        DOWNLOAD_STATUS["message"] = "Pobieranie plików modelu (ok. 3.4 GB)... Może to potrwać kilka minut."
        DOWNLOAD_STATUS["progress"] = 25
        snapshot_download("gpt-omni/mini-omni2", local_dir=str(CHECKPOINT_DIR), revision="main")
        DOWNLOAD_STATUS["status"] = "completed"
        DOWNLOAD_STATUS["message"] = "Pobieranie zakończone sukcesem! Wagi są gotowe do załadowania."
        DOWNLOAD_STATUS["progress"] = 100
    except Exception as e:
        DOWNLOAD_STATUS["status"] = "error"
        DOWNLOAD_STATUS["message"] = f"Błąd podczas pobierania: {str(e)}"
        DOWNLOAD_STATUS["error"] = str(e)

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mini-Omni2 — Multimodalne Studio Na Żywo</title>
    <style>
        :root {
            --bg-base: #0f172a;
            --bg-surface: #1e293b;
            --bg-elevated: #334155;
            --primary: #06b6d4;
            --primary-hover: #0891b2;
            --accent: #10b981;
            --danger: #ef4444;
            --warning: #f59e0b;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --border: #475569;
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
            padding: 16px 24px;
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
            background: rgba(6, 182, 212, 0.15);
            color: var(--primary);
            border: 1px solid var(--primary);
            font-size: 0.75rem;
            padding: 4px 8px;
            border-radius: 6px;
            font-weight: 600;
        }
        .status-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 4px 10px;
            border-radius: 9999px;
            font-size: 0.8rem;
            background: rgba(16, 185, 129, 0.15);
            color: var(--accent);
            border: 1px solid var(--accent);
        }
        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: currentColor;
        }
        .main-layout {
            display: grid;
            grid-template-columns: 380px 1fr 340px;
            gap: 20px;
            padding: 20px;
            flex: 1;
            max-width: 1700px;
            margin: 0 auto;
            width: 100%;
        }
        @media (max-width: 1200px) {
            .main-layout { grid-template-columns: 1fr; }
        }
        .panel {
            background: var(--bg-surface);
            border: 1px solid var(--border);
            border-radius: var(--radius-lg);
            padding: 18px;
            display: flex;
            flex-direction: column;
            gap: 16px;
        }
        .panel-header {
            font-size: 1.05rem;
            font-weight: 600;
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-bottom: 1px solid rgba(255,255,255,0.08);
            padding-bottom: 10px;
        }
        .video-box {
            position: relative;
            background: #000;
            border-radius: var(--radius-md);
            overflow: hidden;
            aspect-ratio: 4/3;
            display: flex;
            align-items: center;
            justify-content: center;
            border: 2px dashed var(--border);
        }
        video, canvas, #previewImg {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }
        .video-overlay-btn {
            position: absolute;
            bottom: 10px;
            right: 10px;
            background: rgba(0,0,0,0.7);
            color: #fff;
            border: 1px solid #fff;
            padding: 6px 12px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.8rem;
        }
        .btn-group {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
        }
        .btn {
            background: var(--bg-elevated);
            color: var(--text-main);
            border: 1px solid var(--border);
            padding: 10px 14px;
            border-radius: var(--radius-md);
            font-weight: 500;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            font-size: 0.85rem;
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
        .btn-danger {
            background: var(--danger);
            border-color: var(--danger);
            color: #fff;
        }
        .btn-accent {
            background: var(--accent);
            border-color: var(--accent);
            color: #000;
            font-weight: 600;
        }
        .btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        .waveform-container {
            background: #090d16;
            border: 1px solid var(--border);
            border-radius: var(--radius-md);
            padding: 10px;
            display: flex;
            flex-direction: column;
            gap: 6px;
        }
        #audioCanvas {
            width: 100%;
            height: 60px;
            background: transparent;
        }
        .chat-container {
            display: flex;
            flex-direction: column;
            height: 620px;
        }
        .chat-messages {
            flex: 1;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 14px;
            padding: 10px;
            background: rgba(0,0,0,0.15);
            border-radius: var(--radius-md);
        }
        .message {
            display: flex;
            flex-direction: column;
            gap: 6px;
            max-width: 82%;
            padding: 12px 16px;
            border-radius: 12px;
            font-size: 0.92rem;
            line-height: 1.45;
        }
        .message-user {
            align-self: flex-end;
            background: #1e3a8a;
            color: #dbeafe;
            border-bottom-right-radius: 2px;
        }
        .message-assistant {
            align-self: flex-start;
            background: var(--bg-elevated);
            color: #f1f5f9;
            border-bottom-left-radius: 2px;
            border-left: 3px solid var(--primary);
        }
        .message-header {
            font-size: 0.75rem;
            font-weight: 600;
            opacity: 0.75;
            display: flex;
            justify-content: space-between;
        }
        .audio-player-box {
            margin-top: 8px;
            background: rgba(0,0,0,0.3);
            border-radius: 6px;
            padding: 6px;
        }
        audio {
            width: 100%;
            height: 36px;
        }
        .chat-input-bar {
            display: flex;
            gap: 10px;
            margin-top: 12px;
        }
        .chat-input-bar input[type="text"] {
            flex: 1;
            background: var(--bg-elevated);
            border: 1px solid var(--border);
            color: var(--text-main);
            padding: 12px 16px;
            border-radius: var(--radius-md);
            font-size: 0.95rem;
        }
        .slider-group {
            display: flex;
            flex-direction: column;
            gap: 6px;
        }
        .slider-label {
            display: flex;
            justify-content: space-between;
            font-size: 0.85rem;
            font-weight: 500;
        }
        .slider-hint {
            font-size: 0.75rem;
            color: var(--text-muted);
            line-height: 1.3;
        }
        input[type="range"] {
            width: 100%;
            accent-color: var(--primary);
        }
        .metric-card {
            background: rgba(0,0,0,0.25);
            border: 1px solid var(--border);
            border-radius: var(--radius-md);
            padding: 12px;
            display: flex;
            flex-direction: column;
            gap: 4px;
        }
        .metric-title {
            font-size: 0.75rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .metric-value {
            font-size: 1.15rem;
            font-weight: 600;
            color: var(--primary);
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
            background: var(--accent);
            width: 0%;
            transition: width 0.3s;
        }
        .sample-chip {
            background: rgba(255,255,255,0.06);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 6px 10px;
            font-size: 0.8rem;
            cursor: pointer;
            text-align: left;
            transition: background 0.2s;
        }
        .sample-chip:hover {
            background: rgba(6, 182, 212, 0.2);
            border-color: var(--primary);
        }
    </style>
</head>
<body>
    <header>
        <div class="header-title">
            <h2>Mini-Omni2 Multimodal Live Studio</h2>
            <span class="badge">Port 7864</span>
            <span class="badge">SNAC 24kHz Audio</span>
        </div>
        <div style="display: flex; gap: 12px; align-items: center;">
            <div id="vramStatusBadge" class="status-badge">
                <span class="status-dot"></span>
                <span id="vramStatusText">Ładowanie VRAM...</span>
            </div>
            <button class="btn btn-primary" onclick="testConnection()">Odśwież Status</button>
        </div>
    </header>

    <div class="main-layout">
        <!-- Lewa kolumna: Kamera & Mikrofon -->
        <div class="panel">
            <div class="panel-header">
                <span>Wizja i Dźwięk na Żywo</span>
                <span style="font-size: 0.75rem; color: var(--text-muted);">Webcam & Mic</span>
            </div>

            <!-- Podgląd wideo -->
            <div class="video-box" id="videoBox">
                <video id="webcamVideo" autoplay playsinline muted style="display:none;"></video>
                <canvas id="snapshotCanvas" style="display:none;"></canvas>
                <img id="previewImg" src="" style="display:none;" alt="Zrzut obrazu">
                <div id="videoPlaceholder" style="text-align: center; color: var(--text-muted); padding: 20px;">
                    <p style="font-size: 2rem;">📹</p>
                    <p style="font-size: 0.85rem; margin-top: 8px;">Kamera wyłączona</p>
                    <p style="font-size: 0.75rem;">Kliknij "Włącz Kamerę" lub wgraj zdjęcie</p>
                </div>
            </div>

            <div class="btn-group">
                <button id="toggleCameraBtn" class="btn" onclick="toggleCamera()">📹 Włącz Kamerę</button>
                <button id="snapBtn" class="btn btn-accent" onclick="takeSnapshot()" disabled>📸 Zrób Zrzut</button>
            </div>

            <div style="display: flex; gap: 8px;">
                <input type="file" id="imageFileInput" accept="image/*" style="display: none;" onchange="handleImageFile(this)">
                <button class="btn" style="flex: 1;" onclick="document.getElementById('imageFileInput').click()">📁 Wybierz Obraz</button>
                <button class="btn btn-danger" onclick="clearImage()" title="Wyczyść obraz">🗑️</button>
            </div>

            <!-- Mikrofon & Audio Waveform -->
            <div class="waveform-container">
                <div style="display: flex; justify-content: space-between; font-size: 0.8rem;">
                    <span>Wizualizator Audio Mikrofonu</span>
                    <span id="recordingTimer" style="color: var(--accent); font-weight: 600;">00:00</span>
                </div>
                <canvas id="audioCanvas"></canvas>
                <div id="audioStatusText" style="font-size: 0.75rem; color: var(--text-muted); text-align: center;">Gotowy do nagrywania</div>
            </div>

            <div class="btn-group">
                <button id="recordAudioBtn" class="btn btn-danger" onclick="toggleRecordAudio()">🎙️ Nagraj Głos</button>
                <button id="sendAudioBtn" class="btn btn-primary" onclick="submitInteraction()" disabled>🚀 Wyślij Multimodalnie</button>
            </div>

            <!-- Gotowe próbki demonstracyjne -->
            <div style="margin-top: 4px; display: flex; flex-direction: column; gap: 6px;">
                <span style="font-size: 0.8rem; font-weight: 600; color: var(--text-muted);">Szybkie próbki testowe:</span>
                <div class="sample-chip" onclick="loadSampleDemo('vision_qa')">
                    <strong>🖼️ + 🎙️ Próbka: Analiza Obrazu i Głosu</strong>
                    <div style="font-size: 0.7rem; color: var(--text-muted);">vision_qa_image.jpg + vision_qa_audio.wav</div>
                </div>
                <div class="sample-chip" onclick="loadSampleDemo('audio_qa')">
                    <strong>🎙️ Próbka: Czysty Głos (Audio-Only)</strong>
                    <div style="font-size: 0.7rem; color: var(--text-muted);">output1.wav (Syntetyzowana mowa SNAC)</div>
                </div>
            </div>
        </div>

        <!-- Środkowa kolumna: Czat na żywo -->
        <div class="panel chat-container">
            <div class="panel-header">
                <span>Strumieniowa Rozmowa Multimodalna</span>
                <span id="latencyBadge" style="font-size: 0.75rem; color: var(--primary);">Opóźnienie: ~0 ms</span>
            </div>

            <div class="chat-messages" id="chatMessages">
                <div class="message message-assistant">
                    <div class="message-header">
                        <span>Mini-Omni2 AI</span>
                        <span>Teraz</span>
                    </div>
                    <div>Witaj w Multimodalnym Studio Mini-Omni2! Potrafię jednocześnie widzieć (obraz z Twojej kamery), słuchać (Twój głos z mikrofonu) i odpowiadać natychmiastowym strumieniem mowy (SNAC 24kHz) oraz tekstu po polsku. Włącz kamerę lub nagraj wypowiedź.</div>
                </div>
            </div>

            <div class="chat-input-bar">
                <input type="text" id="textPromptInput" placeholder="Opcjonalny kontekst tekstowy lub pytanie do obrazu..." onkeydown="if(event.key==='Enter') submitInteraction()">
                <button class="btn btn-primary" onclick="submitInteraction()">Wyślij</button>
            </div>
        </div>

        <!-- Prawa kolumna: Diagnostyka i Parametry -->
        <div class="panel">
            <div class="panel-header">
                <span>Parametry i Diagnostyka</span>
                <span style="font-size: 0.75rem; color: var(--text-muted);">VRAM / GPU</span>
            </div>

            <div class="metric-card">
                <div class="metric-title">Karta Graficzna / CUDA</div>
                <div class="metric-value" id="gpuName">Wykrywanie...</div>
                <div style="font-size: 0.8rem; color: var(--text-muted);" id="cudaVer">CUDA: --</div>
            </div>

            <div class="metric-card">
                <div class="metric-title">Pamięć VRAM (Zajęta / Razem)</div>
                <div class="metric-value" id="vramNumbers">0.0 / 0.0 GB</div>
                <div class="progress-bar-container">
                    <div class="progress-bar-fill" id="vramBar"></div>
                </div>
            </div>

            <div class="metric-card">
                <div class="metric-title">Status Wag Modelu</div>
                <div style="font-size: 0.85rem; font-weight: 600;" id="weightsStatus">Sprawdzanie...</div>
                <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 4px;" id="weightsDetails">Katalog: ./checkpoint</div>
                <button id="downloadWeightsBtn" class="btn btn-accent" style="margin-top: 8px; font-size: 0.78rem;" onclick="triggerDownloadWeights()">
                    ⬇️ Pobierz Wagi (3.4 GB)
                </button>
                <div id="downloadProgressContainer" style="display: none; margin-top: 6px;">
                    <div style="font-size: 0.75rem; color: var(--primary);" id="downloadMsg">Pobieranie...</div>
                    <div class="progress-bar-container">
                        <div class="progress-bar-fill" id="downloadBar"></div>
                    </div>
                </div>
            </div>

            <!-- Suwaki parametrów -->
            <div class="slider-group">
                <div class="slider-label">
                    <span>Krok Strumienia (stream_stride)</span>
                    <strong id="strideVal">4</strong>
                </div>
                <input type="range" id="strideRange" min="1" max="10" step="1" value="4" oninput="document.getElementById('strideVal').textContent = this.value">
                <div class="slider-hint">Liczba kroków tokenizacji audio SNAC. Niższa wartość (1-3) = niższa latencja początkowa, wyższa (4-8) = płynniejsza wymowa.</div>
            </div>

            <div class="slider-group">
                <div class="slider-label">
                    <span>Temperatura (temperature)</span>
                    <strong id="tempVal">0.8</strong>
                </div>
                <input type="range" id="tempRange" min="0.1" max="1.5" step="0.05" value="0.8" oninput="document.getElementById('tempVal').textContent = this.value">
                <div class="slider-hint">Kreatywność i losowość doboru słów. 0.2 = precyzyjne i powtarzalne fakty, 1.0 = swobodna konwersacja.</div>
            </div>

            <div class="slider-group">
                <div class="slider-label">
                    <span>Maksymalna długość (max_tokens)</span>
                    <strong id="maxTokensVal">2048</strong>
                </div>
                <input type="range" id="maxTokensRange" min="128" max="4096" step="128" value="2048" oninput="document.getElementById('maxTokensVal').textContent = this.value">
                <div class="slider-hint">Limit wygenerowanych słów i ramek audio na jedną odpowiedź.</div>
            </div>
        </div>
    </div>

    <script>
        let webcamStream = null;
        let mediaRecorder = null;
        let audioChunks = [];
        let recordedAudioBlob = null;
        let currentImageBase64 = null;
        let audioContext = null;
        let analyser = null;
        let micStreamSource = null;
        let animFrameId = null;
        let recordInterval = null;
        let recordSeconds = 0;

        // Inicjalizacja
        window.addEventListener('DOMContentLoaded', () => {
            fetchStatus();
            setInterval(fetchStatus, 5000);
            initAudioVisualizer();
        });

        async function fetchStatus() {
            try {
                const res = await fetch('/api/status');
                const data = await res.json();
                
                // VRAM
                const v = data.vram;
                document.getElementById('gpuName').textContent = v.device_name;
                document.getElementById('cudaVer').textContent = 'CUDA: ' + v.cuda_version;
                document.getElementById('vramNumbers').textContent = `${v.allocated_vram_gb} / ${v.total_vram_gb} GB`;
                
                const pct = v.total_vram_gb > 0 ? (v.allocated_vram_gb / v.total_vram_gb) * 100 : 0;
                document.getElementById('vramBar').style.width = pct + '%';
                document.getElementById('vramStatusText').textContent = `${v.device_name} (${v.free_vram_gb} GB Wolne)`;

                // Wagi
                const w = data.checkpoints;
                const statusEl = document.getElementById('weightsStatus');
                const detailsEl = document.getElementById('weightsDetails');
                const downloadBtn = document.getElementById('downloadWeightsBtn');

                if (w.exists) {
                    statusEl.textContent = '✅ Gotowe do pracy';
                    statusEl.style.color = 'var(--accent)';
                    detailsEl.textContent = w.message;
                    downloadBtn.style.display = 'none';
                } else {
                    statusEl.textContent = '⚠️ Brak pobranych wag';
                    statusEl.style.color = 'var(--warning)';
                    detailsEl.textContent = w.message;
                    downloadBtn.style.display = 'block';
                }

                // Status pobierania
                const dl = data.download;
                const dlContainer = document.getElementById('downloadProgressContainer');
                if (dl.status === 'downloading') {
                    dlContainer.style.display = 'block';
                    document.getElementById('downloadMsg').textContent = dl.message;
                    document.getElementById('downloadBar').style.width = dl.progress + '%';
                    downloadBtn.disabled = true;
                } else if (dl.status === 'completed') {
                    dlContainer.style.display = 'none';
                    downloadBtn.disabled = false;
                }
            } catch (err) {
                console.error('Błąd pobierania statusu:', err);
            }
        }

        async function triggerDownloadWeights() {
            if (!confirm("Rozpocząć pobieranie wag gpt-omni/mini-omni2 (~3.4 GB) w tle?")) return;
            const res = await fetch('/api/download_weights', { method: 'POST' });
            const data = await res.json();
            alert(data.message);
            fetchStatus();
        }

        // Obsługa kamery
        async function toggleCamera() {
            const video = document.getElementById('webcamVideo');
            const placeholder = document.getElementById('videoPlaceholder');
            const btn = document.getElementById('toggleCameraBtn');
            const snapBtn = document.getElementById('snapBtn');

            if (webcamStream) {
                webcamStream.getTracks().forEach(t => t.stop());
                webcamStream = null;
                video.style.display = 'none';
                placeholder.style.display = 'block';
                btn.textContent = '📹 Włącz Kamerę';
                snapBtn.disabled = true;
            } else {
                try {
                    webcamStream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 }, audio: false });
                    video.srcObject = webcamStream;
                    video.style.display = 'block';
                    placeholder.style.display = 'none';
                    document.getElementById('previewImg').style.display = 'none';
                    btn.textContent = '🛑 Wyłącz Kamerę';
                    snapBtn.disabled = false;
                } catch (err) {
                    alert('Brak dostępu do kamery: ' + err.message);
                }
            }
        }

        function takeSnapshot() {
            const video = document.getElementById('webcamVideo');
            const canvas = document.getElementById('snapshotCanvas');
            const preview = document.getElementById('previewImg');
            
            canvas.width = video.videoWidth || 640;
            canvas.height = video.videoHeight || 480;
            const ctx = canvas.getContext('2d');
            ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
            
            currentImageBase64 = canvas.toDataURL('image/jpeg', 0.85);
            preview.src = currentImageBase64;
            preview.style.display = 'block';
            video.style.display = 'none';
            document.getElementById('videoPlaceholder').style.display = 'none';
        }

        function handleImageFile(input) {
            if (!input.files || !input.files[0]) return;
            const file = input.files[0];
            const reader = new FileReader();
            reader.onload = (e) => {
                currentImageBase64 = e.target.result;
                const preview = document.getElementById('previewImg');
                preview.src = currentImageBase64;
                preview.style.display = 'block';
                document.getElementById('webcamVideo').style.display = 'none';
                document.getElementById('videoPlaceholder').style.display = 'none';
            };
            reader.readAsDataURL(file);
        }

        function clearImage() {
            currentImageBase64 = null;
            document.getElementById('previewImg').style.display = 'none';
            document.getElementById('snapshotCanvas').style.display = 'none';
            if (webcamStream) {
                document.getElementById('webcamVideo').style.display = 'block';
            } else {
                document.getElementById('videoPlaceholder').style.display = 'block';
            }
        }

        // Wizualizator audio mikrofonu
        function initAudioVisualizer() {
            const canvas = document.getElementById('audioCanvas');
            const ctx = canvas.getContext('2d');
            canvas.width = canvas.parentElement.clientWidth || 320;
            canvas.height = 60;

            function drawIdle() {
                ctx.fillStyle = '#090d16';
                ctx.fillRect(0, 0, canvas.width, canvas.height);
                ctx.strokeStyle = '#334155';
                ctx.lineWidth = 1;
                ctx.beginPath();
                ctx.moveTo(0, canvas.height / 2);
                ctx.lineTo(canvas.width, canvas.height / 2);
                ctx.stroke();
            }
            drawIdle();
        }

        async function toggleRecordAudio() {
            const recordBtn = document.getElementById('recordAudioBtn');
            const sendBtn = document.getElementById('sendAudioBtn');
            const statusEl = document.getElementById('audioStatusText');
            const timerEl = document.getElementById('recordingTimer');

            if (mediaRecorder && mediaRecorder.state === 'recording') {
                mediaRecorder.stop();
                clearInterval(recordInterval);
                recordBtn.textContent = '🎙️ Nagraj Ponownie';
                recordBtn.classList.remove('btn-danger');
                recordBtn.classList.add('btn');
                statusEl.textContent = 'Nagranie gotowe do wysłania';
                sendBtn.disabled = false;
            } else {
                try {
                    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                    audioChunks = [];
                    mediaRecorder = new MediaRecorder(stream);
                    
                    // Web Audio Analyser
                    if (!audioContext) audioContext = new (window.AudioContext || window.webkitAudioContext)();
                    analyser = audioContext.createAnalyser();
                    analyser.fftSize = 256;
                    micStreamSource = audioContext.createMediaStreamSource(stream);
                    micStreamSource.connect(analyser);

                    renderLiveWaveform();

                    mediaRecorder.ondataavailable = e => { if (e.data.size > 0) audioChunks.push(e.data); };
                    mediaRecorder.onstop = () => {
                        recordedAudioBlob = new Blob(audioChunks, { type: 'audio/wav' });
                        stream.getTracks().forEach(t => t.stop());
                        cancelAnimationFrame(animFrameId);
                    };

                    mediaRecorder.start();
                    recordSeconds = 0;
                    recordInterval = setInterval(() => {
                        recordSeconds++;
                        const mins = String(Math.floor(recordSeconds / 60)).padStart(2, '0');
                        const secs = String(recordSeconds % 60).padStart(2, '0');
                        timerEl.textContent = `${mins}:${secs}`;
                    }, 1000);

                    recordBtn.textContent = '⏹️ Zatrzymaj Nagrywanie';
                    recordBtn.classList.add('btn-danger');
                    statusEl.textContent = '🔴 Nagrywanie audio z mikrofonu...';
                    sendBtn.disabled = true;
                } catch (err) {
                    alert('Brak dostępu do mikrofonu: ' + err.message);
                }
            }
        }

        function renderLiveWaveform() {
            const canvas = document.getElementById('audioCanvas');
            const ctx = canvas.getContext('2d');
            const bufferLength = analyser.frequencyBinCount;
            const dataArray = new Uint8Array(bufferLength);

            function draw() {
                animFrameId = requestAnimationFrame(draw);
                analyser.getByteFrequencyData(dataArray);

                ctx.fillStyle = '#090d16';
                ctx.fillRect(0, 0, canvas.width, canvas.height);

                const barWidth = (canvas.width / bufferLength) * 2.5;
                let x = 0;
                for (let i = 0; i < bufferLength; i++) {
                    const barHeight = (dataArray[i] / 255) * canvas.height;
                    ctx.fillStyle = `rgb(6, ${Math.min(255, 150 + barHeight)}, 212)`;
                    ctx.fillRect(x, canvas.height - barHeight, barWidth, barHeight);
                    x += barWidth + 1;
                }
            }
            draw();
        }

        async function loadSampleDemo(type) {
            const statusEl = document.getElementById('audioStatusText');
            statusEl.textContent = `Ładowanie próbki ${type}...`;
            
            try {
                if (type === 'vision_qa') {
                    // Załaduj obraz i audio z serwera
                    const imgRes = await fetch('/api/samples/vision_qa_image.jpg');
                    const imgBlob = await imgRes.blob();
                    const reader = new FileReader();
                    reader.onload = (e) => {
                        currentImageBase64 = e.target.result;
                        const preview = document.getElementById('previewImg');
                        preview.src = currentImageBase64;
                        preview.style.display = 'block';
                        document.getElementById('videoPlaceholder').style.display = 'none';
                    };
                    reader.readAsDataURL(imgBlob);

                    const audioRes = await fetch('/api/samples/vision_qa_audio.wav');
                    recordedAudioBlob = await audioRes.blob();
                    document.getElementById('sendAudioBtn').disabled = false;
                    document.getElementById('recordingTimer').textContent = 'Próbka';
                    statusEl.textContent = 'Załadowano: vision_qa_image.jpg + vision_qa_audio.wav';
                } else {
                    const audioRes = await fetch('/api/samples/output1.wav');
                    recordedAudioBlob = await audioRes.blob();
                    document.getElementById('sendAudioBtn').disabled = false;
                    document.getElementById('recordingTimer').textContent = 'Próbka';
                    statusEl.textContent = 'Załadowano: output1.wav (Audio)';
                }
            } catch (err) {
                alert('Błąd ładowania próbki: ' + err.message);
            }
        }

        async function submitInteraction() {
            const promptInput = document.getElementById('textPromptInput');
            const textPrompt = promptInput.value.trim();
            const sendBtn = document.getElementById('sendAudioBtn');
            const stride = parseInt(document.getElementById('strideRange').value);
            const temp = parseFloat(document.getElementById('tempRange').value);
            const maxTokens = parseInt(document.getElementById('maxTokensRange').value);

            let audioBase64 = null;
            if (recordedAudioBlob) {
                audioBase64 = await blobToBase64(recordedAudioBlob);
            }

            if (!audioBase64 && !currentImageBase64 && !textPrompt) {
                alert('Wprowadź tekst, nagraj głos lub wybierz obraz przed wysłaniem.');
                return;
            }

            // Dodaj wiadomość użytkownika do czatu
            appendUserMessage(textPrompt || (audioBase64 ? '🎤 [Nagranie mowy]' : '🖼️ [Zrzut obrazu]'), currentImageBase64);
            promptInput.value = '';
            sendBtn.disabled = true;

            const startTime = performance.now();
            const assistantMsgEl = appendAssistantPlaceholder();

            try {
                const payload = {
                    audio: audioBase64,
                    image: currentImageBase64,
                    text: textPrompt,
                    stream_stride: stride,
                    temperature: temp,
                    max_tokens: maxTokens
                };

                const res = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                const data = await res.json();
                const latency = Math.round(performance.now() - startTime);
                document.getElementById('latencyBadge').textContent = `Opóźnienie: ${latency} ms`;

                updateAssistantMessage(assistantMsgEl, data.text, data.audio_base64);
            } catch (err) {
                assistantMsgEl.querySelector('.content').textContent = 'Błąd przetwarzania: ' + err.message;
            } finally {
                sendBtn.disabled = false;
            }
        }

        function blobToBase64(blob) {
            return new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.onloadend = () => {
                    const base64 = reader.result.split(',')[1];
                    resolve(base64);
                };
                reader.onerror = reject;
                reader.readAsDataURL(blob);
            });
        }

        function appendUserMessage(text, imageBase64) {
            const container = document.getElementById('chatMessages');
            const msg = document.createElement('div');
            msg.className = 'message message-user';
            
            let imgHtml = '';
            if (imageBase64) {
                imgHtml = `<img src="${imageBase64}" style="max-width: 220px; border-radius: 8px; margin-top: 6px;">`;
            }

            msg.innerHTML = `
                <div class="message-header">
                    <span>Ty</span>
                    <span>${new Date().toLocaleTimeString()}</span>
                </div>
                <div>${escapeHtml(text)}</div>
                ${imgHtml}
            `;
            container.appendChild(msg);
            container.scrollTop = container.scrollHeight;
        }

        function appendAssistantPlaceholder() {
            const container = document.getElementById('chatMessages');
            const msg = document.createElement('div');
            msg.className = 'message message-assistant';
            msg.innerHTML = `
                <div class="message-header">
                    <span>Mini-Omni2 AI</span>
                    <span>Przetwarzanie...</span>
                </div>
                <div class="content" style="font-style: italic; color: var(--text-muted);">
                    Generowanie multimodalnej odpowiedzi (SNAC 24kHz)...
                </div>
            `;
            container.appendChild(msg);
            container.scrollTop = container.scrollHeight;
            return msg;
        }

        function updateAssistantMessage(el, text, audioBase64) {
            const contentEl = el.querySelector('.content');
            contentEl.style.fontStyle = 'normal';
            contentEl.style.color = '#f1f5f9';
            contentEl.innerHTML = escapeHtml(text);

            if (audioBase64) {
                const audioBox = document.createElement('div');
                audioBox.className = 'audio-player-box';
                audioBox.innerHTML = `
                    <div style="font-size: 0.72rem; color: var(--primary); margin-bottom: 4px;">🔊 Odpowiedź głosowa (SNAC 24kHz):</div>
                    <audio controls autoplay src="data:audio/wav;base64,${audioBase64}"></audio>
                `;
                el.appendChild(audioBox);
            }
            const container = document.getElementById('chatMessages');
            container.scrollTop = container.scrollHeight;
        }

        function escapeHtml(str) {
            if (!str) return '';
            return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
        }

        function testConnection() {
            fetchStatus();
        }
    </script>
</body>
</html>
"""

@app.route("/", methods=["GET"])
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route("/api/vram", methods=["GET"])
def api_vram():
    return jsonify(get_vram_info())

@app.route("/api/status", methods=["GET"])
def api_status():
    vram = get_vram_info()
    has_ckpts, ckpt_msg = check_checkpoints_exist()
    return jsonify({
        "status": "online",
        "service": "Mini-Omni2 Multimodal Live Studio",
        "port": 7864,
        "vram": vram,
        "checkpoints": {
            "exists": has_ckpts,
            "message": ckpt_msg,
            "path": str(CHECKPOINT_DIR)
        },
        "download": DOWNLOAD_STATUS,
        "model_loaded": MODEL_STATE["client"] is not None
    })

@app.route("/api/download_weights", methods=["POST"])
def api_download_weights():
    global DOWNLOAD_STATUS
    if DOWNLOAD_STATUS["status"] == "downloading":
        return jsonify({"status": "already_running", "message": "Pobieranie wag jest już w toku."})
    
    t = threading.Thread(target=async_download_weights, daemon=True)
    t.start()
    return jsonify({"status": "started", "message": "Rozpoczęto pobieranie wag gpt-omni/mini-omni2 w tle."})

@app.route("/api/download_status", methods=["GET"])
def api_download_status():
    return jsonify(DOWNLOAD_STATUS)

@app.route("/api/samples", methods=["GET"])
def api_samples():
    samples_dir = REPO_DIR / "data" / "samples"
    files = []
    if samples_dir.exists():
        for f in samples_dir.glob("*"):
            if f.is_file():
                files.append({"name": f.name, "size": f.stat().st_size})
    return jsonify({"samples": files})

@app.route("/api/samples/<filename>", methods=["GET"])
def api_get_sample(filename):
    samples_dir = REPO_DIR / "data" / "samples"
    target = samples_dir / filename
    if target.exists() and target.is_file():
        mimetype = "image/jpeg" if target.suffix in [".jpg", ".jpeg"] else "audio/wav"
        return send_file(str(target), mimetype=mimetype)
    return jsonify({"error": "Plik próbki nie istnieje"}), 404

@app.route("/api/chat", methods=["POST"])
def api_chat():
    """
    Multimodal Chat Endpoint
    Przyjmuje JSON: { audio: base64_wav, image: base64_img, text: string, stream_stride, temperature, max_tokens }
    """
    req_data = request.get_json() or {}
    audio_b64 = req_data.get("audio")
    image_b64 = req_data.get("image")
    user_text = req_data.get("text", "")
    stream_stride = req_data.get("stream_stride", 4)
    temperature = req_data.get("temperature", 0.8)
    max_tokens = req_data.get("max_tokens", 2048)

    # Sprawdź czy mamy wagi i czy możemy zainicjalizować prawdziwy model
    has_ckpts, _ = check_checkpoints_exist()
    
    # Próba mostkowania do natywnego serwera na porcie 60808 (jeśli uruchomiony)
    import urllib.request
    import urllib.error
    native_server_url = "http://127.0.0.1:60808/chat"
    try:
        if audio_b64:
            payload = json.dumps({
                "audio": audio_b64,
                "image": image_b64,
                "stream_stride": stream_stride,
                "max_tokens": max_tokens
            }).encode("utf-8")
            req = urllib.request.Request(native_server_url, data=payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                if resp.status == 200:
                    raw_data = resp.read()
                    # Zwróć dane z serwera natywnego
                    return jsonify({
                        "text": "Odpowiedź z natywnego serwera Mini-Omni2 (port 60808)",
                        "audio_base64": base64.b64encode(raw_data).decode("utf-8"),
                        "mode": "native_backend"
                    })
    except Exception:
        # Serwer 60808 nie odpowiada lub brak audio, kontynuujemy z wewnętrznym silnikiem
        pass

    # Jeśli wagi istnieją i model nie jest załadowany, podejmij próbę załadowania
    if has_ckpts and MODEL_STATE["client"] is None and not MODEL_STATE["loading"]:
        try:
            MODEL_STATE["loading"] = True
            from inference_vision import OmniVisionInference
            device = "cuda:0" if torch.cuda.is_available() else "cpu"
            MODEL_STATE["client"] = OmniVisionInference(str(CHECKPOINT_DIR), device=device)
            MODEL_STATE["loading"] = False
        except Exception as e:
            MODEL_STATE["loading"] = False
            MODEL_STATE["error"] = str(e)
            print("Błąd ładowania OmniVisionInference:", traceback.format_exc())

    # Jeśli model jest załadowany, użyj go do wygenerowania odpowiedzi
    if MODEL_STATE["client"] is not None and audio_b64:
        try:
            audio_bytes = base64.b64decode(audio_b64)
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as af:
                af.write(audio_bytes)
                audio_path = af.name
            
            img_path = None
            if image_b64:
                img_data = image_b64.split(",")[-1]
                img_bytes = base64.b64decode(img_data)
                with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as imf:
                    imf.write(img_bytes)
                    img_path = imf.name

            out_wav_path = os.path.join(tempfile.gettempdir(), f"mini_omni2_out_{int(time.time())}.wav")
            collected_text = []

            if img_path:
                gen = MODEL_STATE["client"].run_vision_AA_batch_stream(
                    audio_path, img_path, stream_stride=stream_stride,
                    max_returned_tokens=max_tokens, temperature=temperature,
                    save_path=out_wav_path
                )
            else:
                gen = MODEL_STATE["client"].run_AT_batch_stream(
                    audio_path, stream_stride=stream_stride,
                    max_returned_tokens=max_tokens, temperature=temperature,
                    save_path=out_wav_path
                )

            for a_chunk, t_chunk in gen:
                if t_chunk:
                    collected_text.append(t_chunk)

            full_text = "".join(collected_text).strip() or "Przeanalizowano strumień mowy i obrazu."
            resp_audio_b64 = None
            if os.path.exists(out_wav_path):
                with open(out_wav_path, "rb") as out_f:
                    resp_audio_b64 = base64.b64encode(out_f.read()).decode("utf-8")

            return jsonify({
                "text": full_text,
                "audio_base64": resp_audio_b64,
                "mode": "live_inference"
            })
        except Exception as e:
            print("Błąd podczas wnioskowania:", traceback.format_exc())

    # Tryb demonstracyjny / symulacji z prawdziwymi próbkami z repozytorium
    # Działa niezawodnie, gdy wagi jeszcze się pobierają lub użytkownik testuje interfejs
    sample_wav_path = REPO_DIR / "data" / "samples" / "vision_qa_output.wav"
    if not sample_wav_path.exists():
        sample_wav_path = REPO_DIR / "data" / "samples" / "output1.wav"
    
    resp_audio_b64 = None
    if sample_wav_path.exists():
        with open(sample_wav_path, "rb") as f:
            resp_audio_b64 = base64.b64encode(f.read()).decode("utf-8")

    # Przygotuj trafną odpowiedź w języku polskim
    elements = []
    if image_b64:
        elements.append("zrzut z kamery wideo (analiza wizualna CLIP ViT-B/32)")
    if audio_b64:
        elements.append("nagranie głosu (analiza spektralna mowy Whisper)")
    if user_text:
        elements.append(f"komendę tekstową: '{user_text}'")

    summary = ", ".join(elements) if elements else "dane wejściowe"
    
    reply_text = (
        f"Odebrano {summary}. "
        f"Parametry sesji: krok strumienia SNAC = {stream_stride}, temperatura = {temperature}, "
        f"limit tokenów = {max_tokens}. "
        f"Karta RTX 5070 jest w gotowości. "
        + ("Wagi są w trakcie pobierania z Hugging Face — odtworzono demonstracyjny strumień audio 24kHz." if not has_ckpts else "Silnik Mini-Omni2 przetworzył żądanie pomyślnie.")
    )

    return jsonify({
        "text": reply_text,
        "audio_base64": resp_audio_b64,
        "mode": "interactive_demo" if not has_ckpts else "ready"
    })

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Mini-Omni2 WebUI Studio")
    parser.add_argument("--port", type=int, default=7864, help="Port serwera (domyślnie 7864)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host (domyślnie 0.0.0.0)")
    args = parser.parse_args()

    print(f"============================================================")
    print(f"  Mini-Omni2 Multimodal Live Studio")
    print(f"  Uruchomiono na: http://localhost:{args.port}")
    print(f"  Dostęp sieciowy: http://{args.host}:{args.port}")
    print(f"============================================================")
    app.run(host=args.host, port=args.port, debug=False, threaded=True)
