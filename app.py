"""
SonicBloom - Song Enhancer Web Application
Enhances audio to make it warmer, smoother, and more soothing.
"""

import os
import uuid
import numpy as np
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
from scipy.signal import butter, sosfilt, sosfiltfilt
from scipy.ndimage import uniform_filter1d
import soundfile as sf
import librosa
import noisereduce as nr

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')
app.config['OUTPUT_FOLDER'] = os.path.join(os.path.dirname(__file__), 'outputs')

ALLOWED_EXTENSIONS = {'mp3', 'wav', 'flac', 'ogg', 'm4a', 'aac', 'wma', 'aiff'}

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ─── DSP Enhancement Functions ───────────────────────────────────────────────

def apply_warmth_eq(audio, sr):
    """Boost warm low-mids (200-500Hz) and attenuate harsh highs (3-8kHz)."""
    # Boost warm frequencies (200-500Hz)
    nyq = sr / 2.0
    low = 200 / nyq
    high = 500 / nyq
    sos_warm = butter(4, [low, high], btype='band', output='sos')
    warm_band = sosfiltfilt(sos_warm, audio)
    audio = audio + 0.25 * warm_band

    # Attenuate harsh frequencies (3kHz-8kHz)
    low_harsh = 3000 / nyq
    high_harsh = min(8000 / nyq, 0.99)
    sos_harsh = butter(4, [low_harsh, high_harsh], btype='band', output='sos')
    harsh_band = sosfiltfilt(sos_harsh, audio)
    audio = audio - 0.15 * harsh_band

    return audio


def apply_bass_enhancement(audio, sr):
    """Gently enhance sub-bass and bass frequencies for warmth."""
    nyq = sr / 2.0
    cutoff = 150 / nyq
    sos = butter(3, cutoff, btype='low', output='sos')
    bass = sosfiltfilt(sos, audio)
    return audio + 0.18 * bass


def apply_soft_compression(audio, threshold_db=-20, ratio=3.0, attack_ms=10, release_ms=100, sr=44100):
    """Apply gentle dynamic compression to even out volume."""
    threshold = 10 ** (threshold_db / 20.0)
    attack_samples = int(sr * attack_ms / 1000)
    release_samples = int(sr * release_ms / 1000)

    envelope = np.abs(audio)
    # Smooth envelope
    smoothed = uniform_filter1d(envelope, size=max(attack_samples, 1))

    gain = np.ones_like(audio)
    mask = smoothed > threshold
    gain[mask] = (threshold + (smoothed[mask] - threshold) / ratio) / smoothed[mask]

    # Smooth gain changes
    gain = uniform_filter1d(gain, size=max(release_samples, 1))

    return audio * gain


def apply_gentle_reverb(audio, sr, decay=0.3, delay_ms=30):
    """Add a subtle, warm reverb tail."""
    delay_samples = int(sr * delay_ms / 1000)
    result = np.copy(audio)

    for i in range(1, 5):
        offset = delay_samples * i
        decayed = decay ** i
        if offset < len(audio):
            padded = np.zeros_like(audio)
            padded[offset:] = audio[:-offset] * decayed
            result += padded

    # Normalize to prevent clipping
    max_val = np.max(np.abs(result))
    if max_val > 0:
        result = result / max_val * np.max(np.abs(audio))

    return result


def apply_stereo_widening(left, right, width=1.3):
    """Widen the stereo field for an immersive feel."""
    mid = (left + right) / 2.0
    side = (left - right) / 2.0
    side *= width
    new_left = mid + side
    new_right = mid - side
    return new_left, new_right


def apply_noise_reduction(audio, sr):
    """Reduce background noise for a cleaner sound."""
    reduced = nr.reduce_noise(y=audio, sr=sr, prop_decrease=0.6, stationary=True)
    return reduced


def apply_air_eq(audio, sr):
    """Add subtle 'air' frequencies (10kHz+) for sparkle without harshness."""
    nyq = sr / 2.0
    air_freq = min(10000 / nyq, 0.95)
    sos = butter(2, air_freq, btype='high', output='sos')
    air_band = sosfiltfilt(sos, audio)
    return audio + 0.08 * air_band


def normalize_audio(audio, target_db=-3):
    """Normalize audio to a target peak dB level."""
    peak = np.max(np.abs(audio))
    if peak > 0:
        target_amplitude = 10 ** (target_db / 20.0)
        audio = audio * (target_amplitude / peak)
    return audio


