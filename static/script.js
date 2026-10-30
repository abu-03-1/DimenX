// ===== MODERN 3D STUDIO JAVASCRIPT =====

class ThreeDStudio {
    constructor() {
        this.selectedFile = null;
        this.initializeEventListeners();
        this.initializeParticles();
        this.initializeTextureSystem();
    }

    initializeEventListeners() {
        // File input change
        const fileInput = document.getElementById('fileInput');
        if (fileInput) {
            fileInput.addEventListener('change', (e) => this.handleFileSelect(e));
        }

        // Upload area click
        const uploadArea = document.querySelector('.upload-area');
        if (uploadArea) {
            uploadArea.addEventListener('click', () => fileInput.click());
        }

        // Drag and drop events
        this.initializeDragAndDrop();

        // Model actions
        this.initializeModelActions();
    }

    initializeTextureSystem() {
        // Initialize texture system for model view page
        this.loadColorPalettes();
        
        // Add texture button event listeners
        this.initializeTextureButtons();
    }

    initializeTextureButtons() {
        // Texture application buttons
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('texture-btn') || 
                e.target.closest('.texture-btn')) {
                const btn = e.target.classList.contains('texture-btn') ? e.target : e.target.closest('.texture-btn');
                const modelId = btn.dataset.modelId || this.getCurrentModelId();
                if (modelId && btn.id === 'imageTextureBtn') {
                    this.applyImageTexture(modelId);
                }
            }

