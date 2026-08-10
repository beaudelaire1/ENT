from django.core.management.base import BaseCommand

from core.search import reindex_all


class Command(BaseCommand):
    help = "Reconstruit l’index de recherche global. À exécuter après import_legacy ou une restauration."

    def handle(self, *args, **options):
        counts = reindex_all()
        for key, count in sorted(counts.items()):
            self.stdout.write(f"{key}: {count}")
        self.stdout.write(self.style.SUCCESS(f"Index reconstruit ({sum(counts.values())} entrées)."))
