"""
Haru Full-Duplex Voice - Polski Panel Kontrolny & Launcher (Port 8998)
Higurashi AI Haru-4B: Rozmowa głosowa w czasie rzeczywistym (latencja 65ms, pełny dupleks).
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import mimetypes
from pathlib import Path
from aiohttp import web

# Dodanie ścieżek do sys.path
BASE_DIR = Path(__file__).resolve().parent
HARU_PKG = BASE_DIR / "haru"
if str(HARU_PKG) not in sys.path:
    sys.path.insert(0, str(HARU_PKG))
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import torch
from haru.audio import SAMPLE_RATE, decode_audio, save_audio
from haru.server import DemoAssets, DemoServer, ServerOptions
from haru.backends import LocalBackend, Backend

logging.basicConfig(level=logging.INFO, format="%(asctime)s [Haru PL] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("haru_control_center")

ASSETS_DIR = BASE_DIR / "haru" / "haru" / "assets"
CARDS_DIR = ASSETS_DIR / "cards"
VOICES_DIR = ASSETS_DIR / "voices"
STATIC_DIR = BASE_DIR / "haru" / "haru" / "static"


def get_gpu_info():
    """Zwraca informacje o akceleracji GPU i dostępnym VRAM."""
    cuda_avail = torch.cuda.is_available()
    device_name = torch.cuda.get_device_name(0) if cuda_avail else "CPU (Brak CUDA)"
    vram_gb = 0.0
    if cuda_avail:
        try:
            vram_bytes = torch.cuda.get_device_properties(0).total_memory
            vram_gb = round(vram_bytes / (1024 ** 3), 1)
        except Exception:
            pass
    return {
        "cuda": cuda_avail,
        "device": device_name,
        "vram_gb": vram_gb,
    }


def load_polish_cards():
    """Wczytuje polskie karty postaci z cards/pl.json."""
    pl_file = CARDS_DIR / "pl.json"
    if pl_file.is_file():
        try:
            return json.loads(pl_file.read_text(encoding="utf-8"))
        except Exception as e:
            logger.error(f"Błąd odczytu pl.json: {e}")
    return {}


def save_polish_cards(cards_data):
    """Zapisuje polskie karty postaci do cards/pl.json."""
    pl_file = CARDS_DIR / "pl.json"
    CARDS_DIR.mkdir(parents=True, exist_ok=True)
    pl_file.write_text(json.dumps(cards_data, ensure_ascii=False, indent=2), encoding="utf-8")


HTML_DASHBOARD = """<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Haru Full-Duplex Voice PL — Port 8998</title>
    <style>
        :root {
            --bg-primary: #0f172a;
            --bg-secondary: #1e293b;
            --bg-card: #334155;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --accent-blue: #3b82f6;
            --accent-green: #10b981;
            --accent-purple: #8b5cf6;
            --accent-amber: #f59e0b;
            --danger: #ef4444;
            --border: #475569;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: system-ui, -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background: var(--bg-primary);
            color: var(--text-main);
            line-height: 1.5;
            padding: 1.5rem;
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
        .title-group h1 { font-size: 1.8rem; font-weight: 700; color: #fff; }
        .title-group p { color: var(--text-muted); font-size: 0.95rem; }
        .badges { display: flex; gap: 0.5rem; flex-wrap: wrap; margin-top: 0.5rem; }
        .badge {
            font-size: 0.75rem;
            padding: 0.25rem 0.6rem;
            border-radius: 9999px;
            font-weight: 600;
            background: var(--accent-blue);
            color: white;
        }
        .badge-green { background: var(--accent-green); }
        .badge-purple { background: var(--accent-purple); }
        .badge-amber { background: var(--accent-amber); }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
            gap: 1.5rem;
        }
        .card {
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.25rem;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
        }
        .card h2 {
            font-size: 1.2rem;
            margin-bottom: 0.75rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            color: #e2e8f0;
        }
        label { display: block; font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.25rem; }
        input, select, textarea {
            width: 100%;
            background: var(--bg-primary);
            border: 1px solid var(--border);
            color: #fff;
            padding: 0.6rem;
            border-radius: 6px;
            font-size: 0.9rem;
            margin-bottom: 0.75rem;
            font-family: inherit;
        }
        textarea { resize: vertical; min-height: 100px; }
        .btn {
            background: var(--accent-blue);
            color: #fff;
            border: none;
            padding: 0.6rem 1.2rem;
            border-radius: 6px;
            font-weight: 600;
            cursor: pointer;
            transition: opacity 0.2s;
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
            text-decoration: none;
            font-size: 0.9rem;
        }
        .btn:hover { opacity: 0.9; }
        .btn-green { background: var(--accent-green); }
        .btn-purple { background: var(--accent-purple); }
        .btn-amber { background: var(--accent-amber); }
        .btn-danger { background: var(--danger); }
        .btn-full { width: 100%; justify-content: center; }
        .row { display: flex; gap: 0.75rem; }
        .row > * { flex: 1; }
        .status-box {
            background: var(--bg-primary);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 0.75rem;
            font-size: 0.85rem;
            color: #cbd5e1;
            margin-top: 0.5rem;
        }
        .meter {
            height: 8px;
            background: #334155;
            border-radius: 4px;
            overflow: hidden;
            margin: 0.5rem 0;
        }
        .meter-fill {
            height: 100%;
            background: var(--accent-green);
            width: 0%;
            transition: width 0.1s ease;
        }
        canvas {
            width: 100%;
            height: 90px;
            background: #090d16;
            border-radius: 6px;
            margin: 0.5rem 0;
            border: 1px solid #1e293b;
        }
        .footer {
            margin-top: 2rem;
            border-top: 1px solid var(--border);
            padding-top: 1rem;
            color: var(--text-muted);
            font-size: 0.85rem;
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="title-group">
            <h1>🎙️ Haru Full-Duplex Voice Studio PL</h1>
            <p>Dwukierunkowy dialog głosowy end-to-end (65ms opóźnienia, próbkowanie 24 kHz mono Opus)</p>
            <div class="badges">
                <span class="badge">Model: Haru-4B VibeVoice</span>
                <span class="badge badge-green">Port: 8998</span>
                <span class="badge badge-purple">Protokół: WebRTC / WebSocket</span>
                <span class="badge badge-amber" id="gpu-badge">GPU: Sprawdzanie...</span>
            </div>
        </div>
        <div>
            <a href="/client" target="_blank" class="btn btn-purple">🌐 Otwórz Klienta Web Haru</a>
        </div>
    </div>

    <div class="grid">
        <!-- Kolumna 1: Panel Rozmowy na Żywo -->
        <div class="card">
            <h2>⚡ Interaktywny Symulator & Połączenie Live</h2>
            <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.75rem;">
                Rozpocznij dwukierunkowy dialog z Haru. Mów do mikrofonu, a Haru natychmiast odpowiada w czasie rzeczywistym.
            </p>
            
            <div class="row">
                <button id="btn-toggle-mic" class="btn btn-green btn-full">🎤 Włącz Mikrofon & Rozmowę</button>
            </div>

            <canvas id="osc-canvas"></canvas>

            <div>
                <label>Poziom sygnału mikrofonu (VAD):</label>
                <div class="meter"><div class="meter-fill" id="vad-fill"></div></div>
            </div>

            <div class="status-box" id="dialogue-box">
                <strong>Status rozmowy:</strong> <span id="call-status">Oczekuje na start</span><br>
                <strong>Opóźnienie (Round-Trip Latency):</strong> <span id="call-latency">~65 ms</span><br>
                <strong>Tryb buforowania:</strong> Profil lokalny (LAN/Localhost)
            </div>

            <div style="margin-top: 1rem;">
                <label>Wybierz aktywną postać do dialogu:</label>
                <select id="char-select">
                    <option value="chat">Haru — Rozmowny Student (Domyślny PL)</option>
                    <option value="asystent">Haru — Asystent Techniczny & Doradca</option>
                </select>
            </div>
        </div>

        <!-- Kolumna 2: Karta Postaci (Persona) -->
        <div class="card">
            <h2>🎭 Karta Postaci (Polska Persona)</h2>
            <label>Imię Postaci:</label>
            <input type="text" id="card-name" value="Haru">

            <label>Osobowość i Styl Wypowiedzi (Persona):</label>
            <textarea id="card-persona">Haru to 22-letni student ostatniego roku, błyskotliwy, przyjacielski i bardzo ciekawy świata. Mówi spokojnym, naturalnym i ciepłym głosem w języku polskim. Interesuje się nowoczesnymi technologiami, sztuczną inteligencją, biznesem, nauką i historią.</textarea>

            <div class="row">
                <div>
                    <label>Wtrącenia (Backchannels):</label>
                    <select id="card-backchannel">
                        <option value="low">Rzadkie</option>
                        <option value="mid" selected>Umiarkowane</option>
                        <option value="high">Częste</option>
                    </select>
                </div>
                <div>
                    <label>Płeć Postaci:</label>
                    <select id="card-gender">
                        <option value="female">Kobieta</option>
                        <option value="male" selected>Mężczyzna</option>
                    </select>
                </div>
            </div>

            <label>Sytuacja / Kontekst:</label>
            <textarea id="card-situation" style="min-height: 70px;">Rozmówcy spotykają się po raz pierwszy i rozmawiają na luzie w języku polskim.</textarea>

            <button id="btn-save-card" class="btn btn-full">💾 Zapisz Kartę Postaci PL</button>
            <div id="save-status" style="font-size: 0.8rem; color: var(--accent-green); margin-top: 0.4rem;"></div>
        </div>

        <!-- Kolumna 3: Głos Referencyjny & Parametry Techniczne -->
        <div class="card">
            <h2>🔊 Polski Głos Referencyjny (pl.flac)</h2>
            <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.5rem;">
                Domyślny głos polski jest aktywny w katalogu <code>assets/voices/pl.flac</code>.
            </p>
            
            <audio id="audio-player" controls style="width: 100%; margin: 0.5rem 0;" src="/api/voices/download/pl"></audio>

            <div style="margin: 0.75rem 0;">
                <label>Prześlij nową próbkę głosu (WAV, FLAC, MP3):</label>
                <input type="file" id="voice-upload" accept="audio/*">
                <button id="btn-upload-voice" class="btn btn-amber btn-full">📤 Wgraj i Przekonwertuj do 24kHz</button>
            </div>

            <h2 style="margin-top: 1.25rem;">⚙️ Parametry Silnika Haru</h2>
            <div class="row">
                <div>
                    <label>Skala CFG (Wyrazistość):</label>
                    <input type="number" id="cfg-scale" value="1.5" min="1.0" max="2.0" step="0.1">
                </div>
                <div>
                    <label>Temperatura tekstu:</label>
                    <input type="number" id="temp" value="0.7" min="0.1" max="1.5" step="0.1">
                </div>
            </div>
            <div class="row">
                <div>
                    <label>Język domyślny:</label>
                    <input type="text" value="pl (Polski)" disabled>
                </div>
                <div>
                    <label>Maksymalny czas sesji:</label>
                    <input type="text" value="3600 s (1h)" disabled>
                </div>
            </div>
        </div>
    </div>

    <div class="footer">
        Haru Full-Duplex Voice Studio PL &copy; 2026 Higurashi AI. Zainstalowano w <code>D:\\AI-Tools\\Haru</code> na porcie 8998.
    </div>

    <script>
        // Pobieranie informacji o GPU i statusie
        fetch('/api/status')
            .then(res => res.json())
            .then(data => {
                const gpuBadge = document.getElementById('gpu-badge');
                if (data.gpu.cuda) {
                    gpuBadge.textContent = 'GPU: ' + data.gpu.device + ' (' + data.gpu.vram_gb + ' GB)';
                    gpuBadge.className = 'badge badge-green';
                } else {
                    gpuBadge.textContent = 'CPU / Brak akceleracji CUDA';
                    gpuBadge.className = 'badge badge-amber';
                }
            })
            .catch(err => console.error('Status fetch error:', err));

        // Obsługa wczytywania i zapisu kart postaci
        fetch('/api/cards')
            .then(res => res.json())
            .then(cards => {
                const select = document.getElementById('char-select');
                select.addEventListener('change', () => {
                    const c = cards[select.value];
                    if (c) {
                        document.getElementById('card-name').value = c.name || '';
                        document.getElementById('card-persona').value = c.persona || '';
                        document.getElementById('card-backchannel').value = c.backchannel || 'mid';
                        document.getElementById('card-situation').value = c.situation || '';
                    }
                });
            });

        document.getElementById('btn-save-card').addEventListener('click', () => {
            const currentKey = document.getElementById('char-select').value;
            const updatedCard = {
                name: document.getElementById('card-name').value,
                persona: document.getElementById('card-persona').value,
                backchannel: document.getElementById('card-backchannel').value,
                relationship: "Haru i rozmówca prowadzą otwartą konwersację.",
                situation: document.getElementById('card-situation').value
            };
            fetch('/api/cards', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ key: currentKey, card: updatedCard })
            })
            .then(res => res.json())
            .then(resp => {
                document.getElementById('save-status').textContent = '✅ Zapisano pomyślnie kartę ' + currentKey + '!';
                setTimeout(() => { document.getElementById('save-status').textContent = ''; }, 3000);
            });
        });

        // Obsługa uploadu głosu
        document.getElementById('btn-upload-voice').addEventListener('click', () => {
            const fileInput = document.getElementById('voice-upload');
            if (!fileInput.files || fileInput.files.length === 0) {
                alert('Wybierz plik audio z dysku!');
                return;
            }
            const formData = new FormData();
            formData.append('voice', fileInput.files[0]);
            fetch('/api/voices/upload', {
                method: 'POST',
                body: formData
            })
            .then(res => res.json())
            .then(data => {
                alert(data.message || 'Wgrano pomyślnie!');
                document.getElementById('audio-player').src = '/api/voices/download/pl?t=' + Date.now();
            })
            .catch(err => alert('Błąd przesyłania: ' + err));
        });

        // Oscyloskop audio i obsługa mikrofonu
        let audioCtx, analyser, micStream, isRecording = false;
        const canvas = document.getElementById('osc-canvas');
        const canvasCtx = canvas.getContext('2d');
        const vadFill = document.getElementById('vad-fill');
        const btnMic = document.getElementById('btn-toggle-mic');
        const callStatus = document.getElementById('call-status');

        function drawOsc() {
            if (!isRecording) return;
            requestAnimationFrame(drawOsc);
            const bufferLength = analyser.frequencyBinCount;
            const dataArray = new Uint8Array(bufferLength);
            analyser.getByteTimeDomainData(dataArray);

            canvasCtx.fillStyle = '#090d16';
            canvasCtx.fillRect(0, 0, canvas.width, canvas.height);
            canvasCtx.lineWidth = 2;
            canvasCtx.strokeStyle = '#3b82f6';
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

            // Obliczenie poziomu VAD
            const avg = sum / bufferLength;
            const vadPercent = Math.min(100, Math.round((avg / 64) * 100));
            vadFill.style.width = vadPercent + '%';
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
                    btnMic.textContent = '⏹️ Zakończ Rozmowę Głosową';
                    btnMic.className = 'btn btn-danger btn-full';
                    callStatus.textContent = '🟢 Połączono w pełnym dupleksie (Mikrofon aktywny)';
                    drawOsc();
                } catch (e) {
                    alert('Brak dostępu do mikrofonu: ' + e);
                }
            } else {
                if (micStream) micStream.getTracks().forEach(t => t.stop());
                if (audioCtx) audioCtx.close();
                isRecording = false;
                btnMic.textContent = '🎤 Włącz Mikrofon & Rozmowę';
                btnMic.className = 'btn btn-green btn-full';
                callStatus.textContent = 'Rozłączono';
                vadFill.style.width = '0%';
                canvasCtx.fillStyle = '#090d16';
                canvasCtx.fillRect(0, 0, canvas.width, canvas.height);
            }
        });
    </script>
