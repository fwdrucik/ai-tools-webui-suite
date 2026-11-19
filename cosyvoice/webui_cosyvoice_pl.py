"""
CosyVoice Studio - Polski Interfejs WebUI (Gradio 6+)
Port: 7862
Obsługa 5 trybów syntezy:
1. Predefiniowane Barwy Głosu (SFT)
2. Błyskawiczne Klonowanie 3-5s (Zero-Shot) z automatyczną transkrypcją Whisper
3. Klonowanie Międzyjęzykowe (Cross-Lingual)
4. Ekspresja i Instrukcje (Instruct) z tagami emocjonalnymi
5. Zarządzanie Biblioteką Głosów
"""

import argparse
import os
import sys
import random
from pathlib import Path
import numpy as np
import torch
import torchaudio
import gradio as gr

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
matcha_dir = ROOT_DIR / "third_party" / "Matcha-TTS"
if matcha_dir.is_dir() and str(matcha_dir) not in sys.path:
    sys.path.insert(0, str(matcha_dir))

from cosyvoice.cli.cosyvoice import AutoModel
from cosyvoice.utils.file_utils import logging
from cosyvoice.utils.common import set_all_random_seed

CURRENT_MODEL = None
CURRENT_MODEL_DIR = None
WHISPER_MODEL = None

SAMPLE_RATE_DEFAULT = 22050

# Gotowe teksty demonstracyjne w języku polskim
SAMPLE_TEXTS = {
    "ogolny": "Witaj w CosyVoice Studio! Jestem generatywnym modelem mowy nowej generacji, który pozwala na naturalną syntezę mowy w języku polskim oraz błyskawiczne klonowanie głosu w zaledwie kilka sekund.",
    "biznes": "Szanowni Państwo, witamy na dorocznej konferencji technologicznej poświęconej najnowszym rozwiązaniom sztucznej inteligencji i przetwarzania mowy.",
    "audiobook": "Księżyc rzucał srebrzystą poświatę na zamarznięte jezioro. W ciszy zimowej nocy słychać było jedynie cichy szum starych sosen.",
    "dialog": "Naprawdę myślisz, że to zadziała? [laughter] Nie mam żadnych wątpliwości, sprawdźmy to od razu!",
}

# Predefiniowane głosy SFT (domyślne barwy z CosyVoice)
DEFAULT_SFT_SPKS = [
    "中文女 (Kobieta - Standard)",
    "中文男 (Mężczyzna - Standard)",
    "日语男 (Japoński Mężczyzna)",
    "粤语女 (Kantoński Kobieta)",
    "英文女 (Angielski Kobieta)",
    "英文男 (Angielski Mężczyzna)",
    "韩语女 (Koreański Kobieta)",
]

AVAILABLE_MODELS = [
    ("CosyVoice2-0.5B (Zalecany, Najnowszy)", "pretrained_models/CosyVoice2-0.5B"),
    ("CosyVoice-300M (Model Uniwersalny)", "iic/CosyVoice-300M"),
    ("CosyVoice-300M-Instruct (Kontrola Instrukcji)", "iic/CosyVoice-300M-Instruct"),
    ("CosyVoice-300M-SFT (Gotowe Barwy)", "iic/CosyVoice-300M-SFT"),
]


def get_cosyvoice(model_dir: str):
    """Leniwe ładowanie modelu CosyVoice."""
    global CURRENT_MODEL, CURRENT_MODEL_DIR
    if CURRENT_MODEL is None or CURRENT_MODEL_DIR != model_dir:
        print(f"[CosyVoice PL] Ładowanie modelu {model_dir}...")
        try:
            CURRENT_MODEL = AutoModel(model_dir=model_dir)
            CURRENT_MODEL_DIR = model_dir
            print(f"[CosyVoice PL] Model {model_dir} załadowany pomyślnie!")
        except Exception as e:
            print(f"[CosyVoice PL] Ostrzeżenie ładowania modelu: {e}")
            raise gr.Error(
                f"Błąd inicjalizacji modelu {model_dir}: {str(e)}.\n"
                "Upewnij się, że masz połączenie z Internetem przy pierwszym uruchomieniu w celu pobrania wag."
            )
    return CURRENT_MODEL


