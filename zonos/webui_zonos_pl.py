"""
Zonos Voice Studio - Polski Interfejs WebUI (Gradio 5+)
Zaawansowana ekspresyjna synteza mowy, 8-wymiarowa kontrola emocji i błyskawiczne klonowanie głosu.
Port domyślny: 7860
"""

import argparse
import sys
import os
import torch
import torchaudio
import gradio as gr
from pathlib import Path

# Upewnij sie, ze katalog glowny Zonos jest w sciezce Pythona
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from zonos.model import Zonos, DEFAULT_BACKBONE_CLS as ZonosBackbone
from zonos.conditioning import make_cond_dict, supported_language_codes
from zonos.utils import DEFAULT_DEVICE as device

CURRENT_MODEL_TYPE = None
CURRENT_MODEL = None
SPEAKER_EMBEDDING = None
SPEAKER_AUDIO_PATH = None

# Słownik języków z przyjaznymi polskimi nazwami
LANG_DISPLAY = {
    "pl": "Polski (pl)",
    "en-us": "Angielski US (en-us)",
    "en-gb": "Angielski UK (en-gb)",
    "de": "Niemiecki (de)",
    "fr-fr": "Francuski (fr-fr)",
    "es": "Hiszpański (es)",
    "it": "Włoski (it)",
    "ja": "Japoński (ja)",
    "cmn": "Chiński standardowy (cmn)",
}

# Gotowe teksty demonstracyjne w języku polskim
SAMPLE_TEXTS = {
    "literacki": (
        "Ciemno wszędzie, głucho wszędzie, co to będzie, co to będzie? "
        "Litwo! Ojczyzno moja! ty jesteś jak zdrowie. Nagle z głębi lasu rozległ się tajemniczy dźwięk."
    ),
    "techniczny": (
        "Zonos Voice Studio zostało pomyślnie uruchomione na karcie graficznej z akceleracją CUDA. "
        "Wszystkie parametry akustyczne i wektory emocji są w pełni zsynchronizowane."
    ),
    "ekspresyjny": (
        "Nie do wiary! Naprawdę udało się to osiągnąć w tak krótkim czasie?! "
        "To jest po prostu niesamowite, jestem zachwycony tym rezultatem!"
    ),
    "audiobook": (
        "Zegar na wieży ratuszowej wybił północ. Gęsta mgła otuliła wąskie uliczki starego miasta. "
        "Kroki nieznajomego stawały się coraz cichsze, aż w końcu zamilkły zupełnie."
    ),
}

# Presety emocjonalne (Radość, Smutek, Wstręt, Strach, Zaskoczenie, Gniew, Inne, Neutralność, Pitch, Rate, DNSMOS)
PRESETS = {
    "narrator": {
        "e": [0.05, 0.05, 0.00, 0.00, 0.05, 0.00, 0.05, 0.90],
        "pitch": 40.0,
        "rate": 15.0,
        "dnsmos": 4.2,
        "cfg": 2.0,
        "desc": "Naturalny, wyważony głos lektorski o wysokiej czytelności i neutralności.",
    },
    "prezenter": {
        "e": [0.85, 0.00, 0.00, 0.00, 0.35, 0.00, 0.10, 0.20],
        "pitch": 65.0,
        "rate": 17.5,
        "dnsmos": 4.5,
        "cfg": 2.5,
        "desc": "Żywy, radosny i dynamiczny ton prezentera z wyraźną ekspresją.",
    },
    "smutek": {
        "e": [0.00, 0.85, 0.05, 0.10, 0.00, 0.00, 0.15, 0.20],
        "pitch": 25.0,
        "rate": 11.5,
        "dnsmos": 3.8,
        "cfg": 2.0,
        "desc": "Melancholijny, wolniejszy i intymny głos o obniżonej dynamice tonu.",
    },
    "audiobook_dramat": {
        "e": [0.05, 0.30, 0.10, 0.60, 0.45, 0.25, 0.10, 0.15],
        "pitch": 80.0,
        "rate": 13.5,
        "dnsmos": 4.0,
        "cfg": 2.8,
        "desc": "Budujący napięcie, dramatyczny tembr z wyczuwalnym niepokojem.",
    },
    "dialog": {
        "e": [0.35, 0.10, 0.05, 0.05, 0.40, 0.10, 0.20, 0.45],
        "pitch": 55.0,
        "rate": 15.5,
        "dnsmos": 4.2,
        "cfg": 2.2,
        "desc": "Swobodny, konwersacyjny ton dialogowy z naturalną modulacją głosu.",
    },
}


