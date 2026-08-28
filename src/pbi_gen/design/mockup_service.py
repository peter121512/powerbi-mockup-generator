"""OpenAI image mockup service for the conversational design phase (Stage 13).

- `ImageAdapter` — interface; `OpenAIImageAdapter` (gpt-image-1) reads the key
  from the OPENAI_API_KEY env var (never hard-coded/committed); `StubImageAdapter`
  is deterministic for tests (renders a labelled placeholder PNG, no network).
- `DashboardMockupService.create_mockup` / `.revise_mockup` assemble a
  Power-BI-realistic prompt from the session's request, DataContext, inferred
  KPIs, template inventory and current design choices, then produce a
  `MockupRevision` (image bytes + prompt + delta).

Image generation is the fast design loop; it must produce a realistic preview of
a *future Power BI report* (realistic density, filters, nav, typography), not an
unconstrained graphic.
"""

from __future__ import annotations

import base64
import os
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:  # avoid import cycle
    from .session import DashboardDesignSession


# ─────────────────────────────────────────────────────────────────────────────
# Revision artifact
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class MockupRevision:
    """One image mockup revision."""

    revision_id: str
    revision_number: int
    prompt: str
    image_path: str = ""
    image_bytes: Optional[bytes] = None
    instruction: str = ""  # the user instruction that produced this revision
    delta_summary: str = ""  # what changed vs the previous revision
    adapter: str = ""
    error: str = ""  # populated if image generation failed (design loop continues)

    def to_dict(self) -> dict:
        return {
            "revision_id": self.revision_id,
            "revision_number": self.revision_number,
            "instruction": self.instruction,
            "delta_summary": self.delta_summary,
            "image_path": self.image_path,
            "adapter": self.adapter,
            "prompt_chars": len(self.prompt),
            "error": self.error,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Adapter interface + implementations
# ─────────────────────────────────────────────────────────────────────────────


class ImageAdapter(ABC):
    """Generates an image (PNG bytes) from a text prompt."""

    @abstractmethod
    def generate(self, prompt: str, *, size: str = "1536x1024") -> bytes: ...

    @property
    @abstractmethod
    def name(self) -> str: ...


class OpenAIImageAdapter(ImageAdapter):
    """OpenAI image generation (gpt-image-1). Key from OPENAI_API_KEY env var."""

    def __init__(self, model: str = "gpt-image-1", api_key: Optional[str] = None):
        self._model = model
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self._api_key:
            raise RuntimeError(
                "OPENAI_API_KEY not set. Set it in the environment; do not hard-code it."
            )
        self._client = None

    def _get_client(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(api_key=self._api_key)
        return self._client

    @property
    def name(self) -> str:
        return f"openai:{self._model}"

    def generate(self, prompt: str, *, size: str = "1536x1024") -> bytes:
        client = self._get_client()
        result = client.images.generate(model=self._model, prompt=prompt, size=size)
        b64 = result.data[0].b64_json
        if not b64:
            # Some responses return a URL instead of b64.
            url = getattr(result.data[0], "url", None)
            if url:
                import requests
                return requests.get(url, timeout=60).content
            raise RuntimeError("OpenAI image response contained no image data")
        return base64.b64decode(b64)


class StubImageAdapter(ImageAdapter):
    """Deterministic offline adapter for tests — renders a labelled placeholder PNG.

    No network. The image encodes the revision number + a prompt hash so tests
    can assert determinism and that revisions differ.
    """

    def __init__(self):
        self._counter = 0

    @property
    def name(self) -> str:
        return "stub"

    def generate(self, prompt: str, *, size: str = "1536x1024") -> bytes:
        self._counter += 1
        # Minimal valid 1x1 PNG with the prompt hash baked into a tEXt chunk so
        # different prompts yield different bytes deterministically.
        import zlib
        import struct

        def _chunk(ctype: bytes, data: bytes) -> bytes:
            return (struct.pack(">I", len(data)) + ctype + data
                    + struct.pack(">I", zlib.crc32(ctype + data) & 0xFFFFFFFF))

        sig = b"\x89PNG\r\n\x1a\n"
        ihdr = _chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
        raw = b"\x00\x00\x00\x00"  # one black pixel row
        idat = _chunk(b"IDAT", zlib.compress(raw))
        # Deterministic text metadata from the prompt.
        digest = str(abs(hash(prompt)) % (10 ** 12)).encode()
        text = _chunk(b"tEXt", b"prompt-hash\x00" + digest)
        iend = _chunk(b"IEND", b"")
        return sig + ihdr + text + idat + iend


# ─────────────────────────────────────────────────────────────────────────────
# Prompt assembly + service
# ─────────────────────────────────────────────────────────────────────────────

_TEMPLATE_VOCAB = (
    "Proven Power BI template vocabulary to prefer where it fits the request: "
    "KPI cards (premium_kpi), area/line trend with Monthly/Quarterly/Annual toggle "
    "(premium_trend), horizontal bar (premium_bar), column (premium_column), donut "
    "with centre KPI (premium_donut), data table (premium_table), waterfall/bridge "
    "(premium_waterfall), radial gauge (premium_gauge), key-insights narrative panel "
    "(premium_insights)."
)

_STYLE = (
    "Enterprise executive Power BI report preview, dark navy theme (#0f1623 canvas, "
    "#151d2e panels, #1e293b borders), restrained boardroom aesthetic, crisp Segoe UI "
    "typography, subtle blue/purple/teal accents. 1280x720 report canvas: a 150px left "
    "navigation rail with outline icons + labels, a page title top-left, filter slicers "
    "top-right, a top KPI row, a hero row (wide chart + companion), and a bottom row of "
    "three visuals. Realistic Power BI visual density, containers, headers and controls — "
    "it must look like a real, buildable Power BI report, not abstract art. No emoji."
)


class DashboardMockupService:
    """Creates and revises dashboard image mockups."""

    def __init__(self, adapter: Optional[ImageAdapter] = None, output_dir: Optional[Path] = None):
        self.adapter = adapter or StubImageAdapter()
        self.output_dir = Path(output_dir) if output_dir else None

    # ── prompt assembly ──────────────────────────────────────────────────────

    def build_prompt(self, session: "DashboardDesignSession", *, is_revision: bool,
                     instruction: str = "") -> str:
        ctx = session.data_context
        parts: list[str] = [_STYLE, ""]
        parts.append(f"Business request: {session.original_request}")
        if session.audience:
            parts.append(f"Audience: {session.audience}")
        if ctx:
            parts.append("Data context:\n" + ctx.summary_for_prompt())
        if session.inferred_kpis:
            parts.append("Headline KPIs to feature: " + ", ".join(session.inferred_kpis[:6]))
        if session.design_preferences:
            prefs = "; ".join(f"{k}={v}" for k, v in session.design_preferences.items())
            parts.append(f"Design preferences: {prefs}")

        if not is_revision:
            parts.append(
                _TEMPLATE_VOCAB
                + " For this FIRST mockup, prefer these proven templates/layout where "
                "they satisfy the request, to maximise downstream build fidelity."
            )
        else:
            # Revision: preserve prior design, change only what was asked.
            prev = session.current_revision
            parts.append(
                "This is a REVISION of the existing mockup. Preserve every unchanged "
                "aspect of the previous design (layout, visuals, colours, filters) and "
                "apply ONLY this change: " + instruction
            )
            if prev and prev.delta_summary:
                parts.append(f"Previous change history hint: {prev.delta_summary}")
            parts.append(_TEMPLATE_VOCAB + " You MAY deviate from these templates if the "
                         "user's instruction calls for it, while keeping it a realistic, "
                         "buildable Power BI report.")

        parts.append(
            "Only depict controls/interactions Power BI can plausibly implement "
            "(slicers, cross-filtering, page navigation, tooltips). Do not depict "
            "impossible 3D/animated/real-time behaviours."
        )
        return "\n\n".join(p for p in parts if p)

    # ── generation ─────────────────────────────────────────────────────────────

    def _save(self, revision_id: str, image_bytes: bytes) -> str:
        if not self.output_dir:
            return ""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        path = self.output_dir / f"{revision_id}.png"
        path.write_bytes(image_bytes)
        return str(path)

    def _generate(self, prompt: str) -> tuple[Optional[bytes], str]:
        """Generate an image, returning (bytes, error). On adapter failure the
        design loop continues with a recorded error rather than crashing."""
        try:
            return self.adapter.generate(prompt), ""
        except Exception as e:  # rate limit / network / quota — non-fatal to design
            return None, f"{type(e).__name__}: {e}"

    def create_mockup(self, session: "DashboardDesignSession") -> MockupRevision:
        prompt = self.build_prompt(session, is_revision=False)
        image, err = self._generate(prompt)
        rid = f"rev_{uuid.uuid4().hex[:8]}"
        rev = MockupRevision(
            revision_id=rid, revision_number=1, prompt=prompt,
            image_bytes=image, instruction=session.original_request,
            delta_summary="initial mockup", adapter=self.adapter.name, error=err,
        )
        if image is not None:
            rev.image_path = self._save(rid, image)
        return rev

    def revise_mockup(self, session: "DashboardDesignSession", user_instruction: str) -> MockupRevision:
        prompt = self.build_prompt(session, is_revision=True, instruction=user_instruction)
        image, err = self._generate(prompt)
        rid = f"rev_{uuid.uuid4().hex[:8]}"
        prev_num = session.current_revision.revision_number if session.current_revision else 0
        rev = MockupRevision(
            revision_id=rid, revision_number=prev_num + 1, prompt=prompt,
            image_bytes=image, instruction=user_instruction,
            delta_summary=user_instruction, adapter=self.adapter.name, error=err,
        )
        if image is not None:
            rev.image_path = self._save(rid, image)
        return rev


def default_adapter(output_dir: Optional[Path] = None) -> ImageAdapter:
    """Return the OpenAI adapter if a key is present, else the deterministic stub."""
    if os.environ.get("OPENAI_API_KEY"):
        return OpenAIImageAdapter()
    return StubImageAdapter()
