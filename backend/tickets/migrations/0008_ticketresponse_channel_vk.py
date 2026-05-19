from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tickets', '0007_add_company_fields'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ticketresponse',
            name='channel',
            field=models.CharField(
                choices=[('telegram', 'Telegram'), ('vk', 'VKontakte'), ('internal', 'Внутренняя')],
                default='telegram',
                max_length=32,
            ),
        ),
    ]
