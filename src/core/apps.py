from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self):
        from django.db.models.signals import m2m_changed, post_delete, post_save

        from core.queue import enqueue
        from core.search import SOURCES, has_dependents, index_instance, unindex_instance
        from core.tasks import reindex_dependents_task

        def reindex_dependents(instance):
            """Réindexe la descendance en file : l'utilisateur n'a pas à l'attendre.

            L'objet est désigné par son étiquette et sa clé — une tâche reçoit du JSON,
            et un objet sérialisé serait périmé au moment où le worker le lit. Sans
            courtier, `enqueue` exécute sur place plutôt que d'échouer.

            Rien n'est mis en file pour un objet sans descendance : la plupart des
            enregistrements sont dans ce cas, et une file de tâches vides coûterait plus
            que le travail qu'elle porte.
            """
            if has_dependents(instance):
                enqueue(reindex_dependents_task, instance._meta.label, instance.pk)

        def on_save(sender, instance, **kwargs):
            index_instance(instance)
            reindex_dependents(instance)

        def on_delete(sender, instance, **kwargs):
            unindex_instance(instance)

        for key, source in SOURCES.items():
            post_save.connect(on_save, sender=source.model_label, dispatch_uid=f"search_index_{key}", weak=False)
            post_delete.connect(on_delete, sender=source.model_label, dispatch_uid=f"search_unindex_{key}", weak=False)

        # Ces relations modifient le texte projeté sans sauvegarder l'objet indexé.
        from formations.models import Assessment, Competency, UnitCompetency
        from library.models import LibraryItem, Tag

        def reindex_unit_link(sender, instance, **kwargs):
            competency = Competency.objects.filter(pk=instance.competency_id).first()
            if competency is not None:
                index_instance(competency)

        def reindex_m2m_holder(sender, instance, action, **kwargs):
            if action in {"post_add", "post_remove", "post_clear"}:
                index_instance(instance)
                reindex_dependents(instance)

        def reindex_tag(sender, instance, **kwargs):
            reindex_dependents(instance)

        post_save.connect(reindex_unit_link, sender=UnitCompetency, dispatch_uid="search_unit_link_save", weak=False)
        post_delete.connect(
            reindex_unit_link, sender=UnitCompetency, dispatch_uid="search_unit_link_delete", weak=False
        )
        post_save.connect(reindex_tag, sender=Tag, dispatch_uid="search_tag_save", weak=False)
        m2m_changed.connect(
            reindex_m2m_holder,
            sender=LibraryItem.tags.through,
            dispatch_uid="search_library_tags_change",
            weak=False,
        )
        m2m_changed.connect(
            reindex_m2m_holder,
            sender=Assessment.competencies.through,
            dispatch_uid="search_assessment_competencies_change",
            weak=False,
        )
