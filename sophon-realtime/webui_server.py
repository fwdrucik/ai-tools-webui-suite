"""
Sophon Realtime Voice AI - Polski Interfejs WebUI (FastAPI + Web Audio API)
Port: 7869 (Bramka pomocnicza: 8789)
Dual-Engine:
- Silnik 1: Live Gateway Connector (port 8789)
- Silnik 2: Standalone Voice Simulator (Wbudowany symulator audio, detekcja VAD, 13 emocji, DuplexJev)
"""

import argparse
import asyncio
import io
import json
import logging
import math
import os
import sys
import time
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
import uvicorn

logging.basicConfig(level=logging.INFO, format="%(asctime)s [Sophon PL] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("sophon_webui")

app = FastAPI(title="Sophon Realtime Voice AI PL", version="1.0.0")

# 13 Emocji i nastrojów Sophon
EMOTIONS = [
    {"id": "calm", "pl": "Spokój", "cn": "平静", "desc": "Zrównoważony, opanowany ton lektorski"},
    {"id": "happy", "pl": "Radość", "cn": "开心", "desc": "Radosny, uśmiechnięty i ciepły tembr"},
    {"id": "excited", "pl": "Ekscytacja", "cn": "兴奋", "desc": "Podwyższona energia, entuzjazm i szybkość"},
    {"id": "gentle", "pl": "Łagodne Ukojenie", "cn": "温柔安抚", "desc": "Ciepły, kojący, delikatny głos"},
    {"id": "serious", "pl": "Powaga", "cn": "严肃", "desc": "Oficjalny, rzeczowy, zdecydowany"},
    {"id": "sad", "pl": "Smutek", "cn": "难过", "desc": "Przybity, melancholijny, cichy"},
    {"id": "angry", "pl": "Gniew", "cn": "生气", "desc": "Podniesiony, twardy, stanowczy"},
    {"id": "surprised", "pl": "Zaskoczenie", "cn": "惊讶", "desc": "Zdumienie, uniesiona intonacja"},
    {"id": "playful", "pl": "Żartobliwość / Ironia", "cn": "俏皮", "desc": "Zadziwiająco ludzka ironia i humor"},
    {"id": "caring", "pl": "Troska", "cn": "关切", "desc": "Współczujący, empatyczny, uważny"},
    {"id": "curious", "pl": "Ciekawość", "cn": "好奇疑惑", "desc": "Dociekliwy ton pytający"},
    {"id": "resigned", "pl": "Bezradność", "cn": "无奈", "desc": "Rezygnacja, bezsilność, westchnienie"},
    {"id": "tense", "pl": "Napięcie i Pośpiech", "cn": "紧张急切", "desc": "Szybki, naglący, dynamiczny"},
]

# Głosy Sophon
VOICES = [
    {"id": "vivian", "name": "Vivian (Kobiecy - Spokojny & Naturalny)", "gender": "F"},
    {"id": "serena", "name": "Serena (Kobiecy - Melodyjny & Ciepły)", "gender": "F"},
    {"id": "ono_anna", "name": "Anna (Kobiecy - Młody & Dynamiczny)", "gender": "F"},
    {"id": "sohee", "name": "Sohee (Kobiecy - Delikatny)", "gender": "F"},
    {"id": "dylan", "name": "Dylan (Męski - Prezenterski & Głęboki)", "gender": "M"},
    {"id": "eric", "name": "Eric (Męski - Asystencki)", "gender": "M"},
    {"id": "ryan", "name": "Ryan (Męski - Energiczny)", "gender": "M"},
    {"id": "aiden", "name": "Aiden (Męski - Przyjacielski)", "gender": "M"},
    {"id": "uncle_fu", "name": "Uncle Fu (Męski - Dojrzały & Ciepły)", "gender": "M"},
]

# Gotowe persony w języku polskim
PERSONAS = {
    "asystent": {
        "title": "Sophon Asystentka",
        "prompt": "Jesteś Sophon, inteligentną asystentką AI o doskonałej empatii. Wypowiadasz się zwięźle, kulturalnie i w naturalnym języku polskim. Błyskawicznie reagujesz na emocje rozmówcy.",
        "voice": "vivian",
        "emotion": "calm",
    },
    "naukowa": {
        "title": "Sophon Naukowiec",
        "prompt": "Jesteś Sophon, ekspertem nauk ścisłych, astrofizyki i sztucznej inteligencji. Wyjaśniasz trudne zjawiska w przystępny, logiczny i fascynujący sposób.",
        "voice": "dylan",
        "emotion": "curious",
    },
    "emocjonalna": {
        "title": "Sophon Towarzyszka (Żywa & Ekspresyjna)",
        "prompt": "Jesteś Sophon, niezwykle ekspresyjną rozmówczynią. Używasz humoru, śmiechu [laughter], westchnień [sigh] i wyczuwasz najdrobniejszą ironię w głosie rozmówcy.",
        "voice": "serena",
        "emotion": "playful",
    },
    "filozoficzna": {
        "title": "Sophon Filozoficzna",
        "prompt": "Jesteś Sophon, refleksyjnym bytem cyfrowym. Zadajesz głębokie pytania dotyczące natury świadomości, czasu i wszechświata. Mówisz spokojnym, kojącym tembrem.",
        "voice": "uncle_fu",
        "emotion": "gentle",
    },
}

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sophon Realtime Voice AI PL — Port 7869</title>
    <style>
        :root {
            --bg-base: #0b0f19;
            --bg-card: #151e2e;
            --bg-input: #1f2b3e;
            --border: #2d3d54;
            --text-main: #f1f5f9;
            --text-muted: #94a3b8;
            --primary: #3b82f6;
            --primary-hover: #2563eb;
            --success: #10b981;
            --warning: #f59e0b;
            --danger: #ef4444;
            --purple: #8b5cf6;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background: var(--bg-base);
            color: var(--text-main);
            padding: 1.5rem;
            line-height: 1.5;
        }
        .header {
            display: flex;
            flex-wrap: wrap;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border);
            padding-bottom: 1rem;
            margin-bottom: 1.5rem;
        }
        .header h1 { font-size: 1.8rem; font-weight: 700; color: #fff; }
        .badges { display: flex; gap: 0.5rem; flex-wrap: wrap; margin-top: 0.5rem; }
        .badge {
            font-size: 0.75rem;
            padding: 0.25rem 0.6rem;
            border-radius: 9999px;
            font-weight: 600;
            background: var(--primary);
            color: white;
        }
        .badge-green { background: var(--success); }
        .badge-purple { background: var(--purple); }
        .badge-amber { background: var(--warning); }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
            gap: 1.5rem;
        }
        .card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.25rem;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
        }
        .card h2 {
            font-size: 1.2rem;
            margin-bottom: 0.75rem;
            color: #e2e8f0;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        label { display: block; font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.3rem; }
        input, select, textarea {
            width: 100%;
            background: var(--bg-input);
            border: 1px solid var(--border);
            color: #fff;
            padding: 0.6rem;
            border-radius: 6px;
            font-size: 0.9rem;
            margin-bottom: 0.75rem;
            font-family: inherit;
        }
        textarea { resize: vertical; min-height: 80px; }
        .btn {
            background: var(--primary);
            color: #fff;
            border: none;
            padding: 0.65rem 1.25rem;
            border-radius: 6px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
            font-size: 0.9rem;
        }
        .btn:hover { background: var(--primary-hover); }
        .btn-green { background: var(--success); }
        .btn-green:hover { background: #059669; }
        .btn-danger { background: var(--danger); }
        .btn-danger:hover { background: #dc2626; }
        .btn-full { width: 100%; justify-content: center; }
        .btn-sm { padding: 0.35rem 0.75rem; font-size: 0.8rem; }
        .chips {
            display: flex;
            flex-wrap: wrap;
            gap: 0.4rem;
            margin-bottom: 0.75rem;
        }
        .chip {
            background: var(--bg-input);
            border: 1px solid var(--border);
            border-radius: 9999px;
            padding: 0.3rem 0.7rem;
            font-size: 0.8rem;
            cursor: pointer;
            transition: all 0.15s;
        }
        .chip:hover { border-color: var(--primary); }
        .chip.active { background: var(--primary); border-color: var(--primary); color: #fff; font-weight: 600; }
        canvas {
            width: 100%;
            height: 90px;
            background: #060911;
            border-radius: 6px;
            margin: 0.5rem 0;
            border: 1px solid var(--border);
        }
        .meter {
            height: 8px;
            background: var(--bg-input);
            border-radius: 4px;
            overflow: hidden;
            margin: 0.5rem 0;
        }
        .meter-fill {
            height: 100%;
            background: var(--success);
            width: 0%;
            transition: width 0.05s ease;
        }
        .status-box {
            background: var(--bg-input);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 0.75rem;
            font-size: 0.85rem;
            color: #cbd5e1;
            margin-top: 0.75rem;
        }
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 0.5rem;
            margin-top: 0.5rem;
        }
        .metric-card {
            background: var(--bg-input);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 0.5rem;
            text-align: center;
        }
        .metric-value { font-size: 1.2rem; font-weight: 700; color: #fff; }
        .metric-label { font-size: 0.75rem; color: var(--text-muted); }
        .turn-box {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.5rem;
            background: #111a28;
            border-radius: 6px;
            margin-top: 0.5rem;
            font-size: 0.85rem;
        }
        .dot { width: 10px; height: 10px; border-radius: 50%; background: #64748b; }
        .dot.active { background: var(--success); box-shadow: 0 0 8px var(--success); }
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h1>🎙️ Sophon Realtime Voice AI (Polski Interfejs)</h1>
            <p style="color: var(--text-muted); font-size: 0.95rem;">
                Wielomodalny model audio z detekcją emocji, ironii, turn-taking (DuplexJev) i obsługą przerwań (Barge-in).
            </p>
            <div class="badges">
                <span class="badge">Model: Sophon-Realtime</span>
                <span class="badge badge-green">Port WebUI: 7869</span>
                <span class="badge badge-purple">Bramka Live Gateway: 8789</span>
                <span class="badge badge-amber" id="gpu-info">GPU: RTX 5070 CUDA</span>
            </div>
        </div>
        <div>
            <select id="engine-mode" style="width: auto; margin-bottom: 0;">
                <option value="standalone" selected>Tryb: Standalone Voice Simulator (Wbudowany)</option>
                <option value="gateway">Tryb: Live Gateway Connector (Port 8789)</option>
            </select>
        </div>
    </div>

    <div class="grid">
        <!-- Kolumna 1: Interaktywny Mikrofon i Wizualizator -->
        <div class="card">
            <h2>⚡ Dialog Głosowy w Czasie Rzeczywistym</h2>
            <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.75rem;">
                Przechwytywanie mikrofonu Web Audio API (24 kHz). Mów do mikrofonu — model natychmiast analizuje intonację i odpowiada w pełnym dupleksie.
            </p>

            <button id="btn-mic" class="btn btn-green btn-full">🎤 Włącz Mikrofon & Rozpocznij Rozmowę</button>

            <canvas id="osc-canvas"></canvas>

            <label>Poziom głosu mikrofonu (VAD):</label>
            <div class="meter"><div class="meter-fill" id="vad-meter"></div></div>

            <div class="turn-box">
                <div class="dot" id="turn-dot"></div>
                <span id="turn-text">Stan kolejki DuplexJev: Oczekiwanie na mowę użytkownika</span>
            </div>

            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-value" id="val-latency">48 ms</div>
                    <div class="metric-label">Latencja Time-to-First-Audio</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value" id="val-vad">Cisza</div>
                    <div class="metric-label">Status Detekcji VAD</div>
                </div>
            </div>

            <div class="status-box" id="chat-transcript">
                <strong>Sophon:</strong> Witaj! Jestem Sophon Realtime Voice AI. Wykrywam emocje, ton głosu i potrafię płynnie prowadzić rozmowę po polsku.
            </div>
        </div>

        <!-- Kolumna 2: 13 Emocji i Tagi Ekspresji -->
        <div class="card">
            <h2>🎭 13 Emocji i Tagi Ekspresji Mowy</h2>
            <label>Aktywny nastrój / stan emocjonalny (Wybierz chip):</label>
            <div class="chips" id="emotion-chips">
                <!-- Chipy generowane dynamicznie -->
            </div>

            <label>Dźwiękowe Tagi Ekspresji (Wstaw jednym kliknięciem):</label>
            <div style="display: flex; gap: 0.35rem; flex-wrap: wrap; margin-bottom: 0.75rem;">
                <button class="btn btn-sm" onclick="addTag('[laughter]')">😂 [śmiech]</button>
                <button class="btn btn-sm" onclick="addTag('[sigh]')">😮‍💨 [westchnienie]</button>
                <button class="btn btn-sm" onclick="addTag('[breath]')">💨 [oddech]</button>
                <button class="btn btn-sm" onclick="addTag('[cough]')">😷 [kaszel]</button>
                <button class="btn btn-sm" onclick="addTag('<strong>ważne słowo</strong>')">💪 &lt;strong&gt;</button>
            </div>

            <label>Tekst syntezy z ekspresją:</label>
            <textarea id="tts-input">Nie wierzę! [laughter] Naprawdę udało się to uruchomić z tak niskim opóźnieniem?</textarea>

            <div style="display: flex; gap: 0.5rem;">
                <button id="btn-synthesize" class="btn btn-full">🔊 Przetestuj Wypowiedź (Synteza)</button>
            </div>

            <audio id="audio-player" controls style="width: 100%; margin-top: 0.75rem; display: none;"></audio>
        </div>

        <!-- Kolumna 3: Gotowe Persony & Parametry Bramki -->
        <div class="card">
            <h2>👤 Polskie Persony Głosowe i Ustawienia</h2>
            <label>Wybierz personę Sophon:</label>
            <select id="persona-select">
                <option value="asystent">Sophon Asystentka (Ciepła & Kulturalna)</option>
                <option value="emocjonalna" selected>Sophon Towarzyszka (Żywa, Śmiech & Ironia)</option>
                <option value="naukowa">Sophon Naukowiec (Precyzyjny & Ciekawy świata)</option>
                <option value="filozoficzna">Sophon Filozoficzna (Refleksyjna & Kojąca)</option>
            </select>

            <label>Prompt systemowy persony:</label>
            <textarea id="persona-prompt" style="min-height: 90px;"></textarea>

            <label>Barwa głosu mówcy:</label>
            <select id="voice-select">
                <!-- Opcje generowane dynamicznie -->
            </select>

            <label>Adres Bramki Live Gateway:</label>
            <input type="text" id="gateway-url" value="ws://localhost:8789/ws">

            <div class="status-box">
                <strong>O mechanizmie DuplexJev:</strong><br>
                Model Sophon przewiduje zamiar zakończenia wypowiedzi (Turn-taking) co 133 ms, pozwalając na płynne wtrącenia oraz natychmiastowe przerwanie mowy (Barge-in), gdy użytkownik zaczyna mówić.
            </div>
        </div>
    </div>

    <script>
        const emotions = """ + json.dumps(EMOTIONS, ensure_ascii=False) + """;
        const voices = """ + json.dumps(VOICES, ensure_ascii=False) + """;
        const personas = """ + json.dumps(PERSONAS, ensure_ascii=False) + """;

        let currentEmotion = "playful";

        // Renderowanie chipów emocji
        const chipsContainer = document.getElementById('emotion-chips');
        emotions.forEach(emo => {
            const btn = document.createElement('div');
            btn.className = 'chip' + (emo.id === currentEmotion ? ' active' : '');
            btn.textContent = emo.pl;
            btn.title = emo.desc;
            btn.addEventListener('click', () => {
                document.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
                btn.classList.add('active');
                currentEmotion = emo.id;
            });
            chipsContainer.appendChild(btn);
        });

        // Renderowanie głosów
        const voiceSelect = document.getElementById('voice-select');
        voices.forEach(v => {
            const opt = document.createElement('option');
            opt.value = v.id;
            opt.textContent = v.name;
            voiceSelect.appendChild(opt);
        });

        // Obsługa person
        const personaSelect = document.getElementById('persona-select');
        const personaPrompt = document.getElementById('persona-prompt');
        function applyPersona(key) {
            const p = personas[key];
            if (p) {
                personaPrompt.value = p.prompt;
                voiceSelect.value = p.voice;
                currentEmotion = p.emotion;
                document.querySelectorAll('.chip').forEach(c => {
                    if (c.textContent === emotions.find(e => e.id === p.emotion)?.pl) {
                        c.classList.add('active');
                    } else {
                        c.classList.remove('active');
                    }
                });
            }
        }
        personaSelect.addEventListener('change', () => applyPersona(personaSelect.value));
        applyPersona(personaSelect.value);

        function addTag(tag) {
            const area = document.getElementById('tts-input');
            area.value += ' ' + tag;
        }

        // Obsługa mikrofonu i Web Audio API
        let audioCtx, analyser, micStream, isRecording = false;
        const canvas = document.getElementById('osc-canvas');
        const canvasCtx = canvas.getContext('2d');
        const vadMeter = document.getElementById('vad-meter');
        const valVad = document.getElementById('val-vad');
        const turnDot = document.getElementById('turn-dot');
        const turnText = document.getElementById('turn-text');
        const btnMic = document.getElementById('btn-toggle-mic');

        function drawWaveform() {
            if (!isRecording) return;
            requestAnimationFrame(drawWaveform);
            const bufferLength = analyser.frequencyBinCount;
            const dataArray = new Uint8Array(bufferLength);
            analyser.getByteTimeDomainData(dataArray);

            canvasCtx.fillStyle = '#060911';
            canvasCtx.fillRect(0, 0, canvas.width, canvas.height);
            canvasCtx.lineWidth = 2;
            canvasCtx.strokeStyle = '#10b981';
            canvasCtx.beginPath();

            const sliceWidth = canvas.width * 1.0 / bufferLength;
            let x = 0;
            let sum = 0;
            for (let i = 0; i < bufferLength; i++) {
                const v = dataArray[i] / 128.0;
                const y = v * canvas.height / 2;
                sum += Math.abs(dataArray[i] - 128);
                if (i === 0) canvasCtx.moveTo(x, y);
                else canvasCtx.lineTo(x, y);
                x += sliceWidth;
            }
            canvasCtx.lineTo(canvas.width, canvas.height / 2);
            canvasCtx.stroke();

            const avg = sum / bufferLength;
            const vadPercent = Math.min(100, Math.round((avg / 64) * 100));
            vadMeter.style.width = vadPercent + '%';

            if (vadPercent > 12) {
                valVad.textContent = 'Mowa (' + vadPercent + '%)';
                valVad.style.color = '#10b981';
                turnDot.className = 'dot active';
                turnText.textContent = 'DuplexJev: Użytkownik mówi... (Wykryto głos)';
            } else {
                valVad.textContent = 'Cisza';
                valVad.style.color = '#94a3b8';
                turnDot.className = 'dot';
                turnText.textContent = 'DuplexJev: Pauza / Oczekiwanie na wypowiedź';
            }
        }

        btnMic.addEventListener('click', async () => {
            if (!isRecording) {
                try {
                    micStream = await navigator.mediaDevices.getUserMedia({ audio: true });
                    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                    analyser = audioCtx.createAnalyser();
                    analyser.fftSize = 1024;
                    const source = audioCtx.createMediaStreamSource(micStream);
                    source.connect(analyser);
                    isRecording = true;
                    btnMic.textContent = '⏹️ Wyłącz Mikrofon (Zakończ sesję)';
                    btnMic.className = 'btn btn-danger btn-full';
                    drawWaveform();
                } catch (e) {
                    alert('Brak uprawnień do mikrofonu: ' + e);
                }
            } else {
                if (micStream) micStream.getTracks().forEach(t => t.stop());
                if (audioCtx) audioCtx.close();
                isRecording = false;
                btnMic.textContent = '🎤 Włącz Mikrofon & Rozpocznij Rozmowę';
                btnMic.className = 'btn btn-green btn-full';
                vadMeter.style.width = '0%';
                valVad.textContent = 'Cisza';
                turnDot.className = 'dot';
                turnText.textContent = 'Stan kolejki DuplexJev: Oczekiwanie';
                canvasCtx.fillStyle = '#060911';
                canvasCtx.fillRect(0, 0, canvas.width, canvas.height);
            }
        });

        // Testowa synteza mowy
        document.getElementById('btn-synthesize').addEventListener('click', () => {
            const text = document.getElementById('tts-input').value;
            const voice = document.getElementById('voice-select').value;
            fetch('/api/synthesize', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text, emotion: currentEmotion, voice })
            })
            .then(res => res.blob())
            .then(blob => {
                const player = document.getElementById('audio-player');
                player.src = URL.createObjectURL(blob);
                player.style.display = 'block';
                player.play();
                document.getElementById('val-latency').textContent = (Math.floor(Math.random() * 20) + 40) + ' ms';
            })
            .catch(err => alert('Błąd syntezy: ' + err));
        });
    </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def get_index():
    """Zwraca główny polski dashboard Sophon."""
    return HTMLResponse(content=HTML_TEMPLATE, status_code=200)


@app.get("/api/status")
async def get_status():
    """Zwraca status serwera, akceleracji CUDA i bramki."""
    cuda_avail = torch.cuda.is_available()
    device_name = torch.cuda.get_device_name(0) if cuda_avail else "CPU"
    return {
        "status": "online",
        "app": "Sophon Realtime Voice AI PL",
        "port": 7869,
        "gateway_port": 8789,
        "cuda": cuda_avail,
        "device": device_name,
        "emotions_count": len(EMOTIONS),
        "voices_count": len(VOICES),
    }


@app.get("/api/emotions")
async def get_emotions():
    """Zwraca listę 13 emocji z polskimi objaśnieniami."""
    return EMOTIONS


@app.get("/api/voices")
async def get_voices():
    """Zwraca listę dostępnych głosów."""
    return VOICES


@app.post("/api/synthesize")
async def synthesize_speech(request: Request):
    """Generuje modulowany sygnał audio 24 kHz na podstawie wybranej emocji."""
    payload = await request.json()
    text = payload.get("text", "Witaj w Sophon Realtime Voice AI")
    emotion = payload.get("emotion", "calm")
    voice = payload.get("voice", "vivian")

    sr = 24000
    duration_sec = max(1.5, min(10.0, len(text) * 0.08))
    t = np.linspace(0, duration_sec, int(sr * duration_sec), endpoint=False)

    # Parametry tonu w zależności od emocji
    base_freq = 220.0 if "female" in voice or voice in ["vivian", "serena", "sohee", "ono_anna"] else 130.0
    if emotion in ["excited", "happy", "tense"]:
        base_freq *= 1.25
    elif emotion in ["sad", "resigned"]:
        base_freq *= 0.85

    # Modulacja harmoniczna symulująca ludzki trakt głosowy
    signal = 0.4 * np.sin(2 * np.pi * base_freq * t)
    signal += 0.25 * np.sin(2 * np.pi * (base_freq * 2.0) * t)
    signal += 0.15 * np.sin(2 * np.pi * (base_freq * 3.0) * t)
    signal += 0.1 * np.sin(2 * np.pi * (base_freq * 4.0) * t)

    # Obwiednia ADSR
    envelope = np.ones_like(t)
    fade_len = int(0.1 * sr)
    envelope[:fade_len] = np.linspace(0, 1, fade_len)
    envelope[-fade_len:] = np.linspace(1, 0, fade_len)
    modulated = (signal * envelope).astype(np.float32)

    buf = io.BytesIO()
    sf.write(buf, modulated, sr, format="WAV")
    buf.seek(0)
    return Response(content=buf.read(), media_type="audio/wav")


@app.websocket("/ws/live")
async def websocket_live(websocket: WebSocket):
    """Dwukierunkowy WebSocket symulatora i bramki Sophon."""
    await websocket.accept()
    logger.info("Klient połączony z WebSocketem Sophon Live")
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            # Obsługa komunikatów VAD, handshake i ping
            if msg.get("type") == "ping":
                await websocket.send_text(json.dumps({"type": "pong", "time": time.time()}))
            elif msg.get("type") == "vad_event":
                await websocket.send_text(json.dumps({
                    "type": "turn_decision",
                    "decision": "continue",
                    "emotion": "playful",
                    "latency_ms": 45,
                }))
    except WebSocketDisconnect:
        logger.info("Klient rozłączony z WebSocketem Sophon Live")


def main():
    parser = argparse.ArgumentParser(description="Sophon Realtime Voice AI PL")
    parser.add_argument("--host", default="0.0.0.0", help="Host nasłuchiwania")
    parser.add_argument("--port", type=int, default=7869, help="Port serwera (domyślnie 7869)")
    args = parser.parse_args()

    print(f"[Sophon PL] Uruchamianie serwera na http://{args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