def load_model_if_needed(model_choice: str):
    """Ładuje model Zonos do pamięci VRAM GPU."""
    global CURRENT_MODEL_TYPE, CURRENT_MODEL
    if CURRENT_MODEL_TYPE != model_choice or CURRENT_MODEL is None:
        if CURRENT_MODEL is not None:
            del CURRENT_MODEL
            torch.cuda.empty_cache()
        print(f"[Zonos WebUI PL] Ładowanie modelu {model_choice} na urządzeniu {device}...")
        CURRENT_MODEL = Zonos.from_pretrained(model_choice, device=device)
        CURRENT_MODEL.requires_grad_(False).eval()
        CURRENT_MODEL_TYPE = model_choice
        print(f"[Zonos WebUI PL] Model {model_choice} załadowany pomyślnie!")
    return CURRENT_MODEL


def apply_preset(preset_key: str):
    """Zwraca zaktualizowane wartości sliderów dla wybranego presetu."""
    p = PRESETS.get(preset_key, PRESETS["narrator"])
    e = p["e"]
    msg = f"Aktywowano profil: **{preset_key.upper()}** — {p['desc']}"
    return (
        e[0], e[1], e[2], e[3], e[4], e[5], e[6], e[7],
        p["pitch"], p["rate"], p["dnsmos"], p["cfg"],
        msg
    )


def insert_sample_text(text_key: str):
    """Wstawia gotowy tekst demonstracyjny."""
    return SAMPLE_TEXTS.get(text_key, "")


