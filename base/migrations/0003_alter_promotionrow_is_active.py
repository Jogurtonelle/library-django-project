# Generated by Django 5.0.4 on 2024-05-14 20:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0002_bookcopy_is_reservasion_ready_bookcopy_is_reserved'),
    ]

    operations = [
        migrations.AlterField(
            model_name='promotionrow',
            name='is_active',
            field=models.BooleanField(default=False),
        ),
    ]