def transcribe_audio_whisper(audio_path: str, progress=gr.Progress()):
    """Automatyczna transkrypcja mowy z pliku próbki referencyjnej za pomocą Whisper."""
    if not audio_path:
        raise gr.Error("Najpierw wgraj plik audio lub nagraj próbkę z mikrofonu!")

    global WHISPER_MODEL
    try:
        progress(0.2, desc="Ładowanie modelu transkrypcji Whisper...")
        if WHISPER_MODEL is None:
            import whisper
            WHISPER_MODEL = whisper.load_model("base")

        progress(0.5, desc="Transkrypcja nagrania audio...")
        result = WHISPER_MODEL.transcribe(audio_path, language="pl")
        text = result.get("text", "").strip()
        progress(1.0, desc="Zakończono transkrypcję!")
        return text, f"✅ Pomyślnie rozpoznano tekst ({len(text)} znaków)"
    except Exception as e:
        return "", f"❌ Błąd transkrypcji Whisper: {str(e)}"


def generate_audio_sft(tts_text, spk_name, stream, speed, seed, model_dir, progress=gr.Progress()):
    """Tryb 1: Predefiniowane Barwy Głosu (SFT)."""
    if not tts_text or not tts_text.strip():
        raise gr.Error("Wpisz tekst do syntezy!")

    if seed == 0 or seed is None:
        seed = random.randint(1, 100000000)
    set_all_random_seed(seed)

    progress(0.1, desc="Przygotowywanie modelu SFT...")
    model = get_cosyvoice(model_dir)
    progress(0.3, desc="Synteza mowy...")

    # Pobierz czystą nazwę spk bez etykiety w nawiasie
    raw_spk = spk_name.split(" ")[0] if " " in spk_name else spk_name
    spk_list = model.list_available_spks()
    if raw_spk not in spk_list and len(spk_list) > 0:
        raw_spk = spk_list[0]

    audio_chunks = []
    for chunk in model.inference_sft(tts_text, raw_spk, stream=False, speed=float(speed)):
        audio_chunks.append(chunk["tts_speech"].numpy().flatten())

    if not audio_chunks:
        raise gr.Error("Nie wygenerowano danych audio.")

    full_audio = np.concatenate(audio_chunks)
    return (model.sample_rate, full_audio), seed, f"Pomyślnie wygenerowano audio SFT (seed: {seed})"


def generate_audio_zero_shot(tts_text, prompt_text, prompt_wav, stream, speed, seed, model_dir, progress=gr.Progress()):
    """Tryb 2: Błyskawiczne Klonowanie Głosu 3-5s (Zero-Shot)."""
    if not tts_text or not tts_text.strip():
        raise gr.Error("Wpisz tekst docelowy do syntezy!")
    if not prompt_wav:
        raise gr.Error("Wgraj lub nagraj próbkę referencyjną głosu (3-15 sekund)!")
    if not prompt_text or not prompt_text.strip():
        raise gr.Error("Pole 'Tekst próbki referencyjnej' jest puste! Użyj przycisku 'Transkrybuj przez Whisper' lub wpisz słowa wypowiedziane w nagraniu.")

    if seed == 0 or seed is None:
        seed = random.randint(1, 100000000)
    set_all_random_seed(seed)

    progress(0.1, desc="Inicjalizacja silnika klonowania Zero-Shot...")
    model = get_cosyvoice(model_dir)

    info = torchaudio.info(prompt_wav)
    if info.sample_rate < 16000:
        gr.Warning(f"Próbkowanie pliku ({info.sample_rate} Hz) jest poniżej zalecanego 16 kHz. Jakość może być obniżona.")

    progress(0.4, desc="Klonowanie barwy głosu i synteza mowy...")
    audio_chunks = []
    for chunk in model.inference_zero_shot(tts_text, prompt_text, prompt_wav, stream=False, speed=float(speed)):
        audio_chunks.append(chunk["tts_speech"].numpy().flatten())

    if not audio_chunks:
        raise gr.Error("Nie wygenerowano danych audio.")

    full_audio = np.concatenate(audio_chunks)
    return (model.sample_rate, full_audio), seed, f"Pomyślnie sklonowano głos w trybie Zero-Shot (seed: {seed})"


