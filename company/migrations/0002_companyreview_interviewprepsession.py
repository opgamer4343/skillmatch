from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('company', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='CompanyReview',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('overall_rating',       models.PositiveSmallIntegerField(choices=[(1,'★☆☆☆☆'),(2,'★★☆☆☆'),(3,'★★★☆☆'),(4,'★★★★☆'),(5,'★★★★★')])),
                ('process_rating',       models.PositiveSmallIntegerField(choices=[(1,'★☆☆☆☆'),(2,'★★☆☆☆'),(3,'★★★☆☆'),(4,'★★★★☆'),(5,'★★★★★')])),
                ('communication_rating', models.PositiveSmallIntegerField(choices=[(1,'★☆☆☆☆'),(2,'★★☆☆☆'),(3,'★★★☆☆'),(4,'★★★★☆'),(5,'★★★★★')])),
                ('title',        models.CharField(max_length=120)),
                ('body',         models.TextField()),
                ('is_anonymous', models.BooleanField(default=False)),
                ('is_approved',  models.BooleanField(default=True)),
                ('created_at',   models.DateTimeField(auto_now_add=True)),
                ('company',  models.ForeignKey(limit_choices_to={'role':'company'}, on_delete=django.db.models.deletion.CASCADE, related_name='reviews', to=settings.AUTH_USER_MODEL)),
                ('reviewer', models.ForeignKey(limit_choices_to={'role':'student'}, on_delete=django.db.models.deletion.CASCADE, related_name='company_reviews', to=settings.AUTH_USER_MODEL)),
                ('application', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='review', to='company.application')),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.AlterUniqueTogether(
            name='companyreview',
            unique_together={('company', 'reviewer')},
        ),
        migrations.CreateModel(
            name='InterviewPrepSession',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('questions',        models.JSONField(default=list)),
                ('tips',             models.JSONField(default=list)),
                ('company_summary',  models.TextField(blank=True)),
                ('generated_at',     models.DateTimeField(auto_now_add=True)),
                ('interview', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='prep_session', to='company.interview')),
                ('student',   models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='prep_sessions', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]