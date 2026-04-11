from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('company', '0004_remove_companyreview_admin_note_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='interview',
            name='google_calendar_sync_status',
            field=models.CharField(blank=True, default='not_synced', max_length=30),
        ),
        migrations.AddField(
            model_name='interview',
            name='google_event_id',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='interview',
            name='google_meet_link',
            field=models.URLField(blank=True),
        ),
        migrations.AddField(
            model_name='interview',
            name='reminder_1h_sent',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='interview',
            name='reminder_48h_sent',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='interview',
            name='reminder_now_sent',
            field=models.BooleanField(default=False),
        ),
    ]