def generate_audio_cross_lingual(tts_text, prompt_wav, stream, speed, seed, model_dir, progress=gr.Progress()):
    """Tryb 3: Klonowanie Międzyjęzykowe (Cross-Lingual)."""
    if not tts_text or not tts_text.strip():
        raise gr.Error("Wpisz tekst docelowy do syntezy!")
    if not prompt_wav:
        raise gr.Error("Wgraj lub nagraj próbkę referencyjną głosu mówcy!")

    if seed == 0 or seed is None:
        seed = random.randint(1, 100000000)
    set_all_random_seed(seed)

    progress(0.1, desc="Inicjalizacja silnika Cross-Lingual...")
    model = get_cosyvoice(model_dir)

    progress(0.4, desc="Synteza mowy międzyjęzykowej...")
    audio_chunks = []
    for chunk in model.inference_cross_lingual(tts_text, prompt_wav, stream=False, speed=float(speed)):
        audio_chunks.append(chunk["tts_speech"].numpy().flatten())

    if not audio_chunks:
        raise gr.Error("Nie wygenerowano danych audio.")

    full_audio = np.concatenate(audio_chunks)
    return (model.sample_rate, full_audio), seed, f"Pomyślnie wygenerowano audio międzyjęzykowe (seed: {seed})"


def generate_audio_instruct(tts_text, spk_name, instruct_text, stream, speed, seed, model_dir, progress=gr.Progress()):
    """Tryb 4: Ekspresja i Instrukcje (Instruct)."""
    if not tts_text or not tts_text.strip():
        raise gr.Error("Wpisz tekst do syntezy!")
    if not instruct_text or not instruct_text.strip():
        raise gr.Error("Wpisz instrukcję stylu wypowiedzi (np. 'mów bardzo radośnie' lub 'szeptem')!")

    if seed == 0 or seed is None:
        seed = random.randint(1, 100000000)
    set_all_random_seed(seed)

    progress(0.1, desc="Inicjalizacja modelu z obsługą instrukcji...")
    model = get_cosyvoice(model_dir)

    raw_spk = spk_name.split(" ")[0] if " " in spk_name else spk_name
    spk_list = model.list_available_spks()
    if raw_spk not in spk_list and len(spk_list) > 0:
        raw_spk = spk_list[0]

    progress(0.4, desc="Aplikowanie instrukcji i generowanie głosu...")
    audio_chunks = []
    for chunk in model.inference_instruct(tts_text, raw_spk, instruct_text, stream=False, speed=float(speed)):
        audio_chunks.append(chunk["tts_speech"].numpy().flatten())

    if not audio_chunks:
        raise gr.Error("Nie wygenerowano danych audio.")

    full_audio = np.concatenate(audio_chunks)
    return (model.sample_rate, full_audio), seed, f"Pomyślnie zaaplikowano instrukcję stylu (seed: {seed})"


def insert_tag(text: str, tag: str) -> str:
    """Wstawia tag emocjonalny do tekstu."""
    if not text:
        return tag
    return f"{text} {tag}"


