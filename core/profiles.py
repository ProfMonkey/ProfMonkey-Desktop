"""Offline, user-editable monkey identities with deliberately small safe inputs."""
from __future__ import annotations

PERSONALITIES = {
    # Keep legacy keys stable so existing saves and story records still load.
    'scholar': '教授猴',
    'captain': '探险猴',
    'inventor': '编程猴',
    'sleepy': '摸鱼猴',
    'trickster': '干饭猴',
    'shy': '酷帅猴',
}
DEFAULT_NAMES = ('猴教授', '小探险家', '代码猴', '摸鱼研究员', '香蕉主任', '酷帅猴')


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
        personality = row.get('personality', tuple(PERSONALITIES)[i])
        if not isinstance(personality, str) or personality not in PERSONALITIES:
            personality = 'scholar'
        profiles.append({'name': clean_name(row.get('name'), i), 'personality': personality})
    return profiles
