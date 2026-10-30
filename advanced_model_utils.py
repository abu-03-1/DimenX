import torch
import cv2
import numpy as np
from PIL import Image
import open3d as o3d
import trimesh
import warnings
import scipy.ndimage
import os
from sklearn.cluster import KMeans
import json
import pyrender
from transformers import DPTImageProcessor, DPTForDepthEstimation

warnings.filterwarnings("ignore")

# 🔽 BACKGROUND REMOVAL FUNCTIONS - ADD THIS SECTION 🔽
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
        rect = (50, 50, width-100, height-100)  # Leave some margin
        
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
        
        # Create mask based on color (adjust these values based on your image)
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
        
    # Create transparent background (white background for 3D processing)
    result = image.copy()
    result[mask == 0] = [255, 255, 255]  # White background
    
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
# 🔼 BACKGROUND REMOVAL FUNCTIONS MUDINCHU 🔼

# 🔽 EXISTING ADVANCED MODEL UTILS CODE IRUKKUM - ATHUKU MELAE ADD PANNU 🔽
def load_advanced_midas():
    """Load advanced depth estimation model"""
    print("🧠 Loading Advanced DPT Model...")
    try:
        processor = DPTImageProcessor.from_pretrained("Intel/dpt-large")
        model = DPTForDepthEstimation.from_pretrained("Intel/dpt-large")
        
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"✅ Using device: {device}")
        model.to(device)
        model.eval()
        
        print("✅ Advanced DPT model loaded successfully!")
        return model, processor, device
    except Exception as e:
        print(f"❌ Advanced DPT failed: {e}, using standard MiDaS")
        return load_standard_midas()

def load_standard_midas():
    """Fallback to standard MiDaS"""
    print("🔄 Loading standard MiDaS...")
    model = torch.hub.load("intel-isl/MiDaS", "DPT_Large")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    model.eval()
    
    midas_transforms = torch.hub.load("intel-isl/MiDaS", "transforms")
    transform = midas_transforms.dpt_transform
    
    return model, transform, device

def estimate_high_quality_depth(image_path, model, processor, device):
    """High-quality depth estimation with DPT"""
    try:
        print(f"📁 Loading: {image_path}")
        
        # Load image
        image = Image.open(image_path).convert('RGB')
        original_size = image.size
        
        # Resize for optimal processing
        max_size = 1024
        if max(image.size) > max_size:
            image = image.resize((max_size, int(max_size * image.size[1] / image.size[0])))
        
        # Use DPT for superior depth estimation
        inputs = processor(images=image, return_tensors="pt")
        with torch.no_grad():
            outputs = model(**inputs.to(device))
            predicted_depth = outputs.predicted_depth
        
        # Interpolate to original size
        prediction = torch.nn.functional.interpolate(
            predicted_depth.unsqueeze(1),
            size=image.size[::-1],
            mode="bicubic",
            align_corners=False,
        ).squeeze()
        
        depth = prediction.cpu().numpy()
        
        # Advanced depth processing
        depth = (depth - depth.min()) / (depth.max() - depth.min())
        
        # Multi-stage filtering
        depth_uint8 = (depth * 255).astype(np.uint8)
        
        # Bilateral filter for edge preservation
        depth_filtered = cv2.bilateralFilter(depth_uint8, 15, 80, 80)
        
        # Gaussian filter for smoothness
        depth_filtered = cv2.GaussianBlur(depth_filtered, (5, 5), 1.5)
        
        depth = depth_filtered.astype(np.float32) / 255.0
        
        # Enhanced contrast and detail preservation
        depth = np.power(depth, 0.6)  # Stronger gamma for more 3D pop
        
        print(f"✅ High-quality depth map: {depth.shape}")
        return depth, np.array(image), original_size
        
    except Exception as e:
        print(f"❌ Advanced depth estimation failed: {str(e)}")
        raise e

