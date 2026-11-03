# Gallery photos for the Féminin page (rev 25). The 'On the Pitch'
# section ships hidden on the static site and appears only when this
# model holds published rows — real photos uploaded from the backend.

from django.db import migrations, models
import submissions.models


class Migration(migrations.Migration):

    dependencies = [
        ('submissions', '0006_result'),
    ]

    operations = [
        migrations.CreateModel(
            name='FemininGalleryPhoto',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('caption', models.CharField(blank=True, help_text='Short label shown on the tile, e.g. "Pass & move".', max_length=120)),
                ('alt', models.CharField(blank=True, help_text='Describe the photo for screen readers — who, what, where.', max_length=250, verbose_name='alt text')),
                ('photo', models.ImageField(help_text='JPG, PNG or WebP. Re-encoded on save — hidden metadata is stripped.', storage=submissions.models.FemininGalleryStorage(), upload_to='gallery/feminin/')),
                ('is_published', models.BooleanField(default=False, help_text='The gallery section appears on the Féminin page only when at least one photo is published.', verbose_name='published on website')),
                ('sort', models.PositiveSmallIntegerField(default=0, verbose_name='display order')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Féminin gallery photo',
                'ordering': ['sort', 'id'],
            },
        ),
    ]