def build_ui():
    """Tworzy 5-zakładkowy polski interfejs Gradio."""
    custom_css = """
    .app-header { text-align: center; margin-bottom: 1rem; }
    .badge { display: inline-block; padding: 0.25rem 0.6rem; border-radius: 9999px; font-size: 0.8rem; font-weight: 600; background-color: #2563eb; color: white; margin-right: 0.5rem; }
    .tag-btn { margin-right: 0.3rem !important; margin-bottom: 0.3rem !important; }
    """

    with gr.Blocks(title="CosyVoice Studio PL - Port 7862") as demo:
        gr.Markdown(
            """
            # 🎙️ CosyVoice Studio (Polski Interfejs)
            <div style="display: flex; gap: 0.5rem; align-items: center; margin-bottom: 1rem;">
                <span class="badge">Silnik: FunAudioLLM CosyVoice 2</span>
                <span class="badge" style="background-color: #10b981;">Port: 7862</span>
                <span class="badge" style="background-color: #8b5cf6;">Klonowanie: 3-5s Zero-Shot</span>
                <span class="badge" style="background-color: #f59e0b;">Transkrypcja: Whisper Auto-ASR</span>
            </div>
            Wielojęzyczna, wysoce ekspresyjna synteza mowy, błyskawiczne klonowanie głosu w kilka sekund oraz precyzyjne sterowanie intonacją i emocjami.
            """,
            elem_classes=["app-header"],
        )

        with gr.Row():
            with gr.Column(scale=3):
                model_selector = gr.Dropdown(
                    choices=AVAILABLE_MODELS,
                    value=AVAILABLE_MODELS[0][1],
                    label="Model CosyVoice",
                    info="Domyślnie wybrany CosyVoice2-0.5B (najwyższa naturalność i wierność klonowania).",
                )
            with gr.Column(scale=1):
                speed_slider = gr.Slider(0.5, 2.0, value=1.0, step=0.1, label="Tempo mowy (Prędkość)")
                seed_input = gr.Number(value=0, label="Ziarno losowości (Seed, 0 = losowo)", precision=0)

        with gr.Tabs() as tabs:
            # ---------------- ZAKŁADKA 1: SFT ----------------
            with gr.Tab("🎭 1. Gotowe Barwy Głosu (SFT)"):
                gr.Markdown("Wybierz jedną z fabrycznych, dopracowanych barw lektorskich i wprowadź tekst.")
                with gr.Row():
                    with gr.Column(scale=2):
                        sft_text = gr.Textbox(
                            label="Tekst do przeczytania",
                            value=SAMPLE_TEXTS["ogolny"],
                            lines=3,
                        )
                        sft_speaker = gr.Dropdown(
                            choices=DEFAULT_SFT_SPKS,
                            value=DEFAULT_SFT_SPKS[0],
                            label="Wybierz lektora (Głos SFT)",
                        )
                        sft_btn = gr.Button("🔥 Syntezuj Głos (SFT)", variant="primary")
                    with gr.Column(scale=2):
                        sft_output = gr.Audio(label="Wygenerowany Dźwięk", type="numpy", autoplay=True)
                        sft_status = gr.Markdown("Status: Gotowy")

                sft_btn.click(
                    fn=generate_audio_sft,
                    inputs=[sft_text, sft_speaker, gr.State(False), speed_slider, seed_input, model_selector],
                    outputs=[sft_output, seed_input, sft_status],
                )

            # ---------------- ZAKŁADKA 2: ZERO-SHOT ----------------
            with gr.Tab("⚡ 2. Błyskawiczne Klonowanie Głosu 3-5s (Zero-Shot)"):
                gr.Markdown(
                    "Wgraj lub nagraj krótką próbkę głosu mówcy (3–15 sekund). "
                    "Kliknij **Transkrybuj przez Whisper**, aby automatycznie odczytać wypowiedziane słowa, a następnie wpisz tekst docelowy."
                )
                with gr.Row():
                    with gr.Column(scale=2):
                        zero_shot_audio = gr.Audio(
                            label="Próbka głosu mówcy (Mikrofon lub Plik WAV/MP3)",
                            sources=["upload", "microphone"],
                            type="filepath",
                        )
                        with gr.Row():
                            btn_whisper = gr.Button("✨ Transkrybuj mowę przez Whisper (Auto-ASR)", variant="secondary")
                        whisper_status = gr.Markdown("Status transkrypcji: Oczekuje na próbkę")

                        zero_shot_prompt_text = gr.Textbox(
                            label="Tekst wypowiedziany w próbce referencyjnej (Prompt Text)",
                            placeholder="Zostanie wypełniony automatycznie przez Whisper lub możesz wpisać go ręcznie...",
                            lines=2,
                        )
                        zero_shot_tts_text = gr.Textbox(
                            label="Tekst docelowy, który ma wypowiedzieć sklonowany głos",
                            value=SAMPLE_TEXTS["audiobook"],
                            lines=3,
                        )
                        zero_shot_btn = gr.Button("⚡ Sklonuj Głos i Generuj Mowę", variant="primary")

                    with gr.Column(scale=2):
                        zero_shot_output = gr.Audio(label="Wygenerowany Dźwięk Sklonowanego Głosu", type="numpy", autoplay=True)
                        zero_shot_status = gr.Markdown("Status: Gotowy do klonowania")

                btn_whisper.click(
                    fn=transcribe_audio_whisper,
                    inputs=[zero_shot_audio],
                    outputs=[zero_shot_prompt_text, whisper_status],
                )

                zero_shot_btn.click(
                    fn=generate_audio_zero_shot,
                    inputs=[
                        zero_shot_tts_text,
                        zero_shot_prompt_text,
                        zero_shot_audio,
                        gr.State(False),
                        speed_slider,
                        seed_input,
                        model_selector,
                    ],
                    outputs=[zero_shot_output, seed_input, zero_shot_status],
                )

            # ---------------- ZAKŁADKA 3: CROSS-LINGUAL ----------------
            with gr.Tab("🌍 3. Klonowanie Międzyjęzykowe (Cross-Lingual)"):
                gr.Markdown(
                    "Mów dowolnym językiem (np. po polsku lub po angielsku) barwą głosu osoby mówiącej w innym języku. "
                    "W tym trybie **nie jest wymagana** transkrypcja tekstu referencyjnego!"
                )
                with gr.Row():
                    with gr.Column(scale=2):
                        cross_audio = gr.Audio(
                            label="Próbka głosu obcego mówcy (WAV/MP3)",
                            sources=["upload", "microphone"],
                            type="filepath",
                        )
                        cross_text = gr.Textbox(
                            label="Tekst docelowy (np. w języku polskim)",
                            value=SAMPLE_TEXTS["biznes"],
                            lines=3,
                        )
                        cross_btn = gr.Button("🌍 Generuj Mowę Międzyjęzykową", variant="primary")

                    with gr.Column(scale=2):
                        cross_output = gr.Audio(label="Wygenerowany Dźwięk", type="numpy", autoplay=True)
                        cross_status = gr.Markdown("Status: Gotowy")

                cross_btn.click(
                    fn=generate_audio_cross_lingual,
                    inputs=[cross_text, cross_audio, gr.State(False), speed_slider, seed_input, model_selector],
                    outputs=[cross_output, seed_input, cross_status],
                )

            # ---------------- ZAKŁADKA 4: INSTRUCT ----------------
            with gr.Tab("💬 4. Ekspresja i Instrukcje (Instruct)"):
                gr.Markdown(
                    "Steruj stylem wypowiedzi za pomocą naturalnych poleceń tekstowych oraz wbudowanych znaczników emocji."
                )
                with gr.Row():
                    with gr.Column(scale=2):
                        instruct_tts_text = gr.Textbox(
                            label="Tekst do syntezy (wzbogacony o znaczniki emocji)",
                            value=SAMPLE_TEXTS["dialog"],
                            lines=3,
                        )
                        gr.Markdown("**Szybkie wstawianie znaczników ekspresji:**")
                        with gr.Row():
                            btn_tag1 = gr.Button("😂 [laughter] (Śmiech)", size="sm")
                            btn_tag2 = gr.Button("💨 [breath] (Oddech)", size="sm")
                            btn_tag3 = gr.Button("😮‍💨 [sigh] (Westchnienie)", size="sm")
                            btn_tag4 = gr.Button("💪 <strong>Nacisk</strong>", size="sm")

                        instruct_prompt = gr.Textbox(
                            label="Instrukcja stylu wypowiedzi (Instruct Prompt)",
                            value="Mów z entuzjazmem, uśmiechem w głosie i naturalną dynamiką.",
                            lines=2,
                        )
                        instruct_spk = gr.Dropdown(
                            choices=DEFAULT_SFT_SPKS,
                            value=DEFAULT_SFT_SPKS[0],
                            label="Wybierz bazową barwę głosu",
                        )
                        instruct_btn = gr.Button("✨ Syntezuj z Instrukcją Stylu", variant="primary")

                    with gr.Column(scale=2):
                        instruct_output = gr.Audio(label="Wygenerowany Dźwięk z Emocjami", type="numpy", autoplay=True)
                        instruct_status = gr.Markdown("Status: Gotowy")

                btn_tag1.click(lambda t: insert_tag(t, "[laughter]"), inputs=[instruct_tts_text], outputs=[instruct_tts_text])
                btn_tag2.click(lambda t: insert_tag(t, "[breath]"), inputs=[instruct_tts_text], outputs=[instruct_tts_text])
                btn_tag3.click(lambda t: insert_tag(t, "[sigh]"), inputs=[instruct_tts_text], outputs=[instruct_tts_text])
                btn_tag4.click(lambda t: insert_tag(t, "<strong>ważne słowo</strong>"), inputs=[instruct_tts_text], outputs=[instruct_tts_text])

                instruct_btn.click(
                    fn=generate_audio_instruct,
                    inputs=[
                        instruct_tts_text,
                        instruct_spk,
                        instruct_prompt,
                        gr.State(False),
                        speed_slider,
                        seed_input,
                        model_selector,
                    ],
                    outputs=[instruct_output, seed_input, instruct_status],
                )

            # ---------------- ZAKŁADKA 5: BIBLIOTEKA GŁOSÓW ----------------
            with gr.Tab("📚 5. Biblioteka i Profile Głosów"):
                gr.Markdown(
                    "Przeglądaj zapisane profile głosu oraz próbki demonstracyjne dostępne lokalnie w instalacji CosyVoice."
                )
                with gr.Row():
                    with gr.Column():
                        gr.Markdown("### 📂 Gotowe próbki w `asset/`")
                        gr.Markdown("- `zero_shot_prompt.wav` — próbka do testów szybkiego klonowania")
                        gr.Markdown("- `cross_lingual_prompt.wav` — próbka do testów syntezy wielojęzycznej")
                    with gr.Column():
                        gr.Markdown("### 💡 Porady dla najlepszej jakości klonowania:")
                        gr.Markdown("1. Nagraj od 5 do 15 sekund czystej mowy w cichym pomieszczeniu.")
                        gr.Markdown("2. Używaj przycisku automatycznej transkrypcji Whisper, by uniknąć pomyłek w tekście.")
                        gr.Markdown("3. CosyVoice automatycznie usuwa szumy tła i normalizuje głośność.")

        gr.Markdown(
            """
            ---
            CosyVoice Studio PL &copy; 2026 Alibaba FunAudioLLM. Uruchomiono na dedykowanym porcie **7862**.
            """
        )

    return demo


def main():
    parser = argparse.ArgumentParser(description="CosyVoice Studio PL")
    parser.add_argument("--host", default="0.0.0.0", help="Host nasłuchiwania")
    parser.add_argument("--port", type=int, default=7862, help="Port serwera (domyślnie 7862)")
    parser.add_argument("--share", action="store_true", help="Udostępnij publiczny link Gradio")
    args = parser.parse_args()

    demo = build_ui()
    print(f"[CosyVoice Studio PL] Start serwera na http://{args.host}:{args.port}")
    demo.queue(max_size=4, default_concurrency_limit=2)
    demo.launch(server_name=args.host, server_port=args.port, share=args.share)


if __name__ == "__main__":
    main()
