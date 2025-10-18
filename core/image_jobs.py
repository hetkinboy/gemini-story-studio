# core/image_jobs.py
# -*- coding: utf-8 -*-
import hashlib
import time
import json
from typing import List, Dict, Any, Optional
 
# ====== 1) Helpers: seed & hash ======

def _hash_to_int(s: str, mod: int = 2**31 - 1) -> int:
    h = hashlib.sha256(s.encode("utf-8")).hexdigest()
    return int(h[:12], 16) % mod

def make_seed_for_character(name: str) -> int:
    """Seed ổn định theo tên nhân vật (giữ nét & layout gương mặt)."""
    return _hash_to_int(f"CHAR::{name}")

def make_seed_for_location(name: str) -> int:
    """Seed ổn định theo địa điểm/bối cảnh."""
    return _hash_to_int(f"LOC::{name}")

def make_seed_for_scene(scene_name: str, ep_title: str) -> int:
    """Seed mặc định theo cảnh (fallback nếu không có char/location)."""
    return _hash_to_int(f"SCN::{ep_title}::{scene_name}")

# ====== 2) Lock style & compose prompt ======

def compose_consistent_image_prompt(
    base: str,
    aspect_ratio: str,
    donghua_style: bool,
    characters: List[str],
    character_bible: Optional[Dict[str, Any]] = None,
    location_name: Optional[str] = None
) -> str:
    """Hợp nhất prompt: base + mô tả nhân vật từ Bible + style + negative."""
    base = (base or "").strip()

    # rút miêu tả nhân vật ngắn gọn từ bible
    char_descs = []
    if character_bible and character_bible.get("characters"):
        lut = {c.get("name"): c for c in character_bible["characters"] if c.get("name")}
        for n in characters or []:
            c = lut.get(n)
            if not c: 
                continue
            char_descs.append(
                f"{c.get('name')}: {c.get('look','')}; hair {c.get('hair','')}; outfit {c.get('outfit','')}; colors {c.get('color_theme','')}"
            )

    style = (
        "cel-shaded, clean lineart, Chinese donghua stylization, Asian facial features, "
        "natural black/dark hair unless specified, soft skin rendering, rich fabric texture, "
        "avoid photorealism, avoid western/European facial structure"
        if donghua_style else
        "cinematic stylized look, avoid hyper-realistic faces"
    )
    neg = "low quality, blurry, extra fingers, deformed hands, photorealistic, western/European facial structure"

    char_block = (" | ".join(char_descs)).strip()
    if char_block:
        char_block = f"Characters: {char_block}. "
    loc_block = f"Location: {location_name}. " if location_name else ""

    return (
        f"{char_block}{loc_block}{base}. "
        f"Style: {style}. "
        f"Shot: keyframe still for video sync; aspect ratio {aspect_ratio or '16:9'}; 24fps context. "
        f"Negative: {neg}."
    )

# ====== 3) Build jobs ======

def build_image_jobs_for_episode(project: Any, episode: Any) -> List[Dict[str, Any]]:
    """
    Từ ep.assets['scenes'] → sinh danh sách 'image jobs' với prompt + seed + ref_images (nếu có).
    Trả về list job dict:
      {
        "index": 1,
        "scene": "Giới thiệu Diệp Minh",
        "prompt": "...",
        "seed": 123456,
        "aspect_ratio": "16:9",
        "characters": ["Diệp Minh"],
        "location": "Diễn Võ Trường",  # nếu nhận diện được
        "char_ref_images": {"Diệp Minh": ["path/to/ref1.png", "path/to/ref2.jpg"]}  # optional
      }
    """
    scenes = (episode.assets or {}).get("scenes", []) or []
    jobs = []

    # optional: lấy ref images từ Character Bible (bạn có thể thêm field 'ref_images' trong bible)
    char_refs = {}
    if project.character_bible and project.character_bible.get("characters"):
        for c in project.character_bible["characters"]:
            nm = c.get("name")
            if not nm:
                continue
            refs = c.get("ref_images") or []  # danh sách đường dẫn ảnh local/URL
            if refs:
                char_refs[nm] = refs

    for i, sc in enumerate(scenes, 1):
        name = sc.get("scene", f"Cảnh {i}")
        base = sc.get("image_prompt") or sc.get("sfx_prompt") or episode.summary
        chars = sc.get("characters", []) or []

        # heuristic: đoán 'địa điểm' từ tên cảnh
        location = None
        for key in ["Tông", "Trường", "Điện", "Thành", "Sơn", "Cốc", "Phủ"]:
            if key in name:
                location = name
                break

        prompt = compose_consistent_image_prompt(
            base=base,
            aspect_ratio=project.aspect_ratio,
            donghua_style=project.donghua_style,
            characters=chars,
            character_bible=project.character_bible,
            location_name=location
        )

        # Chọn seed: ưu tiên nhân vật → địa điểm → cảnh
        seed = None
        if chars:
            # nếu có nhiều nhân vật, mix seeds bằng hash
            mix = sum(make_seed_for_character(n) for n in chars)
            seed = mix % (2**31 - 1)
        elif location:
            seed = make_seed_for_location(location)
        else:
            seed = make_seed_for_scene(name, episode.title)

        job = {
            "index": i,
            "scene": name,
            "prompt": prompt,
            "seed": int(seed),
            "aspect_ratio": project.aspect_ratio or "16:9",
            "characters": chars,
            "location": location,
            "char_ref_images": {n: char_refs.get(n, []) for n in chars if n in char_refs}
        }
        jobs.append(job)
    return jobs

