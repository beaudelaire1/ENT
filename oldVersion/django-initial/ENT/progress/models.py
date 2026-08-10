from django.db import models
from django.conf import settings

from curriculum.models import Course


class Progress(models.Model):
    """Tracks a learner's progress on a specific course."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='progresses')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='progresses')
    estimated_hours = models.FloatField(default=0.0)
    actual_hours = models.FloatField(default=0.0)
    MASTERY_LEVEL_CHOICES = [
        (1, '1 - Non abordé'),
        (2, '2 - Découvert'),
        (3, '3 - En cours'),
        (4, '4 - Acquis'),
        (5, '5 - Maîtrisé'),
    ]
    mastery_level = models.IntegerField(choices=MASTERY_LEVEL_CHOICES, default=1)
    comments = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'course')
        verbose_name_plural = 'Progressions'

    def __str__(self) -> str:
        return f"{self.user} – {self.course} (niveau {self.mastery_level})"
