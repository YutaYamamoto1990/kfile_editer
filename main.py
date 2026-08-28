from pathlib import Path

from k_parser import (
    read_k_file,
    extract_keyword_sections,
    parse_element_shell,
    parse_nodes,
)

from node_utils import (
    filter_elements_by_pids,
    collect_node_ids,
    get_target_nodes,
)

from mass_utils import (
    optimize_ramp_distribution,
)

from k_writer import write_element_mass

def main():

    # -------------------------
    # 設定
    # -------------------------
    input_dir = Path("input")

    target_pids = {
        103, 109, 110, 111, 112, 113, 114, 115, 116, 117, 118, 119, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 204, 205, 206
    }
    element_field_width = 8
    node_field_widths = [8, 16, 16, 16]

    # -------------------------
    # 質量条件
    # -------------------------

    additional_mass = 0.329245057

    target_cg_x = -8.698453325
    target_cg_z = 250.7169486

    # 正規化座標上のCG誤差許容値
    cg_tolerance = 1.0e-4

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
    target_elements = filter_elements_by_pids(
        elements,
        target_pids
    )

    print()
    print(f"対象PID: {target_pids}")
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


    # -------------------------
    # ランプ質量最適化
    # -------------------------

    result = optimize_ramp_distribution(
        target_nodes,
        total_mass=additional_mass,
        target_cg_x=target_cg_x,
        target_cg_z=target_cg_z,
        cg_tolerance=cg_tolerance,
    )

    nodal_masses = result["nodal_masses"]

    write_result = write_element_mass(
        nodal_masses,
        output_path="output/element_mass.k",
        start_eid=9000000,
    )

    # -------------------------
    # 結果表示
    # -------------------------

    print()
    print("--- 2D RAMP MASS RESULT ---")

    print(
        f"指定総質量 : "
        f"{additional_mass:.6f}"
    )

    print(
        f"計算総質量 : "
        f"{result['total_mass']:.6f}"
    )

    print()

    print(
        f"指定重心 X : "
        f"{target_cg_x:.6f}"
    )

    print(
        f"計算重心 X : "
        f"{result['cg_x']:.6f}"
    )

    print()

    print(
        f"指定重心 Z : "
        f"{target_cg_z:.6f}"
    )

    print(
        f"計算重心 Z : "
        f"{result['cg_z']:.6f}"
    )

    print()

    print(
        f"CG誤差     : "
        f"{result['cg_error']:.10e}"
    )

    print(
        f"許容値内   : "
        f"{result['cg_condition_met']}"
    )

    print()

    print(
        f"theta      : "
        f"{result['theta_deg']:.6f} deg"
    )

    print(
        f"d          : "
        f"{result['d']:.10f}"
    )

    print()

    print(
        f"最小質量   : "
        f"{result['min_mass']:.10e}"
    )

    print(
        f"最大質量   : "
        f"{result['max_mass']:.10e}"
    )

    print(
        f"質量ありNODE : "
        f"{result['positive_node_count']}"
    )

    print(
        f"質量0 NODE   : "
        f"{result['zero_mass_node_count']}"
    )

    print(
        f"全NODE数     : "
        f"{result['total_node_count']}"
    )

    print()
    print("--- NODE座標範囲 ---")

    print(
        f"X範囲 : "
        f"{result['x_min']:.6f} "
        f"～ {result['x_max']:.6f}"
    )

    print(
        f"Z範囲 : "
        f"{result['z_min']:.6f} "
        f"～ {result['z_max']:.6f}"
    )

    print()

    print(
        f"X重心誤差 : "
        f"{result['cg_error_x']:.6f}"
    )

    print(
        f"Z重心誤差 : "
        f"{result['cg_error_z']:.6f}"
    )


if __name__ == "__main__":
    main()