# ====== 4) Export / Save ======

def jobs_to_json(jobs: List[Dict[str, Any]]) -> str:
    return json.dumps({"image_jobs": jobs, "created_at": int(time.time())}, ensure_ascii=False, indent=2)

def save_jobs_json(path: str, jobs: List[Dict[str, Any]]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(jobs_to_json(jobs))

# ====== 5) (Tuỳ chọn) Gửi sang ComfyUI cục bộ ======
# Yêu cầu: ComfyUI đang chạy ở http://127.0.0.1:8188
# Bạn có thể chuẩn bị 1 workflow JSON có nút IP-Adapter, ControlNet pose/depth tuỳ nhu cầu
# Ở đây mình gửi prompt + seed theo 1 workflow tối giản (text-to-image).

import requests

def send_job_to_comfyui(server_url: str, prompt: str, seed: int, width: int, height: int) -> str:
    """
    Gửi 1 job đơn giản lên ComfyUI: trả về prompt_id để theo dõi.
    Bạn có thể thay 'workflow' tuỳ preset của bạn (SDXL/FLUX).
    """
    # Workflow siêu gọn (txt2img) — bạn thay bằng workflow của bạn để dùng IP-Adapter/ControlNet
    workflow = {
        "3": {  # KSampler
            "inputs": {
                "seed": seed,
                "steps": 30,
                "cfg": 6.5,
                "sampler_name": "euler",
                "scheduler": "normal",
                "denoise": 1.0,
                "model": ["4", 0],
                "positive": ["5", 0],
                "negative": ["6", 0],
                "latent_image": ["7", 0]
            },
            "class_type": "KSampler",
            "_meta": {"title": "KSampler"}
        },
        "4": {  # CheckpointLoader (bạn đổi sang model SDXL/Flux đã cài)
            "inputs": {"ckpt_name": "sdxl_base_1.0.safetensors"},
            "class_type": "CheckpointLoaderSimple",
            "_meta": {"title": "CheckpointLoaderSimple"}
        },
        "5": {  # CLIPTextEncode (prompt)
            "inputs": {"text": prompt, "clip": ["4", 1]},
            "class_type": "CLIPTextEncode",
            "_meta": {"title": "CLIPTextEncode"}
        },
        "6": {  # Negative
            "inputs": {"text": "blurry, low quality, deformed hands", "clip": ["4", 1]},
            "class_type": "CLIPTextEncode",
            "_meta": {"title": "CLIPTextEncode (Negative)"}
        },
        "7": {  # Empty Latent Image
            "inputs": {"width": width, "height": height, "batch_size": 1},
            "class_type": "EmptyLatentImage",
            "_meta": {"title": "EmptyLatentImage"}
        },
        "8": {  # VAE Decode
            "inputs": {"samples": ["3", 0], "vae": ["4", 2]},
            "class_type": "VAEDecode",
            "_meta": {"title": "VAEDecode"}
        },
        "9": {  # Save Image
            "inputs": {"images": ["8", 0]},
            "class_type": "SaveImage",
            "_meta": {"title": "SaveImage"}
        }
    }
    resp = requests.post(f"{server_url.rstrip('/')}/prompt", json={"prompt": workflow})
    resp.raise_for_status()
    return resp.json().get("prompt_id", "")

def batch_send_jobs_to_comfyui(server_url: str, jobs: List[Dict[str, Any]]) -> List[str]:
    ids = []
    # map AR → kích thước
    def ar_to_wh(ar: str):
        ar = (ar or "16:9").strip()
        if ar in ("16:9", "1.78"):
            return (1280, 720)
        if ar in ("9:16",):
            return (720, 1280)
        if ar in ("1:1",):
            return (1024, 1024)
        return (1024, 576)
    for job in jobs:
        w, h = ar_to_wh(job.get("aspect_ratio"))
        pid = send_job_to_comfyui(server_url, job["prompt"], job["seed"], w, h)
        ids.append(pid)
    return ids
