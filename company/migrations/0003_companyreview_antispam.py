from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('company', '0002_companyreview_interviewprepsession'),
    ]

    operations = [
        # Add interview_experience field
        migrations.AddField(
            model_name='companyreview',
            name='interview_experience',
            field=models.TextField(
                default='',
                help_text='What was the interview process like?'
            ),
            preserve_default=False,
        ),
        # Add would_recommend field
        migrations.AddField(
            model_name='companyreview',
            name='would_recommend',
            field=models.BooleanField(default=True),
        ),
        # Add spam detection fields
        migrations.AddField(
            model_name='companyreview',
            name='spam_score',
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='companyreview',
            name='spam_flags',
            field=models.JSONField(default=list),
        ),
        migrations.AddField(
            model_name='companyreview',
            name='flagged_by_admin',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='companyreview',
            name='admin_note',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='companyreview',
            name='ip_address',
            field=models.GenericIPAddressField(blank=True, null=True),
        ),
        # Change is_approved default to False (requires moderation)
        migrations.AlterField(
            model_name='companyreview',
            name='is_approved',
            field=models.BooleanField(default=False),
        ),
    ]