            // Material texture buttons
            if (e.target.classList.contains('variant-btn') && 
                e.target.dataset.texture) {
                const modelId = this.getCurrentModelId();
                const textureType = e.target.dataset.texture;
                if (modelId) {
                    this.applyTexture(modelId, textureType);
                }
            }
        });
    }

    getCurrentModelId() {
        // Extract model ID from current page
        const path = window.location.pathname;
        const modelMatch = path.match(/\/model\/([a-zA-Z0-9]+)/);
        if (modelMatch) return modelMatch[1];
        
        // Try to get from data attributes
        const modelCard = document.querySelector('[data-model-id]');
        return modelCard ? modelCard.dataset.modelId : null;
    }

    async loadColorPalettes() {
        const modelId = this.getCurrentModelId();
        if (modelId) {
            await this.loadColorPalette(modelId);
        }
    }

    // ===== IMAGE COLOR TEXTURE SYSTEM =====

    // Load color palette from original image
    async loadColorPalette(modelId) {
        try {
            const response = await fetch(`/api/extract_colors/${modelId}`);
            const data = await response.json();
            
            if (data.success && data.colors) {
                const colorPalette = document.getElementById('colorPalette');
                if (colorPalette) {
                    colorPalette.innerHTML = '';
                    
                    data.colors.forEach(color => {
                        const swatch = document.createElement('div');
                        swatch.className = 'color-swatch';
                        swatch.style.background = color;
                        swatch.title = color;
                        colorPalette.appendChild(swatch);
                    });
                }
            }
        } catch (error) {
            console.error('Failed to load color palette:', error);
        }
    }

    // Apply image texture to 3D model
    async applyImageTexture(modelId) {
        const btn = document.getElementById('imageTextureBtn');
        const progress = document.getElementById('imageTextureProgress');
        const progressFill = document.getElementById('imageTextureFill');
        const progressText = document.getElementById('imageTextureText');
        
        if (!btn) return;
        
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
        if (progress) progress.style.display = 'block';
        
        try {
            // Simulate progress
            let progressValue = 0;
            const progressInterval = setInterval(() => {
                progressValue += 5;
                if (progressFill) progressFill.style.width = `${progressValue}%`;
                if (progressValue >= 90) clearInterval(progressInterval);
            }, 200);
            
            const response = await fetch(`/api/apply_image_texture/${modelId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });

            const data = await response.json();
            
            clearInterval(progressInterval);
            if (progressFill) progressFill.style.width = '100%';
            
            if (data.success) {
                if (progressText) progressText.textContent = '✅ Texture Applied!';
                this.showNotification('🎨 Image colors applied successfully!', 'success');
                
                // Update download links if available
                this.updateTextureDownloadLinks(modelId, data);
                
                setTimeout(() => {
                    btn.disabled = false;
                    btn.innerHTML = '<i class="fas fa-magic"></i> Apply Image Colors';
                    if (progress) progress.style.display = 'none';
                    if (progressFill) progressFill.style.width = '0%';
                    if (progressText) progressText.textContent = 'Processing...';
                }, 2000);
            } else {
                throw new Error(data.error);
            }
        } catch (error) {
            console.error('Image texture error:', error);
            if (progressText) progressText.textContent = '❌ Failed';
            this.showNotification('❌ Failed to apply image texture: ' + error.message, 'error');
            
            setTimeout(() => {
                btn.disabled = false;
                btn.innerHTML = '<i class="fas fa-magic"></i> Apply Image Colors';
                if (progress) progress.style.display = 'none';
                if (progressFill) progressFill.style.width = '0%';
                if (progressText) progressText.textContent = 'Processing...';
            }, 3000);
        }
    }

    // Apply material texture
    async applyTexture(modelId, textureType) {
        const textureNames = {
            'metal': 'Metal',
            'wood': 'Wood', 
            'glass': 'Glass',
            'gold': 'Gold',
            'silver': 'Silver',
            'crystal': 'Crystal'
        };
        
        try {
            const response = await fetch(`/api/apply_texture/${modelId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    texture_type: textureType
                })
            });

            const data = await response.json();

            if (data.success) {
                this.showNotification(`✅ ${textureNames[textureType]} texture applied!`, 'success');
                this.updateTextureDownloadLinks(modelId, data);
            } else {
                throw new Error(data.error);
            }
        } catch (error) {
            console.error('Texture error:', error);
            this.showNotification('❌ Failed to apply texture: ' + error.message, 'error');
        }
    }

    // Update download links after texture application
    updateTextureDownloadLinks(modelId, textureData) {
        // Update GLB download link
        const glbDownloadBtn = document.querySelector(`[href*="/download_glb/${modelId}"]`);
        if (glbDownloadBtn && textureData.download_url) {
            glbDownloadBtn.href = textureData.download_url;
        }

        // Update preview link
        const previewBtn = document.querySelector(`[href*="/models/${modelId}"]`);
        if (previewBtn && textureData.textured_url) {
            previewBtn.href = textureData.textured_url;
        }

        // Show textured model badge
        this.showTexturedModelBadge();
    }

    showTexturedModelBadge() {
        const badgeContainer = document.querySelector('.quality-badges') || document.querySelector('.model-info');
        if (badgeContainer && !document.querySelector('.texture-badge')) {
            const textureBadge = document.createElement('span');
            textureBadge.className = 'texture-badge';
            textureBadge.innerHTML = '<i class="fas fa-palette"></i> TEXTURED';
            badgeContainer.appendChild(textureBadge);
        }
    }

    initializeDragAndDrop() {
        const uploadArea = document.querySelector('.upload-area');
        if (!uploadArea) return;

        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.style.borderColor = '#00b4db';
            uploadArea.style.background = 'rgba(0, 180, 219, 0.2)';
            uploadArea.classList.add('drag-over');
        });

        uploadArea.addEventListener('dragleave', () => {
            uploadArea.style.borderColor = 'rgba(255, 255, 255, 0.3)';
            uploadArea.style.background = 'transparent';
            uploadArea.classList.remove('drag-over');
        });

        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.style.borderColor = 'rgba(255, 255, 255, 0.3)';
            uploadArea.style.background = 'transparent';
            uploadArea.classList.remove('drag-over');
            
            if (e.dataTransfer.files.length) {
                this.handleFileSelect({ target: { files: e.dataTransfer.files } });
            }
        });
    }

    initializeModelActions() {
        // Add ripple effects to download buttons
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('download-btn') || 
                e.target.classList.contains('action-btn') ||
                e.target.classList.contains('variant-btn') ||
                e.target.classList.contains('texture-btn')) {
                this.createRippleEffect(e);
            }
        });
    }

    initializeParticles() {
        // Particles.js will be initialized by the HTML files directly
        console.log('3D Studio initialized with modern design');
    }

    handleFileSelect(event) {
        const files = event.target.files;
        if (files.length > 0) {
            this.selectedFile = files[0];
            this.processFile(this.selectedFile);
        }
    }

    isValidFile(file) {
        const allowedTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/bmp', 'image/webp'];
        return allowedTypes.includes(file.type);
    }

    processFile(file) {
        if (!this.isValidFile(file)) {
            this.showNotification('Please select a valid image file (PNG, JPG, JPEG, BMP, WEBP)', 'error');
            return;
        }

        if (file.size > 50 * 1024 * 1024) {
            this.showNotification('File size must be less than 50MB', 'error');
            return;
        }

        // Show upload form
        const uploadForm = document.getElementById('uploadForm');
        if (uploadForm) {
            uploadForm.style.display = 'block';
            
            // Auto-generate model name from filename
            const fileName = file.name.replace(/\.[^/.]+$/, "");
            const modelNameInput = document.getElementById('modelName');
            if (modelNameInput) {
                modelNameInput.value = fileName + ' 3D Model';
            }
        }

        this.showNotification('Image selected successfully! Click "Generate 3D Model" to continue.', 'success');
    }

    async uploadFile() {
        if (!this.selectedFile) {
            this.showNotification('Please select a file first!', 'error');
            return;
        }

        const modelNameInput = document.getElementById('modelName');
        const modelName = modelNameInput ? modelNameInput.value : 'My 3D Model';

        const formData = new FormData();
        formData.append('file', this.selectedFile);
        formData.append('model_name', modelName);

        // Show loading state
        this.showLoadingState(true);

        try {
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (data.success) {
                this.showNotification('🎉 ' + data.message, 'success');
                // Reload page to show new model in dashboard
                setTimeout(() => {
                    window.location.reload();
                }, 2000);
            } else {
                this.showNotification('❌ ' + data.error, 'error');
            }
        } catch (error) {
            console.error('Upload error:', error);
            this.showNotification('❌ Upload failed: ' + error, 'error');
        } finally {
            this.showLoadingState(false);
        }
    }

    // 🔽 FBX CONVERSION FUNCTION
    async convertToFBX(modelId) {
        const fbxBtn = document.getElementById(`fbxBtn${modelId}`);
        const progressBar = document.getElementById(`fbxProgress${modelId}`);
        const progressFill = document.getElementById(`fbxProgressFill${modelId}`);
        const progressText = document.getElementById(`fbxProgressText${modelId}`);

        if (!fbxBtn) {
            this.showNotification('FBX conversion element not found', 'error');
            return;
        }

        // Show loading state
        fbxBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Converting...';
        fbxBtn.disabled = true;
        if (progressBar) progressBar.style.display = 'block';
        if (progressText) progressText.style.display = 'block';
        if (progressFill) progressFill.style.width = '30%';

        try {
            const response = await fetch(`/convert_to_fbx/${modelId}`);
            const data = await response.json();

            if (progressFill) progressFill.style.width = '100%';

            if (data.success) {
                this.showNotification('✅ FBX conversion completed! Download ready.', 'success');
                
                // Update button to download FBX
                setTimeout(() => {
                    fbxBtn.innerHTML = '<i class="fas fa-download"></i> Download FBX';
                    fbxBtn.disabled = false;
                    fbxBtn.onclick = () => {
                        window.location.href = data.download_url || `/download_fbx/${modelId}`;
                    };
                    fbxBtn.classList.remove('fbx-btn');
                    fbxBtn.classList.add('converting-btn');
                    if (progressBar) progressBar.style.display = 'none';
                    if (progressText) progressText.style.display = 'none';
                }, 1000);
            } else {
                throw new Error(data.error);
            }
        } catch (error) {
            console.error('FBX conversion error:', error);
            this.showNotification('❌ FBX conversion failed: ' + error.message, 'error');
            
            // Reset button
            fbxBtn.innerHTML = '<i class="fas fa-sync-alt"></i> Convert to FBX';
            fbxBtn.disabled = false;
            if (progressBar) progressBar.style.display = 'none';
            if (progressText) progressText.style.display = 'none';
            if (progressFill) progressFill.style.width = '0%';
        }
    }

    showLoadingState(show) {
        const loadingOverlay = document.getElementById('loadingOverlay');
        if (loadingOverlay) {
            loadingOverlay.style.display = show ? 'flex' : 'none';
        }
        
        if (show) {
            document.body.style.cursor = 'wait';
        } else {
            document.body.style.cursor = 'default';
        }
    }

    createRippleEffect(event) {
        const button = event.target;
        const ripple = document.createElement('span');
        const rect = button.getBoundingClientRect();
        const size = Math.max(rect.width, rect.height);
        const x = event.clientX - rect.left - size / 2;
        const y = event.clientY - rect.top - size / 2;
        
        ripple.style.cssText = `
            position: absolute;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.6);
            transform: scale(0);
            animation: ripple 0.6s linear;
            width: ${size}px;
            height: ${size}px;
            left: ${x}px;
            top: ${y}px;
            pointer-events: none;
        `;
        
        button.style.position = 'relative';
        button.style.overflow = 'hidden';
        button.appendChild(ripple);
        
        setTimeout(() => {
            ripple.remove();
        }, 600);
    }

    showNotification(message, type = 'info') {
        // Remove existing notification
        const existingNotification = document.querySelector('.notification');
        if (existingNotification) {
            existingNotification.remove();
        }

        // Create new notification
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.innerHTML = `
            <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'exclamation-triangle'}"></i>
            ${message}
        `;

        document.body.appendChild(notification);

        // Auto remove after 5 seconds
        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, 5000);
    }

    // Model preview functionality
    previewModel(modelUrl) {
        if (modelUrl) {
            window.open(modelUrl, '_blank');
        } else {
            this.showNotification('Preview not available for this model', 'warning');
        }
    }

    // Download model functionality
    downloadModel(downloadUrl, filename) {
        if (downloadUrl) {
            const link = document.createElement('a');
            link.href = downloadUrl;
            link.download = filename || '3d-model.glb';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            this.showNotification('📥 Download started!', 'success');
        } else {
            this.showNotification('Download link not available', 'error');
        }
    }

    // Share model functionality
    shareModel(modelId) {
        const modelUrl = window.location.href;
        if (navigator.share) {
            navigator.share({
                title: '3D Model - 3D Magic Studio',
                text: 'Check out this amazing 3D model!',
                url: modelUrl
            })
            .then(() => this.showNotification('Model shared successfully!', 'success'))
            .catch(() => this.copyToClipboard(modelUrl));
        } else {
            this.copyToClipboard(modelUrl);
        }
    }

    // Copy to clipboard functionality
    copyToClipboard(text) {
        navigator.clipboard.writeText(text)
            .then(() => this.showNotification('Link copied to clipboard!', 'success'))
            .catch(() => {
                // Fallback for older browsers
                const textArea = document.createElement('textarea');
                textArea.value = text;
                document.body.appendChild(textArea);
                textArea.select();
                document.execCommand('copy');
                document.body.removeChild(textArea);
                this.showNotification('Link copied to clipboard!', 'success');
            });
    }

    // Export model functionality
    exportModel(modelId, format) {
        this.showNotification(`Exporting model to ${format} format...`, 'info');
        // Add export logic here based on format
        setTimeout(() => {
            this.showNotification(`${format} export completed!`, 'success');
        }, 2000);
    }
}

