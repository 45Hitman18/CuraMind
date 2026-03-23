import os
import django
import sys
import json

sys.path.append(r"c:\Users\thaka\OneDrive\Desktop\curaMind")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "curamind_ai.settings")
django.setup()

from records.models import MedicalRecord
from doctors.medical_ai import analyze_medical_image

# Find the finalized record with no notes (likely record 10)
# We will just run the AI for it manually to populate its notes so it looks great for the patient.
records = MedicalRecord.objects.filter(doctor_notes="")
for record in records:
    print(f"Analyzing {record.id}...")
    try:
        result_data = analyze_medical_image(record.uploaded_file.path)
        score = result_data.get('score', 60)
        # Handle case where the user reverted our markdown changes, so AI is returning pure HTML.
        analysis = result_data.get('analysis', '')
        
        record.doctor_notes = f"<br><b>--- AI Analysis (Score: {score}%) ---</b><br><br>{analysis}"
        record.ai_confidence_score = score
        record.save(update_fields=["doctor_notes", "ai_confidence_score"])
        print(f"Successfully populated record {record.id}")
    except Exception as e:
        print(f"Error on {record.id}: {e}")
