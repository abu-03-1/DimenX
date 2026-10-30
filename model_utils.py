import torch
import cv2
import numpy as np
from PIL import Image
import open3d as o3d
import trimesh
import warnings
import scipy.ndimage
import os

warnings.filterwarnings("ignore")

def load_midas():
    """Load basic MiDaS model"""
    print("🧠 Loading Basic MiDaS model...")
    try:
        model = torch.hub.load("intel-isl/MiDaS", "MiDaS_small")
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"✅ Using device: {device}")
        model.to(device)
        model.eval()
        
        midas_transforms = torch.hub.load("intel-isl/MiDaS", "transforms")
        transform = midas_transforms.small_transform
        
        print("✅ Basic MiDaS model loaded successfully!")
        return model, transform, device
    except Exception as e:
        print(f"❌ Error loading basic MiDaS: {str(e)}")
        raise e

def estimate_depth(image_path, midas, transform, device):
    """Basic depth estimation"""
    try:
        print(f"📁 Loading: {image_path}")
        
        # Load image
        pil_image = Image.open(image_path).convert('RGB')
        img = np.array(pil_image)
        
        print(f"🖼️ Image size: {img.shape}")
        
        # Resize if too large
        max_size = 512
        h, w = img.shape[:2]
        if max(h, w) > max_size:
            scale = max_size / max(h, w)
            new_w, new_h = int(w * scale), int(h * scale)
            img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
            print(f"📏 Resized to: {img.shape}")
        
        # Apply transform
        input_batch = transform(img).to(device)
        
        # Predict depth
        with torch.no_grad():
            prediction = midas(input_batch)
            prediction = torch.nn.functional.interpolate(
                prediction.unsqueeze(1),
                size=img.shape[:2],
                mode="bicubic",
                align_corners=False,
            ).squeeze()
        
        depth = prediction.cpu().numpy()
        depth = (depth - depth.min()) / (depth.max() - depth.min())
        
        print(f"✅ Depth estimation completed!")
        return depth, img, img  # Return same image for compatibility
        
    except Exception as e:
        print(f"❌ Error in depth estimation: {str(e)}")
        raise e

def depth_to_mesh(depth, image, original_img, output_base_path):
    """Basic mesh generation"""
    try:
        print("🔄 Creating basic 3D mesh...")
        
        height, width = depth.shape
        points = []
        colors = []
        
        # Create simple point cloud
        for y in range(0, height, 2):
            for x in range(0, width, 2):
                z = depth[y, x] * 3.0
                points.append([x - width/2, y - height/2, z])
                colors.append(image[y, x] / 255.0)
        
        # Create point cloud
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(points)
        pcd.colors = o3d.utility.Vector3dVector(colors)
        
        # Create simple mesh
        try:
            distances = pcd.compute_nearest_neighbor_distance()
            avg_dist = np.mean(distances)
            radius = 3.0 * avg_dist
            
            mesh = o3d.geometry.TriangleMesh.create_from_point_cloud_ball_pivoting(
                pcd, o3d.utility.DoubleVector([radius, radius * 2])
            )
        except:
            # Fallback: create convex hull
            mesh = o3d.geometry.TriangleMesh.create_from_point_cloud_alpha_shape(pcd, 0.03)
        
        # Convert to trimesh and export
        vertices = np.asarray(mesh.vertices)
        faces = np.asarray(mesh.triangles)
        
        tri_mesh = trimesh.Trimesh(vertices=vertices, faces=faces)
        if hasattr(mesh, 'vertex_colors') and len(mesh.vertex_colors) > 0:
            vertex_colors = (np.asarray(mesh.vertex_colors) * 255).astype(np.uint8)
            tri_mesh.visual.vertex_colors = vertex_colors
        
        # Save model
        output_path = f"{output_base_path}_main.glb"
        tri_mesh.export(output_path)
        
        print(f"✅ Basic 3D model saved: {output_path}")
        return True, {'foreground': {'name': 'Main Object', 'path': output_path}}
        
    except Exception as e:
        print(f"❌ Error in basic mesh generation: {str(e)}")
        raise e