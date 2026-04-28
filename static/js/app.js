/**
 * SonicBloom — Frontend Logic
 * Handles file upload, enhancement controls, progress simulation, and download.
 */

document.addEventListener('DOMContentLoaded', () => {
    // ─── DOM References ──────────────────────────────────────
    const uploadZone = document.getElementById('upload-zone');
    const fileInput = document.getElementById('file-input');
    const fileInfo = document.getElementById('file-info');
    const fileName = document.getElementById('file-name');
    const fileSize = document.getElementById('file-size');
    const fileRemove = document.getElementById('file-remove');
    const enhanceBtn = document.getElementById('enhance-btn');
    const intensitySlider = document.getElementById('intensity-slider');
    const intensityValue = document.getElementById('intensity-value');
    const progressSection = document.getElementById('progress-section');
    const progressPercent = document.getElementById('progress-percent');
    const progressRingFill = document.getElementById('progress-ring-fill');
    const progressStatus = document.getElementById('progress-status');
    const resultSection = document.getElementById('result-section');
    const downloadBtn = document.getElementById('download-btn');
    const resetBtn = document.getElementById('reset-btn');
    const errorSection = document.getElementById('error-section');
    const errorMessage = document.getElementById('error-message');
    const errorResetBtn = document.getElementById('error-reset-btn');
    const controlsSection = document.getElementById('controls-section');

    let selectedFile = null;
    const CIRCUMFERENCE = 2 * Math.PI * 52; // progress ring circumference

    // ─── Particle Background ─────────────────────────────────
    const canvas = document.getElementById('particleCanvas');
    const ctx = canvas.getContext('2d');
    let particles = [];

    function resizeCanvas() {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
    }
    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);

    class Particle {
        constructor() { this.reset(); }
        reset() {
            this.x = Math.random() * canvas.width;
            this.y = Math.random() * canvas.height;
            this.size = Math.random() * 2 + 0.5;
            this.speedX = (Math.random() - 0.5) * 0.3;
            this.speedY = (Math.random() - 0.5) * 0.3;
            this.opacity = Math.random() * 0.3 + 0.05;
            this.hue = Math.random() > 0.5 ? 270 : 330;
        }
        update() {
            this.x += this.speedX;
            this.y += this.speedY;
            if (this.x < 0 || this.x > canvas.width || this.y < 0 || this.y > canvas.height) this.reset();
        }
        draw() {
            ctx.beginPath();
            ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
            ctx.fillStyle = `hsla(${this.hue}, 70%, 70%, ${this.opacity})`;
            ctx.fill();
        }
    }

    for (let i = 0; i < 60; i++) particles.push(new Particle());

    function animateParticles() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        particles.forEach(p => { p.update(); p.draw(); });
        requestAnimationFrame(animateParticles);
    }
    animateParticles();

    // ─── File Helpers ────────────────────────────────────────
    function formatSize(bytes) {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / 1048576).toFixed(1) + ' MB';
    }

    function setFile(file) {
        selectedFile = file;
        fileName.textContent = file.name;
        fileSize.textContent = formatSize(file.size);
        uploadZone.classList.add('hidden');
        fileInfo.classList.remove('hidden');
        enhanceBtn.disabled = false;
    }

    function clearFile() {
        selectedFile = null;
        fileInput.value = '';
        uploadZone.classList.remove('hidden');
        fileInfo.classList.add('hidden');
        enhanceBtn.disabled = true;
    }

    // ─── Upload Zone Events ──────────────────────────────────
    uploadZone.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', (e) => { if (e.target.files[0]) setFile(e.target.files[0]); });
    fileRemove.addEventListener('click', clearFile);

    uploadZone.addEventListener('dragover', (e) => { e.preventDefault(); uploadZone.classList.add('drag-over'); });
    uploadZone.addEventListener('dragleave', () => uploadZone.classList.remove('drag-over'));
    uploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadZone.classList.remove('drag-over');
        if (e.dataTransfer.files[0]) setFile(e.dataTransfer.files[0]);
    });

    // ─── Intensity Slider ────────────────────────────────────
    intensitySlider.addEventListener('input', () => {
        intensityValue.textContent = intensitySlider.value + '%';
        // Dynamic slider track fill
        const pct = intensitySlider.value;
        intensitySlider.style.background = `linear-gradient(90deg, #a78bfa ${pct}%, rgba(255,255,255,0.08) ${pct}%)`;
    });
    // Init fill
    intensitySlider.dispatchEvent(new Event('input'));

    // ─── Progress Helpers ────────────────────────────────────
    function setProgress(pct) {
        const offset = CIRCUMFERENCE - (pct / 100) * CIRCUMFERENCE;
        progressRingFill.style.strokeDashoffset = offset;
        progressPercent.textContent = Math.round(pct) + '%';
    }

    function setStep(stepId) {
        const steps = ['step-upload', 'step-analyze', 'step-enhance', 'step-export'];
        const idx = steps.indexOf(stepId);
        steps.forEach((s, i) => {
            const el = document.getElementById(s);
            el.classList.remove('active', 'done');
            if (i < idx) el.classList.add('done');
            else if (i === idx) el.classList.add('active');
        });
    }

    const statusMessages = {
        'step-upload': 'Uploading audio...',
        'step-analyze': 'Analyzing waveform...',
        'step-enhance': 'Applying enhancements...',
        'step-export': 'Exporting enhanced track...',
    };

    // ─── Enhance ─────────────────────────────────────────────
    enhanceBtn.addEventListener('click', async () => {
        if (!selectedFile) return;

        // Show progress, hide others
        controlsSection.classList.add('hidden');
        enhanceBtn.classList.add('hidden');
        fileInfo.classList.add('hidden');
        resultSection.classList.add('hidden');
        errorSection.classList.add('hidden');
        progressSection.classList.remove('hidden');
        setProgress(0);
        setStep('step-upload');
        progressStatus.textContent = statusMessages['step-upload'];

        // Build form data
        const form = new FormData();
        form.append('audio', selectedFile);
        form.append('intensity', (intensitySlider.value / 100).toFixed(2));
        form.append('warmth', document.getElementById('warmth-toggle').checked);
        form.append('bass_boost', document.getElementById('bass-toggle').checked);
        form.append('compression', document.getElementById('compression-toggle').checked);
        form.append('reverb', document.getElementById('reverb-toggle').checked);
        form.append('stereo_width', document.getElementById('stereo-toggle').checked);
        form.append('noise_reduction', document.getElementById('noise-toggle').checked);
        form.append('air', document.getElementById('air-toggle').checked);

        // Simulate progress while waiting
        let fakeProgress = 0;
        const progressInterval = setInterval(() => {
            fakeProgress += Math.random() * 3 + 0.5;
            if (fakeProgress > 90) fakeProgress = 90;
            setProgress(fakeProgress);

            if (fakeProgress < 20) { setStep('step-upload'); progressStatus.textContent = statusMessages['step-upload']; }
            else if (fakeProgress < 45) { setStep('step-analyze'); progressStatus.textContent = statusMessages['step-analyze']; }
            else if (fakeProgress < 85) { setStep('step-enhance'); progressStatus.textContent = statusMessages['step-enhance']; }
            else { setStep('step-export'); progressStatus.textContent = statusMessages['step-export']; }
        }, 400);

        try {
            const resp = await fetch('/upload', { method: 'POST', body: form });
            clearInterval(progressInterval);

            const data = await resp.json();

            if (!resp.ok || data.error) {
                throw new Error(data.error || 'Unknown error');
            }

            // Complete progress
            setProgress(100);
            setStep('step-export');
            progressStatus.textContent = 'Done!';
            document.getElementById('step-export').classList.remove('active');
            document.getElementById('step-export').classList.add('done');

            setTimeout(() => {
                progressSection.classList.add('hidden');
                resultSection.classList.remove('hidden');

                // Populate stats
                const mins = Math.floor(data.duration / 60);
                const secs = Math.floor(data.duration % 60);
                document.getElementById('stat-duration').textContent = `${mins}:${String(secs).padStart(2, '0')}`;
                document.getElementById('stat-samplerate').textContent = (data.sample_rate / 1000).toFixed(1) + ' kHz';
                document.getElementById('stat-channels').textContent = data.channels === 2 ? 'Stereo' : 'Mono';

                downloadBtn.href = data.download_url;
            }, 800);

        } catch (err) {
            clearInterval(progressInterval);
            progressSection.classList.add('hidden');
            errorSection.classList.remove('hidden');
            errorMessage.textContent = err.message || 'Something went wrong during enhancement.';
        }
    });

    // ─── Reset ───────────────────────────────────────────────
    function resetAll() {
        clearFile();
        resultSection.classList.add('hidden');
        errorSection.classList.add('hidden');
        progressSection.classList.add('hidden');
        controlsSection.classList.remove('hidden');
        enhanceBtn.classList.remove('hidden');
        setProgress(0);
    }

    resetBtn.addEventListener('click', resetAll);
    errorResetBtn.addEventListener('click', resetAll);
});
