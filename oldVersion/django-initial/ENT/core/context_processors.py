
from profiles.models import StudentProfile

def student_header(request):
    try:
        student = StudentProfile.objects.first()
    except Exception:
        student = None
    return {'header_student': student}
