document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const uploadArea = document.getElementById('upload-area');
    const imageUpload = document.getElementById('image-upload');
    const uploadPrompt = document.getElementById('upload-prompt');
    const previewContainer = document.getElementById('preview-container');
    const imagePreview = document.getElementById('image-preview');
    const removeBtn = document.getElementById('remove-btn');
    const analyzeBtn = document.getElementById('analyze-btn');
    
    // Left side specific outputs
    const detectedFaceArea = document.getElementById('detected-face-area');
    const detectedFaceImg = document.getElementById('detected-face-img');
    
    // Right side states
    const resultsEmpty = document.getElementById('results-empty');
    const resultsLoading = document.getElementById('results-loading');
    const resultsError = document.getElementById('results-error');
    const resultsContent = document.getElementById('results-content');
    
    // Result fields
    const errorMessage = document.getElementById('error-message');
    const retryBtn = document.getElementById('retry-btn');
    const matchThumbnail = document.getElementById('match-thumbnail');
    const thumbnailFallback = document.getElementById('thumbnail-fallback');
    const fallbackLink = document.getElementById('fallback-link');
    const matchTitle = document.getElementById('match-title');
    const matchSource = document.getElementById('match-source');
    const matchDistance = document.getElementById('match-distance');
    const matchLinkBtn = document.getElementById('match-link');
    
    const snippetSection = document.getElementById('snippet-section');
    const matchSnippet = document.getElementById('match-snippet');
    const tryAnotherBtn = document.getElementById('try-another-btn');
    
    const recordFingerprint = document.getElementById('record-fingerprint');
    const recordContract = document.getElementById('record-contract');
    const recordTx = document.getElementById('record-tx');
    
    // Loading state
    const loadingText = document.getElementById('loading-text');

    let selectedFile = null;

    // --- Upload Logic ---
    uploadArea.addEventListener('click', () => {
        if (!selectedFile) imageUpload.click();
    });

    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        if (!selectedFile) uploadArea.classList.add('dragover');
    });

    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('dragover');
    });

    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        if (e.dataTransfer.files.length && !selectedFile) {
            handleFileSelection(e.dataTransfer.files[0]);
        }
    });

    imageUpload.addEventListener('change', (e) => {
        if (e.target.files.length) {
            handleFileSelection(e.target.files[0]);
        }
    });

    removeBtn.addEventListener('click', (e) => {
        e.stopPropagation(); // prevent triggering upload click
        resetUpload();
    });

    function handleFileSelection(file) {
        if (!file.type.startsWith('image/')) {
            alert('Please select an image file.');
            return;
        }
        
        selectedFile = file;
        const reader = new FileReader();
        reader.onload = (e) => {
            imagePreview.src = e.target.result;
            uploadPrompt.classList.add('hidden');
            previewContainer.classList.remove('hidden');
            analyzeBtn.disabled = false;
        };
        reader.readAsDataURL(file);
    }

    function resetUpload() {
        selectedFile = null;
        imageUpload.value = '';
        imagePreview.src = '';
        uploadPrompt.classList.remove('hidden');
        previewContainer.classList.add('hidden');
        analyzeBtn.disabled = true;
        
        // Hide outputs
        detectedFaceArea.classList.add('hidden');
        
        // Reset right panel
        showState(resultsEmpty);
    }

    // --- UI State Management ---
    function showState(stateElement) {
        [resultsEmpty, resultsLoading, resultsError, resultsContent].forEach(el => {
            el.classList.add('hidden');
        });
        stateElement.classList.remove('hidden');
    }

    let progressInterval;
    function startProgressLabels() {
        const labels = [
            "Detecting face...",
            "Generating facial embedding...",
            "Searching live across the web...",
            "Validating candidate matches...",
            "Building cryptographic fingerprint...",
            "Uploading to blockchain...",
            "Confirming on-chain record..."
        ];
        
        let currentIndex = 0;
        loadingText.innerText = labels[currentIndex];
        
        if (progressInterval) clearInterval(progressInterval);
        
        progressInterval = setInterval(() => {
            if (currentIndex < labels.length - 1) {
                currentIndex++;
                loadingText.innerText = labels[currentIndex];
            } else {
                clearInterval(progressInterval);
            }
        }, 4000);
    }

    function stopProgressLabels() {
        if (progressInterval) {
            clearInterval(progressInterval);
            progressInterval = null;
        }
    }

    // --- Analysis Logic ---
    analyzeBtn.addEventListener('click', async () => {
        if (!selectedFile) return;

        // Setup UI for loading
        analyzeBtn.disabled = true;
        removeBtn.disabled = true;
        detectedFaceArea.classList.add('hidden');
        showState(resultsLoading);
        startProgressLabels();

        const formData = new FormData();
        formData.append('image', selectedFile);

        try {
            const response = await fetch('/api/analyze', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Unknown pipeline failure.');
            }

            renderSuccess(data);

        } catch (err) {
            errorMessage.innerText = err.message;
            showState(resultsError);
        } finally {
            stopProgressLabels();
            analyzeBtn.disabled = false;
            removeBtn.disabled = false;
        }
    });

    retryBtn.addEventListener('click', () => {
        resetUpload();
    });

    if (tryAnotherBtn) {
        tryAnotherBtn.addEventListener('click', () => {
            resetUpload();
        });
    }

    function renderSuccess(data) {
        // Render left side (Detected Face)
        const baseName = selectedFile.name.substring(0, selectedFile.name.lastIndexOf('.'));
        const expectedCropName = `${baseName}_cropped_face.jpg`;
        
        // Add a cache-busting query param so browser fetches new image if same filename
        detectedFaceImg.src = `/api/evidence-image?path=${encodeURIComponent(expectedCropName)}&t=${Date.now()}`;
        
        // Stop the scan line animation once loaded
        detectedFaceImg.onload = () => {
            const scanLine = document.querySelector('.scan-line');
            if (scanLine) scanLine.style.display = 'none';
        };
        detectedFaceArea.classList.remove('hidden');

        // Render right side (Match details)
        const match = data.matched_post;
        
        // Handle image loading (with fallback via proxy)
        matchThumbnail.classList.remove('hidden');
        thumbnailFallback.classList.add('hidden');
        
        let primaryImageUrl = match.image || match.thumbnail;
        
        if (primaryImageUrl) {
            matchThumbnail.src = `/api/proxy-image?url=${encodeURIComponent(primaryImageUrl)}`;
            matchThumbnail.onerror = () => {
                // If primary failed and we tried 'image', fallback to 'thumbnail'
                if (primaryImageUrl === match.image && match.thumbnail && match.image !== match.thumbnail) {
                    primaryImageUrl = match.thumbnail; // to prevent infinite loops, though unlikely here
                    matchThumbnail.src = `/api/proxy-image?url=${encodeURIComponent(match.thumbnail)}`;
                    
                    // Attach a new error handler for the fallback
                    matchThumbnail.onerror = () => {
                        matchThumbnail.classList.add('hidden');
                        thumbnailFallback.classList.remove('hidden');
                        fallbackLink.href = match.link;
                    };
                } else {
                    // Already tried thumbnail, or there is no fallback thumbnail available
                    matchThumbnail.classList.add('hidden');
                    thumbnailFallback.classList.remove('hidden');
                    fallbackLink.href = match.link;
                }
            };
        } else {
            matchThumbnail.classList.add('hidden');
            thumbnailFallback.classList.remove('hidden');
            fallbackLink.href = match.link;
        }

        matchTitle.innerText = match.title;
        matchSource.innerText = match.source;
        
        if (match.snippet) {
            matchSnippet.innerText = match.snippet;
            snippetSection.classList.remove('hidden');
        } else {
            matchSnippet.innerText = "";
            snippetSection.classList.add('hidden');
        }
        
        matchDistance.innerText = parseFloat(match.distance).toFixed(4);
        matchLinkBtn.href = match.link;

        // Render blockchain details
        recordFingerprint.innerText = data.fingerprint;
        recordFingerprint.title = data.fingerprint;
        
        recordContract.innerText = data.contract_address;
        recordContract.title = data.contract_address;
        
        recordTx.innerText = data.tx_hash;
        recordTx.title = data.tx_hash;

        showState(resultsContent);
    }
});
