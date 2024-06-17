# ecospheres-org-ref

Analyse le [Référentiel de l'organisation administrative de l'Etat](https://www.data.gouv.fr/fr/datasets/referentiel-de-lorganisation-administrative-de-letat/) dans le contexte du MTE.

## Run

```
make download
python generate.py > out.md
```

## Structure et interpréation des données

Structure simplifiée :

```json
[
    {
        "nom" : "Ministère de l'Intérieur et des Outre-mer",
        "id" : "fa33b07a-3f71-46d4-b682-569c9faf211e",
        "hierarchie" : [{
        "type_hierarchie" : "Service Fils",
        "service" : "a4b2caf2-d1f5-4839-8992-55ca5f86d439"
        }, {
        "type_hierarchie" : "Autre hiérarchie",
        "service" : "bdd256b8-1ec3-4d4d-afa7-54b2344b45ac"
        }]
    }
]
```

Les liens "Service Fils" sont 1-N, i.e. un Service Fils ne peut avoir qu'un seul parent, et un parent plusieurs enfants. Interprétation : tutelle ou rattachement principal.

Les liens "Autre hiérarchie" sont N-N, i.e. un service rattaché par ce lien peut avoir plusieurs parents, et un parent plusieurs enfants. Interprétaion : tutelle ou rattachement secondaire.

Exemple : DGEC est un "Service Fils" de Ministère de l'Économie, des Finances et de la Souveraineté industrielle et numérique. La tutelle principale de la DGEC est le MEF. DGEC est rattaché par "Autre hiérarchie" au MTE. La tutelle secondaire de la DGEC est le MTE.

> La direction générale de l'Énergie et du Climat (DGEC) est une direction d'administration centrale française qui définit et met en œuvre la politique énergétique de la France et d'approvisionnement en matières premières minérales. Elle est sous l'autorité du Ministère de l’Économie et des Finances avec une tutelle partiellement partagée avec le ministère de la Transition écologique.

## Fonctionnement du script

Le script parcourt le référentiel en partant du MTE. Il produit un fichier markdown représentant son organigramme.

La hiérarchie est affichée sous forme de listes, avec une indentation représentant le niveau d'imbrication. Chaque élément de la liste est qualifié "Service Fils" ou "Autre hiérarchie".

Pour les enfants directs du MTE, on cherche si un autre service de premier niveau a un héritier dont "Autre hiérarchie" pointe vers cet élément. Ceci permet de détecter d'éventuelles tutelles partagées, par exemple pour la DGALN.

NB : on définit un service de premier niveau comme l'élément le plus haut dans la hiérarchie des "Service Fils" sous l'entité "Gouvernement", ce qui correspond au niveau des ministères ou SPM.

```markdown
- Direction générale de l'aménagement, du logement et de la nature (DGALN) :: Service Fils
  - ALT PARENT: Ministère de l'Économie, des Finances et de la Souveraineté industrielle et numérique
  - ALT PARENT: Ministère du Travail, de la Santé et des Solidarités
```

Pour les éléments qualifiés par "Autre hiérarchie", on cherche, quelque soit leur niveau, leur parent principal, i.e. un élément de premier niveau qui porte cet élément via une succession de "Service Fils". Ceci permet de détecter la tutelle principale, par exemple pour la DGEC.

```
- Direction générale de l'énergie et du climat (DGEC) :: Autre hiérarchie
  - PARENT: Ministère de l'Économie, des Finances et de la Souveraineté industrielle et numérique
```

## Exploitation

Le référentiel permet de représenter l'organigramme du MTE. Son exploitation dans un traitement automatisé est toutefois délicate, notamment en ce qui concerne le rapprochement avec des organisations data.gouv.fr. En effet, il n'existe pas d'identifiant universellement partagé des services.

Pistes d'exploitation :
- Matching flou sur le nom, à tester en fonction de la source (nom d'organisation INSPIRE au moissonnage ?).
- Wikidata porte un [identifiant service-public.fr](https://www.wikidata.org/wiki/Property:P6671) qu'on peut tenter de faire correspondre via `itm_identifiant`. Reste à voir comment construire ou retrouver la valeur complète de cette propriété depuis `itm_identifiant: 172165`. A priori, vu le référentiel exploité, `https://lannuaire.service-public.fr/gouvernement/administration-centrale-ou-ministere_{itm_identifiant}` devrait marcher.
- Wikidata porte également :
    - Le [SIREN de l'organisation](https://www.wikidata.org/wiki/Property:P1616), ce qui pourrait permettre de remonter à data.gouv.fr via le SIRET.
    - L'[id de l'organisation sur data.gouv.fr](https://www.wikidata.org/wiki/Property:P3206) pour certaines organisations — [voir les travaux ici](https://github.com/pachevalier/organisations-data-gouv).
