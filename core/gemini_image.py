# core/gemini_image.py
# -*- coding: utf-8 -*-
import io
import os
from typing import List, Optional, Tuple

from PIL import Image
from google import genai
# from google.genai import types as gai_types 


def _first_image_from_parts(parts) -> Optional[Image.Image]:
    """Lấy ảnh đầu tiên từ response.candidates[0].content.parts (inline_data)."""
    if not parts:
        return None
    for p in parts:
        inline = getattr(p, "inline_data", None)
        if inline and getattr(inline, "data", None):
            try:
                return Image.open(io.BytesIO(inline.data))
            except Exception:
                pass
    return None


def gemini25_image_generate(
    prompt: str,
    model_name: str = "gemini-2.5-flash",
    size_hint: str = "1024x576",
) -> Tuple[Optional[Image.Image], str]:
    """
    Sinh ảnh bằng Gemini 2.5 Flash Image (Nano Banana) qua SDK google-genai.
    Trả về: (Pillow Image hoặc None, log_msg)
    - Yêu cầu biến môi trường: GEMINI_API_KEY hoặc GOOGLE_API_KEY
    """
    # Client tự đọc API key từ env: GEMINI_API_KEY hoặc GOOGLE_API_KEY
    client = genai.Client()

    # Khuyến nghị: ghi kích thước mong muốn vào prompt (model hiện nhận theo ngôn ngữ tự nhiên)
    full_prompt = f"Generate an image ~{size_hint}. {prompt}".strip()

    try:
        resp = client.models.generate_content(
            model=model_name,
            contents=[full_prompt],
            # Nếu cần có thể thêm generation_config hoặc safety_settings
            # generation_config=gai_types.GenerateContentConfig(temperature=0.4),
        )
        if not resp or not resp.candidates:
            return None, "No candidates from model."

        parts = resp.candidates[0].content.parts
        img = _first_image_from_parts(parts)
        if img is None:
            return None, (
                "No image data in response. Check model name is 'gemini-2.5-flash-image' "
                "and your API key has image-generation access."
            )
        return img, "ok"

    except Exception as e:
        # gRPC cảnh báo kiểu 'ALTS creds ignored...' là bình thường, có thể bỏ qua
        return None, f"Gemini 2.5 image error: {e}"


def gemini25_images_generate_batch(
    prompts: List[str],
    model_name: str = "gemini-2.5-flash-image",
    size_hint: str = "1024x576",
) -> List[Tuple[Optional[Image.Image], str]]:
    """Sinh nhiều ảnh theo danh sách prompt; trả về list (PIL.Image|None, msg)."""
    out = []
    for p in prompts:
        img, msg = gemini25_image_generate(p, model_name=model_name, size_hint=size_hint)
        out.append((img, msg))
    return out
