# Generated by Django 2.0.13 on 2019-06-28 08:20

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('gestione_peo', '0085_auto_20190628_1017'),
    ]

    operations = [
        migrations.RenameField(
            model_name='moduloinserimentocampi',
            old_name='tipo',
            new_name='field_type',
        ),
    ]
