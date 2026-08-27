from pathlib import Path


def read_k_file(file_path):
    """
    LS-DYNAのKファイルを読み込む。

    Parameters
    ----------
    file_path : str or Path
        読み込むKファイルのパス

    Returns
    -------
    list[str]
        Kファイルを1行ずつ格納したリスト
    """

    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(
            f"Kファイルが見つかりません: {file_path}"
        )

    if file_path.suffix.lower() != ".k":
        raise ValueError(
            f"Kファイルではありません: {file_path}"
        )

    with file_path.open(
        mode="r",
        encoding="utf-8",
        errors="replace"
    ) as f:
        lines = f.readlines()

    return lines



def extract_keyword_sections(lines, keyword):
    """
    指定したLS-DYNAキーワードのセクションをすべて抽出する。

    例:
        keyword = "ELEMENT_SHELL"
        -> *ELEMENT_SHELL から次の *KEYWORD までを1セクションとして取得

    Parameters
    ----------
    lines : list[str]
        Kファイル全行

    keyword : str
        抽出したいキーワード
        例: "ELEMENT_SHELL", "*ELEMENT_SHELL"

    Returns
    -------
    list[list[str]]
        該当したセクションのリスト
    """

    target = keyword.upper()

    if not target.startswith("*"):
        target = "*" + target

    sections = []
    current_section = None

    for line in lines:

        stripped = line.strip()

        # LS-DYNAキーワード行
        if stripped.startswith("*"):

            # すでに対象セクションを読んでいた場合、
            # 次のキーワードが来たので終了
            if current_section is not None:
                sections.append(current_section)
                current_section = None

            # 新しい対象セクション開始
            if stripped.upper() == target:
                current_section = [line]
                continue

        # 対象セクション内なら保存
        if current_section is not None:
            current_section.append(line)

    # ファイル末尾まで対象セクションだった場合
    if current_section is not None:
        sections.append(current_section)

    return sections



def split_fixed_width(line, width):
    """
    文字列を指定された固定幅で分割する。

    空フィールドも削除せず保持する。

    Parameters
    ----------
    line : str
        分割する文字列

    width : int
        1フィールドの文字数

    Returns
    -------
    list[str]
        固定幅で分割された文字列
    """

    line = line.rstrip("\r\n")

    fields = []

    for i in range(0, len(line), width):
        field = line[i:i + width].strip()
        fields.append(field)

    return fields



def split_fixed_widths(line, widths):
    """
    文字列を指定された複数の固定幅で分割する。

    Parameters
    ----------
    line : str
        分割する文字列

    widths : list[int]
        各フィールドの文字数
        例: [8, 16, 16, 16]

    Returns
    -------
    list[str]
        固定幅で分割された文字列
    """

    line = line.rstrip("\r\n")

    fields = []

    start = 0

    for width in widths:
        end = start + width

        field = line[start:end].strip()

        fields.append(field)

        start = end

    return fields



def parse_element_shell(sections, field_width):

    """
    *ELEMENT_SHELL セクションを固定幅で解析する。

    Parameters
    ----------
    sections : list[list[str]]
        extract_keyword_sections() で取得した
        *ELEMENT_SHELL セクション群

    field_width : int
        1フィールドの文字数

    Returns
    -------
    list[dict]
        ELEMENT情報のリスト

        例:
        {
            "eid": 1,
            "pid": 100,
            "nodes": [437, 32, 1, 3]
        }
    """

    elements = []

    for section in sections:

        for line in section:

            stripped = line.strip()

            # 空行
            if not stripped:
                continue

            # キーワード行
            if stripped.startswith("*"):
                continue

            # コメント行
            if stripped.startswith("$"):
                continue

            # 固定幅で分割
            fields = split_fixed_width(
                line,
                field_width
            )

            # EID, PID, N1 が最低限必要
            if len(fields) < 3:
                continue

            try:
                # 位置を保持したまま取得
                eid = int(fields[0])
                pid = int(fields[1])

                node_ids = []

                # N1 ～ N8
                for field in fields[2:10]:

                    # 空フィールドは無視するが、
                    # fields自体からは削除しない
                    if field == "":
                        continue

                    node_id = int(field)

                    if node_id != 0:
                        node_ids.append(node_id)

            except ValueError:
                continue

            elements.append(
                {
                    "eid": eid,
                    "pid": pid,
                    "nodes": node_ids,
                }
            )

    return elements




def parse_nodes(sections, field_widths):
    """
    *NODE セクションを解析する。

    Parameters
    ----------
    sections : list[list[str]]
        extract_keyword_sections() で取得した
        *NODE セクション群

    field_widths : list[int]
        NID, X, Y, Z のフィールド幅

        例:
        [8, 16, 16, 16]

    Returns
    -------
    dict
        NODE IDをキーとした座標辞書

        例:
        {
            1: {
                "x": 609.683,
                "y": -772.959,
                "z": -4.574
            }
        }
    """

    nodes = {}

    for section in sections:

        for line in section:

            stripped = line.strip()

            if not stripped:
                continue

            if stripped.startswith("*"):
                continue

            if stripped.startswith("$"):
                continue

            fields = split_fixed_widths(
                line,
                field_widths
            )

            try:
                nid = int(fields[0])

                x = float(fields[1])
                y = float(fields[2])
                z = float(fields[3])

            except (ValueError, IndexError):
                continue

            nodes[nid] = {
                "x": x,
                "y": y,
                "z": z,
            }

    return nodes




