"""Import the six squads + players from player_seed.json (exported from the
website's the-squad.js roster). Idempotent — re-running updates in place:
squads are keyed by `key`, players by `ref` (the code printed on the paper
data form), so it is safe to run again after editing the seed.

Usage: python manage.py import_roster [path-to-json]
"""
import json
import os

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from submissions.models import Player, Squad


class Command(BaseCommand):
    help = 'Import squads + players from player_seed.json into the dashboard'

    def add_arguments(self, parser):
        parser.add_argument('path', nargs='?',
                            default=str(settings.BASE_DIR / 'player_seed.json'))

    def handle(self, *args, **opts):
        path = opts['path']
        if not os.path.exists(path):
            raise CommandError(f'file not found: {path}')
        with open(path, encoding='utf-8') as fh:
            try:
                data = json.load(fh)
            except json.JSONDecodeError as exc:
                raise CommandError(f'invalid JSON in {path}: {exc}')

        n_squads = n_players = 0
        for s in data.get('squads', []):
            squad, created = Squad.objects.update_or_create(
                key=s['key'],
                defaults=dict(
                    code=s['code'],
                    label=s['label'],
                    formation=s.get('form', '4-3-3'),
                    accent=s.get('accent', '#f59d1e'),
                    sort=s.get('sort', 0),
                ),
            )
            n_squads += 1
            self.stdout.write(f'  {"+" if created else "~"} {squad.key}: {squad.label}')
            for i, p in enumerate(s.get('players', [])):
                # numeric fields are null-able: blank strings (hand-edited
                # seeds) must coerce to None, never crash the import
                age = p.get('age')
                if age == '' or age is None:
                    age = None
                no = p.get('no')
                if no == '' or no is None:
                    no = None
                Player.objects.update_or_create(
                    ref=p['ref'],
                    defaults=dict(
                        squad=squad,
                        number=no,
                        first_name=p['first'],
                        last_name=p['last'],
                        position=p.get('pos', ''),
                        age=age,
                        height_m=p.get('ht', ''),
                        foot=p.get('foot', ''),
                        motto=p.get('motto', ''),
                        photo_url=p.get('photo_url', ''),
                        is_captain=bool(p.get('captain')),
                        is_published=True,      # imported roster = what the site shows today
                        pitch_order=p.get('pitch_order', i + 1),
                    ),
                )
                n_players += 1

        self.stdout.write(self.style.SUCCESS(
            f'OK: {n_squads} squads, {n_players} players imported/updated'))