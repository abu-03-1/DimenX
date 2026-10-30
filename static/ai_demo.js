// static/js/ai_demo.js
class AI3DStudio {
    constructor() {
        this.currentModel = null;
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.controls = null;
        this.isAutoRotating = true;
        this.initializeAIStudio();
    }

    initializeAIStudio() {
        this.initialize3DViewer();
        this.initializeAIEventListeners();
        this.initializeQuickPrompts();
        this.loadRecentModels();
    }

    initialize3DViewer() {
        const container = document.getElementById('modelViewer');
        if (!container) return;

        // Scene setup
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0x1a1a2e);
        this.scene.fog = new THREE.Fog(0x1a1a2e, 10, 50);

        // Camera
        this.camera = new THREE.PerspectiveCamera(75, container.clientWidth / container.clientHeight, 0.1, 1000);
        this.camera.position.z = 5;

        // Renderer
        this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
        this.renderer.setSize(container.clientWidth, container.clientHeight);
        this.renderer.shadowMap.enabled = true;
        this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        container.appendChild(this.renderer.domElement);

        // Controls
        this.controls = new THREE.OrbitControls(this.camera, this.renderer.domElement);
        this.controls.enableDamping = true;
        this.controls.dampingFactor = 0.05;

        // Lighting
        this.setupLighting();

        // Start animation loop
        this.animate();

