# Generated migration for adding company fields to tickets

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tickets', '0006_channelmessage_is_comment_and_more'),
        ('companies', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='channelmessage',
            name='company',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='messages', to='companies.company', verbose_name='Компания'),
        ),
        migrations.AddField(
            model_name='ticket',
            name='company',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='tickets', to='companies.company', verbose_name='Компания'),
        ),
        migrations.AlterField(
            model_name='ticket',
            name='category',
            field=models.CharField(choices=[('complaint', 'Жалоба'), ('praise', 'Благодарность'), ('request', 'Запрос информации'), ('incident', 'Инцидент'), ('suggestion', 'Предложение'), ('payment', 'Вопрос по оплате')], default='request', max_length=32),
        ),
    ]

