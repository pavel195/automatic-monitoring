from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('companies', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='VkBot',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('community_token', models.CharField(max_length=255, unique=True, verbose_name='Токен сообщества')),
                ('community_id', models.CharField(blank=True, max_length=64, verbose_name='ID сообщества')),
                ('community_name', models.CharField(blank=True, max_length=255, verbose_name='Название сообщества')),
                ('status', models.CharField(choices=[('active', 'Активен'), ('inactive', 'Неактивен'), ('error', 'Ошибка')], default='inactive', max_length=32, verbose_name='Статус')),
                ('last_error', models.TextField(blank=True, verbose_name='Последняя ошибка')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Дата обновления')),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='vk_bots', to='companies.company', verbose_name='Компания')),
            ],
            options={
                'verbose_name': 'VK бот',
                'verbose_name_plural': 'VK боты',
                'ordering': ['-created_at'],
            },
        ),
    ]
