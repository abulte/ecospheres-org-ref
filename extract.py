import json
import zipfile

from SPARQLWrapper import SPARQLWrapper, JSON

CRAWL_WIKIDATA = True

ZIP_PATH = "dila_refOrga_admin_Etat_fr.json.zip"
ID_MTE = "05f90b6a-e3d9-4a41-a919-2e2f2d77e517"
ID_GVT = "622a21da-ff27-4f5a-ae74-133aa03d905f"


def get_from_zip():
    data = {"service": []}
    with zipfile.ZipFile(ZIP_PATH, "r") as my_zip:
        for filename in my_zip.namelist():
            if filename.endswith(".json"):
                with my_zip.open(filename) as json_file:
                    json_content = json_file.read().decode("utf-8")
                    data = json.loads(json_content)
                break
    return data["service"]


def get_by_id(_id: str, data: list):
    try:
        return next(d for d in data if d["id"] == _id)
    except StopIteration:
        return {
            "service": _id,
            "nom": _id,
            "hierarchie": []
        }


def get_recursive_hierarchy(obj, data, depth=0):
    hierarchy = []
    if obj.get("hierarchie"):
        for child in obj["hierarchie"]:
            child_obj = get_by_id(child["service"], data)
            hierarchy.append((depth, {
                "id": child["service"],
                "type_hierarchie": child["type_hierarchie"],
                "nom": child_obj["nom"]
            }))
            # Recursively add children of the current child
            hierarchy.extend(
                get_recursive_hierarchy(child_obj, data, depth + 1)
            )
    return hierarchy


def make_graph(data: list, annotation: str = "Service Fils") -> dict:
    """Dict with list of children ids for every id"""
    graph = {}
    for item in data:
        node_id = item["id"]
        children_ids = [
            child["service"]
            for child in item.get("hierarchie", [])
            if child["type_hierarchie"] == annotation
        ]
        if node_id not in graph:
            graph[node_id] = []
        graph[node_id].extend(children_ids)
    return graph


def find_top_level_parent_by_id(_id: str, graph: dict):
    # sanity check, only one parent by id in "Service Fils" graph
    parents = [node for node, children in graph.items() if _id in children]
    assert len(parents) <= 1, "Multiple parents detected"

    parent = next(iter(parents), None)
    # no more parent, top level found
    if parent is None or parent == ID_GVT or parent == ID_MTE:
        return _id
    else:
        return find_top_level_parent_by_id(parent, graph)


def find_top_level_alt_parents_by_id(
        _id: str, alt_graph: dict, sf_graph: dict
):
    parents = [
        node for node, children in alt_graph.items()
        if _id in children and node != ID_MTE
    ]
    return [
        find_top_level_parent_by_id(p, sf_graph) for p in parents
    ]


def indent(level: int) -> str:
    return f"{'  ' * level}-"


def do():
    data = get_from_zip()
    sf_graph = make_graph(data)
    alt_graph = make_graph(data, annotation="Autre hiérarchie")
    mte = get_by_id(ID_MTE, data)
    hierarchy = get_recursive_hierarchy(mte, data)
    for level, item in hierarchy:
        type_hierarchie = (
            item["type_hierarchie"]
            if item["type_hierarchie"] == "Service Fils"
            else f"**{item['type_hierarchie']}**"
        )
        parent = None

        # find top level parent for "autre hiérarchie"
        if item["type_hierarchie"] != "Service Fils":
            parent = find_top_level_parent_by_id(item["id"], sf_graph)
            parent = get_by_id(parent, data)
        current_node = get_by_id(item["id"], data)
        links = entity_links(current_node.get('itm_identifiant'))
        print(
            f"{indent(level)} {item['nom']} :: {type_hierarchie} {links}"
        )
        if parent:
            links = entity_links(parent.get('itm_identifiant'))
            print(f"{indent(level + 1)} PARENT: {parent['nom']} {links}")

        # find alternate parents for level 0
        alt_parents = []
        if level == 0:
            alt_parents = find_top_level_alt_parents_by_id(
                item["id"], alt_graph, sf_graph
            )
        for ap in alt_parents:
            ap_obj = get_by_id(ap, data)
            links = entity_links(ap_obj.get('itm_identifiant'))
            print(f"{indent(level + 1)} ALT PARENT: {ap_obj['nom']} {links}")


def entity_links(id_sp: str | None):
    if not CRAWL_WIKIDATA:
        return
    wd_uri = query_wikidata_by_id_sp(id_sp) if id_sp else None
    dgfr_link = None
    if wd_uri:
        dgfr_id = query_wikidata_by_entity(wd_uri)
        dgfr_link = f"https://www.data.gouv.fr/organizations/{dgfr_id}/" if dgfr_id else ""
    wd_link = f"[wd]({wd_uri})" if wd_uri else ""
    dgfr_link = f"[dgfr]({dgfr_link})" if dgfr_link else ""
    return f"{wd_link} {dgfr_link}"


def query_wikidata_by_id_sp(id_sp: str):
    property_value = f"gouvernement/administration-centrale-ou-ministere_{id_sp}"
    sparql = SPARQLWrapper("https://query.wikidata.org/sparql")
    sparql.setQuery("""
        SELECT?item?itemLabel WHERE {
           ?item wdt:%s "%s".
            SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
        }""" % ("P6671", property_value))
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()

    results = results["results"]["bindings"]  # type: ignore
    assert len(results) <= 1, "Multiple wikidata match on id_sp"
    return results[0]["item"]["value"] if results else None  # type: ignore


def query_wikidata_by_entity(entity_uri: str):
    sparql = SPARQLWrapper("https://query.wikidata.org/sparql")
    entity_id = entity_uri.split("/")[-1]
    sparql.setQuery("""
        SELECT?value WHERE {
            wd:%s wdt:%s?value.
        }""" % (entity_id, "P3206"))
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()

    results = results["results"]["bindings"]  # type: ignore
    assert len(results) <= 1, "Multiple wikidata match on entity_uri"
    return results[0]["value"]["value"] if results else None  # type: ignore


if __name__ == "__main__":
    do()
