#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gemini Omni Live Studio WebUI
Port: 7865
Studio Multimodalne na żywo integrujące obraz z kamery, udostępnianie ekranu, nagrywanie audio i pliki z Google GenAI SDK.
"""
import os
import sys
import base64
import json
import time
import traceback
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_DIR))

from flask import Flask, request, jsonify, render_template_string
from google import genai
from google.genai import types

app = Flask(__name__)

# Persony systemowe w języku polskim
PERSONAS = {
    "visual_expert": {
        "name": "Ekspert Analizy Wizualnej",
        "description": "Precyzyjna inspekcja detali obrazu, kompozycji, odczyt tekstu OCR i relacji przestrzennych",
        "system_instruction": (
            "Jesteś światowej klasy Ekspertem Analizy Wizualnej i Percepcji Przestrzennej. "
            "Odpowiadaj po polsku. Szczegółowo i precyzyjnie opisuj przesłane obrazy, zrzuty ekranu i klatki wideo. "
            "Zwracaj uwagę na ukryte detale, kompozycję, barwy, anomalie, napisy tekstowe (OCR) oraz stan techniczny obiektów."
        )
    },
    "creative_advisor": {
        "name": "Kreatywny Doradca",
        "description": "Twórcze burze mózgów, scenariusze wideo, copywriting i koncepcje marketingowe",
        "system_instruction": (
            "Jesteś dynamicznym i nieszablonowym Kreatywnym Doradcą. Odpowiadaj z pasją i energią po polsku. "
            "Pomagaj w kreowaniu chwytliwych narracji, scenariuszy wideo (np. YouTube, TikTok), angażujących haczyków (hooks) "
            "oraz innowacyjnych koncepcji produktów i marek."
        )
    },
    "tech_architect": {
        "name": "Asystent Kodu i Technologii",
        "description": "Analiza schematów architektonicznych, inspekcja kodu, debugging i optymalizacja",
        "system_instruction": (
            "Jesteś Starszym Inżynierem Oprogramowania i Architektem Systemów AI. Odpowiadaj konkretnie po polsku. "
            "Gdy otrzymasz kod źródłowy, diagramy architektoniczne lub zrzuty konsoli/ekranu, wskaż źródło problemu, "
            "zaproponuj optymalne rozwiązania zgodne z najlepszymi praktykami i dostarcz czysty, gotowy do wdrożenia kod."
        )
    },
    "craftsman_expert": {
        "name": "Ekspert Rękodzieła (FW DRUCIK)",
        "description": "Obróbka drewna, metalu, żywica epoksydowa, druk 3D i wycena wyrobów warsztatowych",
        "system_instruction": (
            "Jesteś doświadczonym Mistrzem Rzemiosła i Ekspertem Wytwórczości Manufaktury FW DRUCIK. "
            "Odpowiadaj po polsku z perspektywy praktyka warsztatowego. Znasz się na obróbce drewna, spawaniu i obróbce metalu, "
            "pracy z żywicą epoksydową, druku 3D oraz technikach szlifowania i wykańczania. "
            "Doradzaj realne metody produkcji, dobór materiałów, szacowanie kosztów i bezpieczeństwo BHP."
        )
    }
}

MODELS = [
    {"id": "gemini-2.5-flash", "name": "Gemini 2.5 Flash", "desc": "Najszybszy multimodalny, idealny do obrazów i głosu na żywo"},
    {"id": "gemini-2.5-pro", "name": "Gemini 2.5 Pro", "desc": "Głębokie wnioskowanie do złożonych schematów, kodu i dokumentów"},
    {"id": "gemini-2.0-flash-exp", "name": "Gemini 2.0 Flash Exp", "desc": "Eksperymentalny model ultra-niskiej latencji"}
]

# Pobranie klucza API z pamięci środowiskowej
CURRENT_API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or ""

def get_masked_key(key):
    if not key:
        return "Brak skonfigurowanego klucza"
    if len(key) <= 8:
        return "****"
    return key[:6] + "..." + key[-4:]

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gemini Omni Live Studio — Multimodalna Wizja i Dźwięk</title>
    <style>
        :root {
            --bg-base: #090d16;
            --bg-surface: #131b2e;
            --bg-elevated: #1e293b;
            --primary: #38bdf8;
            --primary-hover: #0284c7;
            --accent: #a855f7;
            --accent-hover: #9333ea;
            --emerald: #10b981;
            --danger: #ef4444;
            --warning: #f59e0b;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --border: #334155;
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
        .header-left {
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
        .header-right {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .api-key-box {
            background: rgba(0,0,0,0.3);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 6px 12px;
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 0.8rem;
        }
        .main-layout {
            display: grid;
            grid-template-columns: 420px 1fr;
            gap: 20px;
            padding: 20px;
            flex: 1;
            max-width: 1700px;
            margin: 0 auto;
            width: 100%;
        }
        @media (max-width: 1024px) {
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
        .tabs {
            display: flex;
            gap: 6px;
            background: rgba(0,0,0,0.25);
            padding: 4px;
            border-radius: var(--radius-md);
            border: 1px solid var(--border);
        }
        .tab-btn {
            flex: 1;
            padding: 8px 10px;
            font-size: 0.8rem;
            font-weight: 600;
            background: transparent;
            border: none;
            color: var(--text-muted);
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
        }
        .tab-btn.active {
            background: var(--bg-elevated);
            color: var(--primary);
            box-shadow: 0 2px 4px rgba(0,0,0,0.3);
        }
        .tab-content {
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        .media-viewport {
            position: relative;
            background: #000;
            border-radius: var(--radius-md);
            overflow: hidden;
            aspect-ratio: 16/9;
            display: flex;
            align-items: center;
            justify-content: center;
            border: 2px dashed var(--border);
        }
        video, canvas, #capturedPreview {
            width: 100%;
            height: 100%;
            object-fit: cover;
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
        .audio-recorder-box {
            background: #060911;
            border: 1px solid var(--border);
            border-radius: var(--radius-md);
            padding: 12px;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        #audioWaveCanvas {
            width: 100%;
            height: 70px;
            background: transparent;
        }
        .file-dropzone {
            border: 2px dashed var(--border);
            border-radius: var(--radius-md);
            padding: 24px 16px;
            text-align: center;
            background: rgba(0,0,0,0.2);
            cursor: pointer;
            transition: border-color 0.2s;
        }
        .file-dropzone:hover {
            border-color: var(--primary);
        }
        .chat-box {
            display: flex;
            flex-direction: column;
            height: 700px;
        }
        .chat-messages {
            flex: 1;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 16px;
            padding: 14px;
            background: rgba(0,0,0,0.2);
            border-radius: var(--radius-md);
        }
        .message {
            display: flex;
            flex-direction: column;
            gap: 8px;
            max-width: 85%;
            padding: 14px 18px;
            border-radius: 12px;
            font-size: 0.95rem;
            line-height: 1.5;
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
        .message-meta {
            font-size: 0.75rem;
            opacity: 0.75;
            display: flex;
            justify-content: space-between;
        }
        .message-content {
            white-space: pre-wrap;
            word-break: break-word;
        }
        .message-attachment {
            max-width: 260px;
            max-height: 200px;
            border-radius: 8px;
            object-fit: cover;
            border: 1px solid var(--border);
            margin-top: 6px;
        }
        .chips-container {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            margin-top: 8px;
        }
        .chip {
            background: rgba(255,255,255,0.06);
            border: 1px solid var(--border);
            padding: 6px 10px;
            border-radius: 20px;
            font-size: 0.78rem;
            cursor: pointer;
            transition: all 0.2s;
        }
        .chip:hover {
            background: rgba(56, 189, 248, 0.2);
            border-color: var(--primary);
        }
        .input-bar {
            display: flex;
            gap: 10px;
            margin-top: 12px;
        }
        .input-bar textarea {
            flex: 1;
            background: var(--bg-elevated);
            border: 1px solid var(--border);
            color: var(--text-main);
            padding: 12px 16px;
            border-radius: var(--radius-md);
            font-size: 0.95rem;
            resize: none;
            height: 52px;
            font-family: inherit;
        }
        select, input[type="text"] {
            background: var(--bg-elevated);
            border: 1px solid var(--border);
            color: var(--text-main);
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 0.85rem;
            outline: none;
        }
        select:focus, input[type="text"]:focus, textarea:focus {
            border-color: var(--primary);
        }
        .control-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 10px;
        }
    </style>
</head>
<body>
    <header>
        <div class="header-left">
            <h2>Gemini Omni Live Studio</h2>
            <span class="badge">Google GenAI 3.6</span>
            <span class="badge" id="portBadge">Port 7865</span>
        </div>
        <div class="header-right">
            <div class="api-key-box">
                <span>🔑 Klucz API:</span>
                <strong id="maskedKeyText">{{ masked_key }}</strong>
                <button class="btn" style="padding: 3px 8px; font-size: 0.75rem;" onclick="promptApiKey()">Zmień</button>
            </div>
            <button class="btn btn-primary" onclick="testConnection()">Sprawdź Połączenie</button>
        </div>
    </header>

    <div class="main-layout">
        <!-- Lewy Panel: Multimodalne Wejścia -->
        <div class="panel">
            <div class="panel-header">
                <span>Źródła Multimodalne</span>
                <span style="font-size: 0.75rem; color: var(--text-muted);" id="activeSourceLabel">Kamera</span>
            </div>

            <!-- Zakładki wyboru źródła -->
            <div class="tabs">
                <button class="tab-btn active" id="tabCamera" onclick="switchMediaTab('camera')">📹 Kamera</button>
                <button class="tab-btn" id="tabScreen" onclick="switchMediaTab('screen')">🖥️ Ekran</button>
                <button class="tab-btn" id="tabAudio" onclick="switchMediaTab('audio')">🎙️ Audio</button>
                <button class="tab-btn" id="tabFiles" onclick="switchMediaTab('files')">📁 Pliki</button>
            </div>

            <!-- Widok: Kamera & Ekran -->
            <div id="visualContent" class="tab-content">
                <div class="media-viewport" id="viewport">
                    <video id="liveVideo" autoplay playsinline muted style="display:none;"></video>
                    <canvas id="liveCanvas" style="display:none;"></canvas>
                    <img id="capturedPreview" src="" style="display:none;" alt="Zrzut klatki">
                    <div id="mediaPlaceholder" style="text-align: center; color: var(--text-muted); padding: 20px;">
                        <p style="font-size: 2.2rem;" id="mediaIcon">📹</p>
                        <p style="font-size: 0.85rem; margin-top: 8px;" id="mediaTitle">Kamera wyłączona</p>
                        <p style="font-size: 0.75rem;">Kliknij "Uruchom Źródło", aby rozpocząć podgląd</p>
                    </div>
                </div>

                <div class="btn-group">
                    <button id="toggleStreamBtn" class="btn" onclick="toggleCurrentStream()">▶️ Uruchom Kamerę</button>
                    <button id="captureFrameBtn" class="btn btn-accent" onclick="captureFrame()" disabled>📸 Zrób Zrzut Klatki</button>
                </div>
                <button class="btn btn-danger" style="width: 100%;" onclick="clearCapturedVisual()">🗑️ Wyczyść Zrzut Klatki</button>
            </div>

            <!-- Widok: Nagrywanie Audio -->
            <div id="audioContent" class="tab-content" style="display: none;">
                <div class="audio-recorder-box">
                    <div style="display: flex; justify-content: space-between; font-size: 0.8rem;">
                        <span>Oscyloskop Spektralny</span>
                        <span id="audioTimer" style="color: var(--primary); font-weight: 600;">00:00</span>
                    </div>
                    <canvas id="audioWaveCanvas"></canvas>
                    <div id="audioLabel" style="font-size: 0.75rem; color: var(--text-muted); text-align: center;">Gotowy do nagrywania</div>
                </div>

                <div class="btn-group">
                    <button id="recordBtn" class="btn btn-danger" onclick="toggleAudioRecording()">🎙️ Rozpocznij Nagranie</button>
                    <button id="clearAudioBtn" class="btn" onclick="clearRecordedAudio()" disabled>🗑️ Wyczyść Audio</button>
                </div>
                <div id="audioPlaybackContainer" style="display:none; margin-top: 6px;">
                    <audio id="audioPlayback" controls style="width: 100%; height: 38px;"></audio>
                </div>
            </div>

            <!-- Widok: Pliki -->
            <div id="filesContent" class="tab-content" style="display: none;">
                <div class="file-dropzone" onclick="document.getElementById('fileUploadInput').click()">
                    <p style="font-size: 2rem;">📤</p>
                    <p style="font-size: 0.85rem; font-weight: 600; margin-top: 6px;">Upuść plik lub kliknij, aby wgrać</p>
                    <p style="font-size: 0.75rem; color: var(--text-muted); margin-top: 4px;">
                        Obrazy (PNG, JPG, WEBP), Audio (WAV, MP3), PDF, Kod (PY, JS, TS, JSON)
                    </p>
                    <input type="file" id="fileUploadInput" style="display:none;" onchange="handleFileUpload(this)">
                </div>
                <div id="fileInfoBox" style="display:none; background: var(--bg-elevated); padding: 10px; border-radius: 8px; font-size: 0.8rem;">
                    <div style="display: flex; justify-content: space-between;">
                        <strong id="uploadedFileName">nazwa_pliku.ext</strong>
                        <span id="uploadedFileSize">0 KB</span>
                    </div>
                    <button class="btn btn-danger" style="margin-top: 8px; width: 100%; font-size: 0.75rem;" onclick="clearUploadedFile()">Usuń Plik</button>
                </div>
            </div>

            <!-- Konfiguracja Modelu & Persony -->
            <div style="border-top: 1px solid var(--border); padding-top: 14px; display: flex; flex-direction: column; gap: 12px;">
                <div class="control-row">
                    <label style="font-size: 0.82rem; font-weight: 600;">Model Gemini:</label>
                    <select id="modelSelector" style="flex: 1;" onchange="updateModelDesc()">
                        {% for m in models %}
                        <option value="{{ m.id }}">{{ m.name }}</option>
                        {% endfor %}
                    </select>
                </div>
                <div style="font-size: 0.72rem; color: var(--text-muted);" id="modelDesc">
                    Najszybszy multimodalny, idealny do analizy na żywo
                </div>

                <div class="control-row">
                    <label style="font-size: 0.82rem; font-weight: 600;">Persona AI:</label>
                    <select id="personaSelector" style="flex: 1;" onchange="updatePersonaDesc()">
                        {% for k, p in personas.items() %}
                        <option value="{{ k }}">{{ p.name }}</option>
                        {% endfor %}
                    </select>
                </div>
                <div style="font-size: 0.72rem; color: var(--accent);" id="personaDesc">
                    Precyzyjna inspekcja detali obrazu, kompozycji i odczyt tekstu OCR
                </div>

                <div style="display: flex; justify-content: space-between; font-size: 0.8rem; margin-top: 4px;">
                    <span>Temperatura: <strong id="tempDisplay">0.7</strong></span>
                    <input type="range" id="tempInput" min="0.0" max="1.0" step="0.05" value="0.7" style="width: 140px;" oninput="document.getElementById('tempDisplay').textContent = this.value">
                </div>
            </div>
        </div>

        <!-- Prawy Panel: Rozmowa i Analiza -->
        <div class="panel chat-box">
            <div class="panel-header">
                <span>Panel Interakcji Multimodalnej</span>
                <span id="latencyTag" style="font-size: 0.75rem; color: var(--primary);">Czas: -- ms</span>
            </div>

            <!-- Lista wiadomości -->
            <div class="chat-messages" id="chatList">
                <div class="message message-assistant">
                    <div class="message-meta">
                        <span>Gemini Omni Studio</span>
                        <span>Teraz</span>
                    </div>
                    <div class="message-content">Witaj w Gemini Omni Live Studio! Przesyłaj klatki z kamery, zrzuty ekranu, nagrania mikrofonu lub pliki do natychmiastowej analizy z użyciem modeli Gemini 2.5 Flash / Pro. Wybierz personę asystenta i zadaj pytanie.</div>
                </div>
            </div>

            <!-- Szybkie szablony zapytań -->
            <div class="chips-container">
                <div class="chip" onclick="applyQuickPrompt('🔍 Opisz ze szczegółami każdy element, barwy i relacje przestrzenne na tym obrazie.')">🔍 Szczegółowa analiza obrazu</div>
                <div class="chip" onclick="applyQuickPrompt('💻 Przeanalizuj ten zrzut ekranu lub kod pod kątem błędów, luk i optymalizacji.')">💻 Analiza kodu / ekranu</div>
                <div class="chip" onclick="applyQuickPrompt('🎨 Jak ocenić kompozycję i jakie ulepszenia estetyczne sugerujesz?')">🎨 Ocena estetyki i stylu</div>
                <div class="chip" onclick="applyQuickPrompt('🛠️ Jakie technologie rzemieślnicze i kroki warsztatowe FW DRUCIK zastosować do tego wyrobu?')">🛠️ Rzemiosło i warsztat</div>
            </div>

            <!-- Pasek wprowadzania -->
            <div class="input-bar">
                <textarea id="promptInput" placeholder="Wpisz pytanie, polecenie lub instrukcję dla Gemini..." onkeydown="handleTextKey(event)"></textarea>
                <button class="btn btn-primary" id="sendBtn" style="padding: 0 20px;" onclick="sendInteraction()">
                    🚀 Wyślij
                </button>
            </div>
        </div>
    </div>

    <script>
        let currentMode = 'camera'; // camera, screen, audio, files
        let mediaStream = null;
        let capturedVisualBase64 = null;
        let recordedAudioBlob = null;
        let uploadedFileBase64 = null;
        let uploadedFileMeta = null;

        // Audio Analyser
        let audioCtx = null;
        let audioAnalyser = null;
        let audioRecorder = null;
        let audioChunks = [];
        let animId = null;
        let recInterval = null;
        let recSeconds = 0;

        const personasMap = {{ personas|tojson }};
        const modelsMap = {{ models|tojson }};

        window.addEventListener('DOMContentLoaded', () => {
            initAudioWave();
        });

        function switchMediaTab(tab) {
            currentMode = tab;
            ['tabCamera', 'tabScreen', 'tabAudio', 'tabFiles'].forEach(id => {
                document.getElementById(id).classList.remove('active');
            });
            document.getElementById('tab' + tab.charAt(0).toUpperCase() + tab.slice(1)).classList.add('active');

            const visualContent = document.getElementById('visualContent');
            const audioContent = document.getElementById('audioContent');
            const filesContent = document.getElementById('filesContent');

            visualContent.style.display = (tab === 'camera' || tab === 'screen') ? 'flex' : 'none';
            audioContent.style.display = (tab === 'audio') ? 'flex' : 'none';
            filesContent.style.display = (tab === 'files') ? 'flex' : 'none';

            const toggleBtn = document.getElementById('toggleStreamBtn');
            const icon = document.getElementById('mediaIcon');
            const title = document.getElementById('mediaTitle');
            const label = document.getElementById('activeSourceLabel');

            if (tab === 'camera') {
                toggleBtn.textContent = '▶️ Uruchom Kamerę';
                icon.textContent = '📹';
                title.textContent = 'Kamera wyłączona';
                label.textContent = 'Kamera';
            } else if (tab === 'screen') {
                toggleBtn.textContent = '🖥️ Udostępnij Ekran';
                icon.textContent = '🖥️';
                title.textContent = 'Udostępnianie ekranu wyłączone';
                label.textContent = 'Ekran';
            } else if (tab === 'audio') {
                label.textContent = 'Mikrofon';
            } else if (tab === 'files') {
                label.textContent = 'Pliki';
            }
        }

        async function toggleCurrentStream() {
            const video = document.getElementById('liveVideo');
            const placeholder = document.getElementById('mediaPlaceholder');
            const toggleBtn = document.getElementById('toggleStreamBtn');
            const snapBtn = document.getElementById('captureFrameBtn');

            if (mediaStream) {
                stopStream();
                toggleBtn.textContent = (currentMode === 'camera') ? '▶️ Uruchom Kamerę' : '🖥️ Udostępnij Ekran';
                video.style.display = 'none';
                placeholder.style.display = 'block';
                snapBtn.disabled = true;
            } else {
                try {
                    if (currentMode === 'camera') {
                        mediaStream = await navigator.mediaDevices.getUserMedia({ video: { width: 1280, height: 720 }, audio: false });
                    } else if (currentMode === 'screen') {
                        mediaStream = await navigator.mediaDevices.getDisplayMedia({ video: true, audio: false });
                    }
                    video.srcObject = mediaStream;
                    video.style.display = 'block';
                    placeholder.style.display = 'none';
                    document.getElementById('capturedPreview').style.display = 'none';
                    toggleBtn.textContent = '🛑 Zatrzymaj Źródło';
                    snapBtn.disabled = false;
                } catch (err) {
                    alert('Błąd uruchamiania źródła: ' + err.message);
                }
            }
        }

        function stopStream() {
            if (mediaStream) {
                mediaStream.getTracks().forEach(t => t.stop());
                mediaStream = null;
            }
        }

        function captureFrame() {
            const video = document.getElementById('liveVideo');
            const canvas = document.getElementById('liveCanvas');
            const preview = document.getElementById('capturedPreview');

            canvas.width = video.videoWidth || 1280;
            canvas.height = video.videoHeight || 720;
            const ctx = canvas.getContext('2d');
            ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

            capturedVisualBase64 = canvas.toDataURL('image/jpeg', 0.9);
            preview.src = capturedVisualBase64;
            preview.style.display = 'block';
            video.style.display = 'none';
            document.getElementById('mediaPlaceholder').style.display = 'none';
        }

        function clearCapturedVisual() {
            capturedVisualBase64 = null;
            document.getElementById('capturedPreview').style.display = 'none';
            if (mediaStream) {
                document.getElementById('liveVideo').style.display = 'block';
            } else {
                document.getElementById('mediaPlaceholder').style.display = 'block';
            }
        }

        // Audio
        function initAudioWave() {
            const canvas = document.getElementById('audioWaveCanvas');
            const ctx = canvas.getContext('2d');
            canvas.width = canvas.parentElement.clientWidth || 360;
            canvas.height = 70;
            ctx.fillStyle = '#060911';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            ctx.strokeStyle = '#334155';
            ctx.beginPath();
            ctx.moveTo(0, 35);
            ctx.lineTo(canvas.width, 35);
            ctx.stroke();
        }

        async function toggleAudioRecording() {
            const btn = document.getElementById('recordBtn');
            const clearBtn = document.getElementById('clearAudioBtn');
            const label = document.getElementById('audioLabel');
            const timer = document.getElementById('audioTimer');

            if (audioRecorder && audioRecorder.state === 'recording') {
                audioRecorder.stop();
                clearInterval(recInterval);
                btn.textContent = '🎙️ Nagraj Ponownie';
                btn.classList.remove('btn-danger');
                label.textContent = 'Nagranie gotowe';
                clearBtn.disabled = false;
            } else {
                try {
                    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                    audioChunks = [];
                    audioRecorder = new MediaRecorder(stream);

                    if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                    audioAnalyser = audioCtx.createAnalyser();
                    audioAnalyser.fftSize = 256;
                    const src = audioCtx.createMediaStreamSource(stream);
                    src.connect(audioAnalyser);

                    drawWaveform();

                    audioRecorder.ondataavailable = e => { if (e.data.size > 0) audioChunks.push(e.data); };
                    audioRecorder.onstop = () => {
                        recordedAudioBlob = new Blob(audioChunks, { type: 'audio/wav' });
                        stream.getTracks().forEach(t => t.stop());
                        cancelAnimationFrame(animId);
                        const url = URL.createObjectURL(recordedAudioBlob);
                        const player = document.getElementById('audioPlayback');
                        player.src = url;
                        document.getElementById('audioPlaybackContainer').style.display = 'block';
                    };

                    audioRecorder.start();
                    recSeconds = 0;
                    recInterval = setInterval(() => {
                        recSeconds++;
                        const m = String(Math.floor(recSeconds / 60)).padStart(2, '0');
                        const s = String(recSeconds % 60).padStart(2, '0');
                        timer.textContent = `${m}:${s}`;
                    }, 1000);

                    btn.textContent = '⏹️ Zatrzymaj Nagrywanie';
                    btn.classList.add('btn-danger');
                    label.textContent = '🔴 Nagrywanie dźwięku...';
                    clearBtn.disabled = true;
                } catch (err) {
                    alert('Brak dostępu do mikrofonu: ' + err.message);
                }
            }
        }

        function drawWaveform() {
            const canvas = document.getElementById('audioWaveCanvas');
            const ctx = canvas.getContext('2d');
            const bufLen = audioAnalyser.frequencyBinCount;
            const data = new Uint8Array(bufLen);

            function draw() {
                animId = requestAnimationFrame(draw);
                audioAnalyser.getByteFrequencyData(data);
                ctx.fillStyle = '#060911';
                ctx.fillRect(0, 0, canvas.width, canvas.height);
                const barW = (canvas.width / bufLen) * 2.5;
                let x = 0;
                for (let i = 0; i < bufLen; i++) {
                    const barH = (data[i] / 255) * canvas.height;
                    ctx.fillStyle = `rgb(56, ${Math.min(255, 120 + barH)}, 248)`;
                    ctx.fillRect(x, canvas.height - barH, barW, barH);
                    x += barW + 1;
                }
            }
            draw();
        }

        function clearRecordedAudio() {
            recordedAudioBlob = null;
            document.getElementById('audioPlaybackContainer').style.display = 'none';
            document.getElementById('clearAudioBtn').disabled = true;
            document.getElementById('audioLabel').textContent = 'Wyczyszczono nagranie';
            document.getElementById('audioTimer').textContent = '00:00';
            initAudioWave();
        }

        // Pliki
        function handleFileUpload(input) {
            if (!input.files || !input.files[0]) return;
            const f = input.files[0];
            const reader = new FileReader();
            reader.onload = e => {
                uploadedFileBase64 = e.target.result;
                uploadedFileMeta = { name: f.name, size: f.size, type: f.type };
                document.getElementById('uploadedFileName').textContent = f.name;
                document.getElementById('uploadedFileSize').textContent = Math.round(f.size / 1024) + ' KB';
                document.getElementById('fileInfoBox').style.display = 'block';
            };
            reader.readAsDataURL(f);
        }

        function clearUploadedFile() {
            uploadedFileBase64 = null;
            uploadedFileMeta = null;
            document.getElementById('fileUploadInput').value = '';
            document.getElementById('fileInfoBox').style.display = 'none';
        }

        function updatePersonaDesc() {
            const sel = document.getElementById('personaSelector').value;
            const p = personasMap[sel];
            if (p) document.getElementById('personaDesc').textContent = p.description;
        }

        function updateModelDesc() {
            const sel = document.getElementById('modelSelector').value;
            const m = modelsMap.find(item => item.id === sel);
            if (m) document.getElementById('modelDesc').textContent = m.desc;
        }

        function applyQuickPrompt(text) {
            document.getElementById('promptInput').value = text;
            document.getElementById('promptInput').focus();
        }

        function handleTextKey(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendInteraction();
            }
        }

        async function sendInteraction() {
            const promptBox = document.getElementById('promptInput');
            let prompt = promptBox.value.trim();
            const model = document.getElementById('modelSelector').value;
            const persona = document.getElementById('personaSelector').value;
            const temp = parseFloat(document.getElementById('tempInput').value);

            let audioB64 = null;
            if (recordedAudioBlob) {
                audioB64 = await blobToBase64(recordedAudioBlob);
            }

            if (!prompt && (capturedVisualBase64 || audioB64 || uploadedFileBase64)) {
                prompt = "Przeanalizuj i opisz przesłane multimedia.";
            }

            if (!prompt) {
                alert('Proszę podać treść wiadomości lub pytanie.');
                return;
            }

            // Dodaj wiadomość usera do czatu
            appendUserMsg(prompt, capturedVisualBase64, uploadedFileMeta);
            promptBox.value = '';

            const sendBtn = document.getElementById('sendBtn');
            sendBtn.disabled = true;
            const startT = performance.now();

            const assistantMsg = appendAssistantPlaceholder();

            try {
                const payload = {
                    prompt: prompt,
                    model: model,
                    persona: persona,
                    temperature: temp,
                    visual_base64: capturedVisualBase64,
                    audio_base64: audioB64,
                    file_base64: uploadedFileBase64,
                    file_meta: uploadedFileMeta
                };

                const res = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const data = await res.json();
                const latency = Math.round(performance.now() - startT);
                document.getElementById('latencyTag').textContent = `Czas: ${latency} ms`;

                if (data.error) {
                    assistantMsg.querySelector('.message-content').textContent = '⚠️ Błąd Gemini API: ' + data.error;
                } else {
                    assistantMsg.querySelector('.message-content').textContent = data.response;
                }
            } catch (err) {
                assistantMsg.querySelector('.message-content').textContent = 'Błąd sieci: ' + err.message;
            } finally {
                sendBtn.disabled = false;
            }
        }

        function blobToBase64(blob) {
            return new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.onloadend = () => {
                    resolve(reader.result.split(',')[1]);
                };
                reader.onerror = reject;
                reader.readAsDataURL(blob);
            });
        }

        function appendUserMsg(text, imgB64, fileMeta) {
            const list = document.getElementById('chatList');
            const msg = document.createElement('div');
            msg.className = 'message message-user';

            let attachmentsHtml = '';
            if (imgB64) {
                attachmentsHtml += `<img src="${imgB64}" class="message-attachment">`;
            }
            if (fileMeta) {
                attachmentsHtml += `<div style="font-size:0.75rem; background:rgba(0,0,0,0.3); padding:4px 8px; border-radius:4px; margin-top:4px;">📎 Plik: ${fileMeta.name}</div>`;
            }

            msg.innerHTML = `
                <div class="message-meta">
                    <span>Ty</span>
                    <span>${new Date().toLocaleTimeString()}</span>
                </div>
                <div class="message-content">${escapeHtml(text || '(Zapytanie multimodalne)')}</div>
                ${attachmentsHtml}
            `;
            list.appendChild(msg);
            list.scrollTop = list.scrollHeight;
        }

        function appendAssistantPlaceholder() {
            const list = document.getElementById('chatList');
            const msg = document.createElement('div');
            msg.className = 'message message-assistant';
            msg.innerHTML = `
                <div class="message-meta">
                    <span>Gemini AI</span>
                    <span>Generowanie...</span>
                </div>
                <div class="message-content" style="font-style: italic; color: var(--text-muted);">
                    Analizowanie multimodalnych danych przez Gemini...
                </div>
            `;
            list.appendChild(msg);
            list.scrollTop = list.scrollHeight;
            return msg;
        }

        function escapeHtml(str) {
            if (!str) return '';
            return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
        }

        async function promptApiKey() {
            const current = prompt("Wklej swój klucz Google GenAI / Gemini API Key (zostanie zapisany na czas trwania sesji):");
            if (current && current.trim()) {
                const res = await fetch('/api/set_api_key', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ api_key: current.trim() })
                });
                const data = await res.json();
                document.getElementById('maskedKeyText').textContent = data.masked_key;
                alert('Zaktualizowano klucz API!');
            }
        }

        async function testConnection() {
            const res = await fetch('/api/status');
            const data = await res.json();
            alert(`Status Gemini Live Studio:\nUsługa: ${data.status}\nKlucz API: ${data.has_key ? 'Aktywny' : 'Brak'}\nModel domyślny: ${data.default_model}`);
        }
    </script>
</body>
</html>
"""