def create_realistic_mesh(depth, image, original_size):
    """Create ultra-realistic 3D mesh"""
    height, width = depth.shape
    
    print("🎨 Creating ultra-realistic 3D mesh...")
    
    # Calculate advanced surface properties
    dy, dx = np.gradient(depth)
    
    # Enhanced point cloud with micro-details
    vertices = []
    vertex_colors = []
    vertex_normals = []
    
    # Multi-scale sampling strategy
    for y in range(0, height, 1):  # Full resolution for maximum detail
        for x in range(0, width, 1):
            # Advanced depth calculation with curvature
            base_z = depth[y, x] * 12.0  # Increased depth range
            
            # Add micro-details based on local gradients
            local_detail = (dx[y, x]**2 + dy[y, x]**2) * 2.0
            z = base_z + local_detail
            
            # Perspective-correct coordinates
            x_coord = (x - width/2) * 0.012
            y_coord = (y - height/2) * 0.012
            
            # Calculate normal
            normal = np.array([-dx[y, x], -dy[y, x], 1.0])
            normal_length = np.linalg.norm(normal)
            if normal_length > 0:
                normal /= normal_length
            
            vertices.append([x_coord, y_coord, z])
            vertex_colors.append(image[y, x] / 255.0)
            vertex_normals.append(normal)
    
    vertices = np.array(vertices)
    vertex_colors = np.array(vertex_colors)
    vertex_normals = np.array(vertex_normals)
    
    print(f"☁️ Generated {len(vertices)} ultra-detailed points")
    
    # Create advanced point cloud
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(vertices)
    pcd.colors = o3d.utility.Vector3dVector(vertex_colors)
    pcd.normals = o3d.utility.Vector3dVector(vertex_normals)
    
    # Multi-stage outlier removal
    pcd, ind = pcd.remove_statistical_outlier(nb_neighbors=50, std_ratio=1.2)
    pcd, ind = pcd.remove_radius_outlier(nb_points=16, radius=0.05)
    
    print(f"✅ After advanced cleaning: {len(pcd.points)} points")
    
    # High-quality mesh reconstruction
    mesh = create_ultra_quality_mesh(pcd)
    
    return mesh

def create_ultra_quality_mesh(pcd):
    """Ultra-quality mesh reconstruction"""
    print("🔄 Ultra-quality mesh reconstruction...")
    
    # Method 1: Advanced Poisson
    try:
        print("🔹 Advanced Poisson reconstruction...")
        mesh, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(
            pcd, depth=12, width=0, scale=1.2, linear_fit=True
        )
        
        # Smart density-based filtering
        if len(densities) > 0:
            density_threshold = np.quantile(densities, 0.08)  # Keep more details
            vertices_to_remove = densities < density_threshold
            mesh.remove_vertices_by_mask(vertices_to_remove)
        
        print(f"✅ Poisson: {len(mesh.vertices)} vertices, {len(mesh.triangles)} faces")
        return mesh
        
    except Exception as e:
        print(f"❌ Poisson failed: {e}")
    
    # Method 2: Multi-radius ball pivoting
    try:
        print("🔹 Multi-radius ball pivoting...")
        distances = pcd.compute_nearest_neighbor_distance()
        avg_dist = np.mean(distances)
        
        radii = o3d.utility.DoubleVector([
            avg_dist * 0.5, 
            avg_dist * 1.0, 
            avg_dist * 2.0,
            avg_dist * 3.0
        ])
        mesh = o3d.geometry.TriangleMesh.create_from_point_cloud_ball_pivoting(pcd, radii)
        
        print(f"✅ Ball Pivoting: {len(mesh.vertices)} vertices")
        return mesh
        
    except Exception as e:
        print(f"❌ Ball pivoting failed: {e}")
    
    raise Exception("All ultra-quality methods failed")

def enhance_with_pyrender(mesh, image):
    """Use PyRender for professional rendering and texturing"""
    print("🎨 Enhancing with PyRender...")
    
    try:
        # Convert to trimesh first
        vertices = np.asarray(mesh.vertices)
        faces = np.asarray(mesh.triangles)
        
        tri_mesh = trimesh.Trimesh(vertices=vertices, faces=faces)
        
        # Add vertex colors
        if hasattr(mesh, 'vertex_colors') and len(mesh.vertex_colors) > 0:
            vertex_colors = (np.asarray(mesh.vertex_colors) * 255).astype(np.uint8)
            tri_mesh.visual.vertex_colors = vertex_colors
        
        # Professional material properties
        if hasattr(tri_mesh.visual, 'material'):
            tri_mesh.visual.material.ambient = [0.3, 0.3, 0.3, 1.0]
            tri_mesh.visual.material.diffuse = [0.9, 0.9, 0.9, 1.0]
            tri_mesh.visual.material.specular = [0.4, 0.4, 0.4, 1.0]
            tri_mesh.visual.material.shininess = 64.0
        
        return tri_mesh
        
    except Exception as e:
        print(f"❌ PyRender enhancement failed: {e}, using basic enhancement")
        return enhance_basic(mesh, image)

