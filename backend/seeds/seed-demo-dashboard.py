#!/usr/bin/env python3
"""Seed demo rows so dashboard screenshots show realistic data.
Direct ORM inserts — does NOT trigger Resend emails."""
import os, sys, random
import pathlib as _pl
sys.path.insert(0, str(_pl.Path(__file__).resolve().parents[1]))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sporting_pearls_backend.settings')
import django
django.setup()

from datetime import datetime, timedelta, timezone as tz
from submissions.models import Fixture, FormSubmission

FormSubmission.objects.all().delete()
Fixture.objects.all().delete()

now = datetime.now(tz.utc)
def days_ago(n, hour=10, minute=24):
    return (now - timedelta(days=n)).replace(hour=hour, minute=minute, second=random.randint(0,59), microsecond=0)

ROWS = [
    ('form-01-player-registration', 'Amina Hassan', 'amina.hassan@gmail.com',
     {'player_name': 'Amina Hassan', 'dob': '2011-03-14', 'age_group': 'U13',
      'position': 'CM', 'previous_club': 'Mtwapa Stars', 'parent_name': 'Fatma Hassan',
      'parent_phone': '+254 712 445 190', 'consent': 'yes'}, 'reviewed', 'sent', 9),
    ('form-02-trial-application', 'Kito Juma', 'kito.juma@outlook.com',
     {'name': 'Kito Juma', 'email': 'kito.juma@outlook.com', 'phone': '+254 733 210 884',
      'age': '15', 'position': 'RAM', 'current_school': 'Mombasa Academy',
      'preferred_trial_date': '2026-10-12'}, 'new', 'sent', 8),
    ('contact-general-enquiry', 'Grace Wanjiku', 'gwanjiku@yahoo.com',
     {'name': 'Grace Wanjiku', 'email': 'gwanjiku@yahoo.com', 'topic': 'Programmes & Registration',
      'message': 'Hello, I would like to know the monthly fees for the U9 foundation squad and whether training happens during school holidays.'},
     'new', 'sent', 8),
    ('form-04-volunteer-application', 'Peter Otieno', 'peter.otieno@gmail.com',
     {'name': 'Peter Otieno', 'email': 'peter.otieno@gmail.com', 'phone': '+254 720 118 402',
      'role': 'Goalkeeper coach (part-time)', 'availability': 'Tuesday & Thursday evenings, Saturday mornings',
      'experience': '2 seasons with Kisauni FC youth setup'}, 'new', 'sent', 6),
    ('form-06-sponsorship-partnership', 'Neema Beverages Ltd', 'partnerships@neemabev.co.ke',
     {'organisation': 'Neema Beverages Ltd', 'contact_person': 'Salim Mwakalinga',
      'email': 'partnerships@neemabev.co.ke', 'package': 'Bronze — kit branding',
      'message': 'We would like to discuss a junior kit sponsorship for the 2027 season.'},
     'reviewed', 'sent', 5),
    ('form-03-parent-association', 'Rehema Said', 'rehema.said@gmail.com',
     {'name': 'Rehema Said', 'email': 'rehema.said@gmail.com', 'child_name': 'Amb. Said',
      'child_squad': 'Féminin', 'how_help': 'Organising travel logistics for away fixtures'},
     'new', 'sent', 4),
    ('form-05-coach-technical-staff', 'Daniel Kimani', 'd.kimani.coach@gmail.com',
     {'name': 'Daniel Kimani', 'email': 'd.kimani.coach@gmail.com', 'role_applied': 'Head coach — U15',
      'qualifications': 'CAF C License, 6 years youth coaching', 'available_from': '2026-11-01'},
     'new', 'sent', 3),
    ('newsletter-subscription', 'Joseph Mwangi', 'j.mwangi@icloud.com',
     {'email': 'j.mwangi@icloud.com'}, 'new', 'sent', 3),
    ('partnership-application', 'Mtwapa Community Trust', 'info@mtwapatrust.or.ke',
     {'organisation': 'Mtwapa Community Trust', 'email': 'info@mtwapatrust.or.ke',
      'partnership_type': 'Community programme', 'message': 'We run a holiday camp and would love to co-host a coaching week with your U13s.'},
     'new', 'sent', 2),
    ('form-10-safeguarding-report', 'Anonymous', '',
     {'concern': 'Report submitted through the safeguarding channel — details withheld in demo data.',
      'anonymous': 'yes'}, 'archived', 'sent', 2),
    ('form-02-trial-application', 'Victor Chitechi', 'victor.c@gmail.com',
     {'name': 'Victor Chitechi', 'email': 'victor.c@gmail.com', 'phone': '+254 799 003 521',
      'age': '17', 'position': 'ST', 'current_school': 'Kilifi Boys',
      'preferred_trial_date': '2026-10-19'}, 'new', 'pending', 0),
    ('form-01-player-registration', 'Zainab Kibwana', 'z.kibwana@gmail.com',
     {'player_name': 'Zainab Kibwana', 'dob': '2009-08-02', 'age_group': 'U17',
      'position': 'GK', 'previous_club': 'Bamburi Queens', 'parent_name': 'Mariam Kibwana',
      'parent_phone': '+254 714 882 306', 'consent': 'yes'}, 'new', 'sent', 0),
]

for slug, name, email, payload, status, est, d in ROWS:
    obj = FormSubmission.objects.create(
        ref=f'SP-{"NEWS" if "newsletter" in slug else {"contact-general-enquiry":"GENQ","form-01-player-registration":"REG","form-02-trial-application":"TRIAL","form-03-parent-association":"PARENT","form-04-volunteer-application":"VOL","form-05-coach-technical-staff":"COACH","form-06-sponsorship-partnership":"SPON","form-10-safeguarding-report":"SAFE","partnership-application":"PART"}[slug]}-{(now - timedelta(days=d)).strftime("%Y%m%d")}-{random.randint(0x1000,0xFFFF):04X}',
        form_slug=slug, name=name, email=email, payload=payload,
        email_status=est, email_error='' if est == 'sent' else 'queued for retry',
        ip=f'197.232.{random.randint(1,254)}.{random.randint(1,254)}',
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/128.0',
        status=status)
    FormSubmission.objects.filter(pk=obj.pk).update(created_at=days_ago(d))

Fixture.objects.create(team='Sporting Pearls U17', opponent='Coast United Academy',
    competition='Coast Premier League — U17', date=now.date() + timedelta(days=9),
    kickoff='15:00', venue='Mbaraki Sports Club', home_away='home', is_published=True)
Fixture.objects.create(team='SP Féminin', opponent='Kilifi Queens',
    competition='Women Division 2', date=now.date() + timedelta(days=16),
    kickoff='13:30', venue='Kilifi Stadium', home_away='away', is_published=True)
Fixture.objects.create(team='Sporting Pearls U13', opponent='Mombasa Sports Academy',
    competition='Junior League — U13', date=now.date() + timedelta(days=23),
    kickoff='', venue='Pearls Ground, Mtwapa', home_away='home', is_published=False)

print(f'seeded {FormSubmission.objects.count()} submissions + {Fixture.objects.count()} fixtures')
