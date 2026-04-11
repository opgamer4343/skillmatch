from django.db import migrations, models
import django.db.models.deletion
import django.core.validators
from django.conf import settings


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.CreateModel(
            name='Internship',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
                ('department', models.CharField(blank=True, max_length=255)),
                ('description', models.TextField()),
                ('work_type', models.CharField(choices=[('remote', 'Remote'), ('onsite', 'Onsite'), ('hybrid', 'Hybrid')], max_length=20)),
                ('duration', models.CharField(max_length=100)),
                ('required_skills', models.JSONField(blank=True, default=list)),
                ('stipend', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, validators=[django.core.validators.MinValueValidator(0)])),
                ('deadline', models.DateField(blank=True, null=True)),
                ('status', models.CharField(choices=[('active', 'Active'), ('draft', 'Draft'), ('closed', 'Closed')], default='draft', max_length=20)),
                ('required_score_threshold', models.PositiveSmallIntegerField(default=0, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)])),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('company', models.ForeignKey(limit_choices_to={'role': 'company'}, on_delete=django.db.models.deletion.CASCADE, related_name='internships', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='Application',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cover_letter', models.TextField(blank=True)),
                ('status', models.CharField(choices=[('applied', 'Applied'), ('review', 'Review'), ('interview', 'Interview'), ('offer', 'Offer'), ('rejected', 'Rejected')], default='applied', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('internship', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='applications', to='company.internship')),
                ('applicant', models.ForeignKey(limit_choices_to={'role': 'student'}, on_delete=django.db.models.deletion.CASCADE, related_name='applications', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created_at'], 'unique_together': {('internship', 'applicant')}},
        ),
        migrations.CreateModel(
            name='Interview',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('interview_date', models.DateTimeField()),
                ('interview_type', models.CharField(choices=[('video', 'Video'), ('phone', 'Phone'), ('onsite', 'Onsite')], max_length=20)),
                ('meeting_link', models.URLField(blank=True)),
                ('location', models.CharField(blank=True, max_length=255)),
                ('notes', models.TextField(blank=True)),
                ('status', models.CharField(choices=[('scheduled', 'Scheduled'), ('accepted', 'Accepted'), ('reschedule_requested', 'Reschedule Requested'), ('completed', 'Completed'), ('cancelled', 'Cancelled')], default='scheduled', max_length=30)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('application', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='interview', to='company.application')),
                ('scheduled_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='scheduled_interviews', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['interview_date']},
        ),
    ]
