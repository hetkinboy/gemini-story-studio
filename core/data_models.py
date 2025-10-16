from pydantic import BaseModel, Field
from typing import List, Dict, Any

class Episode(BaseModel):
    index: int
    title: str
    summary: str
    script_text: str = ""
    assets: Dict[str, Any] = Field(default_factory=lambda: {"scenes": []})
    tts_text: str = ""

class Season(BaseModel):
    season_index: int = 1
    episode_count: int = 10
    outline: List[Dict[str, str]] = []
    episodes: List[Episode] = []

class Project(BaseModel):
    name: str
    idea: str
    preset: str
    storyline_choices: List[str] = []
    chosen_storyline: str = ""
    seasons: List[Season] = []
    aspect_ratio: str = "16:9"     # "16:9" | "9:16"
    donghua_style: bool = True
    character_bible: Dict[str, Any] = Field(default_factory=lambda: {"characters": []})
