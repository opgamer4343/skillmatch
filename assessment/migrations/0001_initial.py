from django.db import migrations, models
import django.db.models.deletion
import django.core.validators


class Migration(migrations.Migration):
    initial = True

    dependencies = [("accounts", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="SkillCategory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100, unique=True)),
                ("category_type", models.CharField(choices=[("technical", "Technical"), ("soft", "Soft")], max_length=20)),
                ("weight", models.DecimalField(decimal_places=2, default=1.0, max_digits=4)),
                ("description", models.TextField(blank=True)),
            ],
            options={"verbose_name_plural": "Skill categories", "ordering": ["category_type", "name"]},
        ),
        migrations.CreateModel(
            name="AssessmentAttempt",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("attempt_number", models.PositiveIntegerField()),
                ("started_at", models.DateTimeField(auto_now_add=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("technical_score", models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ("soft_score", models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ("overall_score", models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ("score_band", models.CharField(blank=True, choices=[("beginner", "Beginner"), ("foundation", "Foundation"), ("intermediate", "Intermediate"), ("strong", "Strong"), ("expert", "Expert")], max_length=20)),
                ("status", models.CharField(choices=[("started", "Started"), ("completed", "Completed"), ("expired", "Expired"), ("abandoned", "Abandoned")], default="started", max_length=20)),
                ("strengths", models.JSONField(blank=True, default=list)),
                ("weak_areas", models.JSONField(blank=True, default=list)),
                ("job_readiness_message", models.TextField(blank=True)),
                ("improvement_priority", models.TextField(blank=True)),
                ("student", models.ForeignKey(limit_choices_to={"role": "student"}, on_delete=django.db.models.deletion.CASCADE, related_name="assessment_attempts", to="accounts.user")),
            ],
            options={"ordering": ["-started_at"], "unique_together": {("student", "attempt_number")}},
        ),
        migrations.CreateModel(
            name="CourseRecommendation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255)),
                ("provider", models.CharField(max_length=255)),
                ("url", models.URLField()),
                ("platform", models.CharField(max_length=100)),
                ("duration_hours", models.DecimalField(decimal_places=2, default=0, max_digits=6)),
                ("reason", models.TextField(blank=True)),
                ("priority", models.PositiveSmallIntegerField(default=1)),
                ("is_completed", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("student", models.ForeignKey(limit_choices_to={"role": "student"}, on_delete=django.db.models.deletion.CASCADE, related_name="course_recommendations", to="accounts.user")),
            ],
            options={"ordering": ["priority", "-created_at"]},
        ),
        migrations.CreateModel(
            name="StudentCV",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("file", models.FileField(upload_to="cvs/")),
                ("source", models.CharField(choices=[("uploaded", "Uploaded"), ("ai_generated", "AI Generated")], default="uploaded", max_length=20)),
                ("uploaded_at", models.DateTimeField(auto_now=True)),
                ("user", models.OneToOneField(limit_choices_to={"role": "student"}, on_delete=django.db.models.deletion.CASCADE, related_name="student_cv", to="accounts.user")),
            ],
        ),
        migrations.CreateModel(
            name="Question",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("text", models.TextField()),
                ("options", models.JSONField(default=list)),
                ("correct_index", models.PositiveSmallIntegerField(validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(3)])),
                ("difficulty", models.CharField(choices=[("easy", "Easy"), ("medium", "Medium"), ("hard", "Hard")], default="medium", max_length=20)),
                ("explanation", models.TextField(blank=True)),
                ("is_ai_generated", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("category", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="questions", to="assessment.skillcategory")),
            ],
            options={"ordering": ["category__name", "id"]},
        ),
        migrations.CreateModel(
            name="AssessmentAnswer",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("selected_answer", models.PositiveSmallIntegerField(blank=True, null=True, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(3)])),
                ("is_correct", models.BooleanField(default=False)),
                ("time_taken_seconds", models.PositiveSmallIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("attempt", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="answers", to="assessment.assessmentattempt")),
                ("question", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="answers", to="assessment.question")),
            ],
            options={"unique_together": {("attempt", "question")}},
        ),
    ]
