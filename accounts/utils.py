from PIL import Image
from io import BytesIO
from django.core.files.base import ContentFile
import os

def compress_image(uploaded_image, max_width=800, quality=70):
    """
    Resizes and compresses the uploaded image.
    Returns a ContentFile that can be saved to an ImageField.
    """
    if not uploaded_image:
        return None
        
    try:
        img = Image.open(uploaded_image)
        
        # Convert to RGB if necessary (e.g. RGBA -> RGB to save as JPEG)
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
            
        # Resize if width > max_width
        width, height = img.size
        if width > max_width:
            ratio = max_width / width
            new_height = int(height * ratio)
            img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
            
        # Save to buffer
        buffer = BytesIO()
        img.save(buffer, format='JPEG', quality=quality, optimize=True)
        
        # Create ContentFile
        file_name = os.path.splitext(uploaded_image.name)[0] + '.jpg'
        return ContentFile(buffer.getvalue(), name=file_name)
        
    except Exception as e:
        print(f"Error compressing image: {e}")
        return uploaded_image
