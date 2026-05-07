document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('transcribeForm');
    const fileInput = document.getElementById('fileInput');
    const dropZone = document.getElementById('dropZone');
    const fileNameDisplay = document.getElementById('fileName');
    const submitBtn = document.getElementById('submitBtn');
    const spinner = document.getElementById('spinner');
    const statusMessage = document.getElementById('statusMessage');
    const modelSelect = document.getElementById('model');
    const langSelect = document.getElementById('lang');
    const translateSelect = document.getElementById('translate_to');

    const SWISS_GERMAN_MODEL = 'nebi/whisper-large-v3-turbo-swiss-german-ct2-int8';

    let TRANSLATION_PAIRS = {};

    async function fetchTranslationPairs() {
        try {
            const res = await fetch('/api/translations');
            if (res.ok) {
                TRANSLATION_PAIRS = await res.json();
                updateTranslateOptions();
            }
        } catch (e) {
            console.error("Failed to load translation pairs", e);
        }
    }

    function updateTranslateOptions() {
        const lang = langSelect.value;
        const validTargets = TRANSLATION_PAIRS[lang] || [];

        Array.from(translateSelect.options).forEach(opt => {
            if (opt.value === '') {
                opt.disabled = false;  // "None" always available
            } else {
                opt.disabled = !validTargets.includes(opt.value);
                if (opt.selected && opt.disabled) {
                    translateSelect.value = '';
                }
            }
        });
    }

    langSelect.addEventListener('change', () => {
        if (langSelect.value === 'gsw') {
            modelSelect.value = SWISS_GERMAN_MODEL;
            showStatus('Swiss German model auto-selected.', 'normal');
        }
        updateTranslateOptions();
    });

    // Initialize on load
    fetchTranslationPairs();

    // Drag and drop handlers
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, highlight, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, unhighlight, false);
    });

    function highlight(e) {
        dropZone.classList.add('dragover');
    }

    function unhighlight(e) {
        dropZone.classList.remove('dragover');
    }

    dropZone.addEventListener('drop', handleDrop, false);

    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        handleFiles(files);
    }

    // Native picker for "Browse Files" button
    window.pickFile = async function () {
        if (window.pywebview && window.pywebview.api) {
            const filePath = await window.pywebview.api.pick_file();
            if (filePath) {
                window.selectedFilePath = filePath;
                fileNameDisplay.textContent = filePath.split('/').pop() || filePath.split('\\').pop();
                fileInput.value = '';
            }
        } else {
            document.getElementById('fileInput').click();
        }
    };

    const browseBtn = document.querySelector('.btn-secondary');
    if (browseBtn) {
        browseBtn.onclick = (e) => {
            e.preventDefault();
            window.pickFile();
        };
    }

    fileInput.addEventListener('change', function () {
        handleFiles(this.files);
    });

    function handleFiles(files) {
        if (files.length > 0) {
            fileInput.files = files;
            fileNameDisplay.textContent = files[0].name;
            window.selectedFilePath = null;
        }
    }

    // Form submission
    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        if (!fileInput.files.length && !window.selectedFilePath) {
            showStatus('Please select a file first.', 'error');
            return;
        }

        setLoading(true);
        showStatus('Transcribing...', 'normal');

        // Reset progress
        const progressContainer = document.getElementById('progressContainer');
        const progressBar = document.getElementById('progressBar');
        const progressText = document.getElementById('progressText');
        progressContainer.style.display = 'block';
        progressBar.style.width = '0%';
        progressText.textContent = '0%';

        const formData = new FormData(form);

        if (window.selectedFilePath) {
            formData.append('file_path', window.selectedFilePath);
        }

        // Map Swiss German (gsw) to German (de) for the backend/model
        if (formData.get('lang') === 'gsw') {
            formData.set('lang', 'de');
        }

        try {
            const response = await fetch('/transcribe', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                let errMessage = `Server responded with ${response.status}`;
                try {
                    const errorData = await response.json();
                    if (errorData.message) {
                        errMessage = errorData.message;
                    }
                } catch(e) {
                    // Ignore, fallback to generic
                }
                throw new Error(errMessage);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value, { stream: true });
                const lines = chunk.split('\n');

                for (const line of lines) {
                    if (!line.trim()) continue;

                    try {
                        const data = JSON.parse(line);

                        if (data.type === 'progress') {
                            const percent = Math.round(data.value * 100);
                            progressBar.style.width = `${percent}%`;
                            progressText.textContent = `${percent}%`;
                        } else if (data.type === 'status') {
                            showStatus(data.message, 'normal');
                        } else if (data.type === 'complete') {
                            progressBar.style.width = '100%';
                            progressText.textContent = '100%';
                            showStatus('Transcription complete! Download started.', 'success');

                            // Download original SRT
                            await downloadSrtFile(data.url);

                            // Download translated SRT if available
                            if (data.translated_url) {
                                showStatus('Downloading translated subtitles...', 'success');
                                await downloadSrtFile(data.translated_url);
                                showStatus('Both original and translated subtitles downloaded!', 'success');
                            }
                        } else if (data.type === 'error') {
                            showStatus(`Error: ${data.message}`, 'error');
                        }
                    } catch (e) {
                        console.error('Error parsing JSON:', e);
                    }
                }
            }
        } catch (error) {
            console.error('Error:', error);
            showStatus(`Error: ${error.message}`, 'error');
        } finally {
            setLoading(false);
        }
    });

    function setLoading(isLoading) {
        submitBtn.disabled = isLoading;
        spinner.style.display = isLoading ? 'block' : 'none';
    }

    function showStatus(message, type) {
        statusMessage.textContent = message;
        statusMessage.className = 'status-message';
        if (type === 'success') statusMessage.classList.add('status-success');
        if (type === 'error') statusMessage.classList.add('status-error');
    }

    async function downloadSrtFile(url) {
        try {
            const fileRes = await fetch(url);
            const text = await fileRes.text();

            const urlParams = new URLSearchParams(url.split('?')[1]);
            const filename = urlParams.get('download_name') || 'subtitles.srt';

            if (window.pywebview && window.pywebview.api) {
                await window.pywebview.api.save_file(text, filename);
            } else {
                const blob = new Blob([text], { type: 'text/plain' });
                const a = document.createElement('a');
                a.style.display = 'none';
                a.href = URL.createObjectURL(blob);
                a.download = filename;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
            }
        } catch (e) {
            console.error('Download error:', e);
            showStatus(`Download failed: ${e.message}`, 'error');
        }
    }
});
