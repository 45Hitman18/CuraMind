from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("records", "0002_medicalrecord_review_status_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="medicalrecord",
            name="doctor_notes",
            field=models.TextField(blank=True, default=""),
        ),
    ]
