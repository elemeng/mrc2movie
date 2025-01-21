import flet as ft
from flet import GridView, Page, Slider, Text, Column, Row, Image
import numpy as np
import mrcfile

def main(page: Page):
    page.title = "MRC Thumbnails Viewer"
    page.padding = 20
    
    # Create grid view
    grid = GridView(
        expand=True,
        runs_count=5,
        max_extent=200,
        child_aspect_ratio=1.0,
        spacing=10,
        run_spacing=10,
    )
    
    # Size control
    size_slider = Slider(
        min=100,
        max=500,
        value=200,
        divisions=40,
        label="{value}px",
        on_change=lambda e: update_grid_size(e.control.value)
    )
    
    def update_grid_size(size):
        grid.max_extent = size
        grid.update()
    
    # Load MRC thumbnails
    def load_thumbnails():
        # Example MRC file path
        mrc_path = "uploads/250119-catip-ko_20.mrc"
        
        try:
            with mrcfile.open(mrc_path) as mrc:
                data = mrc.data
                # Create thumbnail from middle slice
                mid_slice = data[data.shape[0] // 2]
                # Normalize and convert to uint8
                mid_slice = (255 * (mid_slice - mid_slice.min()) / 
                           (mid_slice.max() - mid_slice.min())).astype(np.uint8)
                
                # Create image control
                img = Image(
                    src_base64=array_to_base64(mid_slice),
                    fit="contain",
                    width=size_slider.value,
                    height=size_slider.value
                )
                grid.controls.append(img)
                grid.update()
        except Exception as e:
            print(f"Error loading MRC file: {e}")
    
    def array_to_base64(array):
        from io import BytesIO
        from PIL import Image as PILImage
        import base64
        
        img = PILImage.fromarray(array)
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode("utf-8")
    
    # Load initial thumbnails
    load_thumbnails()
    
    # Add controls to page
    page.add(
        Column([
            Row([
                Text("Thumbnail Size:"),
                size_slider
            ]),
            grid
        ])
    )

ft.app(target=main)