def generate_audio_pl(
    model_choice,
    text,
    language,
    speaker_audio,
    prefix_audio,
    e_radosc,
    e_smutek,
    e_wstret,
    e_strach,
    e_zaskoczenie,
    e_gniew,
    e_inne,
    e_neutralnosc,
    vq_single,
    fmax,
    pitch_std,
    speaking_rate,
    dnsmos_ovrl,
    speaker_noised,
    cfg_scale,
    top_p,
    top_k,
    min_p,
    linear,
    confidence,
    quadratic,
    seed,
    randomize_seed,
    unconditional_keys,
    progress=gr.Progress(track_tqdm=True),
):
    """Główna funkcja syntezy mowy z obsługą błędów i polskimi komunikatami."""
    if not text or not text.strip():
        raise gr.Error("Wprowadź tekst do syntezy! Pole tekstowe nie może być puste.")

    global SPEAKER_AUDIO_PATH, SPEAKER_EMBEDDING

    try:
        progress(0.05, desc="Inicjalizacja silnika syntezy...")
        selected_model = load_model_if_needed(model_choice)
    except Exception as e:
        raise gr.Error(
            f"Błąd podczas ładowania wag modelu {model_choice}: {str(e)}.\n"
            "Upewnij się, że masz połączenie z Internetem przy pierwszym uruchomieniu, aby pobrać wagi z Hugging Face."
        )

    fmax = float(fmax)
    pitch_std = float(pitch_std)
    speaking_rate = float(speaking_rate)
    dnsmos_ovrl = float(dnsmos_ovrl)
    cfg_scale = float(cfg_scale)
    top_p = float(top_p)
    top_k = int(top_k)
    min_p = float(min_p)
    linear = float(linear)
    confidence = float(confidence)
    quadratic = float(quadratic)
    seed = int(seed)
    max_new_tokens = 86 * 30

    if randomize_seed:
        seed = torch.randint(0, 2**32 - 1, (1,)).item()
    torch.manual_seed(seed)

    # Obliczenie embeddingu głosu referencyjnego (klonowanie)
    if speaker_audio is not None and "speaker" not in unconditional_keys:
        if speaker_audio != SPEAKER_AUDIO_PATH or SPEAKER_EMBEDDING is None:
            progress(0.15, desc="Przetwarzanie próbki głosu mówcy...")
            wav, sr = torchaudio.load(speaker_audio)
            SPEAKER_EMBEDDING = selected_model.make_speaker_embedding(wav, sr)
            SPEAKER_EMBEDDING = SPEAKER_EMBEDDING.to(device, dtype=torch.bfloat16)
            SPEAKER_AUDIO_PATH = speaker_audio

    # Opcjonalne audio prefiksu
    audio_prefix_codes = None
    if prefix_audio is not None:
        try:
            wav_prefix, sr_prefix = torchaudio.load(prefix_audio)
            wav_prefix = wav_prefix.mean(0, keepdim=True)
            wav_prefix = selected_model.autoencoder.preprocess(wav_prefix, sr_prefix)
            wav_prefix = wav_prefix.to(device, dtype=torch.float32)
            audio_prefix_codes = selected_model.autoencoder.encode(wav_prefix.unsqueeze(0))
        except Exception as pe:
            print(f"[Zonos WebUI PL] Ostrzeżenie prefiksu audio: {pe}")

    # Wektor 8 emocji Zonos
    emotion_tensor = torch.tensor(
        [
            float(e_radosc),
            float(e_smutek),
            float(e_wstret),
            float(e_strach),
            float(e_zaskoczenie),
            float(e_gniew),
            float(e_inne),
            float(e_neutralnosc),
        ],
        device=device,
    )

    vq_val = float(vq_single)
    vq_tensor = torch.tensor([vq_val] * 8, device=device).unsqueeze(0)

    # Słownik kondycjonowania
    cond_dict = make_cond_dict(
        text=text,
        language=language,
        speaker=SPEAKER_EMBEDDING,
        emotion=emotion_tensor,
        vqscore_8=vq_tensor,
        fmax=fmax,
        pitch_std=pitch_std,
        speaking_rate=speaking_rate,
        dnsmos_ovrl=dnsmos_ovrl,
        speaker_noised=bool(speaker_noised),
        device=device,
        unconditional_keys=unconditional_keys,
    )
    conditioning = selected_model.prepare_conditioning(cond_dict)

    estimated_generation_duration = max(1.0, 30 * len(text) / 400)
    estimated_total_steps = int(estimated_generation_duration * 86)

    def update_progress(_frame: torch.Tensor, step: int, _total_steps: int) -> bool:
        progress_val = min(0.95, 0.2 + 0.75 * (step / max(1, estimated_total_steps)))
        progress(progress_val, desc=f"Generowanie dźwięku... Krok {step}/{estimated_total_steps}")
        return True

    progress(0.2, desc="Uruchamianie transformera Zonos...")
    try:
        codes = selected_model.generate(
            prefix_conditioning=conditioning,
            audio_prefix_codes=audio_prefix_codes,
            max_new_tokens=max_new_tokens,
            cfg_scale=cfg_scale,
            batch_size=1,
            sampling_params=dict(
                top_p=top_p,
                top_k=top_k,
                min_p=min_p,
                linear=linear,
                conf=confidence,
                quad=quadratic,
            ),
            callback=update_progress,
        )
        progress(0.95, desc="Dekodowanie sygnału audio DAC...")
        wav_out = selected_model.autoencoder.decode(codes).cpu().detach()
        sr_out = selected_model.autoencoder.sampling_rate
        if wav_out.dim() == 2 and wav_out.size(0) > 1:
            wav_out = wav_out[0:1, :]
        audio_data = (sr_out, wav_out.squeeze().numpy())
        status_msg = f"Pomyślnie wygenerowano audio (próbkowanie {sr_out} Hz, seed: {seed})"
        return audio_data, seed, status_msg
    except Exception as ge:
        raise gr.Error(f"Wystąpił błąd podczas generowania mowy: {str(ge)}")