// ===== GLOBAL FUNCTIONS =====

// Global functions for HTML onclick events
function handleFileSelect(input) {
    const files = input.files;
    if (files.length > 0) {
        window.threeDStudio.processFile(files[0]);
    }
}

function uploadFile() {
    if (window.threeDStudio) {
        window.threeDStudio.uploadFile();
    }
}

function previewModel(modelUrl) {
    if (window.threeDStudio) {
        window.threeDStudio.previewModel(modelUrl);
    }
}

function downloadModel(downloadUrl, filename) {
    if (window.threeDStudio) {
        window.threeDStudio.downloadModel(downloadUrl, filename);
    }
}

// FBX CONVERSION GLOBAL FUNCTION
function convertToFBX(modelId) {
    if (window.threeDStudio) {
        window.threeDStudio.convertToFBX(modelId);
    } else {
        console.error('3D Studio not initialized');
        // Fallback: Show error notification
        const notification = document.createElement('div');
        notification.className = 'notification error';
        notification.textContent = 'System not ready. Please refresh the page.';
        document.body.appendChild(notification);
        setTimeout(() => notification.remove(), 5000);
    }
}

// TEXTURE SYSTEM GLOBAL FUNCTIONS
function applyImageTexture(modelId) {
    if (window.threeDStudio) {
        window.threeDStudio.applyImageTexture(modelId);
    }
}

