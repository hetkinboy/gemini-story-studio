# -*- coding: utf-8 -*-
import json
import io
import zipfile
from pathlib import Path
from typing import List, Dict, Any

from core.data_models import Project, Season, Episode
from core.text_utils import _safe_name

APP_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = APP_DIR / "projects"
DATA_DIR.mkdir(exist_ok=True)

def _normalize_assets(value) -> Dict[str, Any]:
    if isinstance(value, dict):
        scenes = value.get("scenes", [])
        if isinstance(scenes, list):
            return {"scenes": scenes}
        return {"scenes": []}
    elif isinstance(value, list):
        return {"scenes": value}
    return {"scenes": []}

def _migrate_project_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    data = dict(data or {})
    data.setdefault("storyline_choices", [])
    data.setdefault("chosen_storyline", "")
    data.setdefault("seasons", [])
    data.setdefault("aspect_ratio", "16:9")
    data.setdefault("donghua_style", True)
    data.setdefault("character_bible", {"characters": []})

    seasons = []
    for si, s in enumerate(data.get("seasons", []), start=1):
        s = dict(s or {})
        s.setdefault("season_index", si)
        s.setdefault("episode_count", s.get("episode_count", 10))
        s.setdefault("outline", s.get("outline", []))
        s.setdefault("episodes", s.get("episodes", []))

        eps_norm = []
        for ei, e in enumerate(s["episodes"], start=1):
            e = dict(e or {})
            e.setdefault("index", e.get("index", ei))
            e.setdefault("title", e.get("title", f"Tập {e['index']:02d}"))
            e.setdefault("summary", e.get("summary", ""))
            e.setdefault("script_text", e.get("script_text", ""))
            e.setdefault("tts_text", e.get("tts_text", ""))
            e["assets"] = _normalize_assets(e.get("assets"))
            eps_norm.append(e)

        s["episodes"] = eps_norm
        seasons.append(s)

    data["seasons"] = seasons
    return data

def save_project(proj: Project) -> Path:
    f = DATA_DIR / f"{_safe_name(proj.name)}.json"
    with f.open("w", encoding="utf-8") as fp:
        json.dump(proj.model_dump(), fp, ensure_ascii=False, indent=2)
    return f

def load_project(path: Path) -> Project:
    p = Path(path)
    if not p.is_absolute():
        p = DATA_DIR | p  # nếu Python <3.9 dùng p = DATA_DIR / p
    with p.open("r", encoding="utf-8") as fp:
        raw = json.load(fp)
    data = _migrate_project_dict(raw)
    return Project(**data)

def export_zip(proj: Project) -> bytes:
    mem = io.BytesIO()
    with zipfile.ZipFile(mem, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("project.json", json.dumps(proj.model_dump(), ensure_ascii=False, indent=2))

        for s in proj.seasons or []:
            s_idx = s.season_index
            s_prefix = f"seasons/season_{s_idx:02d}"
            z.writestr(f"{s_prefix}/outline.json", json.dumps(s.outline or [], ensure_ascii=False, indent=2))

            for ep in s.episodes or []:
                base = f"{s_prefix}/episode_{ep.index:02d}_{_safe_name(ep.title)}"
                z.writestr(f"{base}/script.md", ep.script_text or "")
                assets = _normalize_assets(ep.assets or {"scenes": []})
                z.writestr(f"{base}/assets.json", json.dumps(assets, ensure_ascii=False, indent=2))
                z.writestr(f"{base}/tts.txt", ep.tts_text or "")

                try:
                    scenes = assets.get("scenes", [])
                    lines: List[str] = []
                    for j, sc in enumerate(scenes, 1):
                        segs = sc.get("veo31_segments") or sc.get("segments") or []
                        if not segs:
                            continue
                        lines.append(f"## {sc.get('scene', f'Cảnh {j}')}")
                        for si, seg in enumerate(segs, 1):
                            title = seg.get("title", "")
                            dur = seg.get("duration_sec", 8)
                            veo = seg.get("veo_prompt", "")
                            sfx = seg.get("sfx", "")
                            chars = seg.get("characters", [])
                            lines.append(
                                f"\n# Clip {si} — {dur}s: {title}\n"
                                f"[Characters] {', '.join(chars)}\n"
                                f"{veo}\n"
                                f"[SFX] {sfx}\n"
                            )
                    if lines:
                        z.writestr(f"{base}/veo31_segments.txt", "\n".join(lines))
                except Exception:
                    pass

    mem.seek(0)
    return mem.read()
