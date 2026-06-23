"""
Fixed version: actually attaches the API key this time, and prints the FULL
error response instead of truncating it, since the validation error likely
lists the real valid model names directly.
"""

import requests
import config

CANDIDATE_MODELS = [
    None,
    "turbo",
    "flux-schnell",
    "sdxl",
    "anything",
    "any-dark",
    "unity",
]


def try_model(model_name):
    params = {"width": 256, "height": 256, "nologo": "true"}
    if model_name:
        params["model"] = model_name
    headers = (
        {"Authorization": f"Bearer {config.POLLINATIONS_API_KEY}"}
        if config.POLLINATIONS_API_KEY
        else {}
    )
    url = f"{config.POLLINATIONS_IMAGE_URL}/a%20simple%20red%20circle"

    try:
        response = requests.get(url, params=params, headers=headers, timeout=60)
    except Exception as e:
        return f"ERROR contacting pollinations: {e}"

    if response.ok:
        return f"FREE, WORKS  -> got {len(response.content)} bytes of image data"

    return f"BLOCKED ({response.status_code}) -> {response.text}"


if __name__ == "__main__":
    print("Testing candidate image models against the live pollinations.ai endpoint...\n")
    for model in CANDIDATE_MODELS:
        label = model or "(default, no model param)"
        print(f"--- {label} ---")
        print(try_model(model))
        print()
