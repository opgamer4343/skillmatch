"""
Load questions into the database.

Usage:
    python manage.py load_questions                      # load built-in question bank
    python manage.py load_questions --file questions.json
    python manage.py load_questions --clear              # clear first, then load
"""
import json
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from assessment.models import Question, SkillCategory
from assessment.question_bank import QUESTION_BANK


class Command(BaseCommand):
    help = "Bulk-load questions from the built-in bank or a JSON file."

    def add_arguments(self, parser):
        parser.add_argument("--file", type=str, default=None,
                            help="Path to a JSON file. Defaults to built-in question bank.")
        parser.add_argument("--clear", action="store_true", default=False,
                            help="Delete all existing questions before loading.")

    def handle(self, *args, **options):
        if options["file"]:
            path = Path(options["file"])
            if not path.exists():
                raise CommandError(f"File not found: {options['file']}")
            try:
                questions_data = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                raise CommandError(f"Invalid JSON: {e}")
            self.stdout.write(f"Loaded {len(questions_data)} questions from {options['file']}")
        else:
            questions_data = QUESTION_BANK
            self.stdout.write(f"Using built-in question bank ({len(questions_data)} questions)")

        if options["clear"]:
            q, c = Question.objects.count(), SkillCategory.objects.count()
            Question.objects.all().delete()
            SkillCategory.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Cleared {q} questions and {c} categories."))

        categories_cache = {}
        created = skipped = errors = 0

        for i, item in enumerate(questions_data, start=1):
            missing = [f for f in ("text", "options", "correct_index") if f not in item]
            if missing:
                self.stdout.write(self.style.ERROR(f"  Row {i}: missing {missing} — skipped."))
                errors += 1
                continue
            if not isinstance(item["options"], list) or len(item["options"]) != 4:
                self.stdout.write(self.style.ERROR(f"  Row {i}: options must be list of 4 — skipped."))
                errors += 1
                continue
            try:
                correct = int(item["correct_index"])
                assert correct in (0, 1, 2, 3)
            except Exception:
                self.stdout.write(self.style.ERROR(f"  Row {i}: correct_index must be 0-3 — skipped."))
                errors += 1
                continue

            cat_name = str(item.get("category", "general")).strip().lower()
            cat_type = str(item.get("category_type", "technical")).strip().lower()
            if cat_type not in ("technical", "soft"):
                cat_type = "technical"
            key = (cat_name, cat_type)
            if key not in categories_cache:
                cat, _ = SkillCategory.objects.get_or_create(
                    name=cat_name, defaults={"category_type": cat_type, "weight": 1.00})
                categories_cache[key] = cat

            text = str(item["text"]).strip()
            if Question.objects.filter(category=categories_cache[key], text=text).exists():
                skipped += 1
                continue

            diff = str(item.get("difficulty", "medium")).strip().lower()
            if diff not in ("easy", "medium", "hard"):
                diff = "medium"

            Question.objects.create(
                category=categories_cache[key], text=text, options=item["options"],
                correct_index=correct, difficulty=diff,
                explanation=str(item.get("explanation", "")).strip(),
                is_ai_generated=bool(item.get("is_ai_generated", False)),
            )
            created += 1

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"✓ Created : {created} questions"))
        if skipped:
            self.stdout.write(self.style.WARNING(f"  Skipped : {skipped} duplicates"))
        if errors:
            self.stdout.write(self.style.ERROR(f"  Errors  : {errors} invalid rows"))
        self.stdout.write(f"  Total in DB : {Question.objects.count()} questions")
