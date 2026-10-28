"""v0.21 narrative page is offline and backed by all 6 original avatars."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def test_six_hidden_plot_page_and_home_entry():
    site=(ROOT/'site/secrets.html').read_text(encoding='utf-8')
    home=(ROOT/'site/index.html').read_text(encoding='utf-8')
    assert 'href="secrets.html"' in home
    assert '<script>' in site
    assert 'http://' not in site and 'https://' not in site
    for token in ('消失的第七张收据','第七道猴影','银河发来404',
                  '猴山睡眠总罢工','实验室的零号按钮','最后一张反对票'):
        assert token in site
    for key in ('scholar','trickster','sleepy','inventor','captain','shy'):
        assert (ROOT/'assets/characters_v020'/f'{key}.svg').is_file()
