# Local catalogs

| Runtime file under `meter/data` | Contents |
|---|---|
| `skill_labels.json` | Skill IDs and names; tested rune selections |
| `buff_labels.json` | Buff/debuff IDs, names and stack limits |
| `npc_labels.json` | Monster/NPC template IDs, names and boss flags |
| `dungeon_labels.json` | Map/location names and boss-to-location relationships |
| `periodic_skills.json` | Exact periodic-effect classifications, such as damage DoTs |

There is one active entry per ID or relationship key. Skill names are shared
by damage, healing and cast views; they are not duplicated into separate tables.
The additional `pets.json` and `ui_en.json` contain the checklist and UI translations.

Runtime catalogs contain only operational fields. Source history, observation
statistics, unresolved research IDs and exact confirmation evidence are retained
in the developer edition under `development/catalogs`. The live meter does not
read that directory. Credits and existing license notices are centralised in
[THIRD-PARTY-NOTICES.md](../THIRD-PARTY-NOTICES.md) and `licenses`.

The catalog combines sourced mappings with own checks, corrections, extensions
and evidenced discoveries. An entry can be originally sourced and later
independently confirmed. Numeric derivations remain distinguishable from exact
tests; imported names are not automatically counted as independent confirmations.

The pet checklist is deliberately limited to the existing dungeon and special
pets and the shop/chest list. It does not include the full open-world, island
or Abyss farming catalog. Shop/chest records are listed by those acquisition
sources; this does not establish that a pet can never have another source.
