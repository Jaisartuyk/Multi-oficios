from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_chatroom_chatmessage'),
    ]

    operations = [
        migrations.AddField(
            model_name='professional',
            name='avatar_url',
            field=models.URLField(blank=True, default='', max_length=500, verbose_name='Foto de perfil'),
        ),
        migrations.AddField(
            model_name='jobrequest',
            name='image_url',
            field=models.URLField(blank=True, default='', max_length=500, verbose_name='Foto del problema'),
        ),
        migrations.AddField(
            model_name='recharge',
            name='status',
            field=models.CharField(
                choices=[('APPROVED', 'Aprobada'), ('PENDING', 'Pendiente de revisión'), ('REJECTED', 'Rechazada')],
                default='APPROVED',
                max_length=20,
                verbose_name='Estado',
            ),
        ),
        migrations.AddField(
            model_name='recharge',
            name='receipt_reference',
            field=models.CharField(blank=True, default='', max_length=200, verbose_name='Referencia de pago'),
        ),
        migrations.AddField(
            model_name='recharge',
            name='receipt_url',
            field=models.URLField(blank=True, default='', max_length=500, verbose_name='Foto del comprobante'),
        ),
    ]
