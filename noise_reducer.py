"""
AI Background Noise Reduction
=============================

Two engines are supported:

1. DeepFilterNet (deep learning, best quality, recommended)
2. noisereduce  (spectral gating, lightweight fallback, no neural net)

Install
-------
    pip install deepfilternet torch torchaudio     # AI model
    pip install noisereduce soundfile librosa numpy # fallback + I/O

Usage
-----
    python noise_reducer.py noisy.wav                      # -> noisy_clean.wav
    python noise_reducer.py noisy.wav -o clean.wav
    python noise_reducer.py noisy.mp3 --engine spectral --strength 0.8
"""

import argparse
import sys
from pathlib import Path


# --------------------------------------------------------------------------- #
# Engine 1: DeepFilterNet (AI)
# --------------------------------------------------------------------------- #
def denoise_deepfilternet(input_path: str, output_path: str) -> None:
    from df.enhance import enhance, init_df, load_audio, save_audio

    print("[AI] Loading DeepFilterNet model...")
    model, df_state, _ = init_df()

    print(f"[AI] Reading {input_path}")
    audio, _ = load_audio(input_path, sr=df_state.sr())

    print("[AI] Removing background noise...")
    enhanced = enhance(model, df_state, audio)

    save_audio(output_path, enhanced, df_state.sr())
    print(f"[AI] Saved -> {output_path}")


# --------------------------------------------------------------------------- #
# Engine 2: Spectral gating (fallback)
# --------------------------------------------------------------------------- #
def denoise_spectral(input_path: str, output_path: str, strength: float = 1.0) -> None:
    import librosa
    import noisereduce as nr
    import soundfile as sf

    print(f"[Spectral] Reading {input_path}")
    audio, sr = librosa.load(input_path, sr=None, mono=False)

    print("[Spectral] Removing background noise...")
    # stationary=False adapts to changing noise (traffic, fans, crowds)
    reduced = nr.reduce_noise(
        y=audio,
        sr=sr,
        stationary=False,
        prop_decrease=min(max(strength, 0.0), 1.0),
    )

    # soundfile expects (samples, channels)
    if reduced.ndim == 2:
        reduced = reduced.T
    sf.write(output_path, reduced, sr)
    print(f"[Spectral] Saved -> {output_path}")


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main() -> None:
    parser = argparse.ArgumentParser(description="AI background noise reduction")
    parser.add_argument("input", help="Path to noisy audio file (wav/mp3/flac)")
    parser.add_argument("-o", "--output", help="Output file (default: <input>_clean.wav)")
    parser.add_argument(
        "--engine",
        choices=["ai", "spectral"],
        default="ai",
        help="'ai' = DeepFilterNet, 'spectral' = noisereduce (default: ai)",
    )
    parser.add_argument(
        "--strength",
        type=float,
        default=1.0,
        help="Noise reduction strength 0-1 (spectral engine only)",
    )
    args = parser.parse_args()

    in_path = Path(args.input)
    if not in_path.exists():
        sys.exit(f"Error: file not found: {in_path}")

    out_path = args.output or str(in_path.with_name(in_path.stem + "_clean.wav"))

    if args.engine == "ai":
        try:
            denoise_deepfilternet(str(in_path), out_path)
            return
        except ImportError:
            print("DeepFilterNet not installed -> falling back to spectral gating.")
        except Exception as e:  # model/runtime errors
            print(f"AI engine failed ({e}) -> falling back to spectral gating.")

    denoise_spectral(str(in_path), out_path, args.strength)


if __name__ == "__main__":
    main()