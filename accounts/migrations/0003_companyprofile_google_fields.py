from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_alter_user_managers_alter_user_groups_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='companyprofile',
            name='google_access_token',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='companyprofile',
            name='google_account_connected_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='companyprofile',
            name='google_email',
            field=models.EmailField(blank=True, max_length=254, null=True),
        ),
        migrations.AddField(
            model_name='companyprofile',
            name='google_refresh_token',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='companyprofile',
            name='google_scopes',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='companyprofile',
            name='google_token_uri',
            field=models.URLField(blank=True, default='https://oauth2.googleapis.com/token', null=True),
        ),
    ]
