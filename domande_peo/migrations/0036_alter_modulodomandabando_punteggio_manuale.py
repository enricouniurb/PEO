# Generated by Django 3.2.2 on 2021-09-20 13:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('domande_peo', '0035_modulodomandabando_punteggio_manuale'),
    ]

    operations = [
        migrations.AlterField(
            model_name='modulodomandabando',
            name='punteggio_manuale',
            field=models.FloatField(blank=True, help_text='punteggio manuale attribuito dalla commissione in alternativa al punteggio automatico', null=True),
        ),
    ]