def enhance_basic(mesh, image):
    """Basic enhancement fallback"""
    print("🔄 Basic mesh enhancement...")
    
    vertices = np.asarray(mesh.vertices)
    faces = np.asarray(mesh.triangles)
    
    tri_mesh = trimesh.Trimesh(vertices=vertices, faces=faces)
    
    if hasattr(mesh, 'vertex_colors') and len(mesh.vertex_colors) > 0:
        vertex_colors = (np.asarray(mesh.vertex_colors) * 255).astype(np.uint8)
        tri_mesh.visual.vertex_colors = vertex_colors
    
    return tri_mesh

def create_preview_image(mesh, output_path):
    """Create 3D preview image using PyRender"""
    try:
        print("📷 Creating 3D preview...")
        
        # Convert to PyRender mesh
        vertices = np.asarray(mesh.vertices)
        faces = np.asarray(mesh.triangles)
        
        # Create colored mesh
        if hasattr(mesh.visual, 'vertex_colors'):
            colors = mesh.visual.vertex_colors / 255.0
        else:
            colors = np.ones((len(vertices), 3)) * 0.8
        
        tri_mesh = trimesh.Trimesh(vertices=vertices, faces=faces, vertex_colors=colors)
        
        # Create PyRender scene
        scene = pyrender.Scene(ambient_light=[0.5, 0.5, 0.5], bg_color=[1.0, 1.0, 1.0])
        
        # Add mesh to scene
        mesh_node = pyrender.Mesh.from_trimesh(tri_mesh, smooth=False)
        scene.add(mesh_node)
        
        # Add lights
        light = pyrender.DirectionalLight(color=[1.0, 1.0, 1.0], intensity=2.0)
        light_pose = np.eye(4)
        light_pose[:3, 3] = [2, 2, 2]
        scene.add(light, pose=light_pose)
        
        # Add camera
        camera = pyrender.PerspectiveCamera(yfov=np.pi/3.0, aspectRatio=1.0)
        camera_pose = np.eye(4)
        camera_pose[:3, 3] = [0, 0, 3]
        scene.add(camera, pose=camera_pose)
        
        # Render
        r = pyrender.OffscreenRenderer(800, 800)
        color, depth = r.render(scene)
        
        # Save preview
        preview_path = output_path.replace('.glb', '_preview.png')
        Image.fromarray(color).save(preview_path)
        
        print(f"✅ Preview saved: {preview_path}")
        return preview_path
        
    except Exception as e:
        print(f"❌ Preview creation failed: {e}")
        return None

def create_professional_3d_model(image_path, output_base_path):
    """Complete professional 3D model generation with PyRender"""
    try:
        print("🚀 Starting ULTRA-QUALITY 3D model generation...")
        
        # 🔽 BACKGROUND REMOVAL ADD PANNEN INGA 🔽
        print("🖼️ Preprocessing image (background removal)...")
        processed_image_path = preprocess_image_for_3d(image_path)
        
        # Load advanced model
        model, processor, device = load_advanced_midas()
        
        # Estimate ultra-quality depth using PROCESSED IMAGE
        depth, processed_img, original_size = estimate_high_quality_depth(
            processed_image_path, model, processor, device
        )
        
        # Create ultra-realistic mesh
        mesh = create_realistic_mesh(depth, processed_img, original_size)
        
        # Enhance with PyRender
        enhanced_mesh = enhance_with_pyrender(mesh, processed_img)
        
        # Save professional model
        professional_path = f"{output_base_path}_ULTRA.glb"
        enhanced_mesh.export(professional_path)
        
        # Create preview
        preview_path = create_preview_image(enhanced_mesh, professional_path)
        
        print(f"✅ ULTRA-QUALITY 3D model saved: {professional_path}")
        
        return True, {
            'ultra_quality': professional_path,
            'preview': preview_path,
            'quality': 'ULTRA'
        }
        
    except Exception as e:
        print(f"❌ ULTRA-QUALITY model generation failed: {str(e)}")
        raise e

# For backward compatibility
def load_midas():
    """Alias for basic MiDaS loading"""
    return load_advanced_midas()

def estimate_depth(image_path, midas, transform, device):
    """Alias for enhanced depth estimation"""
    return estimate_high_quality_depth(image_path, midas, transform, device)

def depth_to_mesh(depth, image, original_img, output_base_path):
    """Alias for enhanced mesh generation"""
    return create_realistic_mesh(depth, image, original_img)