@app.route("/", methods=["GET"])
def index():
    return render_template_string(
        HTML_TEMPLATE,
        masked_key=get_masked_key(CURRENT_API_KEY),
        personas=PERSONAS,
        models=MODELS
    )

@app.route("/api/status", methods=["GET"])
def api_status():
    global CURRENT_API_KEY
    return jsonify({
        "status": "online",
        "service": "Gemini Omni Live Studio",
        "port": 7865,
        "has_key": bool(CURRENT_API_KEY),
        "masked_key": get_masked_key(CURRENT_API_KEY),
        "default_model": "gemini-2.5-flash",
        "available_models": [m["id"] for m in MODELS]
    })

@app.route("/api/set_api_key", methods=["POST"])
def api_set_key():
    global CURRENT_API_KEY
    data = request.get_json() or {}
    key = data.get("api_key", "").strip()
    if key:
        CURRENT_API_KEY = key
        return jsonify({"status": "success", "masked_key": get_masked_key(CURRENT_API_KEY)})
    return jsonify({"status": "error", "message": "Pusty klucz"}), 400

@app.route("/api/chat", methods=["POST"])
def api_chat():
    global CURRENT_API_KEY
    req_data = request.get_json(silent=True) or {}

    prompt = req_data.get("prompt")
    if not prompt or not str(prompt).strip():
        return jsonify({
            "error": "Brak promptu",
            "message": "Proszę podać treść wiadomości lub pytanie."
        }), 400
    prompt = str(prompt).strip()

    try:
        temperature = float(req_data.get("temperature", 0.7))
    except (ValueError, TypeError):
        temperature = 0.7

    model_id = req_data.get("model", "gemini-2.5-flash")
    persona_id = req_data.get("persona", "visual_expert")

    visual_b64 = req_data.get("visual_base64")
    audio_b64 = req_data.get("audio_base64")
    file_b64 = req_data.get("file_base64")
    file_meta = req_data.get("file_meta") or {}

    if not CURRENT_API_KEY:
        return jsonify({
            "error": "Brak skonfigurowanego klucza API Gemini. Kliknij 'Zmień' na górnym pasku i podaj swój klucz Google GenAI."
        }), 400

    try:
        client = genai.Client(api_key=CURRENT_API_KEY)
        persona_info = PERSONAS.get(persona_id, PERSONAS["visual_expert"])
        config = types.GenerateContentConfig(
            system_instruction=persona_info["system_instruction"],
            temperature=temperature
        )

        contents = []

        # 1. Tekst zapytania
        contents.append(prompt)

        # 2. Obraz z kamery lub zrzut ekranu
        if visual_b64:
            raw_img = visual_b64.split(",")[-1]
            img_bytes = base64.b64decode(raw_img)
            mime = "image/jpeg"
            if "data:image/png" in visual_b64:
                mime = "image/png"
            elif "data:image/webp" in visual_b64:
                mime = "image/webp"
            contents.append(types.Part.from_bytes(data=img_bytes, mime_type=mime))

        # 3. Nagranie audio
        if audio_b64:
            audio_bytes = base64.b64decode(audio_b64)
            contents.append(types.Part.from_bytes(data=audio_bytes, mime_type="audio/wav"))

        # 4. Plik wgrany przez użytkownika
        if file_b64:
            raw_f = file_b64.split(",")[-1]
            f_bytes = base64.b64decode(raw_f)
            mime = file_meta.get("type") or "application/octet-stream"
            # Dla dokumentów tekstowych i kodu przekaż jako text jeśli to możliwe
            if mime.startswith("text/") or file_meta.get("name", "").endswith((".py", ".js", ".ts", ".json", ".md", ".txt")):
                try:
                    text_content = f_bytes.decode("utf-8", errors="ignore")
                    contents.append(f"--- Zawartość pliku {file_meta.get('name')}: ---\n{text_content}")
                except Exception:
                    contents.append(types.Part.from_bytes(data=f_bytes, mime_type=mime))
            else:
                contents.append(types.Part.from_bytes(data=f_bytes, mime_type=mime))

        # Wywołaj API Gemini
        response = client.models.generate_content(
            model=model_id,
            contents=contents,
            config=config
        )

        reply_text = response.text or "(Otrzymano pustą odpowiedź od modelu)"
        return jsonify({
            "response": reply_text,
            "model": model_id,
            "persona": persona_info["name"]
        })

    except Exception as e:
        err_msg = str(e)
        traceback.print_exc()
        return jsonify({"error": f"Błąd komunikacji z modelem: {err_msg}"}), 500

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Gemini Omni Live Studio WebUI")
    parser.add_argument("--port", type=int, default=7865, help="Port serwera (domyślnie 7865)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host (domyślnie 0.0.0.0)")
    args = parser.parse_args()

    print(f"============================================================")
    print(f"  Gemini Omni Live Studio (Google GenAI)")
    print(f"  Uruchomiono na: http://localhost:{args.port}")
    print(f"  Dostęp sieciowy: http://{args.host}:{args.port}")
    print(f"============================================================")
    app.run(host=args.host, port=args.port, debug=False, threaded=True)