        // Handle resize
        window.addEventListener('resize', () => this.onWindowResize());
    }

    setupLighting() {
        // Ambient light
        const ambientLight = new THREE.AmbientLight(0x404040, 0.6);
        this.scene.add(ambientLight);

        // Directional light
        const directionalLight = new THREE.DirectionalLight(0xffffff, 1);
        directionalLight.position.set(10, 10, 5);
        directionalLight.castShadow = true;
        this.scene.add(directionalLight);

        // Point light
        const pointLight = new THREE.PointLight(0x00ff88, 0.5, 100);
        pointLight.position.set(-5, 5, 5);
        this.scene.add(pointLight);
    }

    animate() {
        requestAnimationFrame(() => this.animate());
        
        if (this.isAutoRotating && this.currentModel) {
            this.currentModel.rotation.y += 0.01;
        }

        this.controls.update();
        this.renderer.render(this.scene, this.camera);
    }

    onWindowResize() {
        const container = document.getElementById('modelViewer');
        if (!container) return;

        this.camera.aspect = container.clientWidth / container.clientHeight;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(container.clientWidth, container.clientHeight);
    }

    initializeAIEventListeners() {
        // AI Form submission
        const aiForm = document.getElementById('aiForm');
        if (aiForm) {
            aiForm.addEventListener('submit', (e) => this.handleAIGeneration(e));
        }

        // Prompt character count
        const promptInput = document.getElementById('prompt');
        if (promptInput) {
            promptInput.addEventListener('input', (e) => this.updatePromptCount(e));
        }

        // Control buttons
        const resetView = document.getElementById('resetView');
        const autoRotate = document.getElementById('autoRotate');
        
        if (resetView) resetView.addEventListener('click', () => this.resetView());
        if (autoRotate) autoRotate.addEventListener('click', () => this.toggleAutoRotate());

        // Texture buttons
        document.querySelectorAll('.texture-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.applyTexture(e.target.dataset.texture));
        });

        // Regenerate button
        const regenerateBtn = document.getElementById('regenerate');
        if (regenerateBtn) {
            regenerateBtn.addEventListener('click', () => this.regenerateModel());
        }
    }

    updatePromptCount(event) {
        const countElement = document.getElementById('promptCount');
        if (countElement) {
            const count = event.target.value.length;
            countElement.textContent = `${count}/500`;
            
            // Color coding
            if (count > 400) {
                countElement.style.color = '#ff6b6b';
            } else if (count > 200) {
                countElement.style.color = '#ffd93d';
            } else {
                countElement.style.color = '#a8e6cf';
            }
        }
    }

    initializeQuickPrompts() {
        document.querySelectorAll('.prompt-card').forEach(card => {
            card.addEventListener('click', () => {
                const prompt = card.dataset.prompt;
                document.getElementById('prompt').value = prompt;
                this.updatePromptCount({ target: { value: prompt } });
            });
        });
    }

    async handleAIGeneration(event) {
        event.preventDefault();
        
        const prompt = document.getElementById('prompt').value;
        const modelName = document.getElementById('modelName').value;
        const complexity = document.getElementById('complexity').value;
        const materialType = document.getElementById('materialType').value;
        const quality = document.getElementById('quality').value;

        if (!prompt.trim()) {
            window.threeDStudio.showNotification('Please enter a prompt description', 'error');
            return;
        }

        // Show progress panel
        this.showProgressPanel();
        this.updateProgress(10, 'Analyzing prompt with AI...');

        try {
            const response = await fetch('/api/ai/text-to-3d', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    prompt: prompt,
                    model_name: modelName,
                    complexity: complexity,
                    material_type: materialType,
                    quality: quality
                })
            });

            const data = await response.json();

            if (data.success) {
                this.updateProgress(100, 'Model generation complete!');
                this.showResults(data);
                this.loadModelIntoViewer(data.model_id);
                this.addToRecentModels(data);
            } else {
                throw new Error(data.error);
            }
        } catch (error) {
            console.error('AI Generation error:', error);
            this.showError(error.message);
        }
    }

    showProgressPanel() {
        const progressPanel = document.getElementById('generationProgress');
        const aiForm = document.getElementById('aiForm');
        
        if (progressPanel) progressPanel.classList.remove('hidden');
        if (aiForm) aiForm.style.opacity = '0.5';
        
        document.getElementById('generateBtn').disabled = true;
    }

    updateProgress(percent, text) {
        const progressFill = document.getElementById('progressFill');
        const progressText = document.getElementById('progressText');
        const progressPercent = document.getElementById('progressPercent');

        if (progressFill) progressFill.style.width = percent + '%';
        if (progressText) progressText.textContent = text;
        if (progressPercent) progressPercent.textContent = percent + '%';

        // Update progress steps
        const steps = document.querySelectorAll('.progress-steps .step');
        if (percent >= 25) steps[0].classList.add('completed');
        if (percent >= 50) steps[1].classList.add('completed');
        if (percent >= 75) steps[2].classList.add('completed');
        if (percent >= 100) steps[3].classList.add('completed');
    }

    showResults(data) {
        const resultsPanel = document.getElementById('resultsPanel');
        const resultModelName = document.getElementById('resultModelName');
        const resultPrompt = document.getElementById('resultPrompt');
        const viewModel = document.getElementById('viewModel');
        const downloadGLB = document.getElementById('downloadGLB');
        const downloadFBX = document.getElementById('downloadFBX');

        if (resultModelName) resultModelName.textContent = data.model_name;
        if (resultPrompt) resultPrompt.textContent = data.prompt;
        if (viewModel) viewModel.href = data.preview_url;
        if (downloadGLB) downloadGLB.href = data.glb_download_url;
        if (downloadFBX) downloadFBX.href = data.fbx_download_url;

        if (resultsPanel) resultsPanel.classList.remove('hidden');

        // Update model stats
        this.updateModelStats(data.vertices, data.faces);
    }

    async loadModelIntoViewer(modelId) {
        try {
            const modelUrl = `/models/${modelId}_ai.glb`;
            const loader = new THREE.GLTFLoader();

            loader.load(modelUrl, (gltf) => {
                // Clear previous model
                if (this.currentModel) {
                    this.scene.remove(this.currentModel);
                }

                this.currentModel = gltf.scene;
                this.scene.add(this.currentModel);

                // Center model
                const box = new THREE.Box3().setFromObject(this.currentModel);
                const center = box.getCenter(new THREE.Vector3());
                this.currentModel.position.sub(center);

                // Scale model to fit view
                const size = box.getSize(new THREE.Vector3());
                const maxDim = Math.max(size.x, size.y, size.z);
                const scale = 5 / maxDim;
                this.currentModel.scale.setScalar(scale);

                window.threeDStudio.showNotification('3D Model loaded in viewer!', 'success');
            }, undefined, (error) => {
                console.error('Model loading error:', error);
                window.threeDStudio.showNotification('Model preview loading failed', 'error');
            });

        } catch (error) {
            console.error('Model loading error:', error);
        }
    }

    updateModelStats(vertices, faces) {
        const vertexCount = document.getElementById('vertexCount');
        const faceCount = document.getElementById('faceCount');
        const qualityLabel = document.getElementById('qualityLabel');
        const modelSize = document.getElementById('modelSize');
        const modelStats = document.getElementById('modelStats');

        if (vertexCount) vertexCount.textContent = vertices.toLocaleString();
        if (faceCount) faceCount.textContent = faces.toLocaleString();
        if (qualityLabel) qualityLabel.textContent = 'AI Generated';
        if (modelSize) modelSize.textContent = formatFileSize(vertices * 100); // Estimate
        if (modelStats) modelStats.classList.remove('hidden');
    }

    showError(message) {
        const errorPanel = document.getElementById('error');
        const errorMessage = document.getElementById('errorMessage');
        
        if (errorMessage) errorMessage.textContent = message;
        if (errorPanel) errorPanel.classList.remove('hidden');
        
        // Reset form
        document.getElementById('generateBtn').disabled = false;
        document.getElementById('aiForm').style.opacity = '1';
        document.getElementById('generationProgress').classList.add('hidden');
    }

    resetView() {
        if (this.controls) {
            this.controls.reset();
        }
    }

    toggleAutoRotate() {
        this.isAutoRotating = !this.isAutoRotating;
        const autoRotateBtn = document.getElementById('autoRotate');
        
        if (autoRotateBtn) {
            if (this.isAutoRotating) {
                autoRotateBtn.classList.add('active');
                autoRotateBtn.innerHTML = '🔄 Auto';
            } else {
                autoRotateBtn.classList.remove('active');
                autoRotateBtn.innerHTML = '⏸️ Paused';
            }
        }
    }

    async applyTexture(textureType) {
        if (!this.currentModel) {
            window.threeDStudio.showNotification('No model loaded to apply texture', 'error');
            return;
        }

        try {
            const response = await fetch(`/api/apply_texture/${this.currentModelId}`, {
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
                window.threeDStudio.showNotification(`${textureType} texture applied!`, 'success');
                // Reload model with new texture
                this.loadModelIntoViewer(this.currentModelId);
            } else {
                throw new Error(data.error);
            }
        } catch (error) {
            window.threeDStudio.showNotification(`Texture application failed: ${error.message}`, 'error');
        }
    }

    regenerateModel() {
        // Clear current results and reset form
        document.getElementById('resultsPanel').classList.add('hidden');
        document.getElementById('generationProgress').classList.add('hidden');
        document.getElementById('aiForm').style.opacity = '1';
        document.getElementById('generateBtn').disabled = false;
        
        // Trigger generation again
        document.getElementById('aiForm').dispatchEvent(new Event('submit'));
    }

    addToRecentModels(modelData) {
        const recentModels = JSON.parse(localStorage.getItem('recentAIModels') || '[]');
        
        // Add new model to beginning
        recentModels.unshift({
            id: modelData.model_id,
            name: modelData.model_name,
            prompt: modelData.prompt,
            created_at: new Date().toISOString(),
            vertices: modelData.vertices,
            faces: modelData.faces
        });

        // Keep only last 6 models
        if (recentModels.length > 6) {
            recentModels.pop();
        }

        localStorage.setItem('recentAIModels', JSON.stringify(recentModels));
        this.loadRecentModels();
    }

    loadRecentModels() {
        const recentModels = JSON.parse(localStorage.getItem('recentAIModels') || '[]');
        const container = document.getElementById('recentModels');
        
        if (!container) return;

        if (recentModels.length === 0) {
            container.innerHTML = '<p class="no-models">No recent AI models yet. Generate your first one!</p>';
            return;
        }

        container.innerHTML = recentModels.map(model => `
            <div class="model-card" onclick="aiStudio.loadRecentModel('${model.id}')">
                <div class="model-card-header">
                    <h4>${model.name}</h4>
                    <span class="ai-badge">AI</span>
                </div>
                <p class="model-prompt">${model.prompt.substring(0, 100)}${model.prompt.length > 100 ? '...' : ''}</p>
                <div class="model-stats">
                    <span>${model.vertices} vertices</span>
                    <span>${formatDate(model.created_at)}</span>
                </div>
            </div>
        `).join('');
    }

    loadRecentModel(modelId) {
        // Load a recent model back into the viewer
        this.currentModelId = modelId;
        this.loadModelIntoViewer(modelId);
        window.threeDStudio.showNotification('Recent model loaded!', 'success');
    }
}

// Initialize AI Studio when page loads
document.addEventListener('DOMContentLoaded', () => {
    window.aiStudio = new AI3DStudio();
});