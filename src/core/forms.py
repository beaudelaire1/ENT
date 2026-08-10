from __future__ import annotations

from django import forms


class ScopedModelForm(forms.ModelForm):
    """ModelForm dont les champs de rattachement sont fixés avant la validation.

    Un formulaire n’expose jamais le propriétaire ni le parent d’un objet : la vue les
    attache après ``is_valid()``. Django exclut alors ces champs de ``full_clean()`` et
    ignore toute ``UniqueConstraint`` qui les mentionne ; le doublon n’est plus arrêté
    que par la base et remonte en ``IntegrityError``, donc en erreur 500.

    En passant ``scope={"owner": user}``, la valeur est posée sur l’instance avant la
    validation et retirée des exclusions : la contrainte est vérifiée par le formulaire
    et le doublon s’affiche comme une erreur de saisie ordinaire.
    """

    def __init__(self, *args, scope=None, **kwargs):
        self.scope = dict(scope or {})
        super().__init__(*args, **kwargs)
        for name, value in self.scope.items():
            setattr(self.instance, name, value)

    def _get_validation_exclusions(self):
        return super()._get_validation_exclusions() - set(self.scope)