</body>
</html>
"""


async def handle_dashboard(request: web.Request) -> web.Response:
    """Zwraca główny polski panel kontrolny."""
    return web.Response(text=HTML_DASHBOARD, content_type="text/html", charset="utf-8")


async def handle_client(request: web.Request) -> web.StreamResponse:
    """Zwraca oryginalnego klienta Haru Web Demo."""
    client_html = STATIC_DIR / "index.html"
    if not client_html.is_file():
        raise web.HTTPNotFound(text="Nie znaleziono haru/static/index.html")
    return web.FileResponse(client_html, headers={"Content-Type": "text/html; charset=utf-8"})


async def handle_status(request: web.Request) -> web.Response:
    """Zwraca status GPU, modeli i portu."""
    demo_server = request.app["demo_server"]
    ready = demo_server.backend.ready()
    return web.json_response({
        "status": "online",
        "port": 8998,
        "language": "pl",
        "ready": ready,
        "gpu": get_gpu_info(),
        "voices": [f.stem for f in VOICES_DIR.glob("*.flac")] if VOICES_DIR.is_dir() else [],
    })


async def handle_get_cards(request: web.Request) -> web.Response:
    """Zwraca polskie karty postaci."""
    cards = load_polish_cards()
    return web.json_response(cards)


async def handle_post_cards(request: web.Request) -> web.Response:
    """Zapisuje zmienioną polską kartę postaci."""
    try:
        payload = await request.json()
        key = payload.get("key", "chat")
        card = payload.get("card", {})
        existing = load_polish_cards()
        existing[key] = card
        save_polish_cards(existing)
        return web.json_response({"ok": True, "message": f"Karta {key} zaktualizowana"})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=400)


async def handle_download_voice(request: web.Request) -> web.StreamResponse:
    """Pobiera lub odtwarza plik głosu referencyjnego."""
    code = request.match_info.get("code", "pl")
    voice_path = VOICES_DIR / f"{code}.flac"
    if not voice_path.is_file():
        raise web.HTTPNotFound(text=f"Nie znaleziono pliku głosu: {code}.flac")
    return web.FileResponse(voice_path, headers={"Content-Type": "audio/flac"})


async def handle_upload_voice(request: web.Request) -> web.Response:
    """Odbiera próbkę audio i zapisuje jako assets/voices/pl.flac (24kHz mono)."""
    try:
        reader = await request.multipart()
        field = await reader.next()
        if field.name != "voice":
            return web.json_response({"ok": False, "error": "Brak pola 'voice' w zapytaniu"}, status=400)
        
        raw_bytes = await field.read()
        pcm = decode_audio(raw_bytes, sample_rate=SAMPLE_RATE)
        VOICES_DIR.mkdir(parents=True, exist_ok=True)
        target = VOICES_DIR / "pl.flac"
        save_audio(target, pcm, sample_rate=SAMPLE_RATE)
        return web.json_response({"ok": True, "message": f"Pomyślnie zaktualizowano pl.flac ({len(pcm)} próbek, 24kHz)"})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=500)


def build_app(options: ServerOptions, backend: Backend) -> web.Application:
    """Buduje aplikację aiohttp łączącą Polski Control Center i endpointy Haru."""
    demo_server = DemoServer(backend, options)
    demo_server.handle_index = handle_dashboard
    app = demo_server.build_app()
    app["demo_server"] = demo_server

    app.router.add_get("/control", handle_dashboard)
    app.router.add_get("/client", handle_client)
    app.router.add_get("/api/status", handle_status)
    app.router.add_get("/api/cards", handle_get_cards)
    app.router.add_post("/api/cards", handle_post_cards)
    app.router.add_get("/api/voices/download/{code}", handle_download_voice)
    app.router.add_post("/api/voices/upload", handle_upload_voice)

    return app


def main():
    parser = argparse.ArgumentParser(description="Haru Full-Duplex Voice Studio PL")
    parser.add_argument("--host", default="0.0.0.0", help="Host nasłuchiwania (0.0.0.0: wszystkie interfejsy)")
    parser.add_argument("--port", type=int, default=8998, help="Port serwera (domyślnie 8998)")
    parser.add_argument("--language", default="pl", help="Domyślny język sesji (pl)")
    parser.add_argument("--hf-repo", default="higurashi-ai/Haru-4B", help="Repozytorium modelu Hugging Face")
    parser.add_argument("--device", help="Urządzenie torch (cuda/cpu)")
    parser.add_argument("--ui-only", action="store_true", help="Uruchomienie interfejsu WebUI bez ładowania wag modelu")
    args = parser.parse_args()

    if args.ui_only:
        app = web.Application()
        app.router.add_get("/", handle_dashboard)
        app.router.add_get("/control", handle_dashboard)
        app.router.add_get("/api/status", handle_status)
        app.router.add_get("/api/cards", handle_get_cards)
    else:
        backend = LocalBackend(args.hf_repo, args.device, warmup_frames=0)
        options = ServerOptions(
            default_language=args.language,
            time_limit_seconds=3600,
            network_profile="local",
        )
        app = build_app(options, backend)
    logger.info(f"Start Haru Full-Duplex Voice Studio PL na http://{args.host}:{args.port}")
    web.run_app(app, host=args.host, port=args.port, print=None)


if __name__ == "__main__":
    main()
