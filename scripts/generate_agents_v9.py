#!/usr/bin/env python3
"""Generate previews; no hooks/profile installation or trust changes."""
from pathlib import Path
import json
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skill"))
from runtime_v9.core import ROLES, atomic_write
from runtime_v9.install import agent_config
from runtime_v9.comath_adapter import PROFILES, profile_binding, render_profile

def main():
    base = Path(__file__).resolve().parents[1]
    shared = (base/'skill/assets/v9/research-method.md').read_text(encoding='utf-8')
    for role in ROLES:
        atomic_write(base/f'integrations/codex/agents/mp_{role}.toml',agent_config(base/'skill',role))
        # Keep old paths inert so an additive overlay never leaves active-looking rc1 drafts.
        atomic_write(base/f'integrations/comath/prompts/{role}.md',
                     '# Retired rc1 adaptation draft — do not install\n\n'
                     'Portable role names are not CoMath registry IDs. Use ../profiles/ and '
                     'docs/v9/COMATH-PROMPTS.md for the current-service profile mapping and integration path.\n')
    for profile in PROFILES:
        atomic_write(base/f'integrations/comath/profiles/{profile}.md',render_profile(profile,shared))
    atomic_write(base/'integrations/comath/profile-bindings.json',
                 json.dumps({'schema':'mathprove.comath-profile-bindings.v1',
                             'profiles':[profile_binding(profile) for profile in PROFILES]},indent=2)+'\n')
    print('Generated nine portable Codex templates and nine current-service CoMath profile supplements; neither installed.')
if __name__=='__main__':main()
