# Generated migration for companies app

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Company',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, verbose_name='Название компании')),
                ('description', models.TextField(blank=True, verbose_name='Описание')),
                ('status', models.CharField(choices=[('pending', 'На модерации'), ('active', 'Активна'), ('inactive', 'Неактивна'), ('suspended', 'Приостановлена')], default='pending', max_length=32, verbose_name='Статус')),
                ('contact_email', models.EmailField(max_length=254, verbose_name='Контактный email')),
                ('contact_phone', models.CharField(blank=True, max_length=32, verbose_name='Контактный телефон')),
                ('default_ack_sla_minutes', models.IntegerField(default=30, verbose_name='SLA подтверждения (минуты)')),
                ('default_resolve_sla_minutes', models.IntegerField(default=720, verbose_name='SLA решения (минуты)')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Дата обновления')),
                ('approved_at', models.DateTimeField(blank=True, null=True, verbose_name='Дата одобрения')),
                ('approved_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='approved_companies', to=settings.AUTH_USER_MODEL, verbose_name='Одобрено пользователем')),
            ],
            options={
                'verbose_name': 'Компания',
                'verbose_name_plural': 'Компании',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(choices=[('operator', 'Оператор'), ('company_admin', 'Администратор компании'), ('superadmin', 'Супер-администратор')], default='operator', max_length=32, verbose_name='Роль')),
                ('phone', models.CharField(blank=True, max_length=32, verbose_name='Телефон')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Дата обновления')),
                ('company', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='users', to='companies.company', verbose_name='Компания')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='profile', to=settings.AUTH_USER_MODEL, verbose_name='Пользователь')),
            ],
            options={
                'verbose_name': 'Профиль пользователя',
                'verbose_name_plural': 'Профили пользователей',
            },
        ),
        migrations.CreateModel(
            name='TelegramBot',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('bot_token', models.CharField(max_length=255, unique=True, verbose_name='Токен бота')),
                ('bot_username', models.CharField(blank=True, max_length=128, verbose_name='Username бота')),
                ('chat_ids', models.JSONField(blank=True, default=list, verbose_name='ID чатов для мониторинга')),
                ('discussion_chat_ids', models.JSONField(blank=True, default=list, verbose_name='ID чатов для обсуждений')),
                ('allow_direct', models.BooleanField(default=False, verbose_name='Разрешить личные сообщения')),
                ('status', models.CharField(choices=[('active', 'Активен'), ('inactive', 'Неактивен'), ('error', 'Ошибка')], default='inactive', max_length=32, verbose_name='Статус')),
                ('last_error', models.TextField(blank=True, verbose_name='Последняя ошибка')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Дата обновления')),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bots', to='companies.company', verbose_name='Компания')),
            ],
            options={
                'verbose_name': 'Telegram бот',
                'verbose_name_plural': 'Telegram боты',
                'ordering': ['-created_at'],
            },
        ),
    ]

