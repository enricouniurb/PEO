# Generated by Django 2.0.3 on 2018-06-06 09:34

from django.db import migrations


class Migration(migrations.Migration):
    
    atomic = False

    dependencies = [
        ('gestione_risorse_umane', '0013_auto_20180604_1507'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='AffinitaOrganizzative',
            new_name='AffinitaOrganizzativa',
        ),
    ]