def build_ui():
    """Tworzy kompletny interfejs Gradio w języku polskim z bogatymi objaśnieniami."""
    supported_models = []
    if "transformer" in ZonosBackbone.supported_architectures:
        supported_models.append("Zyphra/Zonos-v0.1-transformer")
    if "hybrid" in ZonosBackbone.supported_architectures:
        supported_models.append("Zyphra/Zonos-v0.1-hybrid")
    if not supported_models:
        supported_models = ["Zyphra/Zonos-v0.1-transformer"]

    # Utwórz listę kodów języka z priorytetem dla języka polskiego
    lang_choices = []
    for code in supported_language_codes:
        label = LANG_DISPLAY.get(code, code)
        lang_choices.append((label, code))

    # Sortuj tak, aby 'pl' był na samej górze
    lang_choices.sort(key=lambda x: (0 if x[1] == "pl" else (1 if x[1].startswith("en") else 2), x[0]))

    custom_css = """
    .main-title { text-align: center; margin-bottom: 0.5rem; }
    .badge { display: inline-block; padding: 0.25rem 0.6rem; border-radius: 9999px; font-size: 0.8rem; font-weight: 600; background-color: #2563eb; color: white; margin-right: 0.5rem; }
    .card-box { border: 1px solid rgba(128, 128, 128, 0.2); border-radius: 8px; padding: 1rem; margin-bottom: 1rem; }
    .preset-btn { font-weight: 600 !important; }
    """

    with gr.Blocks(title="Zonos Voice Studio PL - Port 7860", css=custom_css) as demo:
        gr.Markdown(
            """
            # 🎙️ Zonos Voice Studio (Polski Interfejs)
            <div style="display: flex; gap: 0.5rem; align-items: center; margin-bottom: 1rem;">
                <span class="badge">Model: 800M MoE Transformer</span>
                <span class="badge" style="background-color: #10b981;">Audio: 44.1 kHz DAC</span>
                <span class="badge" style="background-color: #8b5cf6;">Port: 7860</span>
                <span class="badge" style="background-color: #f59e0b;">Język: Polski (pl) + Multi</span>
            </div>
            **Zonos-v0.1** to rewolucyjny model syntezy mowy (TTS) firmy Zyphra, oferujący precyzyjne sterowanie **8 wymiarami emocji**, parametrami akustycznymi oraz błyskawiczne klonowanie głosu na podstawie krótkiej próbki referencyjnej.
            """,
            elem_classes=["main-title"],
        )

        with gr.Row():
            with gr.Column(scale=3):
                with gr.Group():
                    gr.Markdown("### 📝 Treść Wypowiedzi i Język")
                    text_input = gr.Textbox(
                        label="Tekst do syntezy",
                        placeholder="Wpisz tutaj tekst po polsku, który ma zostać przeczytany przez lektora...",
                        value=SAMPLE_TEXTS["literacki"],
                        lines=4,
                        max_length=600,
                    )
                    with gr.Row():
                        btn_txt1 = gr.Button("📖 Fragment literacki", size="sm")
                        btn_txt2 = gr.Button("⚙️ Komunikat techniczny", size="sm")
                        btn_txt3 = gr.Button("🎭 Dialog ekspresyjny", size="sm")
                        btn_txt4 = gr.Button("🎙️ Narracja audiobooka", size="sm")

                    with gr.Row():
                        language_dropdown = gr.Dropdown(
                            choices=lang_choices,
                            value="pl",
                            label="Język syntezy (Fonetyzacja eSpeak)",
                            info="Domyślnie wybrany język polski (pl).",
                        )
                        model_dropdown = gr.Dropdown(
                            choices=supported_models,
                            value=supported_models[0],
                            label="Wariant modelu Zonos",
                            info="Transformer (800M) z pełnym kondycjonowaniem emocjonalnym.",
                        )

                with gr.Group():
                    gr.Markdown("### 🎭 Profile Emocjonalne (Presety jednym kliknięciem)")
                    gr.Markdown("Wybierz gotowy profil, aby automatycznie skonfigurować wszystkie 8 suwaków emocji oraz akustykę mowy:")
                    with gr.Row():
                        btn_preset_narrator = gr.Button("🎙️ Naturalny Narrator", variant="secondary", elem_classes=["preset-btn"])
                        btn_preset_prezenter = gr.Button("✨ Entuzjastyczny Prezenter", variant="secondary", elem_classes=["preset-btn"])
                        btn_preset_smutek = gr.Button("🌧️ Smutna Opowieść", variant="secondary", elem_classes=["preset-btn"])
                        btn_preset_audiobook = gr.Button("⚡ Dramatyczny Audiobook", variant="secondary", elem_classes=["preset-btn"])
                        btn_preset_dialog = gr.Button("💬 Ekspresyjny Dialog", variant="secondary", elem_classes=["preset-btn"])

                    preset_status = gr.Markdown("Aktywny profil: **Naturalny Narrator** — wyważony tembr lektorski.")

                with gr.Accordion("🎛️ 8 Wymiarów Emocji Zonos (Zaawansowana Kontrola)", open=True):
                    gr.Markdown(
                        "Każdy suwak reprezentuje siłę danej składowej emocjonalnej w skali 0.0 – 1.0. "
                        "Połączenie różnych emocji pozwala uzyskać unikalny, ludzki charakter wypowiedzi."
                    )
                    with gr.Row():
                        e_radosc = gr.Slider(0.0, 1.0, value=0.05, step=0.05, label="😊 Radość (Happiness)", info="Wesoły, pogodny ton")
                        e_smutek = gr.Slider(0.0, 1.0, value=0.05, step=0.05, label="😢 Smutek (Sadness)", info="Przybity, melancholijny")
                        e_wstret = gr.Slider(0.0, 1.0, value=0.00, step=0.05, label="🤢 Wstręt (Disgust)", info="Niechęć, grymas głosu")
                        e_strach = gr.Slider(0.0, 1.0, value=0.00, step=0.05, label="😨 Strach (Fear)", info="Zaniepokojenie, lęk")
                    with gr.Row():
                        e_zaskoczenie = gr.Slider(0.0, 1.0, value=0.05, step=0.05, label="😲 Zaskoczenie (Surprise)", info="Zdumienie, uniesienie")
                        e_gniew = gr.Slider(0.0, 1.0, value=0.00, step=0.05, label="😡 Gniew (Anger)", info="Złość, podniesiony ton")
                        e_inne = gr.Slider(0.0, 1.0, value=0.05, step=0.05, label="🌀 Inne (Other)", info="Nietypowy nastrój")
                        e_neutralnosc = gr.Slider(0.0, 1.0, value=0.90, step=0.05, label="😐 Neutralność (Neutral)", info="Spokojna, obiektywna mowa")

                with gr.Accordion("🔊 Parametry Akustyczne i Jakość Mowy", open=True):
                    with gr.Row():
                        pitch_std_slider = gr.Slider(
                            0.0, 300.0, value=40.0, step=1.0,
                            label="Wariancja tonu (Pitch Std)",
                            info="Wyższe wartości dają bardziej dynamiczną, ekspresyjną intonację głosu.",
                        )
                        speaking_rate_slider = gr.Slider(
                            5.0, 30.0, value=15.0, step=0.5,
                            label="Tempo wypowiedzi (Speaking Rate)",
                            info="Liczba fonemów na sekundę (standardowo 15, mniejsze = wolniej).",
                        )
                    with gr.Row():
                        dnsmos_slider = gr.Slider(
                            1.0, 5.0, value=4.2, step=0.1,
                            label="Jakość DNSMOS (Czystość)",
                            info="Przewidywana jakość toru audio (4.0+ zapewnia krystaliczną czystość).",
                        )
                        fmax_slider = gr.Slider(
                            0, 24000, value=24000, step=500,
                            label="Maksymalna częstotliwość Fmax (Hz)",
                            info="Szerokość pasma akustycznego (24000 Hz dla pełnej jakości Hi-Fi).",
                        )
                        vq_single_slider = gr.Slider(
                            0.5, 0.8, value=0.78, step=0.01,
                            label="Jakość VQ Score",
                            info="Wskaźnik wierności kwantyzacji wektorowej.",
                        )

            with gr.Column(scale=2):
                with gr.Group():
                    gr.Markdown("### 👤 Klonowanie Głosu Mówcy")
                    speaker_audio = gr.Audio(
                        label="Próbka głosu referencyjnego (Mikrofon lub Plik)",
                        sources=["upload", "microphone"],
                        type="filepath",
                    )
                    speaker_noised_checkbox = gr.Checkbox(
                        label="Odfiltruj szumy z próbki mówcy (Denoise)",
                        value=False,
                    )
                    prefix_audio = gr.Audio(
                        label="Opcjonalne audio prefiksu (kontynuacja wypowiedzi)",
                        value="assets/silence_100ms.wav" if os.path.exists("assets/silence_100ms.wav") else None,
                        sources=["upload"],
                        type="filepath",
                    )

                with gr.Group():
                    gr.Markdown("### 🚀 Generowanie Dźwięku")
                    btn_generate = gr.Button("🔥 Generuj Mowę (Zonos TTS)", variant="primary", size="lg")
                    status_text = gr.Markdown("Status: Gotowy do syntezy")
                    output_audio = gr.Audio(label="Wygenerowany Dźwięk (WAV 44.1 kHz)", type="numpy", autoplay=True)

                with gr.Accordion("⚙️ Próbkowanie i Ziarno Losowości (Seed)", open=False):
                    cfg_scale_slider = gr.Slider(1.0, 5.0, value=2.0, step=0.1, label="CFG Scale (Siła kondycjonowania)")
                    seed_number = gr.Number(label="Ziarno losowości (Seed)", value=420, precision=0)
                    randomize_seed_toggle = gr.Checkbox(label="Losuj ziarno przy każdym generowaniu", value=True)

                    gr.Markdown("#### Próbnik NovelAI Unified Sampler")
                    with gr.Row():
                        linear_slider = gr.Slider(-2.0, 2.0, value=0.5, step=0.01, label="Linear")
                        confidence_slider = gr.Slider(-2.0, 2.0, value=0.40, step=0.01, label="Confidence")
                        quadratic_slider = gr.Slider(-2.0, 2.0, value=0.00, step=0.01, label="Quadratic")

                    gr.Markdown("#### Próbnik Klasyczny (Legacy)")
                    with gr.Row():
                        top_p_slider = gr.Slider(0.0, 1.0, value=0.0, step=0.01, label="Top P")
                        top_k_slider = gr.Slider(0.0, 1024, value=0, step=1, label="Top K")
                        min_p_slider = gr.Slider(0.0, 1.0, value=0.0, step=0.01, label="Min P")

                    unconditional_keys = gr.CheckboxGroup(
                        [
                            "speaker",
                            "emotion",
                            "vqscore_8",
                            "fmax",
                            "pitch_std",
                            "speaking_rate",
                            "dnsmos_ovrl",
                            "speaker_noised",
                        ],
                        value=[],
                        label="Klucze bezwarunkowe (Unconditional)",
                        info="Zaznaczenie cechy sprawia, że model nie wymusza jej na siłę, lecz pozwala na automatyczne dopełnienie.",
                    )

        # Obsługa przycisków tekstów demonstracyjnych
        btn_txt1.click(lambda: insert_sample_text("literacki"), outputs=[text_input])
        btn_txt2.click(lambda: insert_sample_text("techniczny"), outputs=[text_input])
        btn_txt3.click(lambda: insert_sample_text("ekspresyjny"), outputs=[text_input])
        btn_txt4.click(lambda: insert_sample_text("audiobook"), outputs=[text_input])

        # Obsługa przycisków presetów
        preset_outputs = [
            e_radosc, e_smutek, e_wstret, e_strach, e_zaskoczenie, e_gniew, e_inne, e_neutralnosc,
            pitch_std_slider, speaking_rate_slider, dnsmos_slider, cfg_scale_slider,
            preset_status
        ]
        btn_preset_narrator.click(lambda: apply_preset("narrator"), outputs=preset_outputs)
        btn_preset_prezenter.click(lambda: apply_preset("prezenter"), outputs=preset_outputs)
        btn_preset_smutek.click(lambda: apply_preset("smutek"), outputs=preset_outputs)
        btn_preset_audiobook.click(lambda: apply_preset("audiobook_dramat"), outputs=preset_outputs)
        btn_preset_dialog.click(lambda: apply_preset("dialog"), outputs=preset_outputs)

        # Obsługa generowania audio
        btn_generate.click(
            fn=generate_audio_pl,
            inputs=[
                model_dropdown,
                text_input,
                language_dropdown,
                speaker_audio,
                prefix_audio,
                e_radosc,
                e_smutek,
                e_wstret,
                e_strach,
                e_zaskoczenie,
                e_gniew,
                e_inne,
                e_neutralnosc,
                vq_single_slider,
                fmax_slider,
                pitch_std_slider,
                speaking_rate_slider,
                dnsmos_slider,
                speaker_noised_checkbox,
                cfg_scale_slider,
                top_p_slider,
                top_k_slider,
                min_p_slider,
                linear_slider,
                confidence_slider,
                quadratic_slider,
                seed_number,
                randomize_seed_toggle,
                unconditional_keys,
            ],
            outputs=[output_audio, seed_number, status_text],
        )

        gr.Markdown(
            """
            ---
            **Instrukcja szybkiego startu**:
            1. Wpisz tekst lub wybierz jeden z gotowych przykładów.
            2. Wybierz gotowy profil emocjonalny (np. *Naturalny Narrator* lub *Entuzjastyczny Prezenter*) albo ręcznie dostosuj 8 suwaków emocji.
            3. (Opcjonalnie) Nagraj swój głos z mikrofonu, aby sklonować barwę.
            4. Kliknij **Generuj Mowę** — wygenerowany plik WAV odsłuchasz w odtwarzaczu i pobierzesz na dysk.
            """
        )

    return demo


def main():
    parser = argparse.ArgumentParser(description="Zonos Voice Studio PL")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host do nasłuchiwania")
    parser.add_argument("--port", type=int, default=7860, help="Port serwera (domyślnie 7860)")
    parser.add_argument("--share", action="store_true", help="Udostępnij publiczny link Gradio")
    args = parser.parse_args()

    demo = build_ui()
    print(f"[Zonos WebUI PL] Start serwera na http://{args.host}:{args.port}")
    demo.launch(server_name=args.host, server_port=args.port, share=args.share)


if __name__ == "__main__":
    main()
