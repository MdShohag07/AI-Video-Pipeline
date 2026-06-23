"""
Step 3: turn each scene's keywords into a matching real stock photo from
Pexels — genuinely free and stable. (We switched away from pollinations.ai's
AI image generation after finding its free tier only trickles in enough
credit for about one image every so often — nowhere near enough for
producing several images per video.)
"""

from pathlib import Path
from typing import List

import requests

import config


def _search_pexels(query: str) -> list:
    headers = {"Authorization": config.PEXELS_API_KEY}
    params = {"query": query, "per_page": 1, "orientation": "portrait"}

    response = requests.get(config.PEXELS_SEARCH_URL, headers=headers, params=params, timeout=30)
    if not response.ok:
        raise RuntimeError(f"Pexels search failed ({response.status_code}): {response.text[:300]}")

    return response.json().get("photos", [])


def generate_images(scene_prompts: List[str], out_dir: str) -> List[str]:
    """
    Finds one matching free stock photo per entry in `scene_prompts` and
    saves them as scene_0.jpg, scene_1.jpg, ... inside `out_dir`.

    Returns the list of saved file paths, in the same order as the prompts.
    """
    if not config.PEXELS_API_KEY:
        raise RuntimeError(
            "No PEXELS_API_KEY found. Get a free key (no payment info needed) at "
            "https://www.pexels.com/api/ and add it to your .env file as:\n"
            "  PEXELS_API_KEY=your_key_here"
        )

    Path(out_dir).mkdir(parents=True, exist_ok=True)
    saved_paths = []

    for i, prompt in enumerate(scene_prompts):
        photos = _search_pexels(prompt)

        if not photos:
            # the full AI-style prompt may be too specific for a stock library —
            # retry with just the first couple of words as a broader search
            broader_query = " ".join(prompt.split()[:2])
            photos = _search_pexels(broader_query)

        if not photos:
            raise RuntimeError(
                f"No stock photo found for scene {i} ('{prompt}'). "
                "Try rewording that scene's image_prompt to be more literal/searchable."
            )

        image_url = photos[0]["src"]["large2x"]
        image_response = requests.get(image_url, timeout=60)
        image_response.raise_for_status()

        out_path = str(Path(out_dir) / f"scene_{i}.jpg")
        with open(out_path, "wb") as f:
            f.write(image_response.content)

        saved_paths.append(out_path)
        print(f"  scene {i + 1}/{len(scene_prompts)} image saved -> {out_path}")

    return saved_paths


if __name__ == "__main__":
    # Quick manual test: python image_gen.py
    test_prompts = [
        "rice fields sunrise",
        "Dhaka street rickshaw",
    ]
    paths = generate_images(test_prompts, "test_images")
    print(paths)
