def filter_elements_by_pid(elements, target_pid):
    """
    指定PIDのELEMENTだけを抽出する。

    Parameters
    ----------
    elements : list[dict]
        parse_element_shell() で作成したELEMENT一覧

    target_pid : int
        抽出したいPID

    Returns
    -------
    list[dict]
        指定PIDに属するELEMENT一覧
    """

    target_elements = []

    for element in elements:
        if element["pid"] == target_pid:
            target_elements.append(element)

    return target_elements


def collect_node_ids(elements):
    """
    ELEMENT一覧から使用されているNODE IDを重複なしで取得する。

    Parameters
    ----------
    elements : list[dict]
        ELEMENT一覧

    Returns
    -------
    set[int]
        重複なしのNODE ID集合
    """

    node_ids = set()

    for element in elements:
        for node_id in element["nodes"]:
            node_ids.add(node_id)

    return node_ids



def get_target_nodes(node_ids, nodes):
    """
    NODE ID集合から、対応する座標情報を取得する。

    Parameters
    ----------
    node_ids : set[int]
        対象NODE ID集合

    nodes : dict
        全NODE情報

    Returns
    -------
    dict
        対象NODEのみの辞書
    """

    target_nodes = {}

    for nid in node_ids:
        if nid in nodes:
            target_nodes[nid] = nodes[nid]

    return target_nodes




