# Generated by Django 3.2.6 on 2021-08-25 13:38

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('wallets', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='wallet',
            old_name='is_favarite',
            new_name='is_favorite',
        ),
    ]