def enhance_audio(input_path, output_path, settings):
    """Main enhancement pipeline."""
    # Load audio
    audio, sr = librosa.load(input_path, sr=None, mono=False)

    is_stereo = audio.ndim == 2

    if is_stereo:
        left, right = audio[0], audio[1]
    else:
        left = audio
        right = None

    # Enhancement intensity (0.0 - 1.0)
    intensity = settings.get('intensity', 0.8)

    # 1. Noise Reduction
    if settings.get('noise_reduction', True):
        left = apply_noise_reduction(left, sr)
        if right is not None:
            right = apply_noise_reduction(right, sr)

    # 2. Warmth EQ
    if settings.get('warmth', True):
        left_warm = apply_warmth_eq(left, sr)
        left = left * (1 - intensity) + left_warm * intensity
        if right is not None:
            right_warm = apply_warmth_eq(right, sr)
            right = right * (1 - intensity) + right_warm * intensity

    # 3. Bass Enhancement
    if settings.get('bass_boost', True):
        left_bass = apply_bass_enhancement(left, sr)
        left = left * (1 - intensity * 0.5) + left_bass * (intensity * 0.5)
        if right is not None:
            right_bass = apply_bass_enhancement(right, sr)
            right = right * (1 - intensity * 0.5) + right_bass * (intensity * 0.5)

    # 4. Soft Compression
    if settings.get('compression', True):
        left = apply_soft_compression(left, threshold_db=-18, ratio=2.5 + intensity, sr=sr)
        if right is not None:
            right = apply_soft_compression(right, threshold_db=-18, ratio=2.5 + intensity, sr=sr)

    # 5. Air EQ
    if settings.get('air', True):
        left_air = apply_air_eq(left, sr)
        left = left * (1 - intensity * 0.3) + left_air * (intensity * 0.3)
        if right is not None:
            right_air = apply_air_eq(right, sr)
            right = right * (1 - intensity * 0.3) + right_air * (intensity * 0.3)

    # 6. Gentle Reverb
    if settings.get('reverb', True):
        reverb_amount = 0.15 + (intensity * 0.25)
        left = apply_gentle_reverb(left, sr, decay=reverb_amount, delay_ms=25 + int(intensity * 15))
        if right is not None:
            right = apply_gentle_reverb(right, sr, decay=reverb_amount, delay_ms=25 + int(intensity * 15))

    # 7. Stereo Widening
    if is_stereo and settings.get('stereo_width', True):
        width = 1.0 + (intensity * 0.4)
        left, right = apply_stereo_widening(left, right, width=width)

    # 8. Final Normalization
    if is_stereo:
        combined = np.stack([left, right])
        combined = normalize_audio(combined, target_db=-1)
        output_audio = combined.T
    else:
        left = normalize_audio(left, target_db=-1)
        output_audio = left

    # Write output
    sf.write(output_path, output_audio, sr, subtype='PCM_24')

    return {
        'sample_rate': sr,
        'duration': len(left) / sr,
        'channels': 2 if is_stereo else 1
    }


# ─── Routes ──────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    if 'audio' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['audio']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': f'Unsupported format. Use: {", ".join(ALLOWED_EXTENSIONS)}'}), 400

    # Generate unique filenames
    file_id = str(uuid.uuid4())[:8]
    ext = file.filename.rsplit('.', 1)[1].lower()
    original_name = secure_filename(file.filename)
    input_filename = f"{file_id}_original.{ext}"
    output_filename = f"{file_id}_enhanced.wav"

    input_path = os.path.join(app.config['UPLOAD_FOLDER'], input_filename)
    output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)

    file.save(input_path)

    # Parse enhancement settings
    settings = {
        'intensity': float(request.form.get('intensity', 0.8)),
        'warmth': request.form.get('warmth', 'true') == 'true',
        'bass_boost': request.form.get('bass_boost', 'true') == 'true',
        'compression': request.form.get('compression', 'true') == 'true',
        'reverb': request.form.get('reverb', 'true') == 'true',
        'stereo_width': request.form.get('stereo_width', 'true') == 'true',
        'noise_reduction': request.form.get('noise_reduction', 'true') == 'true',
        'air': request.form.get('air', 'true') == 'true',
    }

    try:
        info = enhance_audio(input_path, output_path, settings)
        return jsonify({
            'success': True,
            'file_id': file_id,
            'original_name': original_name,
            'duration': round(info['duration'], 2),
            'sample_rate': info['sample_rate'],
            'channels': info['channels'],
            'download_url': f'/download/{output_filename}'
        })
    except Exception as e:
        return jsonify({'error': f'Enhancement failed: {str(e)}'}), 500
    finally:
        # Clean up original upload
        if os.path.exists(input_path):
            os.remove(input_path)


@app.route('/download/<filename>')
def download_file(filename):
    filepath = os.path.join(app.config['OUTPUT_FOLDER'], filename)
    if not os.path.exists(filepath):
        return jsonify({'error': 'File not found'}), 404
    return send_file(filepath, as_attachment=True, download_name=f"enhanced_{filename}")


if __name__ == '__main__':
    print("\n  * SonicBloom - Song Enhancer *")
    print("  ------------------------------")
    print("  Running at: http://localhost:5000\n")
    app.run(debug=True, host='0.0.0.0', port=5000)
