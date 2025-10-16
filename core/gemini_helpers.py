import re, json

def gemini_json(model, prompt: str):
    if model is None:
        raise RuntimeError("Model chưa được khởi tạo")
    try:
        resp = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        return json.loads(resp.text or "{}")
    except Exception:
        resp = model.generate_content(prompt)
        txt = resp.text or ""
        m = re.search(r"```json\s*(\{.*?\}|\[.*?\])\s*```", txt, flags=re.S|re.I)
        if m:
            try: return json.loads(m.group(1))
            except Exception: pass
        m2 = re.search(r"(\{.*\}|\[.*\])", txt, flags=re.S)
        if m2:
            try: return json.loads(m2.group(1))
            except Exception: pass
        return {"raw": txt}

def gemini_text(model, prompt: str) -> str:
    if model is None:
        raise RuntimeError("Model chưa được khởi tạo")
    resp = model.generate_content(prompt)
    return resp.text or ""
