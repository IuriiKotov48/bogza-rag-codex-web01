from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, List, Optional

from llama_cpp import Llama


PROMPT_TEMPLATE = '''
You analyse architectural drawing schedules. Work only with the evidence from the given text.
Room of interest: {room}

Return zero or more lines. Each line must follow this format exactly (no commentary before or after):
CATEGORY|ITEM_CODE|SHORT_DESCRIPTION|SOURCE_NOTE|PRODUCT_URL

Rules:
- CATEGORY must be one of FLOOR, WALLS, CEILING, FURNITURE, CASEWORK, EQUIPMENT.
- ITEM_CODE must be copied exactly as written in the text. If there is no code, leave the field empty but keep the separators.
- SHORT_DESCRIPTION must stay under 12 words and only summarise the item or finish.
- SOURCE_NOTE should capture the detail/elevation/schedule reference that identifies the associated drawing or figure. Leave empty if the text does not include one.
- PRODUCT_URL must be a URL that appears in the text. If there is no URL in the text related to the item, do not output that line.
- Only report data that clearly refers to the specified room. If uncertain, skip it.
- Do not invent new information. If the text does not mention any qualifying item, return nothing.

Text:
"""{page_text}"""
'''

LINE_PATTERN = re.compile(
    r"^(?P<category>[A-Z ]+)\|(?P<item_code>[^|]*)\|(?P<description>[^|]{1,256})\|(?P<detail>[^|]{0,200})\|(?P<url>https?://\S+)$"
)


@dataclass
class Extraction:
    category: str
    item_code: str
    description: str
    detail: str
    url: str


class LocalLLM:
    def __init__(
        self,
        model_path,
        temperature: float = 0.1,
        top_p: float = 0.15,
        ctx_size: int = 2048,
        n_threads: Optional[int] = None,
        n_gpu_layers: int = 0,
    ) -> None:
        kwargs = {
            "model_path": str(model_path),
            "n_ctx": ctx_size,
            "temperature": temperature,
            "top_p": top_p,
            "n_gpu_layers": n_gpu_layers,
        }
        if n_threads is not None:
            kwargs["n_threads"] = n_threads
        self.client = Llama(**kwargs)
        self.temperature = temperature
        self.top_p = top_p

    def extract_items(self, room: str, page_text: str) -> List[Extraction]:
        snippet = page_text.strip()
        if len(snippet) > 6000:
            snippet = snippet[:6000]
        prompt = PROMPT_TEMPLATE.format(room=room, page_text=snippet)
        response = self.client.create_completion(
            prompt=prompt,
            max_tokens=512,
            temperature=self.temperature,
            top_p=self.top_p,
            stop=["\n\n"],
        )
        text = response["choices"][0]["text"]
        return list(self._parse(text))

    @staticmethod
    def _parse(text: str) -> Iterable[Extraction]:
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            match = LINE_PATTERN.match(line)
            if not match:
                continue
            info = match.groupdict()
            yield Extraction(
                category=info["category"].strip(),
                item_code=info["item_code"].strip(),
                description=info["description"].strip(),
                detail=info["detail"].strip(),
                url=info["url"].strip(),
            )