function applyTexture(modelId, textureType) {
    if (window.threeDStudio) {
        window.threeDStudio.applyTexture(modelId, textureType);
    }
}

// Share model global function
function shareModel(modelId) {
    if (window.threeDStudio) {
        window.threeDStudio.shareModel(modelId);
    }
}

// Export model global function
function exportModel(modelId, format) {
    if (window.threeDStudio) {
        window.threeDStudio.exportModel(modelId, format);
    }
}

// ===== INITIALIZATION =====

// Initialize the studio when page loads
document.addEventListener('DOMContentLoaded', () => {
    window.threeDStudio = new ThreeDStudio();
    
    // Add ripple effect styles
    if (!document.querySelector('#ripple-styles')) {
        const style = document.createElement('style');
        style.id = 'ripple-styles';
        style.textContent = `
            @keyframes ripple {
                to {
                    transform: scale(4);
                    opacity: 0;
                }
            }
        `;
        document.head.appendChild(style);
    }
});

// ===== UTILITY FUNCTIONS =====

// Utility function for file size formatting
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Utility function for date formatting
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Format compatibility checker
function getFormatCompatibility(format) {
    const compatibility = {
        'GLB': ['Blender', 'Unity', 'Unreal Engine', 'Three.js', 'AR/VR'],
        'GIB': ['3D Magic Studio', 'Proprietary Tools'],
        'FBX': ['Maya', '3DS Max', 'Cinema 4D', 'Unity', 'Unreal Engine']
    };
    return compatibility[format] || ['Multiple Applications'];
}

// Model statistics calculator
function calculateModelStats(vertices, faces) {
    return {
        complexity: vertices > 1000000 ? 'High' : vertices > 500000 ? 'Medium' : 'Low',
        fileSize: formatFileSize(vertices * 100), // Rough estimate
        optimalUse: vertices > 1000000 ? 'Desktop/Console' : 'Mobile/Web'
    };
} 