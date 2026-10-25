"""Offline, user-editable monkey identities with deliberately small safe inputs."""
from __future__ import annotations

PERSONALITIES = {
    'scholar': '学究猴',
    'trickster': '皮猴',
    'sleepy': '困猴',
}
DEFAULT_NAMES = ('猴教授', '猴助教', '猴学博士', '香蕉主任', '摸鱼研究员', '实习猴')


def clean_name(value: object, index: int = 0) -> str:
    """Prevent control/newline markup in bubbles/portraits; no user text execution."""
    fallback = DEFAULT_NAMES[index % len(DEFAULT_NAMES)]
    if not isinstance(value, str):
        return fallback
    cleaned = ''.join(ch for ch in value if ch.isprintable() and ch not in '\u202e\u202d\u200b').strip()
    return cleaned[:12] or fallback


def clean_profiles(raw: object) -> list[dict[str, str]]:
    """Always return six independently editable profiles, even for 1 pet."""
    profiles = []
    values = raw if isinstance(raw, list) else []
    for i in range(6):
        row = values[i] if i < len(values) and isinstance(values[i], dict) else {}
        personality = row.get('personality', 'scholar' if i == 0 else 'trickster' if i % 2 else 'sleepy')
        if not isinstance(personality, str) or personality not in PERSONALITIES:
            personality = 'scholar'
        profiles.append({'name': clean_name(row.get('name'), i), 'personality': personality})
    return profiles
