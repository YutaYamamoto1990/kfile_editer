from pathlib import Path

from k_parser import (
    read_k_file,
    extract_keyword_sections,
    parse_element_shell,
    parse_nodes,
)

from node_utils import (
    filter_elements_by_pid,
    collect_node_ids,
    get_target_nodes,
)


def main():

    # -------------------------
    # 設定
    # -------------------------
    input_dir = Path("input")

    target_pid = 100

    element_field_width = 8
    node_field_widths = [8, 16, 16, 16]

    # -------------------------
    # Kファイル取得
    # -------------------------
    k_files = list(input_dir.glob("*.k"))

    if not k_files:
        print("inputフォルダにKファイルがありません。")
        return

    k_file = k_files[0]

    print(f"読み込みファイル: {k_file}")

    # -------------------------
    # Kファイル読み込み
    # -------------------------
    lines = read_k_file(k_file)

    print(f"総行数: {len(lines)}")

    # -------------------------
    # ELEMENT_SHELL取得
    # -------------------------
    element_sections = extract_keyword_sections(
        lines,
        "ELEMENT_SHELL"
    )

    elements = parse_element_shell(
        element_sections,
        field_width=element_field_width
    )

    print(f"全ELEMENT数: {len(elements)}")

    # -------------------------
    # PIDでELEMENT抽出
    # -------------------------
    target_elements = filter_elements_by_pid(
        elements,
        target_pid
    )

    print()
    print(f"対象PID: {target_pid}")
    print(f"対象ELEMENT数: {len(target_elements)}")

    # -------------------------
    # 対象NODE ID取得
    # -------------------------
    node_ids = collect_node_ids(
        target_elements
    )

    print(f"使用NODE ID数: {len(node_ids)}")

    # -------------------------
    # NODEセクション取得
    # -------------------------
    node_sections = extract_keyword_sections(
        lines,
        "NODE"
    )

    nodes = parse_nodes(
        node_sections,
        field_widths=node_field_widths
    )

    print(f"全NODE数: {len(nodes)}")

    # -------------------------
    # 対象NODEの座標取得
    # -------------------------
    target_nodes = get_target_nodes(
        node_ids,
        nodes
    )

    print(f"座標取得できた対象NODE数: {len(target_nodes)}")

    # -------------------------
    # NODE不足チェック
    # -------------------------
    missing_node_ids = node_ids - set(target_nodes.keys())

    if missing_node_ids:
        print()
        print(
            f"WARNING: 座標が見つからないNODEが "
            f"{len(missing_node_ids)} 個あります。"
        )

        print("先頭20件:")

        for nid in sorted(missing_node_ids)[:20]:
            print(nid)

    else:
        print("対象NODEはすべて座標取得できました。")

    # -------------------------
    # 確認表示
    # -------------------------
    print()
    print("--- 先頭10 対象NODE ---")

    for nid in sorted(target_nodes)[:10]:

        node = target_nodes[nid]

        print(
            f"NID: {nid:8d}  "
            f"X: {node['x']:16.6f}  "
            f"Y: {node['y']:16.6f}  "
            f"Z: {node['z']:16.6f}"
        )


if __name__ == "__main__":
    main()