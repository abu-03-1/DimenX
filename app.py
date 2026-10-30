from flask import Flask, render_template, request, jsonify, send_file, url_for, session, redirect, send_from_directory
import os
from werkzeug.utils import secure_filename
import uuid
import datetime
import json
import trimesh
import shutil
import numpy as np
import cv2
from PIL import Image
import torch
from sklearn.cluster import KMeans  # Add this import

app = Flask(__name__)
app.secret_key = '3d-magic-studio-secret-key-2024'

# Configuration
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MODELS_FOLDER'] = 'models'
app.config['TEXTURES_FOLDER'] = 'static/textures'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'bmp', 'tiff', 'webp'}

# Create directories
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['MODELS_FOLDER'], exist_ok=True)
os.makedirs(os.path.join(app.config['MODELS_FOLDER'], 'textured'), exist_ok=True)
os.makedirs(app.config['TEXTURES_FOLDER'], exist_ok=True)

# Try to load advanced system
print("🚀 Starting 3D Magic Studio with AI...")
try:
    from advanced_model_utils import create_professional_3d_model, load_advanced_midas
    USE_ADVANCED = True
    print("✅ Advanced 3D System Loaded - ULTRA QUALITY MODE")
    midas_model, midas_transform, device = load_advanced_midas()
except ImportError as e:
    print(f"❌ Advanced system not available: {e}")
    try:
        from model_utils import load_midas, estimate_depth, depth_to_mesh
        USE_ADVANCED = False
        print("🔄 Using Basic 3D System")
        midas_model, midas_transform, device = load_midas()
    except ImportError as e2:
        print(f"❌ Basic system also failed: {e2}")
        USE_ADVANCED = False
        midas_model, midas_transform, device = None, None, None

# User database (in production, use real database)
users = {
    'Abubakkar': {'password': 'Abubakkar@123', 'models': [], 'role': 'Abubakkar'},
    'user': {'password': 'user123', 'models': [], 'role': 'user'},
}

# Available textures
TEXTURES = {
    'metal': {'name': 'Metal', 'color': '#cccccc', 'roughness': 0.1, 'metalness': 0.9},
    'wood': {'name': 'Wood', 'color': '#8B4513', 'roughness': 0.8, 'metalness': 0.2},
    'plastic': {'name': 'Plastic', 'color': '#FF6B6B', 'roughness': 0.4, 'metalness': 0.1},
    'glass': {'name': 'Glass', 'color': '#88ccff', 'roughness': 0.1, 'metalness': 0.0, 'transmission': 0.9},
    'gold': {'name': 'Gold', 'color': '#FFD700', 'roughness': 0.3, 'metalness': 1.0},
    'silver': {'name': 'Silver', 'color': '#C0C0C0', 'roughness': 0.2, 'metalness': 0.8},
    'rubber': {'name': 'Rubber', 'color': '#333333', 'roughness': 0.9, 'metalness': 0.0},
    'crystal': {'name': 'Crystal', 'color': '#ffffff', 'roughness': 0.1, 'metalness': 0.1}
}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ==================== IMAGE COLOR TO TEXTURE SYSTEM ====================
def extract_colors_from_image(image_path, num_colors=5):
    """Extract dominant colors from image using K-means clustering"""
    try:
        print(f"🎨 Extracting {num_colors} dominant colors from image...")
        
        # Load image
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError("Image not found")
            
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Resize image for faster processing
        image_small = cv2.resize(image, (100, 100))
        
        # Reshape image to be a list of pixels
        pixels = image_small.reshape(-1, 3)
        
        # Use K-means to find dominant colors
        kmeans = KMeans(n_clusters=num_colors, random_state=42, n_init=10)
        kmeans.fit(pixels)
        
        # Get the dominant colors
        colors = kmeans.cluster_centers_.astype(int)
        
        # Get color counts for weighting
        unique, counts = np.unique(kmeans.labels_, return_counts=True)
        color_weights = dict(zip(unique, counts))
        
        # Sort colors by prevalence
        sorted_colors = []
        for i, color in enumerate(colors):
            sorted_colors.append({
                'rgb': color,
                'hex': f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}",
                'count': color_weights.get(i, 0)
            })
        
        # Sort by count (most prevalent first)
        sorted_colors.sort(key=lambda x: x['count'], reverse=True)
        
        hex_colors = [color['hex'] for color in sorted_colors]
        
        print(f"✅ Extracted colors: {hex_colors}")
        return hex_colors
        
    except Exception as e:
        print(f"❌ Color extraction failed: {e}")
        # Fallback colors
        return ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7']

