#!/usr/bin/env python3
"""
Script to generate ACB Integration module icon
"""
from PIL import Image, ImageDraw, ImageFont
import os

def create_acb_icon():
    # Create a 128x128 image with a professional banking color scheme
    size = 128
    img = Image.new('RGB', (size, size), color='#1e3a8a')  # Deep blue background
    draw = ImageDraw.Draw(img)
    
    # Add a circular background
    circle_margin = 8
    circle_color = '#3b82f6'  # Lighter blue
    draw.ellipse([circle_margin, circle_margin, size-circle_margin, size-circle_margin], 
                fill=circle_color, outline='#1e40af', width=2)
    
    # Draw bank building silhouette
    building_width = 40
    building_height = 50
    building_x = (size - building_width) // 2
    building_y = size // 2 - 10
    
    # Main building body
    draw.rectangle([building_x, building_y, building_x + building_width, building_y + building_height], 
                  fill='#ffffff', outline='#e5e7eb', width=1)
    
    # Bank pillars
    pillar_width = 4
    pillar_count = 4
    pillar_spacing = (building_width - pillar_count * pillar_width) // (pillar_count + 1)
    
    for i in range(pillar_count):
        pillar_x = building_x + pillar_spacing + i * (pillar_width + pillar_spacing)
        draw.rectangle([pillar_x, building_y + 8, pillar_x + pillar_width, building_y + building_height - 8], 
                      fill='#1e3a8a')
    
    # Bank roof
    roof_height = 8
    roof_points = [
        (building_x - 4, building_y),
        (building_x + building_width//2, building_y - roof_height),
        (building_x + building_width + 4, building_y)
    ]
    draw.polygon(roof_points, fill='#ffffff', outline='#e5e7eb')
    
    # Add connection/integration symbols (arrows)
    arrow_color = '#10b981'  # Green for connection
    
    # Left arrow pointing to building
    draw.polygon([
        (20, size//2 - 5),
        (35, size//2 - 5),
        (35, size//2 - 8),
        (45, size//2),
        (35, size//2 + 8),
        (35, size//2 + 5),
        (20, size//2 + 5)
    ], fill=arrow_color)
    
    # Right arrow pointing from building
    draw.polygon([
        (size - 20, size//2 + 5),
        (size - 35, size//2 + 5),
        (size - 35, size//2 + 8),
        (size - 45, size//2),
        (size - 35, size//2 - 8),
        (size - 35, size//2 - 5),
        (size - 20, size//2 - 5)
    ], fill=arrow_color)
    
    # Add "ACB" text at the bottom
    try:
        # Try to use a built-in font
        font_size = 16
        font = ImageFont.load_default()
        
        text = "ACB"
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        
        text_x = (size - text_width) // 2
        text_y = size - 25
        
        draw.text((text_x, text_y), text, fill='#ffffff', font=font)
    except:
        # Fallback if font loading fails
        pass
    
    # Add small integration dots
    dot_color = '#fbbf24'  # Yellow/orange
    dot_positions = [
        (25, 30), (size-25, 30), (25, size-30), (size-25, size-30)
    ]
    
    for pos in dot_positions:
        draw.ellipse([pos[0]-3, pos[1]-3, pos[0]+3, pos[1]+3], fill=dot_color)
    
    return img

def main():
    # Generate the icon
    icon = create_acb_icon()
    
    # Save the icon
    icon_path = "icon.png"
    icon.save(icon_path, "PNG")
    print(f"ACB Integration icon created successfully: {icon_path}")

if __name__ == "__main__":
    main() 