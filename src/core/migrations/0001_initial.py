import django.contrib.postgres.indexes
import django.contrib.postgres.search
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class PostgresOnlyAddIndex(migrations.AddIndex):
    """Ajoute l’index à l’état du projet, mais ne le crée que sous PostgreSQL.

    L’index GIN n’existe pas sous SQLite, utilisé pour le développement local ; l’état
    reste identique sur les deux moteurs pour que `makemigrations --check` reste vert.
    """

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        if schema_editor.connection.vendor != "postgresql":
            return
        super().database_forwards(app_label, schema_editor, from_state, to_state)

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        if schema_editor.connection.vendor != "postgresql":
            return
        super().database_backwards(app_label, schema_editor, from_state, to_state)


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="SearchEntry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("object_type", models.CharField(max_length=32)),
                ("object_id", models.PositiveBigIntegerField()),
                ("title", models.CharField(max_length=300)),
                ("body", models.TextField(blank=True)),
                ("url", models.CharField(max_length=300)),
                ("search_vector", django.contrib.postgres.search.SearchVectorField(editable=False, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "owner",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="search_entries",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "entrée de recherche",
                "verbose_name_plural": "entrées de recherche",
            },
        ),
        migrations.AddConstraint(
            model_name="searchentry",
            constraint=models.UniqueConstraint(
                fields=("object_type", "object_id"), name="unique_search_entry_per_object"
            ),
        ),
        migrations.AddIndex(
            model_name="searchentry",
            index=models.Index(fields=["owner", "object_type"], name="search_owner_type_idx"),
        ),
        PostgresOnlyAddIndex(
            model_name="searchentry",
            index=django.contrib.postgres.indexes.GinIndex(fields=["search_vector"], name="search_vector_gin_idx"),
        ),
    ]
