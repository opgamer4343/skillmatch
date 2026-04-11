from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [("accounts", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="Notification",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("notif_type", models.CharField(choices=[("otp", "OTP Verification"), ("interview_scheduled", "Interview Scheduled"), ("interview_accepted", "Interview Accepted"), ("interview_reschedule_requested", "Interview Reschedule Requested"), ("interview_cancelled", "Interview Cancelled"), ("interview_reminder", "Interview Reminder"), ("application_received", "Application Received")], max_length=50)),
                ("title", models.CharField(max_length=255)),
                ("body", models.TextField()),
                ("is_read", models.BooleanField(default=False)),
                ("email_sent", models.BooleanField(default=False)),
                ("interview_id", models.PositiveIntegerField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("recipient", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="notifications", to="accounts.user")),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