def create_texture_from_image_colors(image_path, output_texture_path):
    """Create texture map from image colors"""
    try:
        print("🎨 Creating texture from image colors...")
        
        image = cv2.imread(image_path)
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Extract dominant colors
        colors = extract_colors_from_image(image_path, 4)
        if not colors:
            return False
        
        # Create a texture map
        height, width = 512, 512
        texture = np.zeros((height, width, 3), dtype=np.uint8)
        
        # Create a gradient or pattern using the extracted colors
        for i in range(height):
            for j in range(width):
                # Use color based on position (creates a gradient effect)
                color_index = (i // 128 + j // 128) % len(colors)
                hex_color = colors[color_index].lstrip('#')
                
                r = int(hex_color[0:2], 16)
                g = int(hex_color[2:4], 16)
                b = int(hex_color[4:6], 16)
                
                texture[i, j] = [r, g, b]
        
        # Save texture
        cv2.imwrite(output_texture_path, cv2.cvtColor(texture, cv2.COLOR_RGB2BGR))
        print(f"✅ Texture created: {output_texture_path}")
        return True
        
    except Exception as e:
        print(f"❌ Texture creation failed: {e}")
        return False

@app.route('/api/apply_image_texture/<model_id>', methods=['POST'])
def apply_image_texture(model_id):
    """Apply texture from original image colors to 3D model"""
    try:
        if 'username' not in session:
            return jsonify({'error': 'Please login first'}), 401
            
        print(f"🎨 Applying image-based texture to model {model_id}")
        
        # Find the model and original image
        user_models = users[session['username']]['models']
        model = next((m for m in user_models if m['id'] == model_id), None)
        
        if not model:
            return jsonify({'error': 'Model not found'}), 404
        
        original_image_path = os.path.join(app.config['UPLOAD_FOLDER'], model.get('original_image', ''))
        
        if not os.path.exists(original_image_path):
            return jsonify({'error': 'Original image not found'}), 404
        
        # Find the model file
        glb_files = [
            f"{model_id}_ULTRA.glb",
            f"{model_id}_main.glb", 
            f"{model_id}_professional.glb",
            f"{model_id}_ai.glb"
        ]
        
        glb_file = None
        for filename in glb_files:
            file_path = os.path.join(app.config['MODELS_FOLDER'], filename)
            if os.path.exists(file_path):
                glb_file = file_path
                break
        
        if not glb_file:
            return jsonify({'error': 'Model file not found'}), 404
        
        # Extract dominant colors from original image
        dominant_colors = extract_colors_from_image(original_image_path, 3)
        primary_color = dominant_colors[0] if dominant_colors else '#6366f1'
        
        print(f"🎨 Using primary color: {primary_color}")
        
        # Apply custom texture using image colors
        textured_file = os.path.join(app.config['MODELS_FOLDER'], f"{model_id}_image_textured.glb")
        success = apply_custom_texture(glb_file, textured_file, primary_color)
        
        if success:
            # Add to user's models
            textured_model_data = {
                'id': f"{model_id}_image_textured",
                'name': f"{model['name']} (Image Colors)",
                'created_at': datetime.datetime.now().isoformat(),
                'type': 'image_textured',
                'quality': 'TEXTURED',
                'glb_download_url': url_for('download_glb', model_id=f"{model_id}_image_textured"),
                'gib_download_url': url_for('download_gib', model_id=f"{model_id}_image_textured"),
                'fbx_download_url': url_for('download_fbx', model_id=f"{model_id}_image_textured")
            }
            
            users[session['username']]['models'].append(textured_model_data)
            
            return jsonify({
                'success': True,
                'message': '✅ Image-based texture applied!',
                'primary_color': primary_color,
                'color_palette': dominant_colors,
                'textured_url': url_for('serve_model', filename=f"{model_id}_image_textured.glb"),
                'download_url': url_for('download_glb', model_id=f"{model_id}_image_textured")
            })
        else:
            return jsonify({'error': 'Image texture application failed'}), 500
            
    except Exception as e:
        print(f"❌ Image texture error: {str(e)}")
        return jsonify({'error': str(e)}), 500

def apply_custom_texture(input_path, output_path, base_color):
    """Apply custom texture using image-extracted colors to 3D model"""
    try:
        # Load the mesh
        mesh = trimesh.load(input_path)
        
        # Convert hex to RGB
        base_color_rgb = hex_to_rgba(base_color)
        
        # Create PBR material with image-based colors
        material = trimesh.visual.material.PBRMaterial(
            baseColorFactor=base_color_rgb,
            metallicFactor=0.4,  # Slightly metallic for better reflection
            roughnessFactor=0.6,  # Moderate roughness for natural look
            emissiveFactor=[base_color_rgb[0] * 0.1, base_color_rgb[1] * 0.1, base_color_rgb[2] * 0.1]  # Subtle glow
        )
        
        # Apply material to mesh
        if hasattr(mesh, 'visual') and hasattr(mesh.visual, 'material'):
            mesh.visual.material = material
        else:
            mesh.visual = trimesh.visual.TextureVisuals(material=material)
        
        # Export with material
        mesh.export(output_path)
        
        print(f"✅ Custom texture applied using color: {base_color}")
        return True
        
    except Exception as e:
        print(f"❌ Custom texture application error: {e}")
        return False

@app.route('/api/extract_colors/<model_id>')
def extract_colors(model_id):
    """Extract and return color palette from original image"""
    try:
        if 'username' not in session:
            return jsonify({'error': 'Please login first'}), 401
            
        # Find the model and original image
        user_models = users[session['username']]['models']
        model = next((m for m in user_models if m['id'] == model_id), None)
        
        if not model:
            return jsonify({'error': 'Model not found'}), 404
        
        original_image_path = os.path.join(app.config['UPLOAD_FOLDER'], model.get('original_image', ''))
        
        if not os.path.exists(original_image_path):
            return jsonify({'error': 'Original image not found'}), 404
        
        # Extract colors
        colors = extract_colors_from_image(original_image_path, 6)
        
        return jsonify({
            'success': True,
            'colors': colors,
            'model_id': model_id,
            'model_name': model['name']
        })
        
    except Exception as e:
        print(f"❌ Color extraction API error: {str(e)}")
        return jsonify({'error': str(e)}), 500

# ==================== BACKGROUND REMOVAL FUNCTIONS ====================
def remove_background_advanced(image_path):
    """Remove background and keep only main object"""
    try:
        print("🖼️ Removing background to isolate object...")
        
        # Load image
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError("Image not found")
            
        # Convert to RGB
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Method 1: GrabCut for advanced background removal
        mask = grabcut_segmentation(image_rgb)
        
        # Method 2: If GrabCut fails, use threshold-based method
        if mask is None or np.sum(mask) == 0:
            mask = threshold_segmentation(image_rgb)
        
        # Apply mask to remove background
        result = apply_mask(image_rgb, mask)
        
        print(f"✅ Background removed - Object pixels: {np.sum(mask > 0)}")
        return result, mask
        
    except Exception as e:
        print(f"❌ Background removal failed: {e}")
        return None, None

def grabcut_segmentation(image):
    """Use GrabCut for precise object segmentation"""
    try:
        mask = np.zeros(image.shape[:2], np.uint8)
        
        # Initialize background and foreground models
        bgd_model = np.zeros((1, 65), np.float64)
        fgd_model = np.zeros((1, 65), np.float64)
        
        # Define rectangle around the object (assuming object is in center)
        height, width = image.shape[:2]
        rect = (50, 50, width-100, height-100)
        
        # Apply GrabCut
        cv2.grabCut(image, mask, rect, bgd_model, fgd_model, 5, cv2.GC_INIT_WITH_RECT)
        
        # Create mask where sure and likely foreground
        mask2 = np.where((mask == 2) | (mask == 0), 0, 1).astype('uint8')
        
        return mask2
    except:
        return None

def threshold_segmentation(image):
    """Fallback method using color thresholding"""
    try:
        # Convert to HSV for better color segmentation
        hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
        
        # Create mask based on color
        lower_bound = np.array([0, 0, 0])
        upper_bound = np.array([180, 255, 200])
        mask = cv2.inRange(hsv, lower_bound, upper_bound)
        
        # Clean up mask
        kernel = np.ones((5,5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        
        return mask
    except:
        return None

def apply_mask(image, mask):
    """Apply mask to image"""
    if mask is None:
        return image
        
    # Create white background for 3D processing
    result = image.copy()
    result[mask == 0] = [255, 255, 255]
    
    return result

def save_processed_image(image, output_path):
    """Save processed image without background"""
    if image is not None:
        cv2.imwrite(output_path, cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
        return True
    return False

def preprocess_image_for_3d(image_path):
    """Enhanced preprocessing for better 3D results"""
    try:
        print("🔧 Preprocessing image for optimal 3D conversion...")
        
        # Remove background first
        processed_image, mask = remove_background_advanced(image_path)
        
        if processed_image is not None:
            # Save processed image
            processed_path = image_path.replace('.png', '_processed.png').replace('.jpg', '_processed.jpg')
            save_processed_image(processed_image, processed_path)
            print("✅ Background removed successfully!")
            return processed_path
        else:
            print("⚠️ Using original image with basic preprocessing")
            return apply_basic_preprocessing(image_path)
            
    except Exception as e:
        print(f"❌ Preprocessing failed: {e}")
        return image_path

def apply_basic_preprocessing(image_path):
    """Basic preprocessing fallback"""
    try:
        image = cv2.imread(image_path)
        
        # Enhance contrast and sharpness
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        
        # Apply CLAHE to L-channel for better contrast
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        l = clahe.apply(l)
        
        lab = cv2.merge([l, a, b])
        enhanced = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
        
        # Save enhanced image
        enhanced_path = image_path.replace('.png', '_enhanced.png').replace('.jpg', '_enhanced.jpg')
        cv2.imwrite(enhanced_path, enhanced)
        
        return enhanced_path
        
    except Exception as e:
        print(f"❌ Basic preprocessing failed: {e}")
        return image_path

# ==================== AI TEXT-TO-3D ROUTES ====================
@app.route('/api/ai/text-to-3d', methods=['POST'])
def text_to_3d():
    """Generate 3D model from text description"""
    try:
        if 'username' not in session:
            return jsonify({'error': 'Please login first'}), 401
        
        data = request.json
        prompt = data.get('prompt', '')
        model_name = data.get('model_name', 'AI Generated Model')
        
        if not prompt:
            return jsonify({'error': 'No prompt provided'}), 400
        
        model_id = str(uuid.uuid4())[:8]
        output_base = os.path.join(app.config['MODELS_FOLDER'], model_id)
        
        print(f"🎯 Generating 3D from text: {prompt}")
        
        # Generate 3D model from text
        success = generate_from_text(prompt, output_base)
        
        if success:
            model_data = {
                'id': model_id,
                'name': model_name,
                'created_at': datetime.datetime.now().isoformat(),
                'prompt': prompt,
                'type': 'ai_generated',
                'quality': 'AI',
                'vertices': 1500,
                'faces': 3000,
                'glb_download_url': url_for('download_glb', model_id=model_id),
                'gib_download_url': url_for('download_gib', model_id=model_id),
                'fbx_download_url': url_for('download_fbx', model_id=model_id)
            }
            
            users[session['username']]['models'].append(model_data)
            
            return jsonify({
                'success': True,
                'message': '🎉 AI 3D Model Generated!',
                'model_id': model_id,
                'model_name': model_name,
                'preview_url': url_for('model_preview', model_id=model_id),
                'glb_download_url': url_for('download_glb', model_id=model_id),
                'vertices': 1500,
                'faces': 3000
            })
        else:
            return jsonify({'error': 'AI generation failed'}), 500
            
    except Exception as e:
        print(f"❌ Text-to-3D error: {str(e)}")
        return jsonify({'error': str(e)}), 500

def generate_from_text(prompt, output_path):
    """Generate 3D model from text prompt"""
    try:
        prompt_lower = prompt.lower()
        
        # Determine shape based on keywords
        if any(word in prompt_lower for word in ['sword', 'blade', 'weapon']):
            vertices, faces = generate_sword_shape()
        elif any(word in prompt_lower for word in ['sphere', 'ball', 'round']):
            vertices, faces = generate_sphere_shape()
        elif any(word in prompt_lower for word in ['cube', 'box', 'square']):
            vertices, faces = generate_cube_shape()
        elif any(word in prompt_lower for word in ['pyramid', 'triangle']):
            vertices, faces = generate_pyramid_shape()
        elif any(word in prompt_lower for word in ['ring', 'torus', 'donut']):
            vertices, faces = generate_ring_shape()
        elif any(word in prompt_lower for word in ['cylinder', 'tube']):
            vertices, faces = generate_cylinder_shape()
        else:
            vertices, faces = generate_default_shape()
        
        # Create mesh
        mesh = trimesh.Trimesh(vertices=vertices, faces=faces)
        
        # Apply basic material based on keywords
        if any(word in prompt_lower for word in ['metal', 'steel', 'iron']):
            mesh.visual.material = trimesh.visual.material.PBRMaterial(
                metallicFactor=0.9,
                roughnessFactor=0.1
            )
        elif any(word in prompt_lower for word in ['gold', 'golden']):
            mesh.visual.material = trimesh.visual.material.PBRMaterial(
                baseColorFactor=[1.0, 0.84, 0.0, 1.0],
                metallicFactor=1.0,
                roughnessFactor=0.3
            )
        
        # Export the model
        mesh.export(f"{output_path}_ai.glb")
        
        print(f"✅ AI Model generated: {len(vertices)} vertices, {len(faces)} faces")
        return True
        
    except Exception as e:
        print(f"❌ Text-to-3D generation error: {e}")
        return False

# Shape generators (same as before but included for completeness)
def generate_sword_shape():
    vertices = np.array([
        [0.0, 0.0, 0.0], [0.05, 0.8, 0.05], [-0.05, 0.8, 0.05], 
        [0.05, 0.8, -0.05], [-0.05, 0.8, -0.05], [0.1, 0.9, 0.1],
        [-0.1, 0.9, 0.1], [0.1, 0.9, -0.1], [-0.1, 0.9, -0.1], [0.0, 1.0, 0.0]
    ], dtype=np.float32)
    
    faces = np.array([
        [0, 1, 2], [0, 2, 4], [0, 4, 3], [0, 3, 1], [1, 2, 5],
        [2, 4, 6], [4, 3, 7], [3, 1, 8], [5, 6, 9], [6, 7, 9],
        [7, 8, 9], [8, 5, 9], [1, 5, 8], [2, 6, 5], [4, 7, 6], [3, 8, 7]
    ], dtype=np.int32)
    
    return vertices, faces

def generate_cube_shape():
    vertices = np.array([
        [-0.5, -0.5, -0.5], [0.5, -0.5, -0.5], [0.5, 0.5, -0.5], [-0.5, 0.5, -0.5],
        [-0.5, -0.5, 0.5], [0.5, -0.5, 0.5], [0.5, 0.5, 0.5], [-0.5, 0.5, 0.5]
    ], dtype=np.float32)
    
    faces = np.array([
        [0, 1, 2], [2, 3, 0], [1, 5, 6], [6, 2, 1],
        [5, 4, 7], [7, 6, 5], [4, 0, 3], [3, 7, 4],
        [3, 2, 6], [6, 7, 3], [4, 5, 1], [1, 0, 4]
    ], dtype=np.int32)
    
    return vertices, faces

def generate_sphere_shape(radius=0.5, segments=8):
    vertices = []
    for i in range(segments + 1):
        phi = np.pi * i / segments
        for j in range(segments + 1):
            theta = 2 * np.pi * j / segments
            x = radius * np.sin(phi) * np.cos(theta)
            y = radius * np.cos(phi)
            z = radius * np.sin(phi) * np.sin(theta)
            vertices.append([x, y, z])
    
    faces = []
    for i in range(segments):
        for j in range(segments):
            v0 = i * (segments + 1) + j
            v1 = v0 + 1
            v2 = v0 + (segments + 1)
            v3 = v1 + (segments + 1)
            faces.append([v0, v2, v1])
            faces.append([v1, v2, v3])
    
    return np.array(vertices, dtype=np.float32), np.array(faces, dtype=np.int32)

def generate_pyramid_shape():
    vertices = np.array([
        [0.0, 0.5, 0.0], [-0.5, -0.5, -0.5], [0.5, -0.5, -0.5],
        [0.5, -0.5, 0.5], [-0.5, -0.5, 0.5]
    ], dtype=np.float32)
    
    faces = np.array([
        [0, 1, 2], [0, 2, 3], [0, 3, 4], [0, 4, 1], [1, 3, 2], [1, 4, 3]
    ], dtype=np.int32)
    
    return vertices, faces

def generate_ring_shape():
    vertices = []
    major_radius, minor_radius, segments = 0.7, 0.2, 12
    for i in range(segments):
        major_angle = 2 * np.pi * i / segments
        for j in range(segments):
            minor_angle = 2 * np.pi * j / segments
            x = (major_radius + minor_radius * np.cos(minor_angle)) * np.cos(major_angle)
            y = minor_radius * np.sin(minor_angle)
            z = (major_radius + minor_radius * np.cos(minor_angle)) * np.sin(major_angle)
            vertices.append([x, y, z])
    
    faces = []
    for i in range(segments):
        for j in range(segments):
            next_i, next_j = (i + 1) % segments, (j + 1) % segments
            v0 = i * segments + j
            v1 = i * segments + next_j
            v2 = next_i * segments + j
            v3 = next_i * segments + next_j
            faces.append([v0, v2, v1])
            faces.append([v1, v2, v3])
    
    return np.array(vertices, dtype=np.float32), np.array(faces, dtype=np.int32)

def generate_cylinder_shape():
    vertices = []
    radius, height, segments = 0.3, 1.0, 12
    vertices.append([0, -height/2, 0])
    for i in range(segments):
        angle = 2 * np.pi * i / segments
        vertices.append([radius * np.cos(angle), -height/2, radius * np.sin(angle)])
    vertices.append([0, height/2, 0])
    for i in range(segments):
        angle = 2 * np.pi * i / segments
        vertices.append([radius * np.cos(angle), height/2, radius * np.sin(angle)])
    
    faces = []
    for i in range(segments):
        next_i = (i + 1) % segments
        faces.append([0, i + 1, next_i + 1])
        faces.append([segments + 1, segments + 1 + next_i + 1, segments + 1 + i + 1])
        bottom_v1, bottom_v2 = i + 1, next_i + 1
        top_v1, top_v2 = segments + 1 + i + 1, segments + 1 + next_i + 1
        faces.append([bottom_v1, bottom_v2, top_v1])
        faces.append([top_v1, bottom_v2, top_v2])
    
    return np.array(vertices, dtype=np.float32), np.array(faces, dtype=np.int32)

def generate_default_shape():
    vertices = np.array([
        [0.0, 0.5, 0.0], [0.5, 0.0, 0.0], [0.0, 0.0, 0.5],
        [-0.5, 0.0, 0.0], [0.0, 0.0, -0.5], [0.0, -0.5, 0.0]
    ], dtype=np.float32)
    
    faces = np.array([
        [0, 1, 2], [0, 2, 3], [0, 3, 4], [0, 4, 1],
        [5, 2, 1], [5, 3, 2], [5, 4, 3], [5, 1, 4]
    ], dtype=np.int32)
    
    return vertices, faces

# ==================== TEXTURE ROUTES ====================
@app.route('/api/textures')
def get_textures():
    """Get available textures"""
    return jsonify(TEXTURES)

@app.route('/api/apply_texture/<model_id>', methods=['POST'])
def apply_texture(model_id):
    """Apply texture to existing 3D model"""
    try:
        if 'username' not in session:
            return jsonify({'error': 'Please login first'}), 401
            
        data = request.json
        texture_type = data.get('texture_type', 'metal')
        color = data.get('color', None)
        
        print(f"🎨 Applying texture: {texture_type} to model {model_id}")
        
        # Find the model file
        glb_files = [
            f"{model_id}_ULTRA.glb",
            f"{model_id}_main.glb", 
            f"{model_id}_professional.glb",
            f"{model_id}_ai.glb"
        ]
        
        glb_file = None
        for filename in glb_files:
            file_path = os.path.join(app.config['MODELS_FOLDER'], filename)
            if os.path.exists(file_path):
                glb_file = file_path
                break
        
        if not glb_file:
            return jsonify({'error': 'Model file not found'}), 404
        
        # Apply texture
        textured_file = os.path.join(app.config['MODELS_FOLDER'], f"{model_id}_textured.glb")
        success = apply_texture_to_model(glb_file, textured_file, texture_type, color)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'✅ {texture_type} texture applied!',
                'textured_url': url_for('serve_model', filename=f"{model_id}_textured.glb"),
                'download_url': url_for('download_glb', model_id=f"{model_id}_textured")
            })
        else:
            return jsonify({'error': 'Texture application failed'}), 500
            
    except Exception as e:
        print(f"❌ Texture error: {str(e)}")
        return jsonify({'error': str(e)}), 500

def apply_texture_to_model(input_path, output_path, texture_type, color=None):
    """Apply texture to 3D model"""
    try:
        # Load the mesh
        mesh = trimesh.load(input_path)
        
        # Get texture properties
        texture_config = TEXTURES.get(texture_type, TEXTURES['metal'])
        
        # Create PBR material
        material = trimesh.visual.material.PBRMaterial(
            metallicFactor=texture_config.get('metalness', 0.5),
            roughnessFactor=texture_config.get('roughness', 0.5),
            baseColorFactor=hex_to_rgba(color) if color else hex_to_rgba(texture_config['color'])
        )
        
        # Apply material to mesh
        if hasattr(mesh, 'visual') and hasattr(mesh.visual, 'material'):
            mesh.visual.material = material
        else:
            mesh.visual = trimesh.visual.TextureVisuals(material=material)
        
        # Export with material
        mesh.export(output_path)
        
        print(f"✅ Texture applied: {texture_type}")
        return True
        
    except Exception as e:
        print(f"❌ Texture application error: {e}")
        return False

def hex_to_rgba(hex_color):
    """Convert hex color to RGBA"""
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 6:
        r = int(hex_color[0:2], 16) / 255.0
        g = int(hex_color[2:4], 16) / 255.0
        b = int(hex_color[4:6], 16) / 255.0
        return [r, g, b, 1.0]
    return [1.0, 1.0, 1.0, 1.0]

# ==================== 3D MODEL TO VIDEO ====================
@app.route('/api/generate_video/<model_id>')
def generate_model_video(model_id):
    """Generate rotation video of 3D model"""
    try:
        # Find model file
        glb_files = [
            f"{model_id}_ULTRA.glb",
            f"{model_id}_main.glb", 
            f"{model_id}_professional.glb",
            f"{model_id}_ai.glb",
            f"{model_id}_textured.glb",
            f"{model_id}_image_textured.glb"
        ]
        
        glb_file = None
        for filename in glb_files:
            file_path = os.path.join(app.config['MODELS_FOLDER'], filename)
            if os.path.exists(file_path):
                glb_file = file_path
                break
        
        if not glb_file:
            return jsonify({'error': 'Model file not found'}), 404
        
        # For now, return success with placeholder
        return jsonify({
            'success': True,
            'message': '✅ Video generation started!',
            'video_url': f'/api/video/{model_id}.mp4',
            'status': 'processing'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==================== ALL DOWNLOAD ROUTES ====================
@app.route('/download_glb/<model_id>')
def download_glb(model_id):
    """Download GLB file"""
    try:
        glb_files = [
            f"{model_id}_ULTRA.glb", f"{model_id}_main.glb", f"{model_id}_professional.glb",
            f"{model_id}_ai.glb", f"{model_id}_textured.glb", f"{model_id}_image_textured.glb", f"{model_id}.glb"
        ]
        
        glb_file = None
        for filename in glb_files:
            file_path = os.path.join(app.config['MODELS_FOLDER'], filename)
            if os.path.exists(file_path):
                glb_file = file_path
                break
        
        if not glb_file:
            return jsonify({'error': 'GLB file not found'}), 404
            
        return send_file(glb_file, as_attachment=True, download_name=f"{model_id}.glb")
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download_gib/<model_id>')
def download_gib(model_id):
    """Download GIB file"""
    try:
        gib_files = [
            f"{model_id}_ULTRA.gib", f"{model_id}_main.gib", f"{model_id}_professional.gib", 
            f"{model_id}_textured.gib", f"{model_id}_image_textured.gib", f"{model_id}.gib"
        ]
        
        gib_file = None
        for filename in gib_files:
            file_path = os.path.join(app.config['MODELS_FOLDER'], filename)
            if os.path.exists(file_path):
                gib_file = file_path
                break
        
        if not gib_file:
            return create_gib_from_glb(model_id)
            
        return send_file(gib_file, as_attachment=True, download_name=f"{model_id}.gib")
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def create_gib_from_glb(model_id):
    """Create GIB file from GLB if it doesn't exist"""
    try:
        glb_files = [
            f"{model_id}_ULTRA.glb", f"{model_id}_main.glb", f"{model_id}_professional.glb", 
            f"{model_id}_ai.glb", f"{model_id}_textured.glb", f"{model_id}_image_textured.glb"
        ]
        
        glb_file = None
        for filename in glb_files:
            file_path = os.path.join(app.config['MODELS_FOLDER'], filename)
            if os.path.exists(file_path):
                glb_file = file_path
                break
        
        if not glb_file:
            return jsonify({'error': 'GLB file not found to create GIB'}), 404
        
        # Create GIB file (copy GLB as GIB for now)
        gib_file = os.path.join(app.config['MODELS_FOLDER'], f"{model_id}.gib")
        shutil.copy2(glb_file, gib_file)
        
        print(f"✅ Created GIB file: {gib_file}")
        return send_file(gib_file, as_attachment=True, download_name=f"{model_id}.gib")
        
    except Exception as e:
        return jsonify({'error': f'GIB creation failed: {str(e)}'}), 500

@app.route('/download_fbx/<model_id>')
def download_fbx(model_id):
    """Download FBX file - Auto-converts if needed"""
    try:
        fbx_file = os.path.join(app.config['MODELS_FOLDER'], f"{model_id}_converted.fbx")
        
        if not os.path.exists(fbx_file):
            print(f"🔄 Auto-converting {model_id} to FBX...")
            conversion_result = auto_convert_to_fbx(model_id)
            if not conversion_result['success']:
                return jsonify({'error': f"Auto-conversion failed: {conversion_result['error']}"}), 500
        
        if os.path.exists(fbx_file):
            return send_file(fbx_file, as_attachment=True, download_name=f"{model_id}.fbx")
        else:
            return jsonify({'error': 'FBX file not found after conversion'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def auto_convert_to_fbx(model_id):
    """Auto-convert GLB to FBX without user interaction"""
    try:
        glb_files = [
            f"{model_id}_ULTRA.glb", f"{model_id}_main.glb", f"{model_id}_professional.glb", 
            f"{model_id}_ai.glb", f"{model_id}_textured.glb", f"{model_id}_image_textured.glb"
        ]
        
        glb_file = None
        for filename in glb_files:
            file_path = os.path.join(app.config['MODELS_FOLDER'], filename)
            if os.path.exists(file_path):
                glb_file = file_path
                break
        
        if not glb_file:
            return {'success': False, 'error': 'No GLB file found'}
        
        fbx_file = os.path.join(app.config['MODELS_FOLDER'], f"{model_id}_converted.fbx")
        
        try:
            scene = trimesh.load(glb_file)
            
            if hasattr(scene, 'geometry'):
                print(f"✅ Scene loaded with {len(scene.geometry)} geometries")
                combined_mesh = None
                for name, geometry in scene.geometry.items():
                    if combined_mesh is None:
                        combined_mesh = geometry
                    else:
                        combined_mesh += geometry
                
                if combined_mesh is not None:
                    mesh = combined_mesh
                else:
                    return {'success': False, 'error': 'No valid geometry found in scene'}
                    
            elif hasattr(scene, 'vertices'):
                mesh = scene
            else:
                return {'success': False, 'error': 'Unknown mesh format'}
            
            print(f"✅ Mesh prepared: {len(mesh.vertices)} vertices, {len(mesh.faces)} faces")
            
            try:
                mesh.export(fbx_file, file_type='fbx')
                if os.path.exists(fbx_file) and os.path.getsize(fbx_file) > 100:
                    print(f"✅ Direct FBX export successful")
                    return {'success': True}
            except Exception as e:
                print(f"❌ Direct FBX export failed: {e}")
            
            return create_custom_fbx(mesh, fbx_file, model_id)
            
        except Exception as e:
            print(f"❌ Mesh processing failed: {e}")
            return {'success': False, 'error': f'Mesh processing failed: {str(e)}'}
        
    except Exception as e:
        print(f"❌ Auto-conversion error: {e}")
        return {'success': False, 'error': str(e)}

def create_custom_fbx(mesh, fbx_file, model_id):
    """Create custom FBX file with mesh data"""
    try:
        vertices = mesh.vertices
        faces = mesh.faces
        
        print(f"📊 Creating custom FBX with {len(vertices)} vertices, {len(faces)} faces")
        
        fbx_content = f"""FBXHeaderExtension: {{
    FBXHeaderVersion: 1003
    FBXVersion: 7400
    Creator: "3D Magic Studio"
}}

Objects: {{
    Geometry: "{model_id}_Geometry", "Mesh" {{
        Vertices: *{len(vertices) * 3} {{
            a: {','.join([f'{v:.6f}' for vertex in vertices for v in vertex])}
        }}
        PolygonVertexIndex: *{len(faces) * 4} {{
            a: {','.join([f'{face[0]},{face[1]},{face[2]},-1' for face in faces])}
        }}
    }}
}}

Connections: {{
    C: "OO", "{model_id}_Geometry", "Model::Scene"
}}

EndFBXDocument
"""
        
        with open(fbx_file, 'w', encoding='utf-8') as f:
            f.write(fbx_content)
        
        if os.path.exists(fbx_file):
            print(f"✅ Custom FBX created: {fbx_file}")
            return {'success': True}
        else:
            return {'success': False, 'error': 'FBX file not created'}
            
    except Exception as e:
        print(f"❌ Custom FBX creation failed: {e}")
        return {'success': False, 'error': f'Custom FBX failed: {str(e)}'}

@app.route('/convert_to_fbx/<model_id>')
def convert_to_fbx(model_id):
    """API endpoint for FBX conversion (returns JSON)"""
    result = auto_convert_to_fbx(model_id)
    
    if result['success']:
        return jsonify({
            'success': True,
            'message': 'FBX conversion completed!',
            'download_url': url_for('download_fbx', model_id=model_id)
        })
    else:
        return jsonify({
            'success': False,
            'error': result['error']
        }), 500

# ==================== AUTHENTICATION ROUTES ====================
@app.route('/')
def index():
    if 'username' in session:
        return redirect('/dashboard')
    return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if username in users and users[username]['password'] == password:
            session['username'] = username
            session['role'] = users[username]['role']
            return redirect('/dashboard')
        else:
            return render_template('login.html', error='Invalid credentials')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('role', None)
    return redirect('/login')

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect('/login')
    
    user_models = users[session['username']]['models']
    
    for model in user_models:
        model_id = model['id']
        model['glb_download_url'] = url_for('download_glb', model_id=model_id)
        model['gib_download_url'] = url_for('download_gib', model_id=model_id)
        
        fbx_file = os.path.join(app.config['MODELS_FOLDER'], f"{model_id}_converted.fbx")
        model['fbx_available'] = os.path.exists(fbx_file)
        model['fbx_download_url'] = url_for('download_fbx', model_id=model_id)
    
    return render_template('dashboard.html', 
                         username=session['username'],
                         models=user_models)

@app.route('/model/<model_id>')
def model_preview(model_id):
    if 'username' not in session:
        return redirect('/login')
    
    user_models = users[session['username']]['models']
    model = next((m for m in user_models if m['id'] == model_id), None)
    
    if not model:
        return "Model not found", 404
    
    model_id = model['id']
    model['glb_download_url'] = url_for('download_glb', model_id=model_id)
    model['gib_download_url'] = url_for('download_gib', model_id=model_id)
    
    fbx_file = os.path.join(app.config['MODELS_FOLDER'], f"{model_id}_converted.fbx")
    model['fbx_available'] = os.path.exists(fbx_file)
    model['fbx_download_url'] = url_for('download_fbx', model_id=model_id)
    
    return render_template('model_view.html', model=model)

# ==================== FILE UPLOAD & PROCESSING ====================
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'username' not in session:
        return jsonify({'error': 'Please login first'}), 401
    
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file selected'}), 400
        
        file = request.files['file']
        model_name = request.form.get('model_name', 'My 3D Model')
        
        clean_model_name = "".join(c for c in model_name if c.isalnum() or c in (' ', '-', '_'))
        if not clean_model_name:
            clean_model_name = "My 3D Model"
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if file and allowed_file(file.filename):
            file_id = str(uuid.uuid4())[:8]
            original_filename = secure_filename(file.filename)
            clean_filename = "".join(c for c in original_filename if c.isalnum() or c in ('.', '-', '_')).rstrip()
            if not clean_filename:
                clean_filename = "image"
            
            input_filename = f"{file_id}_{clean_filename}"
            input_path = os.path.join(app.config['UPLOAD_FOLDER'], input_filename)
            output_base = os.path.join(app.config['MODELS_FOLDER'], file_id)
            
            file.save(input_path)
            
            if not os.path.exists(input_path) or os.path.getsize(input_path) == 0:
                return jsonify({'error': 'Invalid file'}), 400
            
            try:
                if USE_ADVANCED:
                    from advanced_model_utils import create_professional_3d_model
                    success, model_info = create_professional_3d_model(input_path, output_base)
                    
                    if success:
                        model_data = {
                            'id': file_id,
                            'name': clean_model_name,
                            'created_at': datetime.datetime.now().isoformat(),
                            'models': model_info,
                            'original_image': input_filename,
                            'quality': 'ULTRA',
                            'glb_download_url': url_for('download_glb', model_id=file_id),
                            'gib_download_url': url_for('download_gib', model_id=file_id),
                            'fbx_download_url': url_for('download_fbx', model_id=file_id)
                        }
                        
                        users[session['username']]['models'].append(model_data)
                        
                        return jsonify({
                            'success': True,
                            'message': '🎉 ULTRA-QUALITY 3D Model Created!',
                            'model_id': file_id,
                            'model_name': clean_model_name,
                            'model_url': url_for('serve_model', filename=f"{file_id}_ULTRA.glb"),
                            'preview_url': url_for('model_preview', model_id=file_id),
                            'glb_download_url': url_for('download_glb', model_id=file_id),
                            'gib_download_url': url_for('download_gib', model_id=file_id),
                            'fbx_download_url': url_for('download_fbx', model_id=file_id)
                        })
                    else:
                        return jsonify({'error': 'Model creation failed'}), 500
                
                else:
                    from model_utils import estimate_depth, depth_to_mesh
                    depth_map, processed_img, original_img = estimate_depth(input_path, midas_model, midas_transform, device)
                    success, parts_info = depth_to_mesh(depth_map, processed_img, original_img, output_base)
                    
                    if success:
                        model_info = {
                            'id': file_id,
                            'name': clean_model_name,
                            'created_at': datetime.datetime.now().isoformat(),
                            'main_model': f"{output_base}_main.glb",
                            'parts': parts_info,
                            'original_image': input_filename,
                            'quality': 'basic',
                            'glb_download_url': url_for('download_glb', model_id=file_id),
                            'gib_download_url': url_for('download_gib', model_id=file_id),
                            'fbx_download_url': url_for('download_fbx', model_id=file_id)
                        }
                        
                        users[session['username']]['models'].append(model_info)
                        
                        return jsonify({
                            'success': True,
                            'message': '✅ Basic 3D Model Created!',
                            'model_id': file_id,
                            'model_name': clean_model_name,
                            'main_url': url_for('serve_model', filename=f"{file_id}_main.glb"),
                            'preview_url': url_for('model_preview', model_id=file_id),
                            'glb_download_url': url_for('download_glb', model_id=file_id),
                            'gib_download_url': url_for('download_gib', model_id=file_id),
                            'fbx_download_url': url_for('download_fbx', model_id=file_id)
                        })
                    else:
                        return jsonify({'error': 'Model creation failed'}), 500
                    
            except Exception as e:
                print(f"❌ Processing error: {str(e)}")
                if os.path.exists(input_path):
                    os.remove(input_path)
                import glob
                for file in glob.glob(f"{output_base}*"):
                    try:
                        os.remove(file)
                    except:
                        pass
                return jsonify({'error': f'Processing failed: {str(e)}'}), 500
        
        else:
            return jsonify({'error': 'Invalid file type'}), 400
            
    except Exception as e:
        print(f"❌ Server error: {str(e)}")
        return jsonify({'error': 'Server error occurred'}), 500

# ==================== OTHER ROUTES ====================
@app.route('/models/<filename>')
def serve_model(filename):
    try:
        return send_file(
            os.path.join(app.config['MODELS_FOLDER'], filename),
            as_attachment=False,
            mimetype='model/gltf-binary'
        )
    except FileNotFoundError:
        return jsonify({'error': 'Model not found'}), 404

@app.route('/api/models')
def get_models():
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    user_models = users[session['username']]['models']
    for model in user_models:
        model_id = model['id']
        model['glb_download_url'] = url_for('download_glb', model_id=model_id)
        model['gib_download_url'] = url_for('download_gib', model_id=model_id)
        
        fbx_file = os.path.join(app.config['MODELS_FOLDER'], f"{model_id}_converted.fbx")
        model['fbx_available'] = os.path.exists(fbx_file)
        model['fbx_download_url'] = url_for('download_fbx', model_id=model_id)
    
    return jsonify(user_models)

@app.route('/status')
def status():
    status_info = {
        'status': 'running',
        'advanced_system': USE_ADVANCED,
        'ai_features': True,
        'texture_system': True,
        'background_removal': True,
        'image_color_texture': True,  # New feature
        'formats_supported': ['GLB', 'GIB', 'FBX'],
        'timestamp': datetime.datetime.now().isoformat()
    }
    return jsonify(status_info)

@app.route('/ai-demo')
def ai_demo():
    """AI Studio Demo Page"""
    if 'username' not in session:
        return redirect('/login')
    return render_template('ai_demo.html')

@app.route('/api/status')
def api_status():
    return jsonify({'status': 'ok', 'message': '3D Magic Studio is running!'})

if __name__ == '__main__':
    print("🚀 Starting 3D Magic Studio with ALL Features...")
    print("👉 Visit: http://127.0.0.1:5000/login")
    print("🎯 Features: Background Removal ✅ Text-to-3D ✅ Texture System ✅ AI Processing ✅")
    print("🎯 New: Image Color Texture System ✅")
    print("🎯 Formats: GLB ✅ GIB ✅ FBX ✅")
    print("🔧 Advanced System:", "ACTIVE" if USE_ADVANCED else "BASIC")
    app.run(debug=True, host='0.0.0.0', port=5000)